#!/usr/bin/env python3
"""逐条核查 MRR>=$5k 的 390 条记录的同步状态，清洗头部。"""
import json, re, time, urllib.request
from datetime import datetime, timezone
NOW=datetime(2026,9,4,tzinfo=timezone.utc); SLEEP=3.2
rows=[json.loads(l) for l in open('data/startups.jsonl')]
head=sorted([r for r in rows if (r['revenue']['mrr'] or 0)>=5000], key=lambda r:-(r['revenue']['mrr'] or 0))
PS=re.compile(r"(?:last synced|Data Last Updated)[^0-9]{0,20}(\d{4}-\d{2}-\d{2})",re.I)
PE=re.compile(r"(expired|disconnected|invalid|revoked)",re.I)
out=[]
print(f"核查 {len(head)} 条 MRR>=$5k 的记录", flush=True)
for i,r in enumerate(head,1):
    days=None; exp=None
    try:
        req=urllib.request.Request(f"https://trustmrr.com/startup/{r['slug']}.md",
            headers={"User-Agent":"solo-founder-revenue-research/1.0"})
        with urllib.request.urlopen(req,timeout=25) as resp: t=resp.read().decode('utf-8','replace')
        m=PS.search(t)
        if m:
            try: days=(NOW-datetime.fromisoformat(m.group(1)+"T00:00:00+00:00")).days
            except Exception: pass
        exp=bool(PE.search(t))
    except Exception as e: exp=None
    out.append({"slug":r['slug'],"name":r['name'],"mrr":r['revenue']['mrr'],
                "total":r['revenue']['total'],"d30":r['revenue']['last30Days'],
                "days":days,"expired":exp})
    if i%50==0: print(f"  {i}/{len(head)}", flush=True)
    time.sleep(SLEEP)
json.dump(out,open('data/head_freshness.json','w'),ensure_ascii=False,indent=1)
bad=[x for x in out if x['expired'] or (x['days'] or 0)>30]
tm=sum(x['mrr'] for x in out); bm=sum(x['mrr'] for x in bad)
print(f"\n完成：{len(out)} 条中 {len(bad)} 条过期/陈旧 ({len(bad)/len(out)*100:.1f}%)")
print(f"这些占 $5k+ 组 MRR 的 {bm/tm*100:.1f}%")
print(f"清洗后 MRR>=$5k 的有效条数：{len(out)-len(bad)}")
