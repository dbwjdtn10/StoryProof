"""
Celery 비동기 작업 정의
- AI 분석 작업
- 배경 작업
"""

import os
from typing import Dict, Any
from dataclasses import asdict

from backend.db.session import SessionLocal
from backend.db.models import Novel, Chapter, User, StoryboardStatus
from backend.core.config import settings
from backend.services.analysis import (
    DocumentLoader,
    SceneChunker,
    GeminiStructurer,
    EmbeddingSearchEngine,
    StructuredScene
)

from datetime import datetime

from .celery_app import celery_app


def update_chapter_progress(chapter_id: int, progress: int, status: str = None, message: str = None, error: str = None):
    """
    회차의 스토리보드 처리 진행 상황 업데이트
    
    Args:
        chapter_id: 회차 ID
        progress: 진행률 (0-100)
        status: 처리 상태 (문자열: 'PENDING', 'PROCESSING', 'COMPLETED', 'FAILED')
        message: 진행 메시지
        error: 에러 메시지
    """
    try:
        db = SessionLocal()
        chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
        
        if chapter:
            chapter.storyboard_progress = progress
            if status:
                chapter.storyboard_status = status
            if message:
                chapter.storyboard_message = message
            if error:
                chapter.storyboard_error = error
            
            db.commit()
            # print(f"[DB Update] Chapter {chapter_id}: {progress}% - {status} ({message})")
        else:
            print(f"⚠️ [DB Update Fail] Chapter {chapter_id} not found")
        
        db.close()
    except Exception as e:
        pass


@celery_app.task
def process_chapter_storyboard(novel_id: int, chapter_id: int):
    """
    회차를 스토리보드화하여 Pinecone에 저장하는 백그라운드 작업
    
    Args:
        novel_id: 소설 ID
        chapter_id: 회차 ID
    """
    try:
        # 상태 업데이트: PROCESSING
        update_chapter_progress(chapter_id, 0, "PROCESSING", "초기화 중...")
        
        # 1. 데이터베이스에서 회차 정보 조회
        db = SessionLocal()
        chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
        novel = db.query(Novel).filter(Novel.id == novel_id).first()
        
        if not chapter or not novel:
            error_msg = f"회차를 찾을 수 없습니다: {novel_id}/{chapter_id} (이미 삭제되었을 수 있습니다.)"
            print(f"⚠️ {error_msg}")
            # 이미 삭제된 경우 상태 업데이트가 무의미하므로 즉시 종료
            return
        
        update_chapter_progress(chapter_id, 5, "PROCESSING", f"{chapter.title} 로드 완료")
        
        # 2. Gemini API 키 준비
        gemini_api_key = settings.GOOGLE_API_KEY
        
        # 3. 회차 content를 임시 파일로 저장
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(chapter.content)
            temp_file_path = f.name
        
        update_chapter_progress(chapter_id, 10, "PROCESSING", "준비 완료")
        
        # 4. 스토리보드 처리
        
        # 파일 로드
        loader = DocumentLoader()
        text = loader.load_txt(temp_file_path)
        update_chapter_progress(chapter_id, 15, "PROCESSING", "텍스트 로드 완료")
        
        # 1. Gemini 초기화 (씬 분할 및 구조화에 사용)
        structurer = GeminiStructurer(gemini_api_key)
        
        # 2. 씬 분할 (LLM Anchor-based Approach)
        # LLM이 전체 텍스트를 읽고 '시작 문장'들을 찾아서 자름
        update_chapter_progress(chapter_id, 20, "PROCESSING", "LLM으로 전체 소설 구조 분석 중...")
        
        scenes = structurer.split_scenes(text)
        
        update_chapter_progress(chapter_id, 30, "PROCESSING", f"{len(scenes)}개 씬 분할 완료")
        
        # 3. 씬 구조화 (병렬 처리로 속도 향상)
        from concurrent.futures import ThreadPoolExecutor, as_completed
        structured_scenes = [None] * len(scenes)
        failed_scenes = []
        
        # 동시에 최대 3개 씬까지 병렬 처리 (Gemini API rate limit 고려)
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {}
            for i, scene in enumerate(scenes):
                future = executor.submit(structurer.structure_scene, scene, i)
                futures[future] = i
            
            completed = 0
            for future in as_completed(futures):
                i = futures[future]
                try:
                    structured = future.result()
                    structured_scenes[i] = structured
                    completed += 1
                    
                    # 진행률 계산 (25% ~ 75%)
                    progress = 25 + int(completed / len(scenes) * 50)
                    update_chapter_progress(chapter_id, progress, "PROCESSING", f"씬 분석 중 {completed}/{len(scenes)}")
                except Exception as e:
                    failed_scenes.append(i)
        
        # None 값 제거 (실패한 씬)
        structured_scenes = [s for s in structured_scenes if s is not None]
        
        # Pinecone에 배치 저장
        update_chapter_progress(chapter_id, 80, "PROCESSING", f"Pinecone 저장 중 ({len(structured_scenes)} 씬)")
        
        search_engine = EmbeddingSearchEngine()
        documents = [asdict(scene) for scene in structured_scenes]
        search_engine.add_documents(documents, novel_id, chapter_id)
        update_chapter_progress(chapter_id, 90, "PROCESSING", "저장 완료")
        
        # 5. 전역 엔티티 분석 (캐릭터 특성 등 추출)
        update_chapter_progress(chapter_id, 92, "PROCESSING", "추가 정보 분석 중...")
        try:
            # 소설에 설정된 커스텀 프롬프트가 있으면 사용
            custom_prompt = novel.custom_prompt if novel else None
            global_entities = structurer.extract_global_entities(structured_scenes, custom_system_prompt=custom_prompt)
            
            # Analysis 레코드로 저장
            # 기존 분석 결과가 있으면 업데이트, 없으면 생성
            from backend.db.models import Analysis, AnalysisType, AnalysisStatus
            
            analysis = db.query(Analysis).filter(
                Analysis.chapter_id == chapter_id,
                Analysis.analysis_type == AnalysisType.CHARACTER
            ).first()
            
            if not analysis:
                analysis = Analysis(
                    novel_id=novel_id,
                    chapter_id=chapter_id,
                    analysis_type=AnalysisType.CHARACTER,
                    status=AnalysisStatus.COMPLETED,
                    result=global_entities
                )
                db.add(analysis)
            else:
                analysis.result = global_entities
                analysis.status = AnalysisStatus.COMPLETED
                analysis.updated_at = datetime.utcnow()
                
            db.commit()
            print(f"✅ 전역 엔티티 분석 완료 및 저장: {len(global_entities.get('characters', []))}명")
        except Exception as e:
            print(f"⚠️ 전역 엔티티 분석 실패 (무시됨): {e}")

        # 6. 임시 파일 삭제
        os.unlink(temp_file_path)
        
        # 6. 처리 완료
        # 6. 처리 완료
        # from datetime import datetime (Removed: use top-level import)
        chapter.storyboard_status = "COMPLETED"
        chapter.storyboard_progress = 100
        chapter.storyboard_message = "처리 완료"
        chapter.storyboard_completed_at = datetime.utcnow()
        db.commit()
        
        update_chapter_progress(chapter_id, 100, "COMPLETED", "✓ 처리 완료")
        
    except Exception as e:
        error_msg = f"스토리보드 처리 중 오류: {str(e)}"
        update_chapter_progress(chapter_id, 0, "FAILED", error_msg)
    finally:
        db.close()


