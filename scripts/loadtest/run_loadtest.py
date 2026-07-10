"""
부하 생성기
===========
server_harness.py 로 띄운 API에 시나리오별 부하를 걸고
RPS / p50 / p95 / p99 / 에러율을 측정한다.

사용법:
  python scripts/loadtest/server_harness.py       # 터미널 1 (또는 백그라운드)
  python scripts/loadtest/run_loadtest.py [--quick]

출력: scripts/loadtest/results.json + 콘솔 마크다운 테이블
"""

import asyncio
import json
import os
import statistics
import sys
import time

import httpx

HERE = os.path.dirname(os.path.abspath(__file__))
SEED_PATH = os.path.join(HERE, "seed.json")
RESULTS_PATH = os.path.join(HERE, "results.json")

QUICK = "--quick" in sys.argv
DURATION = 8 if QUICK else 15          # 시나리오당 측정 시간(초)
CONCURRENCIES = [10] if QUICK else [10, 50]


def percentile(sorted_values, p):
    if not sorted_values:
        return 0.0
    k = (len(sorted_values) - 1) * (p / 100)
    f = int(k)
    c = min(f + 1, len(sorted_values) - 1)
    return sorted_values[f] + (sorted_values[c] - sorted_values[f]) * (k - f)


async def worker(client, scenario, deadline, latencies, errors):
    while time.perf_counter() < deadline:
        start = time.perf_counter()
        try:
            r = await client.request(
                scenario["method"], scenario["url"],
                headers=scenario.get("headers"),
                json=scenario.get("json"),
                timeout=30.0,
            )
            elapsed_ms = (time.perf_counter() - start) * 1000
            if r.status_code == scenario["expect"]:
                latencies.append(elapsed_ms)
            else:
                errors.append(r.status_code)
        except Exception:
            errors.append("EXC")


async def run_scenario(base_url, scenario, concurrency):
    latencies, errors = [], []
    async with httpx.AsyncClient(
        base_url=base_url,
        limits=httpx.Limits(max_connections=concurrency + 10),
    ) as client:
        # 워밍업 (측정 제외)
        warm_deadline = time.perf_counter() + 2
        await asyncio.gather(*[
            worker(client, scenario, warm_deadline, [], [])
            for _ in range(min(5, concurrency))
        ])

        deadline = time.perf_counter() + DURATION
        started = time.perf_counter()
        await asyncio.gather(*[
            worker(client, scenario, deadline, latencies, errors)
            for _ in range(concurrency)
        ])
        wall = time.perf_counter() - started

    total = len(latencies) + len(errors)
    latencies.sort()
    return {
        "scenario": scenario["name"],
        "concurrency": concurrency,
        "duration_s": round(wall, 1),
        "requests": total,
        "rps": round(total / wall, 1) if wall > 0 else 0,
        "error_rate_pct": round(len(errors) / total * 100, 2) if total else 0,
        "p50_ms": round(percentile(latencies, 50), 1),
        "p90_ms": round(percentile(latencies, 90), 1),
        "p95_ms": round(percentile(latencies, 95), 1),
        "p99_ms": round(percentile(latencies, 99), 1),
        "max_ms": round(latencies[-1], 1) if latencies else 0,
        "mean_ms": round(statistics.fmean(latencies), 1) if latencies else 0,
    }


def build_scenarios(seed):
    key_hdr = {"X-API-Key": seed["api_key"]}
    widget_hdr = {"Authorization": f"Bearer {seed['widget_token']}"}
    ms_id = seed["manuscript_id"]
    return [
        {
            "name": "baseline (GET /)",
            "method": "GET", "url": "/", "expect": 200,
        },
        {
            "name": "partner usage (GET /usage)",
            "method": "GET", "url": "/api/partner/v1/usage",
            "headers": key_hdr, "expect": 200,
        },
        {
            "name": "widget QA (POST /widget/v1/qa)",
            "method": "POST", "url": "/api/widget/v1/qa",
            "headers": widget_hdr,
            "json": {"question": "주인공이 왜 길드를 떠났어?"},
            "expect": 200,
        },
        {
            "name": "partner QA (POST /manuscripts/qa)",
            "method": "POST", "url": f"/api/partner/v1/manuscripts/{ms_id}/qa",
            "headers": key_hdr,
            "json": {"question": "주인공은 누구야?", "chapter_id": seed["chapter_id"]},
            "expect": 200,
        },
        {
            "name": "manuscript ingest (POST /manuscripts)",
            "method": "POST", "url": "/api/partner/v1/manuscripts",
            "headers": key_hdr,
            "json": {
                "title": "부하테스트 접수", "genre": "판타지",
                "chapters": [
                    {"chapter_number": 1, "title": "1화", "content": "본문 " * 500},
                    {"chapter_number": 2, "title": "2화", "content": "본문 " * 500},
                ],
            },
            "expect": 202,
        },
    ]


async def main():
    with open(SEED_PATH, encoding="utf-8") as f:
        seed = json.load(f)
    base_url = seed["base_url"]

    # 서버 준비 대기
    async with httpx.AsyncClient(base_url=base_url) as client:
        for _ in range(60):
            try:
                if (await client.get("/", timeout=2)).status_code == 200:
                    break
            except Exception:
                pass
            await asyncio.sleep(1)
        else:
            print("서버가 준비되지 않았습니다.", file=sys.stderr)
            sys.exit(1)

    results = []
    for concurrency in CONCURRENCIES:
        for scenario in build_scenarios(seed):
            print(f"[run] {scenario['name']} @ c={concurrency} ...", flush=True)
            results.append(await run_scenario(base_url, scenario, concurrency))

    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump({"seed": {k: v for k, v in seed.items() if k != "api_key" and k != "widget_token"},
                   "duration_per_scenario_s": DURATION,
                   "results": results}, f, ensure_ascii=False, indent=2)

    # 마크다운 테이블 출력
    print("\n| 시나리오 | 동시성 | RPS | p50(ms) | p95(ms) | p99(ms) | 에러율 |")
    print("|---|---|---|---|---|---|---|")
    for r in results:
        print(f"| {r['scenario']} | {r['concurrency']} | {r['rps']} "
              f"| {r['p50_ms']} | {r['p95_ms']} | {r['p99_ms']} | {r['error_rate_pct']}% |")
    print(f"\n결과 저장: {RESULTS_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
