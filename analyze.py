#!/usr/bin/env python3
"""
TrustMRR 全量分析。

口径约定（这是整份分析最容易出错的地方，先写死）：
  mrr           = 月度经常性收入。**订阅制之外的产品这里恒为 0**，
                  Gumroad 就是例子：mrr=0 但 last30Days=$714 万。
  last30Days    = 过去 30 天实收（含一次性、交易抽成），是"现在有没有在赚钱"的真口径
  total         = 累计总收入，是"有没有赚到过钱"的口径

所以"$0"必须分三种说：
  从未赚过     total == 0
  曾经赚过归零  total > 0 且 last30Days == 0
  非订阅在赚   mrr == 0 但 last30Days > 0
"""
import json
import math
import statistics as st
from collections import Counter, defaultdict
from datetime import datetime, timezone

SRC = "data/startups.jsonl"
NOW = datetime(2026, 9, 4, tzinfo=timezone.utc)


def load():
    rows = []
    seen = set()
    for line in open(SRC, encoding="utf-8"):
        try:
            r = json.loads(line)
        except Exception:
            continue
        s = r.get("slug")
        if s in seen:          # 断点续传可能重复写
            continue
        seen.add(s)
        rows.append(r)
    return rows


def money(x):
    return f"${x:,.0f}"


def pct(a, b):
    return f"{a/b*100:.1f}%" if b else "—"


def gini(xs):
    xs = sorted(x for x in xs if x >= 0)
    n = len(xs)
    if n == 0 or sum(xs) == 0:
        return 0.0
    cum = sum((i + 1) * x for i, x in enumerate(xs))
    return (2 * cum) / (n * sum(xs)) - (n + 1) / n


def age_months(iso):
    if not iso:
        return None
    try:
        d = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except Exception:
        return None
    return (NOW - d).days / 30.44


def band(m):
    if m == 0: return "0"
    if m < 100: return "1–99"
    if m < 1000: return "100–999"
    if m < 5000: return "1k–4,999"
    if m < 10000: return "5k–9,999"
    if m < 50000: return "10k–49,999"
    return "50k+"


BANDS = ["0", "1–99", "100–999", "1k–4,999", "5k–9,999", "10k–49,999", "50k+"]


def section(t):
    print(f"\n{'='*72}\n{t}\n{'='*72}")


