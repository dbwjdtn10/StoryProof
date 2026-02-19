"""
임베딩 및 검색 엔진 모듈
BAAI/bge-m3 모델을 사용한 임베딩 생성 및 Pinecone 벡터 검색
"""


import re
from typing import List, Dict, Any, Optional
import numpy as np
from rank_bm25 import BM25Okapi

from backend.core.config import settings
from backend.db.session import SessionLocal
from backend.db.models import VectorDocument

# 전역 모델 및 인덱스 캐시 (싱글톤)
_global_model = None
_global_reranker = None
_global_kiwi = None
_global_bm25_map = {}  # novel_id -> BM25Okapi
_global_corpus_indices_map = {}  # novel_id -> doc_id list


class EmbeddingSearchEngine:
    """임베딩 기반 검색 엔진 (Dual Model + Parent-Child Indexing) + Hybrid Search"""
    
    def __init__(self):
        """
        초기화: 모델은 지연 로딩 방식을 사용하여 필요할 때 로드합니다.
        단일 모델(dragonkue/multilingual-e5-small-ko)로 통합 운영합니다.
        """
        self.model = None
        self.reranker = None
        self.kiwi = None
        self.pc = None
        self.index = None
        self.bm25 = None
        self.corpus_indices = None # BM25용 인덱스 매핑 (index -> doc_id)
        
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
        
        # BM25는 검색 시 novel_id 기준으로 lazy loading 함
        self.bm25_map = _global_bm25_map
        self.corpus_indices_map = _global_corpus_indices_map

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
            available_indexes = []
            try:
                # v3.0.0+ 방식
                available_indexes = [idx.name for idx in self.pc.list_indexes()]
            except AttributeError:
                # v2.x 하위 호환성 (list_indexes가 문자열 리스트 반환)
                available_indexes = self.pc.list_indexes()

            if self.index_name not in available_indexes:
                print(f"[Warning] Pinecone 인덱스 '{self.index_name}'가 존재하지 않습니다.")
                print(f"[Index List] 사용 가능한 인덱스: {available_indexes}")
            else:
                self.index = self.pc.Index(self.index_name)
                print(f"[Success] Pinecone 인덱스 연결: {self.index_name}")
        except Exception as e:
            error_msg = str(e)
            print(f"[Error] Pinecone 초기화 실패: {error_msg}")
            # 만약 패키지 명칭 변경 관련 오류라면 더 명확한 해결 가이드 출력
            if "renamed" in error_msg.lower():
                print("💡 해결 방법: 터미널에서 'pip uninstall pinecone-client pinecone' 후 'pip install pinecone'을 실행하세요.")
                print(f"현재 Python: {sys.executable}")
    
    def _init_bm25(self, novel_id: int):
        """
        특정 소설(novel_id)의 BM25 인덱스 초기화 (Global Singleton Map 사용)
        """
        global _global_bm25_map, _global_corpus_indices_map
        
        if novel_id in _global_bm25_map:
            return
            
        print(f"[Info] Building BM25 Index for Novel {novel_id} (with Kiwi)...")
        kiwi = self._get_kiwi()
        db = SessionLocal()
        try:
            # 해당 소설의 Parent Scene 텍스트만 로드
            docs = db.query(VectorDocument).filter(VectorDocument.novel_id == novel_id).all()
            
            corpus = []
            corpus_indices = []
            
            for doc in docs:
                text = doc.chunk_text
                if not text: continue
                
                # Kiwi 형태소 분석기 적용
                tokens = [t.form for t in kiwi.tokenize(text)]
                corpus.append(tokens)
                corpus_indices.append(doc.vector_id)
            
            if corpus:
                bm25 = BM25Okapi(corpus)
                _global_bm25_map[novel_id] = bm25
                _global_corpus_indices_map[novel_id] = corpus_indices
                print(f"[Success] BM25 Index built for Novel {novel_id} with {len(corpus)} documents")
            else:
                print(f"[Warning] No documents found for BM25 (Novel {novel_id})")
                
        except Exception as e:
            print(f"[Error] Failed to build BM25 Index for Novel {novel_id}: {e}")
        finally:
            db.close()

    def _get_model(self):
        """모델 로드 및 반환 (Lazy Loading & Singleton)"""
        from sentence_transformers import SentenceTransformer
        global _global_model
        
        if _global_model is None:
            print(f"[Info] 모델 로딩 시작: {self.model_name}")
            _global_model = SentenceTransformer(self.model_name)
            print(f"[Success] 모델 로딩 완료: {self.model_name}")
            
        self.model = _global_model
        return self.model

    def _get_reranker(self):
        """Reranker 로드 및 반환 (Lazy Loading & Singleton)"""
        # 설정에서 Reranker 비활성화 시 None 반환
        if not settings.ENABLE_RERANKER:
            return None

        from sentence_transformers import CrossEncoder
        global _global_reranker
        
        # 설정된 Reranker 모델 (없으면 BAAI/bge-reranker-v2-m3 사용)
        reranker_name = getattr(settings, 'RERANKER_MODEL', "BAAI/bge-reranker-v2-m3")

        if _global_reranker is None:
            print(f"[Info] Reranker 로딩 시작: {reranker_name}")
            _global_reranker = CrossEncoder(reranker_name, max_length=512)
            print(f"[Success] Reranker 로딩 완료: {reranker_name}")
            
        self.reranker = _global_reranker
        return self.reranker

    def _get_kiwi(self):
        """Kiwi 형태소 분석기 로드 및 반환 (Lazy Loading & Singleton)"""
        from kiwipiepy import Kiwi
        global _global_kiwi
        
        if _global_kiwi is None:
            print(f"[Info] Kiwi Tokenizer 로딩 시작...")
            _global_kiwi = Kiwi()
            print(f"[Success] Kiwi Tokenizer 로딩 완료")
            
        self.kiwi = _global_kiwi
        return self.kiwi

    def warmup(self):
        """
        서버 시작 시 모델을 미리 로드하여 첫 요청 지연을 방지합니다.
        """
        print("[Warmup] EmbeddingSearchEngine: Preloading models...")
        try:
            self._get_model()    # SentenceTransformer 로드
            self._get_reranker() # CrossEncoder 로드
            self._get_kiwi()     # Kiwi 형태소 분석기 로드
            print("[Warmup] EmbeddingSearchEngine: All models loaded successfully.")
        except Exception as e:
            print(f"[Error] EmbeddingSearchEngine Warmup Failed: {e}")

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
                # [개선] 요약 + 본문 결합으로 검색 품질 향상
                # 요약에는 핵심 키워드가 압축되어 있어 질문과의 어휘 매칭 확률 증가
                # 테스트 결과: 평균 유사도 +2.8~5.9% 향상
                
                # 요약이 있으면 요약을 앞에 추가 (검색 정확도 향상)
                if summary:
                    combined_text = f"[요약] {summary}\n\n{original_text}"
                else:
                    combined_text = original_text
                
                child_chunks = self._split_into_child_chunks(combined_text)
                
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
                # 인덱스 연결 확인 및 재시도
                if self.index is None:
                    print("[Warning] Pinecone 인덱스가 연결되지 않았습니다. 재연결을 시도합니다...")
                    self._init_pinecone()
                    
                if self.index is None:
                    raise RuntimeError(f"Pinecone 인덱스 '{self.index_name}'에 연결할 수 없습니다. 설정을 확인하세요.")

                batch_size = 100
                print(f"[Action] 총 {len(vectors_to_upsert)}개의 Child Chunk를 Pinecone에 업로드합니다...")
                
                for i in range(0, len(vectors_to_upsert), batch_size):
                    batch = vectors_to_upsert[i:i + batch_size]
                    self.index.upsert(vectors=batch)
            
            db.commit()
            print("[Success] Pinecone 업로드 및 DB 저장 완료")
            
            # BM25 인덱스 재구축 (문서 추가 시 해당 소설 인덱스 삭제 유도)
            if novel_id in _global_bm25_map:
                del _global_bm25_map[novel_id]
                del _global_corpus_indices_map[novel_id]
            self._init_bm25(novel_id)
            
        except Exception as e:
            db.rollback()
            print(f"[Error] 문서 저장 실패: {e}")
            raise e
        finally:
            db.close()
    
    def search(
        self, 
        query: str, 
        novel_id: Optional[int] = None, 
        chapter_id: Optional[int] = None, 
        exclude_chapter_id: Optional[int] = None, 
        top_k: int = 5,
        alpha: float = 0.7, # 0.83 vs 0.7 비교 결과, 사용자 제안값인 0.7을 기본으로 채택 (키워드 비중 강화)
        keywords: Optional[List[str]] = None,
        original_query: Optional[str] = None
    ):
        """
        True Hybrid Search (Union of Dense + Sparse)
        
        Args:
            query (str): 검색 질문 (확장된 쿼리일 수 있음)
            novel_id (int): 필터링할 소설 ID
            chapter_id (int): 필터링할 회차 ID
            exclude_chapter_id (int): 제외할 회차 ID
            top_k (int): 반환할 상위 결과 수
            alpha (float): 밀집 검색(Vector) 가중치 (0.0 ~ 1.0)
            keywords (List[str]): 명시적 키워드 리스트
            original_query (str): 원본 질문 (리랭커에서 노이즈 없는 검색을 위해 사용)
        """
        # (Step 1-3 logic remains similar but updated)
        
        # --- 1. Dense Search (Pinecone) ---
        query_embedding = self.embed_text(query)
        
        filter_dict = {}
        if novel_id:
            filter_dict['novel_id'] = novel_id
        if chapter_id:
            filter_dict['chapter_id'] = chapter_id
        elif exclude_chapter_id:
            filter_dict['chapter_id'] = {"$ne": exclude_chapter_id}
        
        dense_results = self.index.query(
            vector=query_embedding,
            top_k=top_k * 10,
            include_metadata=True,
            filter=filter_dict if filter_dict else None
        )
        
        dense_matches = {m.id: m for m in dense_results.matches}
        
        # --- 2. Sparse Search (BM25) ---
        sparse_scores_dict = {}
        sparse_top_parents = []
        
        if novel_id:
            self._init_bm25(novel_id)
            bm25 = _global_bm25_map.get(novel_id)
            corpus_indices = _global_corpus_indices_map.get(novel_id)
            
            if bm25 and corpus_indices:
                if keywords:
                    tokenized_query = keywords
                else:
                    kiwi = self._get_kiwi()
                    tokenized_query = [t.form for t in kiwi.tokenize(query)]
            
                sparse_scores = bm25.get_scores(tokenized_query)
                
                if len(sparse_scores) > 0:
                    max_s = np.max(sparse_scores)
                    min_s = np.min(sparse_scores)
                    if max_s > min_s:
                        normalized_scores = (sparse_scores - min_s) / (max_s - min_s)
                    else:
                        normalized_scores = np.zeros_like(sparse_scores)
                    
                    for idx, norm_score in enumerate(normalized_scores):
                        parent_id = corpus_indices[idx]
                        sparse_scores_dict[parent_id] = float(norm_score)
                        if norm_score > 0:
                            sparse_top_parents.append((parent_id, norm_score))
                    
                    sparse_top_parents.sort(key=lambda x: x[1], reverse=True)
                    sparse_top_parents = sparse_top_parents[:top_k * 10]
        
        # --- 3. Union & Hybrid Scoring ---
        candidate_child_ids = set(dense_matches.keys())
        sparse_parent_ids_to_fetch = set()
        for p_id, _ in sparse_top_parents:
            found = any(c_id.startswith(p_id) for c_id in candidate_child_ids)
            if not found:
                sparse_parent_ids_to_fetch.add(p_id)
        
        if sparse_parent_ids_to_fetch:
            print(f"[Hybrid] Fetching {len(sparse_parent_ids_to_fetch)} sparse candidates from Pinecone...")
            for p_id in sparse_parent_ids_to_fetch:
                try:
                    parts = p_id.split('_')
                    s_idx = int(parts[parts.index('scene')+1])
                    c_id_filter = int(parts[parts.index('chap')+1])
                    
                    temp_res = self.index.query(
                        vector=query_embedding,
                        top_k=3, 
                        filter={"scene_index": s_idx, "novel_id": novel_id, "chapter_id": c_id_filter},
                        include_metadata=True
                    )
                    for t_match in temp_res.matches:
                        if t_match.id not in dense_matches:
                            dense_matches[t_match.id] = t_match
                except (ValueError, IndexError):
                    continue

        # --- 3. Result Merging & Scoring ---
        combined_candidates = self._merge_results(
            dense_matches=dense_matches,
            sparse_scores_dict=sparse_scores_dict,
            dense_weight=alpha,
            sparse_weight=(1.0 - alpha)
        )
        
        # --- 4. Reranking (Cross-Encoder) ---
        rerank_candidates = combined_candidates[:top_k * 10]
        final_results = []
        
        # 리랭킹에는 원본 질문(original_query)을 사용하여 노이즈 감소
        rank_query = original_query or query
        
        try:
            reranker = self._get_reranker()
            
            # Reranker가 활성화된 경우에만 실행
            if reranker:
                pairs = [[rank_query, m.metadata.get('text', '')] for m in rerank_candidates]
                
                if pairs:
                    # activation_fct=nn.Sigmoid() used internally if requested, 
                    # but we'll do it manually to ensure 0-1 range.
                    logits = reranker.predict(pairs)
                    
                    # Sigmoid function for normalization
                    def sigmoid(x):
                        return 1 / (1 + np.exp(-x))
                    
                    scores = sigmoid(logits)
                    
                    for i, match in enumerate(rerank_candidates):
                        match.score = float(scores[i])
                        final_results.append(match)
                    final_results.sort(key=lambda x: x.score, reverse=True)
                else:
                    final_results = rerank_candidates
            else:
                # Reranker 비활성화 시 Hybrid Score 그대로 사용
                # 단, Hybrid Score는 코사인 유사도(0-1)와 BM25(0-1 정규화)의 조합이므로
                # 그대로 사용해도 무방하지만, Reranker 점수와 호환성을 위해 스케일링 고려 가능
                # 현재는 그대로 사용 (Hybrid Score 자체가 신뢰도 지표)
                final_results = rerank_candidates
                
        except Exception as e:
            print(f"[Warning] Reranker failed: {e}. Fallback to Hybrid scores.")
            final_results = rerank_candidates

        # --- 5. Result Formatting & Parent Aggregation ---
        seen_keys = set()
        hits = []
        db = SessionLocal()
        
        try:
            for match in final_results:
                scene_index = int(match.metadata.get('scene_index'))
                match_chapter_id = match.metadata.get('chapter_id') or chapter_id
                
                key = (match_chapter_id, scene_index)
                if key in seen_keys: continue
                seen_keys.add(key)
                
                parent_vector_id = f"novel_{match.metadata.get('novel_id')}_chap_{match_chapter_id}_scene_{scene_index}"
                    
                doc = db.query(VectorDocument).filter(
                    VectorDocument.vector_id == parent_vector_id
                ).first()
                
                if doc:
                    scene_data = doc.metadata_json
                    scene_data['matched_chunk'] = match.metadata.get('text', '')
                    scene_data['similarity'] = match.score
                    
                    hits.append({
                        'document': scene_data,
                        'chapter_id': match_chapter_id,
                        'similarity': match.score,
                        'vector_id': match.id
                    })
                
                if len(hits) >= top_k:
                    break
        finally:
            db.close()
        
        return hits

    def _merge_results(
        self, 
        dense_matches: Dict[str, Any], 
        sparse_scores_dict: Dict[str, float],
        dense_weight: float = 0.7,
        sparse_weight: float = 0.3
    ) -> List[Any]:
        """
        벡터 검색 결과와 키워드 검색 결과를 병합하고 가중치에 따라 최종 점수를 계산합니다.
        """
        combined = []
        for c_id, match in dense_matches.items():
            parent_id = c_id.rsplit('_chunk_', 1)[0]
            dense_score = match.score
            sparse_score = sparse_scores_dict.get(parent_id, 0.0)
            
            # 최종 하이브리드 점수 계산
            match.score = (dense_weight * dense_score) + (sparse_weight * sparse_score)
            combined.append(match)
            
        # 점수 기준 내림차순 정렬
        combined.sort(key=lambda x: x.score, reverse=True)
        return combined
