#!/usr/bin/env python3
"""
Produce data/startups-anon.jsonl: every field the analysis needs, none that names a product
or a founder who did not choose to be named.

Why: the raw dump carries the name and founder handle of all 10,150 products, including the
2,654 that never earned a cent. The post's rule is that products and founders who did not
earn are reported only in aggregate. Publishing the raw file would break that rule.

What survives: every field report_v2.py reads. Identity is replaced by a salted hash, so
founder concentration and joins against head_freshness.json still work. The AI keyword match
is precomputed into `ai_related` because it needs name and description, which are dropped.

    python3 anonymize.py            # writes data/startups-anon.jsonl
    python3 anonymize.py --check    # verifies the anon file reproduces the headline numbers
"""
import json, hashlib, sys, os
from datetime import datetime, timezone

SRC = "data/startups.jsonl"
OUT = "data/startups-anon.jsonl"
FRESH = "data/head_freshness.json"
OUT_FRESH = "data/head_freshness-anon.json"

# Salt is committed on purpose: the point is to stop casual lookup of who earned nothing,
# not to resist a determined re-identification attack against a public leaderboard.
SALT = "trustmrr-census-2026-09-04"
AI_KW = ("ai", "gpt", "llm", "agent", "copilot", "generat", "prompt", "chatbot")

KEEP = ["country", "category", "foundedDate", "paymentProvider", "isMobileApp",
        "customers", "activeSubscriptions", "askingPrice", "previousAskingPrice",
        "profitMarginLast30Days", "growth30d", "growthMRR30d", "multiple", "rank",
        "onSale", "firstListedForSaleAt", "listingTier", "stealthMode",
        "visitorsLast30Days", "revenuePerVisitor", "offerCount", "pageviewCount"]

def hid(prefix, value):
    if not value:
        return None
    return prefix + hashlib.sha256((SALT + str(value)).encode()).hexdigest()[:12]

def ai_related(r):
    blob = " ".join(str(r.get(k) or "") for k in ("name", "description", "category")).lower()
    return any(k in blob for k in AI_KW)

def convert():
    n = 0
    with open(SRC) as f, open(OUT, "w") as out:
        for line in f:
            r = json.loads(line)
            rec = {k: r.get(k) for k in KEEP}
            rec["id"] = hid("p_", r.get("slug"))
            rec["founder_id"] = hid("f_", r.get("xHandle"))
            rec["ai_related"] = ai_related(r)
            rec["revenue"] = {
                "mrr": (r.get("revenue") or {}).get("mrr") or 0,
                "last30Days": (r.get("revenue") or {}).get("last30Days") or 0,
                "total": (r.get("revenue") or {}).get("total") or 0,
            }
            out.write(json.dumps(rec, ensure_ascii=False) + "\n")
            n += 1
    print(f"wrote {OUT}: {n} records")

    if os.path.exists(FRESH):
        hf = json.load(open(FRESH))
        for h in hf:
            h["id"] = hid("p_", h.get("slug"))
            h.pop("slug", None)
            h.pop("name", None)
        json.dump(hf, open(OUT_FRESH, "w"), ensure_ascii=False, indent=1)
        print(f"wrote {OUT_FRESH}: {len(hf)} records")

def check():
    rows = [json.loads(l) for l in open(OUT)]
    g = lambda r, k: (r["revenue"].get(k) or 0)
    n = len(rows)
    never = sum(1 for r in rows if not any(g(r, k) for k in ("mrr", "last30Days", "total")))
    earning = sum(1 for r in rows if g(r, "last30Days") > 0)
    stale = set()
    if os.path.exists(OUT_FRESH):
        stale = {h["id"] for h in json.load(open(OUT_FRESH)) if h.get("expired") or (h.get("days") or 0) > 30}
    w5 = [r for r in rows if g(r, "mrr") >= 5000 and r["id"] not in stale]
    founders = len({r["founder_id"] for r in rows if r["founder_id"]})
    ai = sum(1 for r in rows if r["ai_related"])
    exp = [("N", n, 10150), ("never earned", never, 2654), ("earning now", earning, 4987),
           ("mrr>=5k cleaned", len(w5), 353), ("unique founders", founders, 5697), ("AI related", ai, 5049)]
    ok = True
    for label, got, want in exp:
        mark = "ok " if got == want else "DIFF"
        if got != want:
            ok = False
        print(f"{mark} {label:18} {got:>6}  expected {want}")
    print("\nanon file reproduces the headline numbers" if ok else "\nMISMATCH — do not publish until resolved")
    return 0 if ok else 1

if __name__ == "__main__":
    if "--check" in sys.argv:
        sys.exit(check())
    convert()
    sys.exit(check())
