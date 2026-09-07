#!/usr/bin/env python3
"""v2 报告所需的全部数字，一次算完。口径见 analyze.py 顶部。"""
import json, statistics as st
from collections import Counter, defaultdict
from datetime import datetime, timezone
NOW = datetime(2026, 9, 5, tzinfo=timezone.utc)

rows=[]; seen=set()
for l in open("data/startups.jsonl"):
    r=json.loads(l)
    if r["slug"] in seen: continue
    seen.add(r["slug"]); rows.append(r)
N=len(rows)
g=lambda r,k:(r["revenue"].get(k) or 0)
mrr=lambda r:g(r,"mrr"); l30=lambda r:g(r,"last30Days"); tot=lambda r:g(r,"total")
pct=lambda a,b: f"{a/b*100:.1f}%" if b else "—"
M=lambda x:f"${x:,.0f}"

# 陈旧头部
hf=json.load(open("data/head_freshness.json"))
stale={h["slug"] for h in hf if h["expired"] or (h["days"] or 0)>30}
print("=== 0 基础 ===")
print("N",N,"MRR",M(sum(map(mrr,rows))),"30d",M(sum(map(l30,rows))),"total",M(sum(map(tot,rows))))
never=[r for r in rows if tot(r)==0 and mrr(r)==0 and l30(r)==0]
print("从未赚过(严格)",len(never),pct(len(never),N))
print("曾赚过",sum(1 for r in rows if tot(r)>0),pct(sum(1 for r in rows if tot(r)>0),N))
print("近30天在赚",sum(1 for r in rows if l30(r)>0),pct(sum(1 for r in rows if l30(r)>0),N))
w5=[r for r in rows if mrr(r)>=5000]; w5c=[r for r in w5 if r["slug"] not in stale]
print("MRR≥5k 原始",len(w5),pct(len(w5),N),"清洗后",len(w5c),pct(len(w5c),N))
d5=[r for r in rows if l30(r)>=5000]; d5c=[r for r in d5 if r["slug"] not in stale]
print("30d≥5k 原始",len(d5),pct(len(d5),N),"清洗后(仅剔头部陈旧)",len(d5c),pct(len(d5c),N))
for th in (100,1000,10000):
    print(f"  MRR≥{th}:",sum(1 for r in rows if mrr(r)>=th),pct(sum(1 for r in rows if mrr(r)>=th),N),
          f" 30d≥{th}:",sum(1 for r in rows if l30(r)>=th),pct(sum(1 for r in rows if l30(r)>=th),N))
print("MRR 中位(非零)",M(st.median([mrr(r) for r in rows if mrr(r)>0])),
      "30d 中位(非零)",M(st.median([l30(r) for r in rows if l30(r)>0])),
      "total 中位(非零)",M(st.median([tot(r) for r in rows if tot(r)>0])))
print("陈旧头部",len(stale),"条, MRR",M(sum(mrr(r) for r in rows if r["slug"] in stale)),
      pct(sum(mrr(r) for r in rows if r["slug"] in stale),sum(map(mrr,rows))))
print("  其中 30d 也>0 的",sum(1 for r in rows if r["slug"] in stale and l30(r)>0),
      " 30d 合计",M(sum(l30(r) for r in rows if r["slug"] in stale)))