# @celery_app.task(bind=True, max_retries=3)
def analyze_chapter_task(self, analysis_id: int, chapter_id: int, analysis_type: str) -> Dict[str, Any]:
    """
    회차 분석 비동기 작업
    
    Args:
        self: Celery task 인스턴스
        analysis_id: 분석 ID
        chapter_id: 회차 ID
        analysis_type: 분석 유형
        
    Returns:
        Dict: 분석 결과
    """
    # TODO: 분석 상태 업데이트
    # TODO: 회차 텍스트 조회
    # TODO: AI 엔진으로 분석 수행
    # TODO: 결과 저장
    pass


# ===== 벡터 스토어 작업 =====

# @celery_app.task
def index_novel_task(novel_id: int) -> Dict[str, Any]:
    """
    소설을 벡터 스토어에 인덱싱
    
    Args:
        novel_id: 소설 ID
        
    Returns:
        Dict: 인덱싱 결과
    """
    # TODO: 소설 텍스트 조회
    # TODO: 벡터 스토어에 추가
    # TODO: 문서 ID 저장
    pass


# @celery_app.task
def index_chapter_task(chapter_id: int) -> Dict[str, Any]:
    """
    회차를 벡터 스토어에 인덱싱
    
    Args:
        chapter_id: 회차 ID
        
    Returns:
        Dict: 인덱싱 결과
    """
    # TODO: 회차 텍스트 조회
    # TODO: 벡터 스토어에 추가
    pass


# @celery_app.task
def remove_novel_from_vector_store_task(novel_id: int) -> None:
    """
    벡터 스토어에서 소설 제거
    
    Args:
        novel_id: 소설 ID
    """
    # TODO: 벡터 스토어에서 삭제
    pass


# ===== 정기 작업 =====

# @celery_app.task
def cleanup_old_analyses_task() -> Dict[str, int]:
    """
    오래된 분석 결과 정리
    
    Returns:
        Dict: 정리된 분석 수
    """
    # TODO: 30일 이상 된 분석 결과 삭제
    # TODO: 실패한 분석 정리
    pass


# @celery_app.task
def cleanup_old_chat_histories_task() -> Dict[str, int]:
    """
    오래된 채팅 히스토리 정리
    
    Returns:
        Dict: 정리된 채팅 수
    """
    # TODO: 90일 이상 된 채팅 히스토리 삭제
    pass


# ===== 알림 작업 =====

# @celery_app.task
def send_analysis_complete_notification_task(user_id: int, analysis_id: int) -> None:
    """
    분석 완료 알림 전송
    
    Args:
        user_id: 사용자 ID
        analysis_id: 분석 ID
    """
    # TODO: 이메일 또는 푸시 알림 전송
    pass


# ===== 유틸리티 함수 =====

def get_task_status(task_id: str) -> Dict[str, Any]:
    """
    Celery 작업 상태 조회
    
    Args:
        task_id: 작업 ID
        
    Returns:
        Dict: 작업 상태 정보
    """
    # TODO: AsyncResult로 작업 상태 조회
    pass


def cancel_task(task_id: str) -> bool:
    """
    Celery 작업 취소
    
    Args:
        task_id: 작업 ID
        
    Returns:
        bool: 취소 성공 여부
    """
    # TODO: 작업 취소
    pass


# ===== Celery Beat 스케줄 (정기 작업) =====

# celery_app.conf.beat_schedule = {
#     "cleanup-old-analyses": {
#         "task": "backend.worker.tasks.cleanup_old_analyses_task",
#         "schedule": 86400.0,  # 매일
#     },
#     "cleanup-old-chat-histories": {
#         "task": "backend.worker.tasks.cleanup_old_chat_histories_task",
#         "schedule": 86400.0,  # 매일
#     },
# }
