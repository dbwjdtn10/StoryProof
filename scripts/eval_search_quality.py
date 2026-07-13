"""
검색 품질 평가 하네스 (Redis/Celery/Docker 불필요)
==================================================
scripts/eval/search_quality_corpus.py의 멀티챕터 테스트 소설을 실제
Gemini+Pinecone 파이프라인으로 색인한 뒤, 질문-정답 쌍을 파트너/위젯
API와 동일한 chatbot_service.ask()로 채점한다.

측정 항목:
- found 케이스: 근거를 찾았는지(found_context) + 답변에 기대 키워드 포함 여부
- not_found 케이스(스포일러 회차 필터 / 본문에 없는 사실): 정말 "못 찾음"으로
  답했는지 — 여기서 틀리면 회차 필터가 새고 있거나 환각이 발생한 것

사용법:
  python scripts/eval_search_quality.py            # 전체 실행
  python scripts/eval_search_quality.py --limit 3   # 앞 N개 질문만 (쿼터 절약용 스모크 테스트)

전제: .env에 GOOGLE_API_KEY / PINECONE_API_KEY 설정.
주의: Gemini 무료 티어는 하루 요청 한도가 낮다(모델당 20건). 코퍼스 색인만으로도
      여러 건 소모하니, 쿼터가 빠듯하면 --limit으로 질문 수를 줄여서 먼저 확인할 것.
"""

import argparse
import json
import os
import sys
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")  # Windows 콘솔(cp949)에서 이모지/특수문자 깨짐 방지

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scripts.eval.search_quality_corpus import CHAPTERS, QA_PAIRS  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(HERE, "eval_search_quality.db")
RESULTS_PATH = os.path.join(HERE, "eval", "results.json")


def step(msg):
    print(f"\n{'=' * 60}\n[STEP] {msg}\n{'=' * 60}", flush=True)


def rebind_sqlite():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    import backend.db.session as session_mod
    from backend.db.models import Base

    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
    session_mod.engine = engine
    session_mod.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(engine)
    return session_mod


