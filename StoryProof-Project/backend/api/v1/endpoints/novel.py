"""
소설/회차 관리 API 엔드포인트
- 소설 CRUD
- 회차 CRUD
- 소설 목록 조회 (페이지네이션)
"""

from sqlalchemy import text
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
import chardet
from pydantic import BaseModel
from threading import Thread
from backend.db.session import get_db
from backend.core.security import get_current_user
from backend.db.models import Novel, Chapter, User, StoryboardStatus
from backend.worker.tasks import process_chapter_storyboard
from backend.schemas.novel_schema import (
    NovelCreate, NovelUpdate, NovelResponse, NovelListResponse,
    ChapterCreate, ChapterUpdate, ChapterResponse, ChapterListResponse
)


router = APIRouter()


# ===== 스키마 =====

class StoryboardProgressResponse(BaseModel):
    """스토리보드 처리 진행 상황"""
    chapter_id: int
    status: str  # pending, processing, completed, failed
    progress: int  # 0-100
    message: Optional[str] = None  # 진행 메시지
    error: Optional[str] = None
    
    class Config:
        from_attributes = True


async def load_txt_from_upload(file: UploadFile) -> str:
    """TXT 파일 로드 (자동 인코딩 감지)"""
    raw_data = await file.read()
    
    # 인코딩 감지
    result = chardet.detect(raw_data)
    detected_encoding = result['encoding']
    confidence = result['confidence']
    
    if confidence > 0.7 and detected_encoding:
        try:
            text = raw_data.decode(detected_encoding)
            return text
        except Exception:
            pass
            
    encodings = ['utf-8', 'cp949', 'euc-kr', 'utf-16', 'latin-1']
    
    for encoding in encodings:
        try:
            text = raw_data.decode(encoding)
            return text
        except (UnicodeDecodeError, UnicodeError, LookupError):
            continue

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"지원하지 않는 인코딩입니다. (시도한 인코딩: {encodings})"
    )

# ===== 소설 합치기 =====
class MergeRequest(BaseModel):
    source_ids: List[int]
    target_id: int

