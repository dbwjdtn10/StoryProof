"""
임베딩 및 검색 엔진 모듈
BAAI/bge-m3 모델을 사용한 임베딩 생성 및 Pinecone 벡터 검색
"""


import re
import time
import logging
import threading
from typing import List, Dict, Any, Optional
import numpy as np
from rank_bm25 import BM25Okapi

from backend.core.config import settings
from backend.db.session import SessionLocal
from backend.db.models import VectorDocument

logger = logging.getLogger(__name__)

# 전역 모델 및 인덱스 캐시 (싱글톤)
_global_model = None
_global_reranker = None
_global_kiwi = None
_global_bm25_map = {}  # novel_id -> BM25Okapi
_global_bm25_dirty = set()  # lazy rebuild 대상 novel_id
_global_corpus_indices_map = {}  # novel_id -> doc_id list
_bm25_lock = threading.Lock()  # BM25 캐시 동시 접근 보호

# EmbeddingSearchEngine 싱글톤
_global_engine = None
_engine_lock = threading.Lock()


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

    def _init_pinecone(self, max_retries: int = 3):
        """Pinecone 클라이언트 및 인덱스 초기화 (재시도 포함)"""
        import sys
        for attempt in range(max_retries):
            try:
                from pinecone import Pinecone
                self.pc = Pinecone(api_key=self.pinecone_api_key)

                available_indexes = []
                try:
                    available_indexes = [idx.name for idx in self.pc.list_indexes()]
                except AttributeError:
                    available_indexes = self.pc.list_indexes()

                if self.index_name not in available_indexes:
                    logger.warning(f"Pinecone 인덱스 '{self.index_name}' 없음. 사용 가능: {available_indexes}")
                else:
                    self.index = self.pc.Index(self.index_name)
                    logger.info(f"Pinecone 인덱스 연결 성공: {self.index_name}")
                return  # 성공 시 종료
            except Exception as e:
                error_msg = str(e)
                if "renamed" in error_msg.lower():
                    logger.error(f"Pinecone 패키지 충돌: {error_msg}. "
                                 f"'pip uninstall pinecone-client pinecone && pip install pinecone' 실행 필요. "
                                 f"Python: {sys.executable}")
                    return  # 패키지 문제는 재시도 무의미
                if attempt < max_retries - 1:
                    wait = 2 ** attempt  # 1s, 2s, 4s
                    logger.warning(f"Pinecone 초기화 실패 (시도 {attempt+1}/{max_retries}): {e}. {wait}초 후 재시도...")
                    time.sleep(wait)
                else:
                    logger.error(f"Pinecone 초기화 최종 실패 ({max_retries}회 시도): {e}")
    
    def _init_bm25(self, novel_id: int):
        """
        특정 소설(novel_id)의 BM25 인덱스 초기화 (Global Singleton Map 사용)
        dirty 플래그가 설정된 경우 강제 재구축합니다.
        """
        global _global_bm25_map, _global_corpus_indices_map, _global_bm25_dirty

        with _bm25_lock:
            # dirty 플래그가 있으면 기존 캐시 삭제 후 재구축
            if novel_id in _global_bm25_dirty:
                _global_bm25_map.pop(novel_id, None)
                _global_corpus_indices_map.pop(novel_id, None)
                _global_bm25_dirty.discard(novel_id)

            if novel_id in _global_bm25_map:
                return

        logger.info(f"Building BM25 Index for Novel {novel_id} (with Kiwi POS filtering)...")
        db = SessionLocal()
        try:
            # 해당 소설의 Parent Scene 텍스트만 로드
            docs = db.query(VectorDocument).filter(VectorDocument.novel_id == novel_id).all()

            corpus = []
            corpus_indices = []

            for doc in docs:
                text = doc.chunk_text
                if not text: continue

                # 요약이 있으면 텍스트에 포함 (BM25 키워드 커버리지 확대)
                metadata = doc.metadata_json or {}
                summary = metadata.get('summary', '')
                if summary:
                    text = f"{summary} {text}"

                # Kiwi 형태소 분석기 적용 (POS 필터링: 내용어만)
                tokens = self._tokenize_for_bm25(text)
                corpus.append(tokens)
                corpus_indices.append(doc.vector_id)

            with _bm25_lock:
                if corpus:
                    bm25 = BM25Okapi(corpus)
                    _global_bm25_map[novel_id] = bm25
                    _global_corpus_indices_map[novel_id] = corpus_indices
                    logger.info(f"BM25 Index built for Novel {novel_id} with {len(corpus)} documents")
                else:
                    logger.warning(f"No documents found for BM25 (Novel {novel_id})")

        except Exception as e:
            logger.error(f"Failed to build BM25 Index for Novel {novel_id}: {e}")
        finally:
            db.close()

    def _get_model(self):
        """모델 로드 및 반환 (Lazy Loading & Singleton)"""
        from sentence_transformers import SentenceTransformer
        global _global_model
        
        if _global_model is None:
            logger.info(f"모델 로딩 시작: {self.model_name}")
            _global_model = SentenceTransformer(self.model_name)
            logger.info(f"모델 로딩 완료: {self.model_name}")
            
        self.model = _global_model
        return self.model

    def _get_reranker(self):
        """Reranker 로드 및 반환 (Lazy Loading & Singleton)"""
        from sentence_transformers import CrossEncoder
        global _global_reranker
        
        reranker_name = settings.RERANKER_MODEL

        if _global_reranker is None:
            logger.info(f"Reranker 로딩 시작: {reranker_name}")
            _global_reranker = CrossEncoder(reranker_name, max_length=512)
            logger.info(f"Reranker 로딩 완료: {reranker_name}")
            
        self.reranker = _global_reranker
        return self.reranker

    # BM25에 사용할 품사 태그 (내용어만 선별)
    _BM25_POS_TAGS = frozenset({'NNG', 'NNP', 'NNB', 'VV', 'VA', 'SL', 'SH'})

    def _get_kiwi(self):
        """Kiwi 형태소 분석기 로드 및 반환 (Lazy Loading & Singleton)"""
        from kiwipiepy import Kiwi
        global _global_kiwi

        if _global_kiwi is None:
            logger.info("Kiwi Tokenizer 로딩 시작...")
            _global_kiwi = Kiwi()
            logger.info("Kiwi Tokenizer 로딩 완료")

        self.kiwi = _global_kiwi
        return self.kiwi

    def _tokenize_for_bm25(self, text: str) -> List[str]:
        """BM25용 토큰화: 내용어(명사/동사/형용사/외국어)만 추출하여 검색 정밀도 향상"""
        kiwi = self._get_kiwi()
        return [t.form for t in kiwi.tokenize(text) if t.tag in self._BM25_POS_TAGS]

    def warmup(self):
        """
        서버 시작 시 모델을 미리 로드하여 첫 요청 지연을 방지합니다.
        """
        import os
        # os.environ 직접 확인 (pydantic .env 로딩 우회, 기본값 False)
        _enable_reranker = os.environ.get('ENABLE_RERANKER', 'false').strip().lower() in ('true', '1', 'yes')
        logger.info("EmbeddingSearchEngine: Preloading models...")
        try:
            self._get_model()    # SentenceTransformer 로드
            if _enable_reranker:
                self._get_reranker() # CrossEncoder 로드
            else:
                logger.info("Reranker 비활성화")
            self._get_kiwi()     # Kiwi 형태소 분석기 로드
            logger.info("EmbeddingSearchEngine: All models loaded successfully.")
        except Exception as e:
            logger.error(f"EmbeddingSearchEngine Warmup Failed: {e}")

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

    def embed_texts_batch(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """여러 텍스트를 배치로 임베딩 변환 (개별 호출 대비 30-40x 빠름)"""
        model = self._get_model()
        embeddings = model.encode(texts, normalize_embeddings=True, batch_size=batch_size)
        return embeddings.tolist()

    def delete_chapter_vectors(self, novel_id: int, chapter_id: int):
        """챕터 삭제 시 Pinecone 벡터 및 BM25 캐시 정리"""
        global _global_bm25_map, _global_corpus_indices_map

        if self.index is not None:
            try:
                self.index.delete(filter={
                    "novel_id": {"$eq": novel_id},
                    "chapter_id": {"$eq": chapter_id}
                })
                logger.info(f"Deleted Pinecone vectors for novel={novel_id}, chapter={chapter_id}")
            except Exception as e:
                logger.warning(f"Pinecone 벡터 삭제 실패 (novel={novel_id}, chapter={chapter_id}): {e}")

        # BM25 캐시 무효화 (lazy rebuild: 검색 시점에 재구축)
        with _bm25_lock:
            _global_bm25_dirty.add(novel_id)

    def add_documents(self, documents: List[Dict], novel_id: int, chapter_id: int):
        """
        Parent-Child Indexing 전략:
        1. DB에는 Parent Scene 전체 저장 (Bible/View용)
        2. Pinecone에는 Child Chunk 저장 (Search용)
        """
        logger.info(f"{len(documents)}개 씬(Parent) 처리 중... (Parent-Child Strategy)")
        
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

            # Phase 1: DB 저장 + Child Chunk 텍스트 수집 (임베딩 전)
            all_chunk_texts = []
            all_chunk_meta = []  # (parent_vector_id, scene_index, chunk_index)

            for doc in documents:
                scene_index = doc['scene_index']
                original_text = doc.get('original_text', '')
                summary = doc.get('summary', '')

                # 1. DB에 Parent Scene 저장
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

                # 2. Child Chunk 텍스트 수집
                if summary:
                    combined_text = f"[요약] {summary}\n\n{original_text}"
                else:
                    combined_text = original_text

                child_chunks = self._split_into_child_chunks(combined_text)

                for i, chunk_text in enumerate(child_chunks):
                    all_chunk_texts.append(chunk_text)
                    all_chunk_meta.append((parent_vector_id, scene_index, i, chunk_text))

                if (scene_index + 1) % 5 == 0:
                    logger.info(f"Parent 씬 처리 중: {scene_index + 1}/{len(documents)}")

            # Phase 2: 배치 임베딩 (개별 호출 대비 30-40x 빠름)
            logger.info(f"배치 임베딩 시작: {len(all_chunk_texts)}개 청크")
            all_embeddings = self.embed_texts_batch(all_chunk_texts) if all_chunk_texts else []

            # Phase 3: 벡터 조립
            for idx, (parent_id, scene_index, chunk_idx, chunk_text) in enumerate(all_chunk_meta):
                child_id = f"{parent_id}_chunk_{chunk_idx}"
                metadata = {
                    'novel_id': novel_id,
                    'chapter_id': chapter_id,
                    'scene_index': scene_index,
                    'type': 'child',
                    'text': chunk_text,
                    'chunk_index': chunk_idx
                }
                vectors_to_upsert.append({
                    'id': child_id,
                    'values': all_embeddings[idx],
                    'metadata': metadata
                })
            
            # Pinecone 업로드 (배치 처리)
            if vectors_to_upsert:
                # 인덱스 연결 확인 및 재시도
                if self.index is None:
                    logger.warning("Pinecone 인덱스가 연결되지 않았습니다. 재연결을 시도합니다...")
                    self._init_pinecone()
                    
                if self.index is None:
                    raise RuntimeError(f"Pinecone 인덱스 '{self.index_name}'에 연결할 수 없습니다. 설정을 확인하세요.")

                batch_size = 100
                logger.info(f"총 {len(vectors_to_upsert)}개의 Child Chunk를 Pinecone에 업로드합니다...")
                
                for i in range(0, len(vectors_to_upsert), batch_size):
                    batch = vectors_to_upsert[i:i + batch_size]
                    self.index.upsert(vectors=batch)
            
            db.commit()
            logger.info("Pinecone 업로드 및 DB 저장 완료")
            
            # BM25 인덱스 lazy rebuild: dirty 마킹만 하고 검색 시점에 재구축
            with _bm25_lock:
                _global_bm25_dirty.add(novel_id)
            
        except Exception as e:
            db.rollback()
            logger.error(f"문서 저장 실패: {e}")
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
        # Pinecone 인덱스가 None이면 재연결 시도
        if self.index is None:
            self._init_pinecone()
            if self.index is None:
                logger.warning("Pinecone 사용 불가. BM25-only 폴백 검색 수행")
                return self._bm25_only_search(query, novel_id, top_k, keywords)

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
                    tokenized_query = self._tokenize_for_bm25(query)
            
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
            logger.debug(f"Fetching {len(sparse_parent_ids_to_fetch)} sparse candidates from Pinecone...")
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
        
        if settings.ENABLE_RERANKER:
            try:
                reranker = self._get_reranker()
                pairs = [[rank_query, m.metadata.get('text', '')] for m in rerank_candidates]

                if pairs:
                    logits = reranker.predict(pairs)

                    def sigmoid(x):
                        return 1 / (1 + np.exp(-x))

                    scores = sigmoid(logits)

                    for i, match in enumerate(rerank_candidates):
                        match.score = float(scores[i])
                        final_results.append(match)
                    final_results.sort(key=lambda x: x.score, reverse=True)
                else:
                    final_results = rerank_candidates
            except Exception as e:
                logger.warning(f"Reranker failed: {e}. Fallback to Hybrid scores.")
                final_results = rerank_candidates
        else:
            final_results = rerank_candidates

        # --- 5. Result Formatting & Parent Aggregation (Batch DB query) ---
        seen_keys = set()
        unique_matches = []  # (match, parent_vector_id)
        for match in final_results:
            scene_index = int(match.metadata.get('scene_index'))
            match_chapter_id = match.metadata.get('chapter_id') or chapter_id
            key = (match_chapter_id, scene_index)
            if key in seen_keys:
                continue
            seen_keys.add(key)
            parent_vector_id = f"novel_{match.metadata.get('novel_id')}_chap_{match_chapter_id}_scene_{scene_index}"
            unique_matches.append((match, parent_vector_id))
            if len(unique_matches) >= top_k:
                break

        hits = []
        db = SessionLocal()
        try:
            # 배치 DB 조회 (N+1 → 1 쿼리)
            parent_ids = [pid for _, pid in unique_matches]
            docs = db.query(VectorDocument).filter(
                VectorDocument.vector_id.in_(parent_ids)
            ).all()
            doc_map = {d.vector_id: d for d in docs}

            for match, parent_vector_id in unique_matches:
                doc = doc_map.get(parent_vector_id)
                if doc:
                    scene_data = doc.metadata_json
                    scene_data['matched_chunk'] = match.metadata.get('text', '')
                    scene_data['similarity'] = match.score
                    hits.append({
                        'document': scene_data,
                        'chapter_id': match.metadata.get('chapter_id') or chapter_id,
                        'similarity': match.score,
                        'vector_id': match.id
                    })
        finally:
            db.close()
        
        return hits

    def _bm25_only_search(
        self,
        query: str,
        novel_id: Optional[int],
        top_k: int = 5,
        keywords: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Pinecone 사용 불가 시 BM25(키워드)만으로 검색하는 폴백.
        DB의 VectorDocument에서 Parent Scene을 직접 조회합니다.
        """
        if not novel_id:
            return []

        self._init_bm25(novel_id)
        bm25 = _global_bm25_map.get(novel_id)
        corpus_indices = _global_corpus_indices_map.get(novel_id)

        if not bm25 or not corpus_indices:
            logger.warning(f"BM25 인덱스 없음 (novel={novel_id}). 폴백 검색 불가")
            return []

        if keywords:
            tokenized_query = keywords
        else:
            tokenized_query = self._tokenize_for_bm25(query)

        scores = bm25.get_scores(tokenized_query)
        top_indices = np.argsort(scores)[::-1][:top_k]

        hits = []
        db = SessionLocal()
        try:
            for idx in top_indices:
                if scores[idx] <= 0:
                    continue
                parent_vector_id = corpus_indices[idx]
                doc = db.query(VectorDocument).filter(
                    VectorDocument.vector_id == parent_vector_id
                ).first()
                if doc and doc.metadata_json:
                    scene_data = doc.metadata_json
                    # BM25 점수를 0~1 범위로 정규화
                    max_score = float(np.max(scores)) if np.max(scores) > 0 else 1.0
                    norm_score = float(scores[idx]) / max_score
                    scene_data['similarity'] = norm_score
                    hits.append({
                        'document': scene_data,
                        'chapter_id': doc.chapter_id,
                        'similarity': norm_score,
                        'vector_id': parent_vector_id
                    })
        finally:
            db.close()

        logger.info(f"BM25-only 폴백 검색 완료: {len(hits)}건 (novel={novel_id})")
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


def get_embedding_search_engine() -> EmbeddingSearchEngine:
    """EmbeddingSearchEngine 싱글톤 인스턴스 반환 (스레드 안전)"""
    global _global_engine
    if _global_engine is None:
        with _engine_lock:
            if _global_engine is None:
                _global_engine = EmbeddingSearchEngine()
    return _global_engine
