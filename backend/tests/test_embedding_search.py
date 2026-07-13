"""임베딩/하이브리드 검색 유닛 테스트

2026-07-13 E2E 데모에서 발견된 두 가지 검색 품질 버그의 회귀 테스트:
1. 소규모 코퍼스에서 BM25 min-max 정규화가 0으로 수렴 → 하이브리드 점수가
   dense_weight(0.7)에 구조적으로 갇혀 답변 게이트(0.55)를 못 넘는 문제.
2. e5 계열 임베딩 모델에 "query: "/"passage: " 프리픽스가 누락된 문제.

Pinecone/DB 네트워크 호출 없이 순수 로직만 검증한다.
실행: pytest backend/tests/test_embedding_search.py -v
"""

import types
from unittest.mock import MagicMock

import pytest
from rank_bm25 import BM25Okapi
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.core.config import settings
from backend.db.models import Base, VectorDocument
from backend.services.analysis.embedding_engine import EmbeddingSearchEngine
import backend.services.analysis.embedding_engine as ee_mod


def _make_engine():
    """__init__(네트워크 호출 포함)을 건너뛰고 빈 인스턴스를 만든다."""
    engine = EmbeddingSearchEngine.__new__(EmbeddingSearchEngine)
    engine.model = None
    engine.model_name = settings.KOREAN_EMBEDDING_MODEL
    engine.pc = None
    engine.index = None
    engine.reranker = None
    engine.kiwi = None
    return engine


class TestEmbeddingPrefix:
    """e5 계열 모델은 query:/passage: 프리픽스가 있어야 의도된 성능이 나온다."""

    def test_embed_text_adds_query_prefix(self):
        engine = _make_engine()
        fake_model = MagicMock()
        fake_model.encode.return_value = MagicMock(tolist=lambda: [0.1, 0.2])
        engine._get_model = lambda: fake_model

        engine.embed_text("주인공은 누구야?")

        called_text = fake_model.encode.call_args[0][0]
        assert called_text == "query: 주인공은 누구야?"

    def test_embed_texts_batch_adds_passage_prefix(self):
        engine = _make_engine()
        fake_model = MagicMock()
        fake_model.encode.return_value = MagicMock(tolist=lambda: [[0.1], [0.2]])
        engine._get_model = lambda: fake_model

        engine.embed_texts_batch(["첫 문장", "둘째 문장"])

        called_texts = fake_model.encode.call_args[0][0]
        assert called_texts == ["passage: 첫 문장", "passage: 둘째 문장"]


class TestMergeResultsWeighting:
    """_merge_results는 순수 가중합 로직 — 버그의 핵심 메커니즘을 직접 검증."""

    def test_dense_only_weight_preserves_full_dense_score(self):
        engine = _make_engine()
        match = types.SimpleNamespace(score=0.8)

        merged = engine._merge_results(
            dense_matches={"novel_1_chap_1_scene_0_chunk_0": match},
            sparse_scores_dict={},
            dense_weight=1.0,
            sparse_weight=0.0,
        )

        assert merged[0].score == pytest.approx(0.8)

    def test_default_weight_caps_score_when_sparse_signal_absent(self):
        """수정 전 동작(버그 재현): sparse가 항상 0이면 0.7*dense에 갇힌다.

        dense_score=0.75는 e5 코사인 유사도로는 꽤 강한 매치인데도, sparse
        성분(30%)이 통째로 낭비되면 0.7*0.75=0.525로 답변 게이트(0.55)를
        구조적으로 못 넘는다 — 2026-07-13 발견 버그의 핵심 메커니즘.
        """
        engine = _make_engine()
        match = types.SimpleNamespace(score=0.75)

        merged = engine._merge_results(
            dense_matches={"novel_1_chap_1_scene_0_chunk_0": match},
            sparse_scores_dict={},
            dense_weight=0.7,
            sparse_weight=0.3,
        )

        assert merged[0].score == pytest.approx(0.525)
        assert merged[0].score < settings.CHATBOT_MIN_ANSWER_SIMILARITY


