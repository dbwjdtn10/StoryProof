"""
임베딩 및 검색 엔진 모듈
BAAI/bge-m3 모델을 사용한 임베딩 생성 및 Pinecone 벡터 검색
"""

import re
from typing import List, Dict, Any, Optional

from backend.core.config import settings
from backend.db.session import SessionLocal
from backend.db.models import VectorDocument

# 전역 모델 캐시 (싱글톤)
_global_model = None


class EmbeddingSearchEngine:
    """임베딩 기반 검색 엔진 (Dual Model + Parent-Child Indexing)"""
    
    def __init__(self):
        """
        초기화: 모델은 지연 로딩 방식을 사용하여 필요할 때 로드합니다.
        단일 모델(dragonkue/multilingual-e5-small-ko)로 통합 운영합니다.
        """
        self.model = None
        self.pc = None
        self.index = None
        
        # 모델 이름 설정 (한국어/다국어 통합 처리)
        self.model_name = settings.KOREAN_EMBEDDING_MODEL
        
        # Pinecone 설정
        self.pinecone_api_key = settings.PINECONE_API_KEY
        self.index_name = settings.PINECONE_INDEX_NAME
        
        # 청킹 설정
        self.child_chunk_size = settings.CHILD_CHUNK_SIZE
        self.child_chunk_overlap = settings.CHILD_CHUNK_OVERLAP

        # 초기 Pinecone 연결 (인덱스 확인용)
        self._init_pinecone()

    def _init_pinecone(self):
        """Pinecone 클라이언트 및 인덱스 초기화"""
        import sys
        import os
        try:
            # 런타임 진단 정보 출력 (개발 시에만 유용)
            try:
                import pinecone
                # print(f"[DEBUG] Pinecone Module: {getattr(pinecone, '__file__', 'Unknown')}")
                # print(f"[DEBUG] Pinecone Version: {getattr(pinecone, '__version__', 'Unknown')}")
            except:
                pass

            from pinecone import Pinecone
            self.pc = Pinecone(api_key=self.pinecone_api_key)
            
            # 인덱스 확인
            if self.index_name not in [idx.name for idx in self.pc.list_indexes()]:
                print(f"⚠️ Pinecone 인덱스 '{self.index_name}'가 존재하지 않습니다.")
            else:
                self.index = self.pc.Index(self.index_name)
                print(f"✅ Pinecone 인덱스 연결: {self.index_name}")
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Pinecone 초기화 실패: {error_msg}")
            # 만약 패키지 명칭 변경 관련 오류라면 더 명확한 해결 가이드 출력
            if "renamed" in error_msg.lower():
                print("💡 해결 방법: 터미널에서 'pip uninstall pinecone-client pinecone' 후 'pip install pinecone'을 실행하세요.")
                print(f"현재 Python: {sys.executable}")

    def _get_model(self):
        """모델 로드 및 반환 (Lazy Loading & Singleton)"""
        from sentence_transformers import SentenceTransformer
        global _global_model
        
        if _global_model is None:
            print(f"🔄 모델 로딩 시작: {self.model_name}")
            _global_model = SentenceTransformer(self.model_name)
            print(f"✅ 모델 로딩 완료: {self.model_name}")
            
        self.model = _global_model
        return self.model

    def _split_into_child_chunks(self, text: str) -> List[str]:
        """Parent Scene을 지정된 크기의 Child Chunk로 분할 (Sliding Window)"""
        chunks = []
        if not text:
            return chunks
            
        step = self.child_chunk_size - self.child_chunk_overlap
        if step <= 0:
            step = 1
            
        for i in range(0, len(text), step):
            chunk = text[i:i + self.child_chunk_size]
            if len(chunk) < 50: # 너무 짧은 자투리는 제외 (옵션)
                continue
            chunks.append(chunk)
            
        # 텍스트가 짧아서 청크가 없는 경우 원본 그대로 추가
        if not chunks and text:
            chunks.append(text)
            
        return chunks

    def embed_text(self, text: str) -> List[float]:
        """텍스트를 임베딩 벡터로 변환"""
        model = self._get_model()
        embedding = model.encode(text, normalize_embeddings=True)
        return embedding.tolist()

    def add_documents(self, documents: List[Dict], novel_id: int, chapter_id: int):
        """
        Parent-Child Indexing 전략:
        1. DB에는 Parent Scene 전체 저장 (Bible/View용)
        2. Pinecone에는 Child Chunk 저장 (Search용)
        """
        print(f"\n📥 {len(documents)}개 씬(Parent) 처리 중... (Parent-Child Strategy)")
        
        db = SessionLocal()
        vectors_to_upsert = []
        
        try:
            # 0. 해당 챕터의 기존 VectorDocument(Parent) 및 Child 데이터 삭제 (초기화)
            # Pinecone에서도 삭제해야 하지만, ID 기반 덮어쓰기가 우선이므로 일단 DB부터 정리
            # 만약 씬 개수가 줄어들 경우를 위해 기존 챕터 데이터 삭제
            db.query(VectorDocument).filter(
                VectorDocument.novel_id == novel_id,
                VectorDocument.chapter_id == chapter_id
            ).delete()
            db.commit()

            for doc in documents:
                scene_index = doc['scene_index']
                original_text = doc.get('original_text', '')
                summary = doc.get('summary', '') 
                
                # 1. DB에 Parent Scene 저장
                # 고유 ID 생성 (Parent용) - Chapter ID 포함하여 충돌 방지
                parent_vector_id = f"novel_{novel_id}_chap_{chapter_id}_scene_{scene_index}"
                
                new_doc = VectorDocument(
                    novel_id=novel_id,
                    chapter_id=chapter_id,
                    vector_id=parent_vector_id,
                    chunk_index=scene_index,
                    chunk_text=original_text,
                    metadata_json=doc
                )
                db.add(new_doc)

                # 2. Child Chunk 생성 (Pinecone 용)
                # ... (rest of the logic remains similar but uses new parent_vector_id)
                
                # 2. Child Chunk 생성 및 임베딩 준비
                # 텍스트 = 요약 + 본문 (검색 정확도를 위해 요약도 앞단에 배치)
                # 하지만 정확한 위치 검색을 원한다면 본문만 자르는게 나을 수 있음.
                # 여기서는 본문 위주로 청킹.
                
                child_chunks = self._split_into_child_chunks(original_text)
                
                for i, chunk_text in enumerate(child_chunks):
                    # Child Chunk 임베딩
                    embedding = self.embed_text(chunk_text)
                    
                    # Child Vector ID
                    child_id = f"{parent_vector_id}_chunk_{i}"
                    
                    # Metadata (Parent 추적용)
                    metadata = {
                        'novel_id': novel_id,
                        'chapter_id': chapter_id,
                        'scene_index': scene_index,
                        'type': 'child', # 구분자
                        'text': chunk_text, # 검색 결과에서 하이라이트 매칭용으로 저장
                        'chunk_index': i
                    }
                    
                    vectors_to_upsert.append({
                        'id': child_id,
                        'values': embedding,
                        'metadata': metadata
                    })

                if (scene_index + 1) % 5 == 0:
                    print(f"  Parent 씬 처리 중: {scene_index + 1}/{len(documents)}")
            
            # Pinecone 업로드 (배치 처리)
            if vectors_to_upsert:
                batch_size = 100
                print(f"🚀 총 {len(vectors_to_upsert)}개의 Child Chunk를 Pinecone에 업로드합니다...")
                
                for i in range(0, len(vectors_to_upsert), batch_size):
                    batch = vectors_to_upsert[i:i + batch_size]
                    self.index.upsert(vectors=batch)
            
            db.commit()
            print("✅ Pinecone 업로드 및 DB 저장 완료")
            
        except Exception as e:
            db.rollback()
            print(f"❌ 문서 저장 실패: {e}")
            raise e
        finally:
            db.close()
    
    def search(self, query: str, novel_id: Optional[int] = None, chapter_id: Optional[int] = None, top_k: int = 5):
        """
        벡터 유사도 검색을 수행하고 Parent Scene 정보를 집계합니다.
        
        Args:
            query (str): 검색 질문
            novel_id (int): 필터링할 소설 ID
            chapter_id (int): 필터링할 회차 ID (선택)
            top_k (int): 반환할 상위 결과 수
        """
        query_embedding = self.embed_text(query)
        
        # Pinecone 필터
        filter_dict = {}
        if novel_id:
            filter_dict['novel_id'] = novel_id
        
        # 검색 (Child Chunk를 찾음)
        # top_k를 조금 넉넉하게 잡음 (같은 씬의 여러 청크가 나올 수 있으므로)
        search_limit = top_k * 3 
        
        results = self.index.query(
            vector=query_embedding,
            top_k=search_limit,
            include_metadata=True,
            filter=filter_dict if filter_dict else None
        )
        
        # Parent Scene 집계 (중복 제거)
        seen_keys = set() # (chapter_id, scene_index) 쌍으로 관리
        hits = []
        db = SessionLocal()
        
        try:
            for match in results.matches:
                scene_index = int(match.metadata.get('scene_index'))
                match_chapter_id = match.metadata.get('chapter_id') or chapter_id
                
                # 중복 체크 키 생성
                key = (match_chapter_id, scene_index)
                
                if key in seen_keys:
                    continue
                
                seen_keys.add(key)
                
                # DB에서 Parent Scene 조회
                if match_chapter_id:
                    parent_vector_id = f"novel_{novel_id}_chap_{match_chapter_id}_scene_{scene_index}"
                else:
                    parent_vector_id = f"novel_{novel_id}_scene_{scene_index}"
                    
                doc = db.query(VectorDocument).filter(
                    VectorDocument.vector_id == parent_vector_id
                ).first()
                
                if doc:
                    scene_data = doc.metadata_json
                    
                    # 매치된 Child Text 정보를 추가로 제공 (하이라이트 힌트용)
                    scene_data['matched_chunk'] = match.metadata.get('text', '')
                    scene_data['similarity'] = match.score
                    
                    hits.append({
                        'document': scene_data,
                        'chapter_id': chapter_id,
                        'similarity': match.score,
                        'vector_id': match.id
                    })
                
                if len(hits) >= top_k:
                    break
                    
        finally:
            db.close()
        
        return hits
