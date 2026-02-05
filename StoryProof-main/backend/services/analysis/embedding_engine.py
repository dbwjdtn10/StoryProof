"""
임베딩 및 검색 엔진 모듈
BAAI/bge-m3 모델을 사용한 임베딩 생성 및 Pinecone 벡터 검색
"""

from typing import List, Dict

from backend.core.config import settings
from backend.db.session import SessionLocal
from backend.db.models import VectorDocument


class EmbeddingSearchEngine:
    """임베딩 기반 검색 엔진 (Pinecone 연동)"""
    
    def __init__(self):
        """
        BAAI/bge-m3 모델을 사용한 임베딩 생성
        Pinecone을 벡터 저장소로 사용
        """
        try:
            from sentence_transformers import SentenceTransformer
            from pinecone import Pinecone
        except ImportError:
            raise ImportError("sentence-transformers, pinecone 필요: pip install sentence-transformers pinecone")
        
        print("🔄 BAAI/bge-m3 모델 로딩 중...")
        self.model = SentenceTransformer('BAAI/bge-m3')
        print("✅ 임베딩 모델 로드 완료")
        
        # Pinecone 초기화
        self.pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        self.index_name = settings.PINECONE_INDEX_NAME
        
        # 인덱스 확인
        if self.index_name not in [idx.name for idx in self.pc.list_indexes()]:
            print(f"⚠️ Pinecone 인덱스 '{self.index_name}'가 존재하지 않습니다. 먼저 생성해주세요.")
        
        self.index = self.pc.Index(self.index_name)
        print(f"✅ Pinecone 인덱스 연결: {self.index_name}")
    
    def embed_text(self, text: str) -> List[float]:
        """텍스트를 임베딩 벡터로 변환"""
        embedding = self.model.encode(text, normalize_embeddings=True)
        return embedding.tolist()
    
    def add_documents(self, documents: List[Dict], novel_id: int):
        """문서들을 임베딩하여 Pinecone과 DB에 저장"""
        print(f"\n📥 {len(documents)}개 문서 처리 중...")
        
        db = SessionLocal()
        vectors_to_upsert = []
        
        try:
            for i, doc in enumerate(documents):
                # 검색용 텍스트 생성 (요약 + 원문 일부)
                search_text = f"{doc.get('summary', '')} {doc.get('original_text', '')[:1000]}"
                
                # 임베딩 생성
                embedding = self.embed_text(search_text)
                
                # 고유 ID 생성
                vector_id = f"novel_{novel_id}_scene_{doc['scene_index']}"
                
                # Pinecone 메타데이터 준비
                metadata = {
                    'novel_id': novel_id,
                    'scene_index': doc['scene_index'],
                    'summary': doc.get('summary', '')[:200],
                }
                
                vectors_to_upsert.append({
                    'id': vector_id,
                    'values': embedding,
                    'metadata': metadata
                })
                
                # DB에 상세 정보 저장 (VectorDocument)
                existing_doc = db.query(VectorDocument).filter(
                    VectorDocument.vector_id == vector_id
                ).first()
                
                if existing_doc:
                    existing_doc.chunk_text = doc.get('original_text', '')
                    existing_doc.metadata_json = doc
                else:
                    new_doc = VectorDocument(
                        novel_id=novel_id,
                        chapter_id=None,
                        vector_id=vector_id,
                        chunk_index=doc['scene_index'],
                        chunk_text=doc.get('original_text', ''),
                        metadata_json=doc
                    )
                    db.add(new_doc)
                
                if (i + 1) % 10 == 0:
                    print(f"  진행: {i + 1}/{len(documents)}")
            
            # Pinecone 업로드 (배치 처리)
            batch_size = 100
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
    
    def search(self, query: str, novel_id: int = None, top_k: int = 5) -> List[Dict]:
        """소설 내에서 쿼리와 유사한 씬 검색"""
        
        # 쿼리 임베딩
        query_embedding = self.embed_text(query)
        
        # Pinecone 쿼리 필터
        filter_dict = {}
        if novel_id:
            filter_dict['novel_id'] = novel_id
        
        # Pinecone 검색
        results = self.index.query(
            vector=query_embedding,
            top_k=top_k,
            include_metadata=True,
            filter=filter_dict if filter_dict else None
        )
        
        # 결과 매핑
        hits = []
        db = SessionLocal()
        try:
            for match in results.matches:
                vector_id = match.id
                score = match.score
                
                # DB에서 원본 데이터 조회
                doc = db.query(VectorDocument).filter(
                    VectorDocument.vector_id == vector_id
                ).first()
                
                if doc:
                    scene_data = doc.metadata_json
                    hits.append({
                        'document': scene_data,
                        'similarity': score,
                        'vector_id': vector_id
                    })
                else:
                    # DB에 없을 경우 Pinecone 메타데이터 사용
                    print(f"⚠️ DB에서 문서 {vector_id}를 찾을 수 없습니다.")
                    hits.append({
                        'document': {
                            'scene_index': match.metadata.get('scene_index'),
                            'summary': match.metadata.get('summary'),
                            'characters': [],
                            'locations': [],
                            'original_text': f"[Warning: DB Sync Error]\n{match.metadata.get('summary', '내용 없음')}"
                        },
                        'similarity': score,
                        'vector_id': vector_id
                    })
        finally:
            db.close()
        
        return hits
