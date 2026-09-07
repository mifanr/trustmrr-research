# trustmrr-research

Data and scripts behind a full census of [TrustMRR](https://trustmrr.com), a leaderboard of
indie products that connects directly to payment providers and only shows verified revenue.

All 10,150 listed products, pulled 2026-09-04. Write-up:
[I pulled all 10,150 products on TrustMRR](https://mifanr.com/en/posts/trustmrr-census/)
· [中文](https://mifanr.com/posts/trustmrr-census/)

Every number in the post can be recomputed from this repository, except one: the 7.0% first-two-pages figure in the pagination note. Anonymization hashes product names, so the alphabetical page order that figure depends on is gone. If your figures differ from
mine, [tell me](https://x.com/Mifanr).

## Why this exists

A claim circulates in indie hacker circles: 58% of products on TrustMRR make no money. It is
arithmetically correct and it counts the wrong thing.

`revenue.mrr` counts subscription revenue only. A product selling a one-time template reports
0 there no matter how much it sells. ShipFast has $1,270,003 in lifetime revenue and an mrr of
0. Gumroad took $7.14M in the last 30 days and reports an mrr of 0. Counting `mrr == 0` gives
5,930 records, 58.4%, and 1,222 of those took in money in the last 30 days.

Products that have never earned a cent, defined strictly as all three revenue fields at zero:
**2,654, or 26.1%**.

## Quick start

No API key needed. The dataset is in the repo.

```bash
python3 report_v2.py        # every number in the post, offline, a few seconds
```

To pull a fresh copy instead:

```bash
cp .env.example .env        # add your own TRUSTMRR_API_KEY
python3 fetch.py            # ~1 hour at 18 req/min, under the 20/min limit
python3 staleness.py        # detail-page freshness check for the top records
python3 anonymize.py        # rebuild the anonymized dataset
python3 report_v2.py
```

## Files

| Path | What it is |
|---|---|
| `data/startups-anon.jsonl` | 10,150 records, one per line, anonymized. See below. |
| `data/head_freshness-anon.json` | Sync-freshness audit of all 390 records with mrr ≥ $5,000, plus a random 40 as a site-wide control |
| `data/report_v2.txt` | Output of `report_v2.py`; the source of every figure in the post |
| `data/staleness.json` | Intermediate sync-lag results |
| `data/fetched_pages.json` | Pagination log from the pull |
| `report_v2.py` | The analysis. Reads local files only, no network. |
| `fetch.py` | Pulls the full leaderboard from the API |
| `staleness.py` | Reads each detail page for last-synced date and expiry flag |
| `anonymize.py` | Builds the anonymized dataset from a raw pull, and verifies it |
| `analyze.py`, `clean_head.py` | First-pass scripts, superseded by `report_v2.py`, kept for provenance |

## About the anonymized dataset

The raw pull carries the name and founder handle of every product, including the 2,654 that
never earned anything. The write-up reports products and founders who did not earn only in
aggregate, and shipping the raw file would break that. So the published dataset drops names,
slugs, descriptions, websites and founder handles, and replaces identity with a salted hash.

Nothing analytic is lost. `founder_id` preserves founder concentration. `id` joins against the
freshness audit. The AI keyword match, which needs name and description, is precomputed into
`ai_related`. `anonymize.py --check` asserts that the anonymized file reproduces six headline
figures exactly:

```
N 10150 · never earned 2654 · earning now 4987
mrr>=5k cleaned 353 · unique founders 5697 · AI related 5049
```

Run `fetch.py` with your own key if you need the identifying fields.

## The three revenue fields

This is the foundation of the whole analysis and the place the circulating figure goes wrong.

- `revenue.mrr` — monthly **subscription** revenue. Zero for one-time products, always.
- `revenue.last30Days` — actual receipts over the past thirty days, subscription or not.
- `revenue.total` — lifetime revenue.

Site-wide, `last30Days` sums to 2.08× the sum of `mrr`. Removing Gumroad, the largest single
outlier, still leaves 1.69×. So roughly 40% of the money on the platform is not subscription
revenue, and an MRR-only view misses about a quarter of the products that are earning.

## Method details that change the numbers

- **Top-end figures exclude stale records.** Of the 390 records with mrr ≥ $5,000, 37 were
  flagged expired or had not synced in over 30 days. Their mrr sums to $6,726,998, which is
  37.4% of the site total. The single largest, at 19.8% of site-wide mrr, shows
  `Stripe API key expired` and last synced 2026-04-20. Cleaned, 353 records clear $5,000,
  3.5% rather than the raw 3.8%.
- **Age** is computed from `foundedDate` to 2026-09-05 at 30.44 days per month. 1,529 records
  (15.1%) have no valid founding date and are excluded from age statistics.
- **AI classification** matches keywords in name, description and category, hitting 49.7%. The
  platform's own category field gives 21.2%. Both definitions produce the same conclusions.
- **Pagination is not random.** The API pages alphabetically by product name, and the first two
  pages hold 7.0% of products with mrr ≥ $5,000 against 2.5% site-wide. Sampling the first N
  pages inflates the top end by half. Sample randomly or pull everything.
- **92 records report `mrr > 0` with `total == 0`.** The fields contradict each other, so they
  are counted separately as inconsistent rather than folded into any category.
- The API returns 10,150 records while the site's homepage shows 10,048. I could not account
  for the 1% difference.

## What this data cannot answer

- **Self-selected sample.** Only people willing to connect a payment provider and publish
  revenue appear here. Nothing in this data describes the ones who did not.
- **Left truncation.** The platform launched 2025-10-31. Products that died before that never
  had a chance to appear, which is most of why older cohorts look strong.
- **Exit bias.** About three in ten products above $5,000 a month are listed for sale, and a
  sold product leaves the board.

So 3.5%, 5.1% and 19.2% are point-in-time stock figures, not anyone's odds. Using them as odds
makes all three mistakes at once.

## Naming

Revenue on this platform is published by the product owners themselves, after connecting a
payment provider. The write-up names only products and founders who publicly display their own
revenue. Products and founders who did not earn appear only in aggregate, which is also why
this repository ships the anonymized dataset rather than the raw pull.

Not affiliated with TrustMRR. Conclusions do not represent the platform.

## Verified

The anonymized dataset reproduces the raw pull exactly. Every numeric token printed by
`report_v2.py` is identical whether it reads `data/startups.jsonl` (raw, not published) or
`data/startups-anon.jsonl` (published). The one exception is a single section on
Chinese-language founders, which needs `name` and `description` and is skipped with a note.

## License

Code under MIT. The data originates from TrustMRR's public API; rights remain with the platform
and the individual product owners. It is included here so the published conclusions can be
checked, not as a redistribution of their product.
