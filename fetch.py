#!/usr/bin/env python3
"""
TrustMRR 全量抓取。

限速 20 req/min（官方），这里按 3.3s/次跑 ≈ 18 req/min 留余量。
每页 10 条硬上限，10,150 条 ≈ 1,015 次请求 ≈ 56 分钟。

断点续传：已抓到的页写进 data/startups.jsonl，重跑时跳过已有页。
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

BASE = "https://trustmrr.com/api/v1/startups"
OUT = "data/startups.jsonl"
STATE = "data/fetched_pages.json"
PER_PAGE = 10
SLEEP = 3.3          # 秒/请求 ≈ 18 req/min
MAX_RETRY = 5


def load_key():
    for line in open(".env"):
        line = line.strip()
        if line.startswith("TRUSTMRR_API_KEY="):
            return line.split("=", 1)[1].strip()
    sys.exit(".env 里没有 TRUSTMRR_API_KEY")


def fetch(page, key):
    """返回 (data, meta)；失败时抛异常。"""
    req = urllib.request.Request(
        f"{BASE}?limit={PER_PAGE}&page={page}",
        headers={
            "Authorization": f"Bearer {key}",
            "Accept": "application/json",
            "User-Agent": "solo-founder-revenue-research/1.0",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        body = json.loads(r.read().decode())
    return body.get("data", []), body.get("meta", {})


def main():
    key = load_key()
    os.makedirs("data", exist_ok=True)

    done = set()
    if os.path.exists(STATE):
        done = set(json.load(open(STATE)))
        print(f"续传：已完成 {len(done)} 页", flush=True)

    # 先探总数
    data, meta = fetch(1, key)
    total = meta.get("total", 0)
    pages = (total + PER_PAGE - 1) // PER_PAGE
    print(f"总计 {total} 条 / {pages} 页，预计 {pages * SLEEP / 60:.0f} 分钟", flush=True)

    out = open(OUT, "a", encoding="utf-8")
    t0 = time.time()

    for page in range(1, pages + 1):
        if page in done:
            continue

        for attempt in range(MAX_RETRY):
            try:
                rows, _ = fetch(page, key)
                for row in rows:
                    out.write(json.dumps(row, ensure_ascii=False) + "\n")
                out.flush()
                done.add(page)
                break
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    wait = 20 * (attempt + 1)
                    print(f"  p{page} 限速，等 {wait}s", flush=True)
                    time.sleep(wait)
                else:
                    print(f"  p{page} HTTP {e.code}，重试 {attempt+1}", flush=True)
                    time.sleep(5 * (attempt + 1))
            except Exception as e:
                print(f"  p{page} {type(e).__name__}，重试 {attempt+1}", flush=True)
                time.sleep(5 * (attempt + 1))
        else:
            print(f"  p{page} 放弃", flush=True)

        if page % 50 == 0:
            json.dump(sorted(done), open(STATE, "w"))
            el = time.time() - t0
            rate = len(done) / el * 60 if el else 0
            eta = (pages - len(done)) / rate if rate else 0
            print(f"[{len(done)}/{pages}] {rate:.1f} 页/分，剩余约 {eta:.0f} 分钟", flush=True)

        time.sleep(SLEEP)

    json.dump(sorted(done), open(STATE, "w"))
    out.close()
    print(f"完成：{len(done)}/{pages} 页 → {OUT}", flush=True)


if __name__ == "__main__":
    main()
