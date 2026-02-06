"""
소설/회차 관리 API 엔드포인트 (Refactored)
- 모든 로직은 Service Layer로 이관됨
"""

from fastapi import APIRouter, Depends, status, Query, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional

from backend.db.session import get_db
from backend.core.security import get_current_user
from backend.services.novel_service import NovelService
from backend.schemas.novel_schema import (
    NovelCreate, NovelUpdate, NovelResponse, NovelListResponse,
    ChapterResponse, ChapterUpdate
)

router = APIRouter()

# ===== 소설 관리 =====

@router.post("/", status_code=status.HTTP_201_CREATED, response_model=NovelResponse)
async def create_novel(
    novel_data: NovelCreate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return NovelService.create_novel(db, novel_data, current_user.id)

@router.get("/", response_model=NovelListResponse)
async def get_novels(
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
async def get_novel(
    novel_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return NovelService.get_novel(db, novel_id, current_user.id)

@router.put("/{novel_id}", response_model=NovelResponse)
async def update_novel(
    novel_id: int,
    novel_update: NovelUpdate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return NovelService.update_novel(db, novel_id, novel_update, current_user.id)

@router.delete("/{novel_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_novel(
    novel_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    NovelService.delete_novel(db, novel_id, current_user.id)

# ===== 회차 관리 =====

@router.get("/{novel_id}/chapters", response_model=List[ChapterResponse])
async def get_chapters(
    novel_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    is_admin = getattr(current_user, "is_admin", False)
    return NovelService.get_chapters(db, novel_id, current_user.id, is_admin)

@router.get("/{novel_id}/chapters/{chapter_id}", response_model=ChapterResponse)
async def get_chapter(
    novel_id: int,
    chapter_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    is_admin = getattr(current_user, "is_admin", False)
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
    is_admin = getattr(current_user, "is_admin", False)
    return await NovelService.create_chapter_from_file(
        db, novel_id, current_user.id, file, chapter_number, title, is_admin
    )

@router.post("/{novel_id}/chapters/{chapter_id}/analyze", status_code=status.HTTP_202_ACCEPTED)
async def reanalyze_chapter(
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
    is_admin = getattr(current_user, "is_admin", False)
    # 권한 및 존재 여부 확인 (NovelService 내부 로직 활용 권장)
    # 여기서는 간단히 Service 호출
    return NovelService.analyze_chapter(db, novel_id, chapter_id, current_user.id, is_admin)

@router.put("/{novel_id}/chapters/{chapter_id}", response_model=ChapterResponse)
async def update_chapter(
    novel_id: int,
    chapter_id: int,
    chapter_update: ChapterUpdate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    is_admin = getattr(current_user, "is_admin", False)
    return NovelService.update_chapter(db, novel_id, chapter_id, chapter_update, current_user.id, is_admin)

@router.delete("/{novel_id}/chapters/{chapter_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chapter(
    novel_id: int,
    chapter_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    is_admin = getattr(current_user, "is_admin", False)
    NovelService.delete_chapter(db, novel_id, chapter_id, current_user.id, is_admin)

# ===== 레거시/기타 엔드포인트 유지 (스토리보드 진행률 등) =====
# TODO: 이것들도 Service로 올릴 수 있음

@router.get("/{novel_id}/chapters/{chapter_id}/storyboard-status")
async def get_storyboard_status(
    novel_id: int,
    chapter_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    is_admin = getattr(current_user, "is_admin", False)
    chapter = NovelService.get_chapter(db, novel_id, chapter_id, current_user.id, is_admin)
    
    return {
        "chapter_id": chapter.id,
        "status": chapter.storyboard_status,
        "progress": chapter.storyboard_progress,
        "message": chapter.storyboard_message,
        "error": chapter.storyboard_error
    }

@router.get("/{novel_id}/chapters/{chapter_id}/bible")
async def get_chapter_bible(
    novel_id: int,
    chapter_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from backend.services.analysis_service import AnalysisService
    is_admin = getattr(current_user, "is_admin", False)
    return AnalysisService.get_chapter_bible(db, novel_id, chapter_id, current_user.id, is_admin)
 