@router.patch("/{novel_id}/merge-contents")
async def merge_novel_contents(
    novel_id: int, 
    request: MergeRequest,
    db: Session = Depends(get_db)
):
    try:
        # 1. 순서 결정 (target_id를 가장 앞으로)
        ordered_ids = []
        if request.target_id:
            ordered_ids.append(request.target_id)
        if request.source_ids:
            for s_id in request.source_ids:
                if s_id not in ordered_ids:
                    ordered_ids.append(s_id)

        # 2. 데이터 조회
        chapters = db.query(Chapter).filter(
            Chapter.id.in_(ordered_ids),
            Chapter.novel_id == novel_id
        ).all()
        ch_map = {c.id: c for c in chapters}

        if not ch_map:
            raise HTTPException(status_code=404, detail="병합할 데이터를 찾을 수 없습니다.")

        # 3. 본문 조립 (순서대로)
        combined_content_list = []
        for ch_id in ordered_ids:
            ch = ch_map.get(ch_id)
            if ch and ch.content:
                # 분석 엔진이 장 구분을 명확히 할 수 있도록 헤더 삽입
                header = f"\n\n### {ch.title if ch.title else f'제 {ch.chapter_number}화'} ###\n"
                combined_content_list.append(header + ch.content)

        final_content = "".join(combined_content_list).strip()

        # 4. 새 회차 생성
        last_ch = db.query(Chapter).filter(Chapter.novel_id == novel_id).order_by(Chapter.chapter_number.desc()).first()
        new_num = (last_ch.chapter_number + 1) if last_ch else 1

        new_chapter = Chapter(
            novel_id=novel_id,
            chapter_number=new_num,
            title="통합 분석본",
            content=final_content,
            word_count=len(final_content.split()),
            storyboard_status="PENDING"  # 분석 대기 상태로 시작
        )
        db.add(new_chapter)
        db.flush()

        # 5. 기존 데이터 삭제 (재분석을 할 것이므로 분석 기록도 삭제)
        db.execute(text("DELETE FROM analyses WHERE chapter_id IN :ids"), {"ids": tuple(ordered_ids)})
        db.execute(text("DELETE FROM chapters WHERE id IN :ids"), {"ids": tuple(ordered_ids)})

        db.commit()

        # 6. [핵심] 찾은 분석 함수 호출 (백그라운드 스레드 실행)
        # API 응답을 즉시 보내기 위해 별도 스레드에서 분석을 가동합니다.
        try:
            thread = Thread(
                target=process_chapter_storyboard,
                args=(novel_id, new_chapter.id),
                daemon=False
            )
            thread.start()
            print(f"🚀 새 회차(ID: {new_chapter.id})에 대한 통합 재분석 스레드 시작")
        except Exception as e:
            print(f"⚠️ 분석 스레드 가동 실패: {str(e)}")

        return {
            "status": "success", 
            "new_id": new_chapter.id,
            "message": "병합이 완료되었으며, 통합된 내용으로 새로운 분석을 시작했습니다."
        }

    except Exception as e:
        db.rollback()
        print(f"❌ 오류 발생: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))



# ===== 소설 생성 =====

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_novel(
    novel_data: NovelCreate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    새 소설 생성
    
    Args:
        novel_data: 소설 정보 (title, description, genre)
        current_user: 현재 인증된 사용자
        db: 데이터베이스 세션
        
    Returns:
        NovelResponse: 생성된 소설 정보
    """
    novel = Novel(
        title=novel_data.title,
        description=novel_data.description,
        genre=novel_data.genre,
        custom_prompt=novel_data.custom_prompt,
        author_id=current_user.id,
        is_public=novel_data.is_public
    )
    db.add(novel)
    db.commit()
    db.refresh(novel)
    return novel


# ===== 소설 목록 조회 =====

@router.get("/")
async def get_novels(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    search: Optional[str] = None,
    genre: Optional[str] = None,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    소설 목록 조회 (페이지네이션)
    
    Args:
        skip: 건너뛸 항목 수
        limit: 가져올 항목 수
        search: 검색어 (제목, 설명)
        genre: 장르 필터
        current_user: 현재 인증된 사용자
        db: 데이터베이스 세션
        
    Returns:
        NovelListResponse: 소설 목록 및 총 개수
    """
    query = db.query(Novel).filter(Novel.author_id == current_user.id)
    
    if search:
        query = query.filter(
            (Novel.title.ilike(f"%{search}%")) | 
            (Novel.description.ilike(f"%{search}%"))
        )
        
    if genre:
        query = query.filter(Novel.genre == genre)
        
    total = query.count()
    novels = query.offset(skip).limit(limit).all()
    
    return NovelListResponse(total=total, novels=novels)


# ===== 소설 상세 조회 =====

@router.get("/{novel_id}")
async def get_novel(
    # novel_id: int,
    # current_user = Depends(get_current_user),
    # db: Session = Depends(get_db)
):
    """
    소설 상세 정보 조회
    
    Args:
        novel_id: 소설 ID
        current_user: 현재 인증된 사용자
        db: 데이터베이스 세션
        
    Returns:
        NovelResponse: 소설 상세 정보
        
    Raises:
        HTTPException: 소설을 찾을 수 없거나 권한이 없는 경우
    """
    # TODO: 소설 조회
    # TODO: 권한 확인 (작가 본인 또는 공개 소설)
    pass


# ===== 소설 수정 =====

@router.put("/{novel_id}")
async def update_novel(
    novel_id: int,
    novel_update: NovelUpdate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not novel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="소설을 찾을 수 없습니다."
        )
        
    if novel.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="권한이 없습니다."
        )
        
    if novel_update.title is not None:
        novel.title = novel_update.title
    if novel_update.description is not None:
        novel.description = novel_update.description
    if novel_update.genre is not None:
        novel.genre = novel_update.genre
    if novel_update.custom_prompt is not None:
        novel.custom_prompt = novel_update.custom_prompt
    if novel_update.is_public is not None:
        novel.is_public = novel_update.is_public
    if novel_update.is_completed is not None:
        novel.is_completed = novel_update.is_completed
        
    db.commit()
    db.refresh(novel)
    return novel


# ===== 소설 삭제 =====

@router.delete("/{novel_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_novel(
    # novel_id: int,
    # current_user = Depends(get_current_user),
    # db: Session = Depends(get_db)
):
    """
    소설 삭제
    
    Args:
        novel_id: 소설 ID
        current_user: 현재 인증된 사용자
        db: 데이터베이스 세션
        
    Raises:
        HTTPException: 소설을 찾을 수 없거나 권한이 없는 경우
    """
    # TODO: 소설 조회
    # TODO: 권한 확인 (작가 본인만)
    # TODO: 소설 삭제 (연관된 회차, 분석 결과도 함께 삭제)
    pass


# ===== 새로운 소설 or 새로운 회차 생성 =====

@router.post("/{novel_id}/chapters", status_code=status.HTTP_201_CREATED)
async def create_chapter(
    # novel_id: int,
    # chapter_data: ChapterCreate,
    # current_user = Depends(get_current_user),
    # db: Session = Depends(get_db)
):
    """
    새 회차 생성
    
    Args:
        novel_id: 소설 ID
        chapter_data: 회차 정보 (chapter_number, title, content)
        current_user: 현재 인증된 사용자
        db: 데이터베이스 세션
        
    Returns:
        ChapterResponse: 생성된 회차 정보
        
    Raises:
        HTTPException: 소설을 찾을 수 없거나 권한이 없는 경우
    """
    # TODO: 소설 조회 및 권한 확인
    # TODO: 회차 번호 중복 확인
    # TODO: 단어 수 계산
    # TODO: 회차 생성
    pass





@router.get("/{novel_id}/chapters")
async def get_chapters(
    novel_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    소설의 회차 목록 조회
    
    Args:
        novel_id: 소설 ID
        current_user: 현재 인증된 사용자
        db: 데이터베이스 세션
        
    Returns:
        List[ChapterResponse]: 회차 목록
        
    Raises:
        HTTPException: 소설을 찾을 수 없거나 권한이 없는 경우
    """
    novel = db.query(Novel).filter(Novel.id == novel_id).first()
    if not novel:
        raise HTTPException(status_code=404, detail="Novel not found")
        
    # Check permission (author or admin)
    if novel.author_id != current_user.id and not current_user.is_admin:
         raise HTTPException(status_code=403, detail="Not authorized")

    chapters = db.query(Chapter).filter(Chapter.novel_id == novel_id).order_by(Chapter.chapter_number).all()
    return chapters


# ===== 회차 상세 조회 =====

@router.get("/{novel_id}/chapters/{chapter_id}")
async def get_chapter(
    novel_id: int,
    chapter_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    회차 상세 정보 조회
    
    Args:
        novel_id: 소설 ID
        chapter_id: 회차 ID
        current_user: 현재 인증된 사용자
        db: 데이터베이스 세션
        
    Returns:
        ChapterResponse: 회차 상세 정보
        
    Raises:
        HTTPException: 회차를 찾을 수 없거나 권한이 없는 경우
    """
    try:
        # 1. 소설 조회 (권한 확인용)
        novel = db.query(Novel).filter(Novel.id == novel_id).first()
        if not novel:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="소설을 찾을 수 없습니다."
            )

        # 2. 회차 조회
        chapter = db.query(Chapter).filter(
            Chapter.id == chapter_id,
            Chapter.novel_id == novel_id
        ).first()
        
        if not chapter:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="회차를 찾을 수 없습니다."
            )
            
        # 3. 권한 확인 (작가 본인, 관리자, 또는 공개 소설)
        is_owner = novel.author_id == current_user.id
        is_admin = current_user.is_admin
        
        if not is_owner and not is_admin:
            # 공개 소설이 아니면 접근 불가
            if not novel.is_public:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="권한이 없습니다."
                )
        
        return chapter
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"서버 오류가 발생했습니다: {str(e)}"
        )