class TestSearchCorpusSizeGate:
    """search()가 코퍼스 크기에 따라 dense_weight를 올바르게 보정하는지 end-to-end 검증."""

    @pytest.fixture
    def db_session_factory(self, monkeypatch):
        engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
        tables = [t for name, t in Base.metadata.tables.items() if name != "analyses"]
        Base.metadata.create_all(engine, tables=tables)
        TestingSession = sessionmaker(bind=engine)
        monkeypatch.setattr(ee_mod, "SessionLocal", TestingSession)
        return TestingSession

    def _seed_vector_doc(self, session_factory, novel_id, chapter_id, scene_index, text):
        db = session_factory()
        vector_id = f"novel_{novel_id}_chap_{chapter_id}_scene_{scene_index}"
        db.add(VectorDocument(
            novel_id=novel_id, chapter_id=chapter_id, vector_id=vector_id,
            chunk_index=0, chunk_text=text, metadata_json={},
        ))
        db.commit()
        db.close()
        return vector_id

    def _make_dense_match(self, vector_id, score, novel_id, chapter_id, scene_index, text):
        return types.SimpleNamespace(
            id=f"{vector_id}_chunk_0", score=score,
            metadata={
                "novel_id": novel_id, "chapter_id": chapter_id,
                "scene_index": scene_index, "text": text,
            },
        )

    def _seed_bm25(self, novel_id, corpus_tokens):
        """_init_bm25()가 DB를 다시 읽지 않도록 글로벌 캐시를 직접 채운다."""
        ee_mod._global_bm25_map[novel_id] = BM25Okapi(corpus_tokens)
        ee_mod._global_corpus_indices_map[novel_id] = [
            f"novel_{novel_id}_chap_1_scene_{i}" for i in range(len(corpus_tokens))
        ]

    def teardown_method(self):
        ee_mod._global_bm25_map.clear()
        ee_mod._global_corpus_indices_map.clear()

    def test_small_corpus_falls_back_to_dense_only(self, db_session_factory):
        novel_id, chapter_id, scene_index = 101, 1, 0
        vector_id = self._seed_vector_doc(
            db_session_factory, novel_id, chapter_id, scene_index, "주인공은 위드다."
        )
        match = self._make_dense_match(vector_id, 0.8, novel_id, chapter_id, scene_index, "주인공은 위드다.")

        engine = _make_engine()
        engine._get_model = lambda: MagicMock(
            encode=MagicMock(return_value=MagicMock(tolist=lambda: [0.0] * 384))
        )
        engine.index = MagicMock()
        engine.index.query.return_value = types.SimpleNamespace(matches=[match])

        # 코퍼스 크기 1 < SEARCH_MIN_BM25_CORPUS_SIZE(5) → dense-only 폴백 발동
        self._seed_bm25(novel_id, [["위드"]])

        hits = engine.search(
            query="주인공은 누구야?", novel_id=novel_id, chapter_id=chapter_id,
            top_k=1, alpha=0.7, keywords=["위드"],
        )

        assert len(hits) == 1
        assert hits[0]["similarity"] == pytest.approx(0.8)

    def test_sufficient_corpus_with_signal_uses_configured_alpha(self, db_session_factory):
        novel_id, chapter_id, scene_index = 102, 1, 0
        vector_id = self._seed_vector_doc(
            db_session_factory, novel_id, chapter_id, scene_index, "주인공은 위드다."
        )
        match = self._make_dense_match(vector_id, 0.8, novel_id, chapter_id, scene_index, "주인공은 위드다.")

        engine = _make_engine()
        engine._get_model = lambda: MagicMock(
            encode=MagicMock(return_value=MagicMock(tolist=lambda: [0.0] * 384))
        )
        engine.index = MagicMock()
        engine.index.query.return_value = types.SimpleNamespace(matches=[match])

        # 코퍼스 크기 6 >= 임계값(5), 첫 문서만 쿼리 토큰을 포함해 정규화 시 최고점(1.0) 확보
        corpus_tokens = [["위드"]] + [["다른", "장면", str(i)] for i in range(5)]
        self._seed_bm25(novel_id, corpus_tokens)

        hits = engine.search(
            query="주인공은 누구야?", novel_id=novel_id, chapter_id=chapter_id,
            top_k=1, alpha=0.7, keywords=["위드"],
        )

        assert len(hits) == 1
        # 0.7*0.8(dense) + 0.3*1.0(sparse, 정규화 최고점) = 0.86
        assert hits[0]["similarity"] == pytest.approx(0.86, abs=0.01)