print("mrr>0 但 30d==0:",sum(1 for r in rows if mrr(r)>0 and l30(r)==0))
top1=sorted(map(mrr,rows),reverse=True)[:N//100]
print("MRR top1% 占",pct(sum(top1),sum(map(mrr,rows))),"  30d top1%",pct(sum(sorted(map(l30,rows),reverse=True)[:N//100]),sum(map(l30,rows))))

print("\n=== 1 年龄 × 结局 ===")
def age(r):
    d=r.get("foundedDate")
    if not d: return None
    try: return (NOW-datetime.fromisoformat(d.replace("Z","+00:00"))).days/30.44
    except: return None
B=[("≤3月",0,3),("3–6月",3,6),("6–12月",6,12),("1–2年",12,24),("2–4年",24,48),(">4年",48,1e9)]
print(f"{'年龄段':<8}{'n':>6}{'从未赚':>8}{'在赚':>8}{'MRR≥1k':>8}{'MRR≥5k':>8}{'30d≥5k':>8}{'挂牌卖':>8}")
for nm,lo,hi in B:
    grp=[r for r in rows if (a:=age(r)) is not None and lo<=a<hi]
    n=len(grp)
    if not n: continue
    print(f"{nm:<8}{n:>6}{pct(sum(1 for r in grp if r in never),n):>8}{pct(sum(1 for r in grp if l30(r)>0),n):>8}"
          f"{pct(sum(1 for r in grp if mrr(r)>=1000),n):>8}{pct(sum(1 for r in grp if mrr(r)>=5000),n):>8}"
          f"{pct(sum(1 for r in grp if l30(r)>=5000),n):>8}{pct(sum(1 for r in grp if r.get('onSale')),n):>8}")
noage=sum(1 for r in rows if age(r) is None); print("无成立日期",noage,pct(noage,N))
for nm,grp in (("从未赚过",never),("曾赚过归零",[r for r in rows if tot(r)>0 and l30(r)==0]),
               ("在赚<1k",[r for r in rows if 0<l30(r)<1000]),("MRR≥5k",w5),("MRR≥5k清洗",w5c),("全体",rows)):
    ag=[a for a in map(age,grp) if a is not None]
    print(f"  {nm:<10} n={len(ag):>5} 中位年龄 {st.median(ag):5.1f} 月  P25 {sorted(ag)[len(ag)//4]:5.1f}  P75 {sorted(ag)[3*len(ag)//4]:5.1f}  >2年 {pct(sum(1 for a in ag if a>=24),len(ag))}")
# 死亡时间：曾赚过归零的年龄分布
dead=[a for a in map(age,[r for r in rows if tot(r)>0 and l30(r)==0]) if a is not None]
print("  曾赚过归零 年龄分布:", " ".join(f"{nm} {pct(sum(1 for a in dead if lo<=a<hi),len(dead))}" for nm,lo,hi in B))
# 平台成立日 vs 产品成立日：TrustMRR 2025-10-31 上线；成立日期在此之前的产品占比
pre=sum(1 for r in rows if (a:=age(r)) is not None and a>10.2)
print("  成立于 TrustMRR 上线(2025-10-31)之前的产品",pre,pct(pre,N))

print("\n=== 2 AI vs 非AI ===")
KW=("ai","gpt","llm","agent","copilot","generat","prompt","chatbot")
isai=lambda r:any(k in f"{r.get('name','')} {r.get('description','')} {r.get('category','')}".lower() for k in KW)
for cond,label in ((lambda r:True,"全体"),(lambda r:(age(r) or 99)<=12,"≤12月"),(lambda r:12<(age(r) or -1)<=24,"1–2年")):
    for nm,grp in (("AI",[r for r in rows if isai(r) and cond(r)]),("非AI",[r for r in rows if not isai(r) and cond(r)])):
        n=len(grp)
        print(f"  {label:<6}{nm:<4} n={n:>5}  从未赚 {pct(sum(1 for r in grp if r in never),n):>6}  在赚 {pct(sum(1 for r in grp if l30(r)>0),n):>6}"
              f"  MRR≥1k {pct(sum(1 for r in grp if mrr(r)>=1000),n):>6}  MRR≥5k {pct(sum(1 for r in grp if mrr(r)>=5000),n):>6}  30d≥5k {pct(sum(1 for r in grp if l30(r)>=5000),n):>6}"
              f"  中位30d(非零) {M(st.median([l30(r) for r in grp if l30(r)>0]) if any(l30(r)>0 for r in grp) else 0)}")
cat_ai=sum(1 for r in rows if (r.get("category") or "")=="Artificial Intelligence")
print("  category=AI 的",cat_ai,pct(cat_ai,N))

print("\n=== 3 非 MRR 收入 ===")
sm,sl=sum(map(mrr,rows)),sum(map(l30,rows))
print("30d/MRR 全体",f"{sl/sm:.2f}x  非MRR份额 {pct(sl-sm,sl)}")
print("  30d 最高且 mrr=0 的前 15：")
for r in sorted([r for r in rows if mrr(r)==0],key=lambda r:-l30(r))[:15]:
    print(f"    {r['name'][:28]:<30} 30d {M(l30(r)):>12}  total {M(tot(r)):>14}  {r.get('category')}  {r.get('country')}")
plat={"gumroad"}
ex=[r for r in rows if r["slug"] not in plat]
print("剔 Gumroad:",f"{sum(map(l30,ex))/sum(map(mrr,ex)):.2f}x 非MRR {pct(sum(map(l30,ex))-sum(map(mrr,ex)),sum(map(l30,ex)))}")
ex2=[r for r in ex if r["slug"] not in stale]
print("再剔陈旧头部:",f"{sum(map(l30,ex2))/sum(map(mrr,ex2)):.2f}x 非MRR {pct(sum(map(l30,ex2))-sum(map(mrr,ex2)),sum(map(l30,ex2)))}")
# 按产品：每个在赚的产品，其 30d 里超过 mrr 的部分
earn=[r for r in rows if l30(r)>0]
onlyone=[r for r in earn if mrr(r)==0]
print("在赚的产品",len(earn),"其中 mrr=0",len(onlyone),pct(len(onlyone),len(earn)))
print("  mrr=0 但 30d≥1k",sum(1 for r in onlyone if l30(r)>=1000)," ≥5k",sum(1 for r in onlyone if l30(r)>=5000)," ≥10k",sum(1 for r in onlyone if l30(r)>=10000))
mixed=[r for r in earn if mrr(r)>0 and l30(r)>mrr(r)*1.2]
print("  mrr>0 且 30d 超 mrr 20% 以上(混合模式)",len(mixed),pct(len(mixed),len(earn)))
# 中位数产品视角：在赚的产品里，30d 中有多少不是 mrr（逐产品）
shares=[max(0,l30(r)-mrr(r))/l30(r) for r in earn]
print("  逐产品非MRR份额 中位",f"{st.median(shares)*100:.0f}%")
# 头部（30d≥5k）里非订阅占多少
h=[r for r in rows if l30(r)>=5000]
print("  30d≥5k 的",len(h),"个里 mrr=0 的",sum(1 for r in h if mrr(r)==0),pct(sum(1 for r in h if mrr(r)==0),len(h)))

print("\n=== 4 创始人（用累计与 30d，不用 MRR） ===")
byf=defaultdict(list)
for r in rows:
    if r.get("xHandle"): byf[r["xHandle"]].append(r)
print("有 handle",sum(len(v) for v in byf.values()),pct(sum(len(v) for v in byf.values()),N),"去重",len(byf))
multi={k:v for k,v in byf.items() if len(v)>1}
print("≥2 产品的创始人",len(multi),pct(len(multi),len(byf)),"覆盖产品",sum(len(v) for v in multi.values()))
print("  产品数最多的 12 位（累计收入 / 30d / 产品中在赚的个数）:")
for h_,v in sorted(byf.items(),key=lambda kv:-len(kv[1]))[:12]:
    print(f"    @{h_:<18} {len(v):>3}  total {M(sum(map(tot,v))):>12}  30d {M(sum(map(l30,v))):>10}  在赚 {sum(1 for x in v if l30(x)>0)}/{len(v)}")
# 单产品 vs 多产品创始人：人均与最佳产品
def best(v,f): return max(map(f,v))
for nm,grp in (("1 个产品",[v for v in byf.values() if len(v)==1]),("2–3 个",[v for v in byf.values() if 2<=len(v)<=3]),("4 个以上",[v for v in byf.values() if len(v)>=4])):
    n=len(grp)
    print(f"  {nm:<8} 创始人 {n:>5}  有产品在赚 {pct(sum(1 for v in grp if any(l30(x)>0 for x in v)),n):>6}"
          f"  最佳产品30d≥1k {pct(sum(1 for v in grp if best(v,l30)>=1000),n):>6}  ≥5k {pct(sum(1 for v in grp if best(v,l30)>=5000),n):>6}"
          f"  合计30d中位 {M(st.median([sum(map(l30,v)) for v in grp]))}")
# 赢家创始人里几人有第二个
for th_nm,f in (("MRR≥5k",mrr),("30d≥5k",l30)):
    wf={k:[x for x in v if f(x)>=5000] for k,v in byf.items()}
    wf={k:v for k,v in wf.items() if v}
    two=sum(1 for v in wf.values() if len(v)>1)
    print(f"  {th_nm} 产品的可识别创始人 {len(wf)} 位，其中 {two} 位有 2 个以上 ({pct(two,len(wf))})；他们名下产品总数中位 {st.median([len(byf[k]) for k in wf]):.0f}")
    # 赢家的其他产品表现
    others=[x for k in wf for x in byf[k] if f(x)<5000]
    print(f"    这些赢家名下的其他产品 {len(others)} 个，其中在赚 {pct(sum(1 for x in others if l30(x)>0),len(others)) if others else '—'}")

print("\n=== 5 挂牌出售 ===")
sale=[r for r in rows if r.get("onSale")]
print("全体挂牌",len(sale),pct(len(sale),N)," MRR≥5k 中挂牌",pct(sum(1 for r in w5 if r.get("onSale")),len(w5))," 30d≥5k 中",pct(sum(1 for r in d5 if r.get("onSale")),len(d5)))
print("  从未赚过 中挂牌",pct(sum(1 for r in never if r.get("onSale")),len(never)))
mult=[r["multiple"] for r in sale if isinstance(r.get("multiple"),(int,float)) and r["multiple"]>0]
print("  有倍数",len(mult),"中位",f"{st.median(mult):.1f}x")
ask=[r["askingPrice"] for r in sale if isinstance(r.get("askingPrice"),(int,float)) and r["askingPrice"]>0]
print("  有要价",len(ask),"中位",M(st.median(ask)))

print("\n=== 6 国家（含中文读者关心的） ===")
byc=defaultdict(list)
for r in rows: byc[r.get("country") or "未标注"].append(r)
print(f"  {'国家':<6}{'n':>6}{'从未赚':>8}{'在赚':>8}{'MRR≥5k':>8}{'30d≥5k':>8}{'30d中位(非零)':>14}")
for c in ("US","FR","CN","HK","TW","SG","JP","IN","DE","GB","CA","AU","KR","VN","未标注"):
    v=byc.get(c,[])
    if not v: print(f"  {c:<6} 无"); continue
    nz=[l30(r) for r in v if l30(r)>0]
    print(f"  {c:<6}{len(v):>6}{pct(sum(1 for r in v if r in never),len(v)):>8}{pct(sum(1 for r in v if l30(r)>0),len(v)):>8}"
          f"{pct(sum(1 for r in v if mrr(r)>=5000),len(v)):>8}{pct(sum(1 for r in v if l30(r)>=5000),len(v)):>8}{M(st.median(nz)) if nz else '—':>14}")
print("  国家数",len(byc))
# CN 的头部
cn=sorted(byc.get("CN",[]),key=lambda r:-l30(r))[:8]
print("  CN 30d 前 8：")
for r in cn: print(f"    {r['name'][:26]:<28} MRR {M(mrr(r)):>10} 30d {M(l30(r)):>10} total {M(tot(r)):>12} {r.get('category')} {'挂牌' if r.get('onSale') else ''}")
# 中文创始人（名字含 CJK）
import re
cjk=re.compile(r'[一-鿿]')
zh=[r for r in rows if cjk.search(r.get("xFounderName") or "") or cjk.search(r.get("description") or "")]
print("  创始人名或描述含中文的产品",len(zh),"在赚",pct(sum(1 for r in zh if l30(r)>0),len(zh)),"30d≥5k",sum(1 for r in zh if l30(r)>=5000))

print("\n=== 7 品类（30d 口径补充） ===")
byk=defaultdict(list)
for r in rows: byk[r.get("category") or "未标注"].append(r)
print(f"  {'品类':<24}{'n':>6}{'从未赚':>8}{'在赚':>8}{'MRR≥5k':>8}{'30d≥5k':>8}")
for k,v in sorted(byk.items(),key=lambda kv:-len(kv[1])):
    if len(v)<80: continue
    print(f"  {k[:22]:<24}{len(v):>6}{pct(sum(1 for r in v if r in never),len(v)):>8}{pct(sum(1 for r in v if l30(r)>0),len(v)):>8}"
          f"{pct(sum(1 for r in v if mrr(r)>=5000),len(v)):>8}{pct(sum(1 for r in v if l30(r)>=5000),len(v)):>8}")

print("\n=== 8 其他 ===")
gr=[r["growthMRR30d"] for r in rows if isinstance(r.get("growthMRR30d"),(int,float))]
print("MRR 增长率 有值",len(gr),"中位",f"{st.median(gr):.1f}%","负",pct(sum(1 for x in gr if x<0),len(gr)),"正",pct(sum(1 for x in gr if x>0),len(gr)))
grw=[r["growthMRR30d"] for r in w5c if isinstance(r.get("growthMRR30d"),(int,float))]
print("  清洗后 MRR≥5k 的增长率 中位",f"{st.median(grw):.1f}%","负",pct(sum(1 for x in grw if x<0),len(grw)))
pp=Counter(r.get("paymentProvider") for r in rows); print("支付渠道",pp.most_common(6))
mob=sum(1 for r in rows if r.get("isMobileApp")); print("移动应用",mob,pct(mob,N))
subs=[r.get("activeSubscriptions") or 0 for r in rows]
print("活跃订阅 中位",st.median(subs),"=0",pct(sum(1 for s in subs if s==0),N),"  MRR≥5k 清洗后订阅数中位",st.median([r.get("activeSubscriptions") or 0 for r in w5c]))
cust=[r.get("customers") or 0 for r in w5c]; print("  MRR≥5k 清洗后 customers 中位",st.median(cust))
# 每客单价：mrr/activeSubscriptions
arpu=[mrr(r)/r["activeSubscriptions"] for r in w5c if (r.get("activeSubscriptions") or 0)>0]
print("  MRR≥5k 清洗后 每订阅月费中位",M(st.median(arpu)),"P25",M(sorted(arpu)[len(arpu)//4]),"P75",M(sorted(arpu)[3*len(arpu)//4]))
arpu_all=[mrr(r)/r["activeSubscriptions"] for r in rows if (r.get("activeSubscriptions") or 0)>0 and mrr(r)>0]
print("  全体有订阅的 每订阅月费中位",M(st.median(arpu_all)),"n",len(arpu_all))
# Marc Lou
ml=byf.get("marclou",[])
print("Marc Lou 产品",len(ml),"total",M(sum(map(tot,ml))),"30d",M(sum(map(l30,ml))),"mrr",M(sum(map(mrr,ml))))
for r in sorted(ml,key=lambda r:-tot(r))[:6]: print(f"    {r['name'][:24]:<26} total {M(tot(r)):>12} 30d {M(l30(r)):>10} mrr {M(mrr(r)):>8}")

print("\n=== 补 · 年龄 × 30d≥1k、在赚者 30d 中位（2026-09-05 补算，takeaways 用）===")
for nm,lo,hi in B:
    grp=[r for r in rows if (a:=age(r)) is not None and lo<=a<hi]
    e=sorted(l30(r) for r in grp if l30(r)>0)
    if grp and e:
        print(f"{nm:<8}{len(grp):>6}  30d≥1k {pct(sum(1 for r in grp if l30(r)>=1000),len(grp)):>6}  在赚 {pct(len(e),len(grp)):>6}  在赚者30d中位 ${st.median(e):,.0f}")