# ===== 회차 수정 =====

@router.put("/{novel_id}/chapters/{chapter_id}")
async def update_chapter(
    novel_id: int,
    chapter_id: int,
    chapter_update: ChapterUpdate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    회차 정보 수정
    
    Args:
        novel_id: 소설 ID
        chapter_id: 회차 ID
        chapter_update: 수정할 회차 정보
        current_user: 현재 인증된 사용자
        db: 데이터베이스 세션
        
    Returns:
        ChapterResponse: 수정된 회차 정보
        
    Raises:
        HTTPException: 회차를 찾을 수 없거나 권한이 없는 경우
    """
    # 1. 소설 조회 (권한 확인용)
    novel = db.query(Novel).filter(Novel.id == novel_id).first()
    if not novel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="소설을 찾을 수 없습니다."
        )
        
    # 2. 권한 확인 (작가 본인만 수정 가능)
    if novel.author_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="권한이 없습니다."
        )

    # 3. 회차 조회
    chapter = db.query(Chapter).filter(
        Chapter.id == chapter_id,
        Chapter.novel_id == novel_id
    ).first()
    
    if not chapter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="회차를 찾을 수 없습니다."
        )
        
    # 4. 회차 정보 업데이트
    if chapter_update.title is not None:
        chapter.title = chapter_update.title
        
    if chapter_update.content is not None:
        chapter.content = chapter_update.content
        # 단어 수 재계산
        chapter.word_count = len(chapter_update.content.split())
        
    if chapter_update.chapter_number is not None:
        # 회차 번호 중복 확인 (다른 회차와 겹치는지)
        if chapter_update.chapter_number != chapter.chapter_number:
            existing = db.query(Chapter).filter(
                Chapter.novel_id == novel_id,
                Chapter.chapter_number == chapter_update.chapter_number
            ).first()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"이미 존재하는 회차 번호입니다: {chapter_update.chapter_number}화"
                )
        chapter.chapter_number = chapter_update.chapter_number
    
    db.commit()
    db.refresh(chapter)
    
    return chapter


# ===== 회차 삭제 =====

@router.delete("/{novel_id}/chapters/{chapter_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chapter(
    novel_id: int,
    chapter_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    회차 삭제
    
    Args:
        novel_id: 소설 ID
        chapter_id: 회차 ID
        current_user: 현재 인증된 사용자
        db: 데이터베이스 세션
        
    Raises:
        HTTPException: 회차를 찾을 수 없거나 권한이 없는 경우
    """
    # 1. 소설 조회 (권한 확인용)
    novel = db.query(Novel).filter(Novel.id == novel_id).first()
    if not novel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="소설을 찾을 수 없습니다."
        )
        
    # 2. 권한 확인 (작가 본인만 삭제 가능)
    if novel.author_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="권한이 없습니다."
        )

    # 3. 회차 조회
    chapter = db.query(Chapter).filter(
        Chapter.id == chapter_id,
        Chapter.novel_id == novel_id
    ).first()
    
    if not chapter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="회차를 찾을 수 없습니다."
        )
        
    # 4. 회차 삭제
    db.delete(chapter)
    db.commit()