def score(qa, result):
    found_context = bool(result.get("found_context"))
    answer = (result.get("answer") or "")

    if qa["expect"] == "found":
        keyword_hit = any(kw in answer for kw in qa["expected_keywords"])
        passed = found_context and keyword_hit
        reason = "" if passed else (
            "근거 못 찾음" if not found_context else "답변에 기대 키워드 없음"
        )
    else:  # not_found
        passed = not found_context
        reason = "" if passed else "찾으면 안 되는데 근거를 찾음(회차필터 누수/환각 위험)"

    return passed, reason


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="앞 N개 질문만 실행 (쿼터 절약)")
    args = parser.parse_args()

    from backend.core.config import settings
    if not settings.GOOGLE_API_KEY or not settings.PINECONE_API_KEY:
        print("[ERROR] .env에 GOOGLE_API_KEY / PINECONE_API_KEY를 설정하세요.")
        sys.exit(1)

    qa_pairs = QA_PAIRS[: args.limit] if args.limit else QA_PAIRS
    print(f"코퍼스: {len(CHAPTERS)}개 챕터 / 질문: {len(qa_pairs)}개 "
          f"(전체 {len(QA_PAIRS)}개 중)")

    session_mod = rebind_sqlite()

    # ---- 1. 코퍼스 시드 ----
    step("1/3 테스트 소설 시드")
    import secrets
    from backend.db.models import User, Novel, Chapter
    from backend.core.security import hash_password

    db = session_mod.SessionLocal()
    user = User(email="eval@internal", username="eval_user",
                hashed_password=hash_password(secrets.token_urlsafe(16)),
                is_active=True, is_verified=True)
    db.add(user)
    db.flush()
    novel = Novel(title="검색품질 평가용 소설", author_id=user.id)
    db.add(novel)
    db.flush()

    chapter_ids = {}
    for ch in CHAPTERS:
        chapter = Chapter(
            novel_id=novel.id, chapter_number=ch["chapter_number"], title=ch["title"],
            content=ch["content"], word_count=len(ch["content"]),
            storyboard_status="PENDING",
        )
        db.add(chapter)
        db.flush()
        chapter_ids[ch["chapter_number"]] = chapter.id
    db.commit()
    novel_id = novel.id
    db.close()
    print(f"novel_id={novel_id}, chapters={chapter_ids}")

    # ---- 2. 색인 (Celery 태스크 동기 실행) ----
    step("2/3 스토리보드 분석 — 씬 분할 → 구조화(Gemini) → 임베딩(Pinecone)")
    from backend.worker.tasks import process_chapter_storyboard
    from backend.db.models import Chapter as ChapterModel

    for num, cid in chapter_ids.items():
        t0 = time.time()
        process_chapter_storyboard(novel_id, cid)
        db = session_mod.SessionLocal()
        ch = db.query(ChapterModel).filter(ChapterModel.id == cid).first()
        status_ = ch.storyboard_status
        error_ = ch.storyboard_error
        db.close()
        print(f"  {num}화: {status_} ({time.time() - t0:.1f}초)")
        if status_ != "COMPLETED":
            print(f"[ERROR] {num}화 색인 실패: {error_}")
            sys.exit(1)

    print("Pinecone 인덱스 반영 대기 (10초)...")
    time.sleep(10)

    # ---- 3. Q&A 채점 ----
    step("3/3 Q&A 채점")
    from backend.services.chatbot_service import get_chatbot_service
    chatbot = get_chatbot_service()

    db = session_mod.SessionLocal()
    results = []
    for qa in qa_pairs:
        t0 = time.time()
        try:
            result = chatbot.ask(
                question=qa["question"], novel_id=novel_id,
                chapter_id=chapter_ids.get(qa["chapter_scope"]) if qa["chapter_scope"] else None,
                db=db,
            )
        except Exception as e:
            result = {"answer": f"[예외] {e}", "found_context": False, "similarity": 0.0}
        elapsed = time.time() - t0
        passed, reason = score(qa, result)

        results.append({
            "id": qa["id"], "question": qa["question"], "expect": qa["expect"],
            "chapter_scope": qa["chapter_scope"], "passed": passed, "reason": reason,
            "answer": result.get("answer"), "similarity": result.get("similarity"),
            "found_context": result.get("found_context"), "elapsed_s": round(elapsed, 1),
        })
        mark = "PASS" if passed else "FAIL"
        print(f"[{mark}] {qa['id']}: {qa['question']} "
              f"(유사도 {result.get('similarity', 0):.2f}, {elapsed:.1f}초)"
              + (f" — {reason}" if reason else ""))
    db.close()

    # ---- 정리: 평가용 Pinecone 벡터 삭제 ----
    step("정리 — 평가용 벡터 삭제")
    from backend.services.analysis.embedding_engine import get_embedding_search_engine
    engine = get_embedding_search_engine()
    for cid in chapter_ids.values():
        engine.delete_chapter_vectors(novel_id, cid)
    print("Pinecone 평가 벡터 삭제 완료")

    # ---- 리포트 ----
    total = len(results)
    passed_n = sum(1 for r in results if r["passed"])
    found_cases = [r for r in results if r["expect"] == "found"]
    not_found_cases = [r for r in results if r["expect"] == "not_found"]
    found_pass = sum(1 for r in found_cases if r["passed"])
    not_found_pass = sum(1 for r in not_found_cases if r["passed"])

    os.makedirs(os.path.dirname(RESULTS_PATH), exist_ok=True)
    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump({
            "total": total, "passed": passed_n,
            "found_recall": f"{found_pass}/{len(found_cases)}" if found_cases else "N/A",
            "not_found_precision": f"{not_found_pass}/{len(not_found_cases)}" if not_found_cases else "N/A",
            "results": results,
        }, f, ensure_ascii=False, indent=2)

    print(f"\n{'=' * 60}")
    print(f"[결과] {passed_n}/{total} 통과")
    print(f"  - found 케이스 recall: {found_pass}/{len(found_cases)}")
    print(f"  - not_found 케이스 정확도(오탐 방지): {not_found_pass}/{len(not_found_cases)}")
    print(f"결과 저장: {RESULTS_PATH}")
    print("=" * 60)

    sys.exit(0 if passed_n == total else 1)


if __name__ == "__main__":
    main()
