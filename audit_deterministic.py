# -*- coding: utf-8 -*-
"""确定性全量审计——所有有明确判据的字段，程序逐条核对，零 AI 判断。
用法：python audit_deterministic.py  （在项目根目录运行）
输出：AUDIT_REPORT.md + 控制台摘要
"""
import json, csv, io, re, sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path('.')
fails, stats = [], []
def ck(name, ok, detail=""):
    stats.append((name, ok, detail))
    if not ok: fails.append(f"{name}: {detail}")
    print(("PASS " if ok else "FAIL ") + name + "  " + detail)

def load(p): return json.loads((ROOT/p).read_text(encoding='utf-8'))

# ---------- 加载八表 ----------
ev1 = load('data/events_v2/入蜀記_events.json')
ev2 = load('data/events_v2/吳船錄_events.json')
wk  = load('data/works_v1/works.json')
pl  = load('data/base/places.json')
per = load('data/base/persons.json')
src = load('data/base/sources.json')
tl  = load('data/base/timeline.json')
inter = load('data/base/intertexts.json')
ev = ev1 + ev2

ck('八表条数', (len(ev1),len(ev2),len(wk),len(pl),len(per),len(src),len(tl),len(inter))==(156,110,17,383,34,6,34,223),
   f'{len(ev1)}/{len(ev2)}/{len(wk)}/{len(pl)}/{len(per)}/{len(src)}/{len(tl)}/{len(inter)}')

# ---------- 1. orig 连续子串 ----------
def norm(s): return re.sub(r'\s+', '', s or '')
src_r = norm((ROOT/'source/text/陸游_入蜀記.md').read_text(encoding='utf-8'))
src_w = norm((ROOT/'source/text/范成大_吳船錄.md').read_text(encoding='utf-8'))
bad=[e['id'] for e in ev1 if norm(e['orig']) not in src_r]
bad+=[e['id'] for e in ev2 if norm(e['orig']) not in src_w]
ck('events.orig 连续子串(266)', not bad, f'越界{len(bad)} {bad[:3]}')
# works.orig
wb=[]
for w in wk:
    cands=list((ROOT/'source/text').glob(f"*_{w['title']}.md"))
    if not cands or norm(w.get('orig')) not in norm(cands[0].read_text(encoding='utf-8')):
        wb.append(w['id'])
ck('works.orig 连续子串(17)', not wb, f'越界{len(wb)} {wb[:3]}')

# ---------- 2. 引文连续子串 ----------
evmap={e['id']:norm(e['orig']) for e in ev}
wkmap={w['id']:norm(w.get('orig')) for w in wk}
badq=[]
for r in inter:
    base = wkmap if r.get('source_table')=='works' else evmap
    if norm(r['quote']) not in base.get(r['source_id'],''): badq.append(r['id'])
ck('intertexts.quote 连续子串(223)', not badq, f'越界{len(badq)} {badq[:3]}')

# ---------- 3. 外键悬空 ----------
pid={p['id'] for p in per}; plid={p['id'] for p in pl}; sid={s['id'] for s in src}
wid={w['id'] for w in wk}; eid=set(evmap)
d=[]
for w in wk:
    for k,ref in [('author_id',pid),('place_id',plid),('source_id',sid)]:
        if w.get(k) and w[k] not in ref: d.append(('works',w['id'],k))
for e in ev:
    for k,ref in [('person_id',pid),('place_id',plid),('source_id',sid)]:
        if e.get(k) and e[k] not in ref: d.append(('events',e['id'],k))
for r in inter:
    if r.get('target_person_id') and r['target_person_id'] not in pid: d.append(('inter',r['id'],'target'))
    if r.get('source_id') and r['source_id'] not in (wid if r.get('source_table')=='works' else eid): d.append(('inter',r['id'],'source'))
for t in tl:
    if t.get('ref_id') and t['ref_id'] not in (wid|pid|sid): d.append(('timeline',t['id'],'ref'))
ck('外键悬空=0', not d, f'{len(d)} {d[:3]}')

# ---------- 4. 坐标 ----------
half=[p['id'] for p in pl if (p.get('lat') is None)!=(p.get('lon') is None)]
out=[p['id'] for p in pl if p.get('lat') is not None and not (15<=p['lat']<=55 and 70<=p['lon']<=140)]
ck('坐标无半null', not half, f'{len(half)} {half[:3]}')
ck('坐标全在中国范围', not out, f'{len(out)} {out[:3]}')

# ---------- 5. id 连续 / 唯一 ----------
def contiguous(ids, prefix, n):
    return ids==[f'{prefix}{i:03d}' for i in range(1,n+1)]
ids_inter=[r['id'] for r in inter]
ck('intertexts id 连续(允许int-066作废缺号)',
   ids_inter==[f'int-{i:03d}' for i in range(1,225) if i!=66],
   f'条数{len(ids_inter)} 缺号{set(f"int-{i:03d}" for i in range(1,225))-set(ids_inter)}')
ck('events id 连续', contiguous([e['id'] for e in ev1],'RSC-',156) and contiguous([e['id'] for e in ev2],'WCL-',110))
dup=[k for k in set(p['id'] for p in per) if sum(1 for p in per if p['id']==k)>1]
ck('persons id 无重复', not dup, f'重复{dup}')

# ---------- 6. relation 枚举 ----------
ENUM={'追慕','质疑','考订','唱和','纪其遗迹'}
badrel=[r['id'] for r in inter if r.get('relation') not in ENUM]
ck('relation 全在枚举内', not badrel, f'{len(badrel)} {badrel[:3]}')

# ---------- 7. CSV 与 JSON 一致 ----------
pairs=[('data/works_v1/works.csv',wk),('data/base/intertexts.csv',inter),('data/base/persons.csv',per),
       ('data/base/places.csv',pl),('data/base/sources.csv',src),('data/base/timeline.csv',tl),
       ('data/events_v2/入蜀記_events.csv',ev1),('data/events_v2/吳船錄_events.csv',ev2)]
for f,obj in pairs:
    raw=(ROOT/f).read_bytes()
    rows=list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))))
    ck(f'CSV {Path(f).name}', raw[:3]==b'\xef\xbb\xbf' and len(rows)==len(obj), f'rows={len(rows)} json={len(obj)}')

# ---------- 报告 ----------
lines=['# 确定性全量审计报告','',f'判据数 {len(stats)}，失败 {len(fails)}。','',
       '| 判据 | 结果 | 说明 |','|---|---|---|']
for n,ok,d in stats:
    lines.append(f'| {n} | {"PASS" if ok else "FAIL"} | {d} |')
if fails:
    lines += ['','## 失败项',''] + [f'- {x}' for x in fails]
(ROOT/'AUDIT_REPORT.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
print(f'\n共 {len(stats)} 项判据，失败 {len(fails)} 项。报告 -> AUDIT_REPORT.md')
sys.exit(1 if fails else 0)
