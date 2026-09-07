#!/usr/bin/env python3
"""
测量数据新鲜度：API 不返回同步时间，只有详情页 .md 有。

抽样策略：
  A 组 = MRR 最高的 40 条（它们主导所有聚合数字，最该查）
  B 组 = 随机 40 条（估计全站过期率）
限速与主抓取一致。
"""
import json, random, re, time, urllib.request
from datetime import datetime, timezone

NOW = datetime(2026, 9, 4, tzinfo=timezone.utc)
SLEEP = 3.3

rows = [json.loads(l) for l in open("data/startups.jsonl")]
top = sorted(rows, key=lambda r: -(r["revenue"]["mrr"] or 0))[:40]
random.seed(20260904)
rest = [r for r in rows if r not in top]
rnd = random.sample(rest, 40)

PAT_SYNC = re.compile(r"(?:last synced|Data Last Updated)[^0-9]{0,20}(\d{4}-\d{2}-\d{2})", re.I)
PAT_EXP = re.compile(r"(expired|disconnected|invalid|revoked)", re.I)


def probe(slug):
    try:
        req = urllib.request.Request(
            f"https://trustmrr.com/startup/{slug}.md",
            headers={"User-Agent": "solo-founder-revenue-research/1.0"},
        )
        with urllib.request.urlopen(req, timeout=25) as r:
            txt = r.read().decode("utf-8", "replace")
    except Exception as e:
        return None, None, f"ERR {type(e).__name__}"
    m = PAT_SYNC.search(txt)
    d = None
    if m:
        try:
            d = (NOW - datetime.fromisoformat(m.group(1) + "T00:00:00+00:00")).days
        except Exception:
            pass
    return d, bool(PAT_EXP.search(txt)), None


def run(group, name):
    out = []
    print(f"\n=== {name} (n={len(group)}) ===", flush=True)
    for r in group:
        days, expired, err = probe(r["slug"])
        out.append((r, days, expired, err))
        flag = "过期" if expired else ("?" if days is None else f"{days}天前")
        print(f"  {r['name'][:26]:<28} MRR ${r['revenue']['mrr'] or 0:>10,.0f}  {flag}{' '+err if err else ''}", flush=True)
        time.sleep(SLEEP)
    ok = [d for _, d, _, e in out if d is not None]
    exp = sum(1 for _, _, x, _ in out if x)
    stale = sum(1 for d in ok if d > 30)
    print(f"  → 可测 {len(ok)}/{len(group)}；标记过期 {exp}；同步超 30 天 {stale}", flush=True)
    if ok:
        ok.sort()
        print(f"  → 同步滞后中位 {ok[len(ok)//2]} 天，最久 {ok[-1]} 天", flush=True)
    # 加权：这批的 MRR 里有多少来自过期记录
    tm = sum(r["revenue"]["mrr"] or 0 for r, _, _, _ in out)
    sm = sum(r["revenue"]["mrr"] or 0 for r, d, x, _ in out if x or (d or 0) > 30)
    if tm:
        print(f"  → 该组 MRR 中来自过期/陈旧记录的占 {sm/tm*100:.1f}%", flush=True)
    return out


a = run(top, "A 组：MRR 前 40（主导聚合数字）")
b = run(rnd, "B 组：随机 40（估计全站）")
json.dump(
    [{"slug": r["slug"], "mrr": r["revenue"]["mrr"], "days": d, "expired": x, "err": e}
     for grp in (a, b) for r, d, x, e in grp],
    open("data/staleness.json", "w"), ensure_ascii=False, indent=1)
print("\n写入 data/staleness.json")