# ===== 파일 업로드로 회차 생성 =====

@router.post("/{novel_id}/chapters/upload", status_code=status.HTTP_201_CREATED)
async def upload_chapter_file(
    novel_id: int,
    file: UploadFile = File(...),
    chapter_number: int = Form(...),
    title: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    파일 업로드로 회차 생성
    
    Args:
        novel_id: 소설 ID
        file: 업로드 파일 (TXT)
        chapter_number: 회차 번호
        title: 회차 제목
        current_user: 현재 인증된 사용자
        db: 데이터베이스 세션
        
    Returns:
        ChapterResponse: 생성된 회차 정보
        
    Raises:
        HTTPException: 파일 형식이 지원되지 않거나 파싱 실패
    """
    # 1. 소설 조회 및 권한 확인
    novel = db.query(Novel).filter(Novel.id == novel_id).first()
    if not novel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="소설을 찾을 수 없습니다."
        )
    
    # 작가 본인이거나 관리자만 가능
    if novel.author_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="권한이 없습니다."
        )

    # 2. 회차 번호 중복 확인
    existing_chapter = db.query(Chapter).filter(
        Chapter.novel_id == novel_id,
        Chapter.chapter_number == chapter_number
    ).first()
    
    if existing_chapter:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"이미 존재하는 회차 번호입니다: {chapter_number}화"
        )
        
    # 3. 파일 내용 읽기
    content = ""
    filename = file.filename.lower()
    
    if filename.endswith(".txt"):
        content = await load_txt_from_upload(file)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="지원하지 않는 파일 형식입니다. 현재 .txt 파일만 지원합니다."
        )
        
    if not content.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="파일 내용이 비어있습니다."
        )

    # 4. 회차 생성
    # word_count 계산
    word_count = len(content.split())
    
    new_chapter = Chapter(
        novel_id=novel_id,
        chapter_number=chapter_number,
        title=title,
        content=content,
        word_count=word_count,
        storyboard_status="PENDING"
    )
    
    db.add(new_chapter)
    
    try:
        db.commit()
        db.refresh(new_chapter)
        
        # 백그라운드 작업: 스토리보드 처리
        # 별도 스레드에서 비동기 실행하여 API 응답이 빠르게 나가도록 함
        try:
            from backend.worker.tasks import process_chapter_storyboard
            from threading import Thread
            
            # 스토리보드 처리를 별도 스레드에서 실행 (메인 스레드 차단 안 함)
            thread = Thread(
                target=process_chapter_storyboard,
                args=(novel_id, new_chapter.id),
                daemon=False
            )
            thread.start()
        except Exception as e:
            pass
        
        return new_chapter
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"데이터베이스 저장 중 오류가 발생했습니다: {str(e)}"
        )


# ===== 스토리보드 처리 진행 상황 조회 =====

@router.get("/{novel_id}/chapters/{chapter_id}/storyboard-status")
async def get_storyboard_status(
    novel_id: int,
    chapter_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    회차의 스토리보드 처리 상태 조회
    
    Args:
        novel_id: 소설 ID
        chapter_id: 회차 ID
        current_user: 현재 인증된 사용자
        db: 데이터베이스 세션
        
    Returns:
        StoryboardProgressResponse: 처리 상태 및 진행률
    """
    # 권한 확인
    novel = db.query(Novel).filter(Novel.id == novel_id).first()
    if not novel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="소설을 찾을 수 없습니다."
        )
    
    if novel.author_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="권한이 없습니다."
        )
    
    # 회차 조회
    chapter = db.query(Chapter).filter(
        Chapter.id == chapter_id,
        Chapter.novel_id == novel_id
    ).first()
    
    if not chapter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="회차를 찾을 수 없습니다."
        )
    
    return StoryboardProgressResponse(
        chapter_id=chapter.id,
        status=chapter.storyboard_status,
        progress=chapter.storyboard_progress,
        message=chapter.storyboard_message,
        error=chapter.storyboard_error
    )