def main():
    rows = load()
    N = len(rows)
    mrr = [r["revenue"]["mrr"] or 0 for r in rows]
    l30 = [r["revenue"]["last30Days"] or 0 for r in rows]
    tot = [r["revenue"]["total"] or 0 for r in rows]

    section(f"0 · 样本  N = {N:,}")
    print(f"MRR 合计      {money(sum(mrr))}")
    print(f"近 30 天合计   {money(sum(l30))}")
    print(f"累计总收入     {money(sum(tot))}")

    # ---------- 1 三个口径的分布 ----------
    section("1 · 三个收入口径的分布（这是报告的地基）")
    for label, xs in (("MRR", mrr), ("近30天实收", l30), ("累计总收入", tot)):
        nz = [x for x in xs if x > 0]
        print(f"\n【{label}】")
        print(f"  =0        {sum(1 for x in xs if x==0):>6,}  {pct(sum(1 for x in xs if x==0), N)}")
        print(f"  >0        {len(nz):>6,}  {pct(len(nz), N)}")
        print(f"  中位数(全体) {money(st.median(xs))}")
        if nz:
            print(f"  中位数(非零) {money(st.median(nz))}")
        print(f"  平均数     {money(sum(xs)/N)}   ← 与中位数的差距 = 头部拉动")
        print(f"  Gini      {gini(xs):.3f}")
        s = sum(xs)
        if s:
            top = sorted(xs, reverse=True)
            for k in (1, 10):
                c = max(1, N * k // 100)
                print(f"  top {k}% 占总量  {pct(sum(top[:c]), s)}")

    section("2 · MRR 分档")
    c = Counter(band(m) for m in mrr)
    cum = 0
    for b in reversed(BANDS):
        cum += c[b]
        print(f"  {b:>12}  {c[b]:>6,}  {pct(c[b],N):>7}   ≥该档累计 {pct(cum,N)}")

    # ---------- 3 $0 的三分解 ----------
    section("3 · 「$0」到底是什么（关键修正）")
    never = [r for r in rows if (r["revenue"]["total"] or 0) == 0]
    once = [r for r in rows if (r["revenue"]["total"] or 0) > 0 and (r["revenue"]["last30Days"] or 0) == 0]
    onetime = [r for r in rows if (r["revenue"]["mrr"] or 0) == 0 and (r["revenue"]["last30Days"] or 0) > 0]
    print(f"  从未赚过一分钱   total=0            {len(never):>6,}  {pct(len(never),N)}")
    print(f"  曾赚过现已归零   total>0, 30d=0     {len(once):>6,}  {pct(len(once),N)}")
    print(f"  非订阅但在赚钱   mrr=0, 30d>0       {len(onetime):>6,}  {pct(len(onetime),N)}")
    z = sum(1 for m in mrr if m == 0)
    print(f"\n  MRR=0 合计 {z:,} ({pct(z,N)})，但其中 {len(onetime):,} 个近 30 天确实在赚钱")
    print(f"  → 「{pct(z,N)} 赚不到钱」是错的；正确说法是「{pct(len(never),N)} 从未赚到过一分钱」")

    # ---------- 4 年龄 ----------
    section("4 · 年龄：$0 是新品还是死品")
    def age_dist(group, name):
        ages = [a for a in (age_months(r.get("foundedDate")) for r in group) if a is not None]
        if not ages:
            print(f"  {name}: 无成立日期"); return
        buckets = [("≤3月",0,3),("3–6月",3,6),("6–12月",6,12),("1–2年",12,24),(">2年",24,1e9)]
        line = "  ".join(f"{n} {pct(sum(1 for a in ages if lo<=a<hi), len(ages))}" for n,lo,hi in buckets)
        print(f"  {name:<16} n={len(ages):>5,} 中位 {st.median(ages):>5.1f}月 | {line}")
    age_dist(never, "从未赚过")
    age_dist(once, "曾赚过归零")
    age_dist([r for r in rows if (r["revenue"]["mrr"] or 0) >= 5000], "MRR≥$5k")
    age_dist(rows, "全体")

    # ---------- 5 创始人集中度 ----------
    section("5 · 创始人集中度（抽样做不出来的东西）")
    byf = defaultdict(list)
    for r in rows:
        h = r.get("xHandle")
        if h:
            byf[h].append(r)

    print(f"  有创始人标识的产品 {sum(len(v) for v in byf.values()):,} / {N:,}")
    print(f"  去重创始人数       {len(byf):,}")
    multi = {k: v for k, v in byf.items() if len(v) > 1}
    print(f"  拥有 2 个以上产品的 {len(multi):,} 人，覆盖 {sum(len(v) for v in multi.values()):,} 个产品")
    print("\n  产品数最多的 12 位：")
    for h, v in sorted(byf.items(), key=lambda kv: -len(kv[1]))[:12]:
        tm = sum(x["revenue"]["mrr"] or 0 for x in v)
        nm = v[0].get("xFounderName") or h
        print(f"    @{h:<20} {len(v):>3} 个产品   MRR 合计 {money(tm):>12}   {nm}")

    win = [r for r in rows if (r["revenue"]["mrr"] or 0) >= 5000]
    wf = defaultdict(int)
    for r in win:
        if r.get("xHandle"):
            wf[r["xHandle"]] += 1
    print(f"\n  MRR≥$5k 的产品 {len(win):,} 个，来自 {len(wf):,} 位可识别创始人")
    rep = sum(1 for v in wf.values() if v > 1)
    print(f"  其中 {rep} 位拥有不止一个 $5k+ 产品（占这批创始人的 {pct(rep, len(wf))}）")

    # ---------- 6 品类 / 国家 ----------
    for field, title in (("category", "6 · 品类"), ("country", "7 · 国家")):
        section(f"{title}：成功密度（每个结论都带分母）")
        g = defaultdict(list)
        for r in rows:
            g[r.get(field) or "未标注"].append(r["revenue"]["mrr"] or 0)
        stats = []
        for k, v in g.items():
            if len(v) < 25:
                continue
            stats.append((k, len(v), sum(1 for x in v if x >= 5000) / len(v), st.median(v), sum(v)))
        print(f"  {'':<22}{'总数':>7}{'≥$5k占比':>10}{'中位MRR':>10}{'MRR合计':>14}")
        for k, n, rate, med, s in sorted(stats, key=lambda x: -x[2])[:14]:
            print(f"  {str(k)[:20]:<22}{n:>7,}{rate*100:>9.1f}%{money(med):>10}{money(s):>14}")

    # ---------- 8 AI ----------
    section("8 · AI 产品 vs 其余（控制年龄）")
    KW = ("ai", "gpt", "llm", "agent", "copilot", "generat", "prompt", "chatbot")
    def is_ai(r):
        t = f"{r.get('name','')} {r.get('description','')} {r.get('category','')}".lower()
        return any(k in t for k in KW)
    ai = [r for r in rows if is_ai(r)]
    non = [r for r in rows if not is_ai(r)]
    for name, grp in (("AI 相关", ai), ("非 AI", non)):
        m = [r["revenue"]["mrr"] or 0 for r in grp]
        ages = [a for a in (age_months(r.get("foundedDate")) for r in grp) if a is not None]
        print(f"  {name:<8} n={len(grp):>6,}  MRR=0 {pct(sum(1 for x in m if x==0),len(m)):>7}"
              f"  ≥$5k {pct(sum(1 for x in m if x>=5000),len(m)):>6}"
              f"  中位MRR {money(st.median(m)):>6}"
              f"  中位年龄 {st.median(ages):.1f}月" if ages else "")
    young = [r for r in rows if (age_months(r.get("foundedDate")) or 99) <= 12]
    ya, yn = [r for r in young if is_ai(r)], [r for r in young if not is_ai(r)]
    print("\n  只看成立 ≤12 个月的（控制年龄）：")
    for name, grp in (("AI 相关", ya), ("非 AI", yn)):
        m = [r["revenue"]["mrr"] or 0 for r in grp]
        if m:
            print(f"    {name:<8} n={len(grp):>6,}  MRR=0 {pct(sum(1 for x in m if x==0),len(m)):>7}"
                  f"  ≥$5k {pct(sum(1 for x in m if x>=5000),len(m)):>6}")

    # ---------- 9 增长与在售 ----------
    section("9 · 增长、订阅、在售")
    gr = [r.get("growthMRR30d") for r in rows if isinstance(r.get("growthMRR30d"), (int, float))]
    if gr:
        print(f"  有 MRR 增长率的 {len(gr):,} 个，中位 {st.median(gr):.1f}%，"
              f"负增长占 {pct(sum(1 for x in gr if x<0), len(gr))}")
    subs = [r.get("activeSubscriptions") or 0 for r in rows]
    print(f"  活跃订阅数：中位 {st.median(subs):.0f}，为 0 的占 {pct(sum(1 for x in subs if x==0), N)}")
    sale = [r for r in rows if r.get("onSale")]
    print(f"  挂牌出售 {len(sale):,} 个 ({pct(len(sale),N)})")
    mult = [r.get("multiple") for r in sale if isinstance(r.get("multiple"), (int, float))]
    if mult:
        print(f"  其中 {len(mult)} 个有估值倍数，中位 {st.median(mult):.1f}x")

    # ---------- 10 达到 $5k 的绝对数 ----------
    section("10 · 结论性数字")
    for th in (1000, 5000, 6000, 10000):
        c = sum(1 for m in mrr if m >= th)
        print(f"  MRR ≥ {money(th):>8}：{c:>6,} 个  {pct(c,N):>7}   （每 {N/c:.0f} 个产品里 1 个）" if c else "")
    ever = sum(1 for t in tot if t > 0)
    print(f"\n  曾赚到过任何钱：{ever:,}  {pct(ever,N)}")
    print(f"  近30天在赚钱：  {sum(1 for x in l30 if x>0):,}  {pct(sum(1 for x in l30 if x>0),N)}")


if __name__ == "__main__":
    main()
