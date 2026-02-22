"""
소설/회차 관리 API 엔드포인트 (Refactored)
- 모든 로직은 Service Layer로 이관됨
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import List, Optional
from urllib.parse import quote

from backend.db.session import get_db
from backend.core.security import get_current_user
from backend.services.novel_service import NovelService
from backend.services.analysis_service import AnalysisService
from backend.services.export_service import BibleExportService, ChapterExportService
from backend.core.utils import sanitize_filename
from backend.schemas.novel_schema import (
    NovelCreate, NovelUpdate, NovelResponse, NovelListResponse,
    ChapterResponse, ChapterListItem, ChapterUpdate, ChapterMergeRequest
)

router = APIRouter()


def _is_admin(user) -> bool:
    """사용자의 관리자 상태 추출"""
    return getattr(user, "is_admin", False)


# ===== 소설 관리 =====

@router.post("/", status_code=status.HTTP_201_CREATED, response_model=NovelResponse)
def create_novel(
    novel_data: NovelCreate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return NovelService.create_novel(db, novel_data, current_user.id)

@router.get("/", response_model=NovelListResponse)
def get_novels(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    search: Optional[str] = None,
    genre: Optional[str] = None,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    novels, total = NovelService.get_novels(db, current_user.id, skip, limit, search, genre)
    return NovelListResponse(total=total, novels=novels)

@router.get("/{novel_id}", response_model=NovelResponse)
def get_novel(
    novel_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return NovelService.get_novel(db, novel_id, current_user.id)

@router.put("/{novel_id}", response_model=NovelResponse)
def update_novel(
    novel_id: int,
    novel_update: NovelUpdate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return NovelService.update_novel(db, novel_id, novel_update, current_user.id)

@router.delete("/{novel_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_novel(
    novel_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    NovelService.delete_novel(db, novel_id, current_user.id)

@router.patch("/{novel_id}/merge-contents", response_model=ChapterResponse)
def merge_chapters(
    novel_id: int,
    merge_data: ChapterMergeRequest,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    회차 병합 API
    - 여러 회차 내용을 하나로 합칩니다. (target_id로 병합)
    - 병합된 소스 회차들은 삭제됩니다.
    """
    is_admin = _is_admin(current_user)
    return NovelService.merge_chapters(
        db, novel_id, merge_data.target_id, merge_data.source_ids, current_user.id, is_admin
    )

# ===== 회차 관리 =====