# ===== 스토리보드 바이블 데이터 조회 =====

@router.get("/{novel_id}/chapters/{chapter_id}/bible")
async def get_chapter_bible(
    novel_id: int,
    chapter_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    회차의 스토리보드 바이블(인물, 아이템, 장소, 타임라인 등) 조회
    
    Args:
        novel_id: 소설 ID
        chapter_id: 회차 ID
        current_user: 현재 인증된 사용자
        db: 데이터베이스 세션
        
    Returns:
        Dict: 스토리보드 바이블 정보 (인물, 아이템, 장소, 타임라인, 주요 사건)
    """
    # 권한 확인
    novel = db.query(Novel).filter(Novel.id == novel_id).first()
    if not novel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="소설을 찾을 수 없습니다."
        )
    
    if novel.author_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="권한이 없습니다."
        )
    
    # 회차 조회
    chapter = db.query(Chapter).filter(
        Chapter.id == chapter_id,
        Chapter.novel_id == novel_id
    ).first()
    
    if not chapter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="회차를 찾을 수 없습니다."
        )
    
    # 먼저 저장된 분석 결과(Analysis 레코드)가 있는지 확인
    from backend.db.models import Analysis, AnalysisType, VectorDocument
    
    analysis_record = db.query(Analysis).filter(
        Analysis.chapter_id == chapter_id,
        Analysis.analysis_type == AnalysisType.CHARACTER
    ).first()
    
    # 분석된 결과가 있으면 사용
    if analysis_record and analysis_record.result:
        result = analysis_record.result
        
        # 다만 appearance_count 등은 통계가 필요하므로 씬 데이터도 확인
        # VectorDocument에서 씬 정보 조회
        scenes = db.query(VectorDocument).filter(
            VectorDocument.novel_id == novel_id
        ).order_by(VectorDocument.chunk_index).all()
        
        character_stats = {}
        for scene in scenes:
            metadata = scene.metadata_json or {}
            for char in metadata.get('characters', []):
                if char:
                    if char not in character_stats:
                        character_stats[char] = {'count': 0, 'appearances': []}
                    character_stats[char]['count'] += 1
                    character_stats[char]['appearances'].append(scene.chunk_index)
        
        # 분석 결과에 통계 보강
        if 'characters' in result:
            for char in result['characters']:
                name = char.get('name')
                if name and name in character_stats:
                    char['appearance_count'] = character_stats[name]['count']
                    char['appearances'] = character_stats[name]['appearances']
                else:
                    char['appearance_count'] = 1
                    char['appearances'] = [char.get('first_appearance', 0)]
        
        return result

    # 분석 결과가 없으면 기존 로직(VectorDocument기반 집계) 수행
    scenes = db.query(VectorDocument).filter(
        VectorDocument.novel_id == novel_id
    ).order_by(VectorDocument.chunk_index).all()
    
    # 바이블 데이터 추출
    bible_data = {
        "characters": [],  # {name, description, first_appearance}
        "locations": [],   # {name, description, appearances}
        "items": [],       # {name, description, first_appearance}
        "key_events": [],  # {summary, scene_index, characters_involved}
        "timeline": []     # {time, event}
    }
    
    character_dict = {}  # name -> character 정보
    location_dict = {}   # name -> location 정보
    item_dict = {}       # name -> item 정보
    
    # 모든 씬에서 정보 수집
    for scene in scenes:
        metadata = scene.metadata_json or {}
        
        # 인물 추출
        for char in metadata.get('characters', []):
            if char and char not in character_dict:
                character_dict[char] = {
                    'name': char,
                    'first_appearance': scene.chunk_index,
                    'appearances': [scene.chunk_index],
                    'description': '', # 기본값
                    'traits': []      # 기본값
                }
            elif char:
                if scene.chunk_index not in character_dict[char]['appearances']:
                    character_dict[char]['appearances'].append(scene.chunk_index)
        
        # 장소 추출
        for loc in metadata.get('locations', []):
            if loc and loc not in location_dict:
                location_dict[loc] = {
                    'name': loc,
                    'appearances': [scene.chunk_index],
                    'description': ''
                }
            elif loc:
                if scene.chunk_index not in location_dict[loc]['appearances']:
                    location_dict[loc]['appearances'].append(scene.chunk_index)
        
        # 아이템 추출
        for item in metadata.get('items', []):
            if item and item not in item_dict:
                item_dict[item] = {
                    'name': item,
                    'first_appearance': scene.chunk_index,
                    'description': ''
                }
        
        # 주요 사건 추출
        for event in metadata.get('key_events', []):
            if event:
                bible_data['key_events'].append({
                    'summary': event,
                    'scene_index': scene.chunk_index,
                    'characters_involved': metadata.get('characters', [])
                })
        
        # 타임라인
        time_period = metadata.get('time_period')
        if time_period:
            bible_data['timeline'].append({
                'time': time_period,
                'event': metadata.get('summary', ''),
                'scene_index': scene.chunk_index
            })
    
    # 바이블 데이터 변환
    bible_data['characters'] = [
        {
            'name': char_info['name'],
            'first_appearance': char_info['first_appearance'],
            'appearance_count': len(char_info['appearances']),
            'appearances': sorted(char_info['appearances']),
            'description': char_info.get('description', ''),
            'traits': char_info.get('traits', [])
        }
        for char_info in character_dict.values()
    ]
    
    bible_data['locations'] = [
        {
            'name': loc_info['name'],
            'appearance_count': len(loc_info['appearances']),
            'appearances': sorted(loc_info['appearances']),
            'description': loc_info.get('description', '')
        }
        for loc_info in location_dict.values()
    ]
    
    bible_data['items'] = [
        {
            'name': item_info['name'],
            'first_appearance': item_info['first_appearance'],
            'description': item_info.get('description', '')
        }
        for item_info in item_dict.values()
    ]
    
    return bible_data