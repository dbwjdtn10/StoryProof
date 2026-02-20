"""
소설 서비스 모듈

소설 및 챕터의 CRUD 작업, 파일 업로드, 분석 요청 등을 처리하는 서비스입니다.
"""

from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_
from fastapi import HTTPException, status, UploadFile
import chardet
from datetime import datetime
import logging

from backend.db.models import Novel, Chapter, VectorDocument, CharacterChatRoom
from backend.schemas.novel_schema import NovelCreate, NovelUpdate, ChapterUpdate
from backend.core.config import settings

# 로거 설정
logger = logging.getLogger(__name__)


class NovelService:
    """소설 및 챕터 관리 서비스"""
    @staticmethod
    def get_novels(
        db: Session, 
        user_id: int, 
        skip: int = 0, 
        limit: int = 10,
        search: Optional[str] = None,
        genre: Optional[str] = None
    ) -> Tuple[List[Novel], int]:
        """
        사용자의 소설 목록 조회 (페이지네이션 및 필터링 지원)
        
        Args:
            db: 데이터베이스 세션
            user_id: 사용자 ID
            skip: 건너뛸 레코드 수 (페이지네이션)
            limit: 조회할 최대 레코드 수
            search: 검색어 (제목 또는 설명에서 검색)
            genre: 장르 필터
            
        Returns:
            Tuple[List[Novel], int]: (소설 목록, 전체 개수)
        """
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
        """
        소설 상세 정보 조회
        
        Args:
            db: 데이터베이스 세션
            novel_id: 소설 ID
            user_id: 사용자 ID
            
        Returns:
            Novel: 소설 객체
            
        Raises:
            HTTPException: 소설을 찾을 수 없는 경우
        """
        novel = db.query(Novel).filter(Novel.id == novel_id).first()
        if not novel:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="소설을 찾을 수 없습니다."
            )
        
        # 권한 확인 (작가 본인 또는 공개 소설)
        if novel.author_id != user_id and not novel.is_public:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="권한이 없습니다."
            )

        return novel

    @staticmethod
    def create_novel(db: Session, novel_data: NovelCreate, user_id: int) -> Novel:
        """
        새로운 소설 생성
        
        Args:
            db: 데이터베이스 세션
            novel_data: 소설 생성 데이터
            user_id: 작성자 ID
            
        Returns:
            Novel: 생성된 소설 객체
        """
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
        
        # Pinecone 벡터 정리 (모든 챕터)
        try:
            from backend.services.analysis.embedding_engine import EmbeddingSearchEngine
            engine = EmbeddingSearchEngine()
            chapters = db.query(Chapter).filter(Chapter.novel_id == novel_id).all()
            for chapter in chapters:
                engine.delete_chapter_vectors(novel_id, chapter.id)
        except Exception as e:
            logger.warning(f"Pinecone 벡터 정리 실패 (novel={novel_id}): {e}")

        # 관련 이미지 파일 삭제
        import os
        import glob

        base_dir = os.getcwd()
        images_dir = os.path.join(base_dir, "backend", "static", "images")
        pattern = os.path.join(images_dir, f"novel_{novel_id}_*.png")

        deleted_count = 0
        for image_path in glob.glob(pattern):
            try:
                os.remove(image_path)
                deleted_count += 1
                logger.info(f"[Cleanup] Deleted image: {os.path.basename(image_path)}")
            except Exception as e:
                logger.warning(f"Failed to delete {os.path.basename(image_path)}: {e}")

        if deleted_count > 0:
            logger.info(f"[Cleanup] Deleted {deleted_count} image(s) for novel {novel_id}")

        db.delete(novel)
        db.commit()

    @staticmethod
    def analyze_chapter(db: Session, novel_id: int, chapter_id: int, user_id: int, is_admin: bool = False) -> None:
        """
        챕터 분석 요청 (백그라운드 작업 트리거)
        
        Celery 워커를 통해 비동기로 챕터 분석을 수행합니다.
        인물, 장소, 아이템 등의 스토리보드 요소를 추출합니다.
        
        Args:
            db: 데이터베이스 세션
            novel_id: 소설 ID
            chapter_id: 챕터 ID
            user_id: 사용자 ID
            is_admin: 관리자 권한 여부
            
        Returns:
            Dict: 분석 시작 상태 정보
        """
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
        """
        파일 업로드를 통한 챕터 생성 및 자동 분석 트리거
        
        TXT 파일을 업로드하여 새로운 챕터를 생성하고,
        자동으로 백그라운드 분석 작업을 시작합니다.
        
        Args:
            db: 데이터베이스 세션
            novel_id: 소설 ID
            user_id: 사용자 ID
            file: 업로드된 파일 객체
            chapter_number: 챕터 번호
            title: 챕터 제목
            is_admin: 관리자 권한 여부
            
        Returns:
            Chapter: 생성된 챕터 객체
            
        Raises:
            HTTPException: 파일이 비어있거나, 중복 챕터 번호인 경우
        """
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
        """
        TXT 파일 내용 읽기 (인코딩 자동 감지)
        
        chardet 라이브러리를 사용하여 파일 인코딩을 자동으로 감지하고,
        실패 시 일반적인 인코딩들을 순차적으로 시도합니다.
        
        Args:
            file: 업로드된 파일 객체
            
        Returns:
            str: 디코딩된 파일 내용
            
        Raises:
            HTTPException: 지원하지 않는 인코딩인 경우
        """
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
            
        # Pinecone 벡터 정리 (DB 삭제 전에 수행)
        try:
            from backend.services.analysis.embedding_engine import EmbeddingSearchEngine
            EmbeddingSearchEngine().delete_chapter_vectors(novel_id, chapter_id)
        except Exception as e:
            logger.warning(f"Pinecone 벡터 정리 실패 (chapter={chapter_id}): {e}")

        # 관련된 캐릭터 채팅방 삭제 (Cascade가 안 걸려 있을 경우 수동 삭제)
        # CharacterChatMessage는 CharacterChatRoom 삭제 시 ORM cascade로 삭제됨
        chat_rooms = db.query(CharacterChatRoom).filter(CharacterChatRoom.chapter_id == chapter_id).all()
        for room in chat_rooms:
            db.delete(room)

        # 채팅방 삭제를 먼저 DB에 반영
        db.flush()

        db.delete(chapter)
        db.commit()

    @staticmethod
    def merge_chapters(
        db: Session, 
        novel_id: int, 
        target_id: int, 
        source_ids: List[int], 
        user_id: int, 
        is_admin: bool = False
    ) -> Chapter:
        """
        여러 회차를 하나로 병합
        
        Args:
            db: 데이터베이스 세션
            novel_id: 소설 ID
            target_id: 병합된 내용이 저장될 대상 회차 ID
            source_ids: 병합할 소스 회차 ID 목록 (대상 회차 포함 가능)
            user_id: 사용자 ID
            is_admin: 관리자 권한 여부
            
        Returns:
            Chapter: 병합된 대상 회차 객체
        """
        # 1. 권한 및 소설 확인
        novel = db.query(Novel).filter(Novel.id == novel_id).first()
        if not novel:
            raise HTTPException(status_code=404, detail="소설을 찾을 수 없습니다.")
            
        if novel.author_id != user_id and not is_admin:
            raise HTTPException(status_code=403, detail="권한이 없습니다.")

        # 2. 관련 모든 회차 조회
        all_ids = set(source_ids) | {target_id}
        chapters = db.query(Chapter).filter(
            Chapter.novel_id == novel_id,
            Chapter.id.in_(all_ids)
        ).all()
        
        if len(chapters) != len(all_ids):
            raise HTTPException(status_code=404, detail="일부 회차를 찾을 수 없습니다.")
            
        # 3. 요청된 순서대로 정렬 (target_id가 첫 번째, 그 뒤로 source_ids 순서)
        ordered_ids = [target_id] + [sid for sid in source_ids if sid != target_id]
        
        # ID를 키로 하는 딕셔너리 생성
        chapter_map = {c.id: c for c in chapters}
        
        # 4. 내용 병합
        merged_content_parts = []
        for cid in ordered_ids:
            if cid not in chapter_map:
                continue
                
            ch = chapter_map[cid]
            # 제목을 포함하여 구분할 수도 있지만, 여기서는 내용만 단순 병합하거나 구분자 추가
            # 요구사항에 따라 다르지만, 파일 병합 스크립트 참고: "\n\n--- {title} 시작 ---\n"
            header = f"\n\n--- {ch.title} ---\n"
            merged_content_parts.append(header + ch.content)
            
        final_content = "".join(merged_content_parts).strip()
        
        # 5. 대상 회차 업데이트 및 나머지 삭제
        target_chapter = next((c for c in chapters if c.id == target_id), None)
        if not target_chapter:
             raise HTTPException(status_code=404, detail="대상 회차를 찾을 수 없습니다.") # Should not happen
             
        target_chapter.content = final_content
        target_chapter.word_count = len(final_content.split())
        
        # 삭제 대상 (target 제외)
        for ch in chapters:
            if ch.id != target_id:
                db.delete(ch)
                
        db.commit()
        db.refresh(target_chapter)
        
        # TODO: 병합 후 재분석 트리거? 
        # 일단 내용이 바뀌었으므로 상태 초기화
        target_chapter.storyboard_status = "PENDING"
        target_chapter.storyboard_progress = 0
        db.commit()
        
        # 백그라운드 분석 트리거 (선택 사항)
        try:
            from backend.worker.tasks import process_chapter_storyboard
            process_chapter_storyboard.delay(novel_id, target_chapter.id)
        except Exception as e:
            logger.warning(f"병합 후 재분석 트리거 실패: {e}")
            
        return target_chapter