@router.get("/{novel_id}/chapters", response_model=List[ChapterListItem])
def get_chapters(
    novel_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    is_admin = _is_admin(current_user)
    return NovelService.get_chapters(db, novel_id, current_user.id, is_admin)

@router.get("/{novel_id}/chapters/{chapter_id}", response_model=ChapterResponse)
def get_chapter(
    novel_id: int,
    chapter_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    is_admin = _is_admin(current_user)
    return NovelService.get_chapter(db, novel_id, chapter_id, current_user.id, is_admin)

@router.post("/{novel_id}/chapters/upload", status_code=status.HTTP_201_CREATED, response_model=ChapterResponse)
async def upload_chapter_file(
    novel_id: int,
    file: UploadFile = File(...),
    chapter_number: int = Form(...),
    title: str = Form(...),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """파일 업로드로 회차 생성 (백그라운드 분석 트리거 포함)"""
    # 입력 유효성 검사
    if chapter_number <= 0:
        raise HTTPException(status_code=400, detail="회차 번호는 1 이상이어야 합니다.")
    if len(title) > 255:
        raise HTTPException(status_code=400, detail="제목은 255자 이하여야 합니다.")

    is_admin = _is_admin(current_user)
    return await NovelService.create_chapter_from_file(
        db, novel_id, current_user.id, file, chapter_number, title, is_admin
    )

@router.post("/{novel_id}/chapters/{chapter_id}/analyze", status_code=status.HTTP_202_ACCEPTED)
def reanalyze_chapter(
    novel_id: int,
    chapter_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    회차 재분석 요청 (백그라운드 작업 시작)
    - 텍스트 분할 (500자 단위 청크)
    - Pinecone 벡터 인덱싱
    - 스토리보드 구조화 (LLM)
    """
    is_admin = _is_admin(current_user)
    # 권한 및 존재 여부 확인 (NovelService 내부 로직 활용 권장)
    # 여기서는 간단히 Service 호출
    return NovelService.analyze_chapter(db, novel_id, chapter_id, current_user.id, is_admin)

@router.put("/{novel_id}/chapters/{chapter_id}", response_model=ChapterResponse)
def update_chapter(
    novel_id: int,
    chapter_id: int,
    chapter_update: ChapterUpdate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    회차 수정
    """
    is_admin = _is_admin(current_user)
    return NovelService.update_chapter(db, novel_id, chapter_id, chapter_update, current_user.id, is_admin)

@router.delete("/{novel_id}/chapters/{chapter_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_chapter(
    novel_id: int,
    chapter_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    is_admin = _is_admin(current_user)
    NovelService.delete_chapter(db, novel_id, chapter_id, current_user.id, is_admin)

# ===== 레거시/기타 엔드포인트 유지 (스토리보드 진행률 등) =====
# TODO: 이것들도 Service로 올릴 수 있음

@router.get("/{novel_id}/chapters/{chapter_id}/storyboard-status")
def get_storyboard_status(
    novel_id: int,
    chapter_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    is_admin = _is_admin(current_user)
    chapter = NovelService.get_chapter(db, novel_id, chapter_id, current_user.id, is_admin)
    
    return {
        "chapter_id": chapter.id,
        "status": chapter.storyboard_status,
        "progress": chapter.storyboard_progress,
        "message": chapter.storyboard_message,
        "error": chapter.storyboard_error
    }

@router.get("/{novel_id}/chapters/{chapter_id}/export")
def export_chapter(
    novel_id: int,
    chapter_id: int,
    format: str = Query(..., pattern="^(txt|pdf|docx)$"),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """챕터 본문을 TXT/PDF/DOCX 파일로 내보내기"""
    is_admin = _is_admin(current_user)
    chapter = NovelService.get_chapter(db, novel_id, chapter_id, current_user.id, is_admin)

    content_html = chapter.content or ""
    display_title = getattr(chapter, "title", "") or ""

    if format == "txt":
        content_bytes = ChapterExportService.export_chapter_txt(content_html, display_title)
        media_type = "text/plain; charset=utf-8"
        ext = "txt"
    elif format == "pdf":
        content_bytes = ChapterExportService.export_chapter_pdf(content_html, display_title)
        media_type = "application/pdf"
        ext = "pdf"
    else:
        content_bytes = ChapterExportService.export_chapter_docx(content_html, display_title)
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ext = "docx"

    safe_title = sanitize_filename(display_title)
    display_name = f"{safe_title}.{ext}" if safe_title != "untitled" else f"chapter_{chapter_id}.{ext}"
    ascii_fallback = f"chapter_{chapter_id}.{ext}"
    encoded_name = quote(display_name)

    return Response(
        content=content_bytes,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{ascii_fallback}"; filename*=UTF-8\'\'{encoded_name}'
        },
    )

@router.get("/{novel_id}/chapters/{chapter_id}/bible/export")
def export_bible(
    novel_id: int,
    chapter_id: int,
    format: str = Query(..., pattern="^(txt|pdf|docx)$"),
    search: str = Query("", description="검색 필터"),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """바이블 데이터를 TXT/PDF/DOCX 파일로 내보내기"""
    is_admin = _is_admin(current_user)
    bible_data = AnalysisService.get_chapter_bible(db, novel_id, chapter_id, current_user.id, is_admin)

    # 소설 제목 가져오기
    novel = NovelService.get_novel(db, novel_id, current_user.id)
    title = getattr(novel, "title", "")

    # 검색 필터 적용
    if search.strip():
        bible_data = BibleExportService.filter_bible_data(bible_data, search)

    # 포맷별 내보내기
    if format == "txt":
        content_bytes = BibleExportService.export_txt(bible_data, title)
        media_type = "text/plain; charset=utf-8"
        ext = "txt"
    elif format == "pdf":
        content_bytes = BibleExportService.export_pdf(bible_data, title)
        media_type = "application/pdf"
        ext = "pdf"
    else:  # docx
        content_bytes = BibleExportService.export_docx(bible_data, title)
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ext = "docx"

    # 파일명: filename*에 한글 포함, filename에는 ASCII 폴백
    safe_title = sanitize_filename(title)
    display_name = f"{safe_title}_바이블.{ext}" if safe_title != "untitled" else f"bible_{novel_id}_{chapter_id}.{ext}"
    ascii_fallback = f"bible_{novel_id}_{chapter_id}.{ext}"
    encoded_name = quote(display_name)

    return Response(
        content=content_bytes,
        media_type=media_type,
        headers={
            "Content-Disposition": f"attachment; filename=\"{ascii_fallback}\"; filename*=UTF-8''{encoded_name}"
        },
    )

@router.get("/{novel_id}/chapters/{chapter_id}/bible")
def get_chapter_bible(
    novel_id: int,
    chapter_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    is_admin = _is_admin(current_user)
    return AnalysisService.get_chapter_bible(db, novel_id, chapter_id, current_user.id, is_admin)
 
