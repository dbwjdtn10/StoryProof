import os
import sys
import json
import logging
from pathlib import Path
from tqdm import tqdm

# 프로젝트 루트를 Python 경로에 추가
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(project_root)

from backend.services.analysis.gemini_structurer import GeminiStructurer
from backend.services.analysis.embedding_engine import EmbeddingSearchEngine
from backend.core.config import settings

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def process_corpus(input_dir: str, output_file: str):
    """
    novel_corpus_kr 폴더의 소설들을 읽어 새로운 청킹/임베딩 방식으로 변환 및 저장
    """
    input_path = Path(input_dir)
    if not input_path.exists():
        logger.error(f"입력 디렉토리를 찾을 수 없습니다: {input_dir}")
        return

    # 출력 폴더 생성
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    # 엔진 초기화
    structurer = GeminiStructurer()
    search_engine = EmbeddingSearchEngine()

    processed_novels = []
    
    # 텍스트 파일 목록 가져오기
    txt_files = list(input_path.glob("*.txt"))
    logger.info(f"📚 총 {len(txt_files)}개의 소설 파일을 발견했습니다.")

    for txt_file in txt_files:
        logger.info(f"📖 처리 중: {txt_file.name}")
        
        try:
            with open(txt_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 1. LLM 씬 분할 (Parent Chunks)
            logger.info(f"  ✂️ AI 씬 분할 시작...")
            scenes = structurer.split_scenes(content)
            logger.info(f"  ✅ {len(scenes)}개 씬 분할 완료")
            
            novel_chunks = []
            
            # 2. 각 씬별 Child Chunk 생성 및 임베딩
            for i, scene_text in enumerate(tqdm(scenes, desc=f"  Embedding {txt_file.name}")):
                # Child Chunks 생성 (200/50 방식)
                child_chunks = search_engine._split_into_child_chunks(scene_text)
                
                for j, chunk_text in enumerate(child_chunks):
                    # 임베딩 생성 (384차원 e5-small)
                    embedding = search_engine.embed_text(chunk_text)
                    
                    novel_chunks.append({
                        "chunk_id": f"{i}_{j}",
                        "scene_index": i,
                        "text": chunk_text,
                        "embedding": embedding,
                        "metadata": {
                            "novel": txt_file.name,
                            "scene_idx": i,
                            "chunk_idx": j
                        }
                    })
            
            processed_novels.append({
                "filename": txt_file.name,
                "chunks": novel_chunks
            })
            
        except Exception as e:
            logger.error(f"❌ {txt_file.name} 처리 중 오류 발생: {e}")
            continue

    # 3. 결과 저장
    output_data = {
        "model": settings.MULTILINGUAL_EMBEDDING_MODEL,
        "dimension": 384,
        "novels": {n["filename"]: {"chunks": n["chunks"]} for n in processed_novels}
    }
    
    # Legacy 형식 호환을 위한 리스트 형태도 생성
    legacy_format = processed_novels

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(legacy_format, f, ensure_ascii=False, indent=2)
    
    logger.info(f"🎉 전처리가 완료되었습니다! 결과 저장: {output_file}")

if __name__ == "__main__":
    # 실행 경로 설정
    CORPUS_DIR = os.path.join(project_root, "novel_corpus_kr")
    OUTPUT_FILE = os.path.join(project_root, "processed_results_new", "novel_embeddings.json")
    
    process_corpus(CORPUS_DIR, OUTPUT_FILE)
