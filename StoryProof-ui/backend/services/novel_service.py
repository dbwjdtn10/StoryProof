from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_
from fastapi import HTTPException, status, UploadFile
import chardet
from datetime import datetime

from backend.db.models import Novel, Chapter, VectorDocument
from backend.schemas.novel_schema import NovelCreate, NovelUpdate, ChapterUpdate
from backend.core.config import settings

class NovelService:
    @staticmethod
    def get_novels(
        db: Session, 
        user_id: int, 
        skip: int = 0, 
        limit: int = 10,
        search: Optional[str] = None,
        genre: Optional[str] = None
    ) -> Tuple[List[Novel], int]:
        """소설 목록 조회 및 총 개수 반환"""
        query = db.query(Novel).filter(Novel.author_id == user_id)
        
        if search:
            query = query.filter(
                (Novel.title.ilike(f"%{search}%")) | 
                (Novel.description.ilike(f"%{search}%"))
            )
            
        if genre:
            query = query.filter(Novel.genre == genre)
            
        total = query.count()
        novels = query.offset(skip).limit(limit).all()
        return novels, total

    @staticmethod
    def get_novel(db: Session, novel_id: int, user_id: int) -> Novel:
        """소설 상세 조회 (권한 확인 포함)"""
        novel = db.query(Novel).filter(Novel.id == novel_id).first()
        if not novel:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="소설을 찾을 수 없습니다."
            )
        
        # 권한 확인 (작가 본인 또는 공개 소설)
        if novel.author_id != user_id and not novel.is_public:
             # 관리자 여부는 컨트롤러에서 확인하거나 여기서 user 객체를 받아 확인해야 함.
             # 일단 기본적인 로직만 이동
             pass # 호출부에서 처리하도록 반환만
             
        return novel

    @staticmethod
    def create_novel(db: Session, novel_data: NovelCreate, user_id: int) -> Novel:
        """소설 생성"""
        novel = Novel(
            title=novel_data.title,
            description=novel_data.description,
            genre=novel_data.genre,
            custom_prompt=novel_data.custom_prompt,
            author_id=user_id,
            is_public=novel_data.is_public
        )
        db.add(novel)
        db.commit()
        db.refresh(novel)
        return novel

    @staticmethod
    def update_novel(db: Session, novel_id: int, update_data: NovelUpdate, user_id: int) -> Novel:
        """소설 수정"""
        novel = db.query(Novel).filter(Novel.id == novel_id).first()
        if not novel:
            raise HTTPException(status_code=404, detail="소설을 찾을 수 없습니다.")
            
        if novel.author_id != user_id:
            raise HTTPException(status_code=403, detail="권한이 없습니다.")
            
        if update_data.title is not None:
            novel.title = update_data.title
        if update_data.description is not None:
            novel.description = update_data.description
        if update_data.genre is not None:
            novel.genre = update_data.genre
        if update_data.custom_prompt is not None:
            novel.custom_prompt = update_data.custom_prompt
        if update_data.is_public is not None:
            novel.is_public = update_data.is_public
        if update_data.is_completed is not None:
            novel.is_completed = update_data.is_completed
            
        db.commit()
        db.refresh(novel)
        return novel

    @staticmethod
    def delete_novel(db: Session, novel_id: int, user_id: int) -> None:
        """소설 삭제"""
        novel = db.query(Novel).filter(Novel.id == novel_id).first()
        if not novel:
            raise HTTPException(status_code=404, detail="소설을 찾을 수 없습니다.")
            
        if novel.author_id != user_id:
            raise HTTPException(status_code=403, detail="권한이 없습니다.")
            
        db.delete(novel)
        db.commit()

    @staticmethod
    def analyze_chapter(db: Session, novel_id: int, chapter_id: int, user_id: int, is_admin: bool = False) -> None:
        """회차 분석 요청 (Celery Task 트리거)"""
        # 1. 권한 확인
        chapter = NovelService.get_chapter(db, novel_id, chapter_id, user_id, is_admin)
        
        # 2. 상태 초기화 및 Celery Task 호출
        chapter.storyboard_status = "PENDING"
        chapter.storyboard_progress = 0
        chapter.storyboard_message = "분석 대기 중..."
        db.commit()

        from backend.worker.tasks import process_chapter_storyboard
        process_chapter_storyboard.delay(novel_id, chapter_id)
        
        return {"status": "accepted", "message": "Analysis started in background"}

    @staticmethod
    def get_chapters(db: Session, novel_id: int, user_id: int, is_admin: bool = False) -> List[Chapter]:
        """회차 목록 조회"""
        novel = db.query(Novel).filter(Novel.id == novel_id).first()
        if not novel:
            raise HTTPException(status_code=404, detail="Novel not found")
            
        if novel.author_id != user_id and not is_admin:
             raise HTTPException(status_code=403, detail="Not authorized")

        return db.query(Chapter).filter(Chapter.novel_id == novel_id).order_by(Chapter.chapter_number).all()

    @staticmethod
    def get_chapter(db: Session, novel_id: int, chapter_id: int, user_id: int, is_admin: bool = False) -> Chapter:
        """회차 상세 조회"""
        novel = db.query(Novel).filter(Novel.id == novel_id).first()
        if not novel:
            raise HTTPException(status_code=404, detail="소설을 찾을 수 없습니다.")

        chapter = db.query(Chapter).filter(
            Chapter.id == chapter_id,
            Chapter.novel_id == novel_id
        ).first()
        
        if not chapter:
            raise HTTPException(status_code=404, detail="회차를 찾을 수 없습니다.")
            
        # 권한 확인
        if novel.author_id != user_id and not is_admin and not novel.is_public:
            raise HTTPException(status_code=403, detail="권한이 없습니다.")
            
        return chapter

    @staticmethod
    async def create_chapter_from_file(
        db: Session, 
        novel_id: int, 
        user_id: int, 
        file: UploadFile, 
        chapter_number: int, 
        title: str,
        is_admin: bool = False
    ) -> Chapter:
        """파일 업로드로 회차 생성 및 분석 트리거"""
        # 1. 소설 조회 및 권한 확인
        novel = db.query(Novel).filter(Novel.id == novel_id).first()
        if not novel:
            raise HTTPException(status_code=404, detail="소설을 찾을 수 없습니다.")
        
        if novel.author_id != user_id and not is_admin:
            raise HTTPException(status_code=403, detail="권한이 없습니다.")

        # 2. 중복 확인
        existing = db.query(Chapter).filter(
            Chapter.novel_id == novel_id,
            Chapter.chapter_number == chapter_number
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"이미 존재하는 회차 번호입니다: {chapter_number}화")

        # 3. 파일 로드
        content = await NovelService._load_txt_content(file)
        if not content.strip():
             raise HTTPException(status_code=400, detail="파일 내용이 비어있습니다.")

        # 4. 저장
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
            
            # 5. 백그라운드 작업 트리거
            try:
                from backend.worker.tasks import process_chapter_storyboard
                process_chapter_storyboard.delay(novel_id, new_chapter.id)
            except Exception as e:
                print(f"⚠️ Celery 작업 등록 실패: {e}")
            
            return new_chapter
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"DB Error: {str(e)}")

    @staticmethod
    async def _load_txt_content(file: UploadFile) -> str:
        """TXT 파일 내용 읽기 (인코딩 자동 감지)"""
        raw_data = await file.read()
        
        # 1. chardet으로 감지
        result = chardet.detect(raw_data)
        if result['confidence'] > 0.7 and result['encoding']:
            try:
                return raw_data.decode(result['encoding'])
            except:
                pass
        
        # 2. 실패 시 일반적인 인코딩 시도
        encodings = ['utf-8', 'cp949', 'euc-kr', 'utf-16', 'latin-1']
        for enc in encodings:
            try:
                return raw_data.decode(enc)
            except:
                continue
                
        raise HTTPException(status_code=400, detail="지원하지 않는 인코딩입니다.")

    @staticmethod
    def update_chapter(
        db: Session, 
        novel_id: int, 
        chapter_id: int, 
        update_data: ChapterUpdate, 
        user_id: int,
        is_admin: bool = False
    ) -> Chapter:
        """회차 수정"""
        novel = db.query(Novel).filter(Novel.id == novel_id).first()
        if not novel:
            raise HTTPException(status_code=404, detail="소설을 찾을 수 없습니다.")
            
        if novel.author_id != user_id and not is_admin:
            raise HTTPException(status_code=403, detail="권한이 없습니다.")

        chapter = db.query(Chapter).filter(
            Chapter.id == chapter_id,
            Chapter.novel_id == novel_id
        ).first()
        
        if not chapter:
            raise HTTPException(status_code=404, detail="회차를 찾을 수 없습니다.")
            
        if update_data.title:
            chapter.title = update_data.title
        if update_data.content:
            chapter.content = update_data.content
            chapter.word_count = len(update_data.content.split())
        if update_data.chapter_number is not None:
             if update_data.chapter_number != chapter.chapter_number:
                # 중복 체크
                existing = db.query(Chapter).filter(
                    Chapter.novel_id == novel_id,
                    Chapter.chapter_number == update_data.chapter_number
                ).first()
                if existing:
                    raise HTTPException(status_code=400, detail="이미 존재하는 회차 번호입니다.")
                chapter.chapter_number = update_data.chapter_number
                
        if update_data.scenes is not None:
            # 씬 데이터(VectorDocument) 업데이트
            vector_docs = db.query(VectorDocument).filter(
                VectorDocument.novel_id == novel_id,
                VectorDocument.chapter_id == chapter_id
            ).order_by(VectorDocument.chunk_index).all()
            
            if len(vector_docs) == len(update_data.scenes):
                for doc, new_text in zip(vector_docs, update_data.scenes):
                    doc.chunk_text = new_text
            else:
                # 씬 개수가 다를 경우 처리가 복잡하므로 일단 로그만 남기고 스킵 (재분석 권장)
                print(f"Warning: Scene count mismatch. DB({len(vector_docs)}) != Update({len(update_data.scenes)}). Skipping scene update.")
                
        db.commit()
        db.refresh(chapter)
        return chapter

    @staticmethod
    def delete_chapter(db: Session, novel_id: int, chapter_id: int, user_id: int, is_admin: bool = False) -> None:
        """회차 삭제"""
        novel = db.query(Novel).filter(Novel.id == novel_id).first()
        if not novel:
            raise HTTPException(status_code=404, detail="소설을 찾을 수 없습니다.")
            
        if novel.author_id != user_id and not is_admin:
            raise HTTPException(status_code=403, detail="권한이 없습니다.")

        chapter = db.query(Chapter).filter(
            Chapter.id == chapter_id,
            Chapter.novel_id == novel_id
        ).first()
        
        if not chapter:
            raise HTTPException(status_code=404, detail="회차를 찾을 수 없습니다.")
            
        db.delete(chapter)
        db.commit()
