# -*- coding: utf-8 -*-
"""回填 works_v1 + events_v2 占位外键（原文件覆盖，保留原列序，仅注入新列），并自检外键悬空=0。
新增字段：
  works  : source_id（挂 sources.id，按 author 归并）
  events : person_id（挂 persons.id）、source_id（挂 sources.id，按书归并）、
          place_id（把 events 的中文 place 映射到 places.id）
works 的 place_id：把 占位(pl-*)/中文 统一映射到 places.id。
纪律：坐标/地名查不到→null，不估算；外键悬空须为 0。
"""
import io, os, json, csv, sys
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.abspath(os.path.join(HERE, '..'))

# ---- 读基础表 ----
places = json.load(open(os.path.join(HERE, 'places.json'), encoding='utf-8'))
persons = json.load(open(os.path.join(HERE, 'persons.json'), encoding='utf-8'))
sources = json.load(open(os.path.join(HERE, 'sources.json'), encoding='utf-8'))

v2pid = {}
for p in places:
    v2pid[p['id']] = p['id']
    for v in p['name_variants']:
        v2pid.setdefault(v, p['id'])
    v2pid.setdefault(p['name'], p['id'])

pid_set = set(p['id'] for p in persons)
pl_set = set(p['id'] for p in places)
sid_set = set(s['id'] for s in sources)
# author -> source id（一人默认 source）
src_by_author = {}
for s in sources:
    src_by_author.setdefault(s['author_id'], s['id'])

def resolve_place(val):
    if not val:
        return None
    if val in v2pid:
        return v2pid[val]
    # 容错：剥离重复 pl- 前缀（旧回填可能产生 pl-pl-*）再查
    v = val
    while v.startswith('pl-pl-'):
        v = 'pl-' + v[len('pl-pl-'):]
        if v in v2pid:
            return v2pid[v]
    return None

# ---- 原列序（保持不动，仅在其后追加新列）----
RSC_COLS = ['id','juan','month','day','date_raw','orig','kind','place','place_all',
            'place_waypoint','place_departed','activity','landscape','weather','emotion','imagery','note']
WCL_COLS = ['id','juan','month','ganzhi','day_num','day_src','date_raw','orig','kind',
            'place','place_all','activity','landscape','weather','emotion','imagery','note']
WK_COLS = ['id','title','author_id','parent_id','genre','visit_year','visit_month','visit_day',
           'write_year','write_month','write_day','date_orig','place_id','situation','theme',
           'mood','structure','imagery','style','note']

def write_json(p, rows):
    io.open(p, 'w', encoding='utf-8', newline='\n').write(json.dumps(rows, ensure_ascii=False, indent=2) + '\n')

def write_csv(p, rows, cols):
    with io.open(p, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(cols)
        for row in rows:
            w.writerow([(('|'.join(row[c]) if isinstance(row.get(c), list) else (row.get(c) if row.get(c) is not None else ''))) for c in cols])

# ============ works_v1 ============
wj = os.path.join(DATA, 'works_v1', 'works.json')
wc = os.path.join(DATA, 'works_v1', 'works.csv')
works = json.load(open(wj, encoding='utf-8'))
for w in works:
    w['source_id'] = src_by_author.get(w.get('author_id'))
    w['place_id'] = resolve_place(w.get('place_id'))
write_json(wj, works)
write_csv(wc, works, WK_COLS + ['source_id'])

# ============ events_v2 ============
EV = [
    ('入蜀記_events', 'p-lu-you', 'src-lu-you-wg', RSC_COLS, RSC_COLS + ['person_id','source_id','place_id']),
    ('吳船錄_events', 'p-fan-chengda', 'src-fan-chengda-wg', WCL_COLS, WCL_COLS + ['person_id','source_id','place_id']),
]
ev_all = []
for fname, pid, sid, jcols, ccols in EV:
    p = os.path.join(DATA, 'events_v2', fname + '.json')
    c = os.path.join(DATA, 'events_v2', fname + '.csv')
    ev = json.load(open(p, encoding='utf-8'))
    for e in ev:
        e['person_id'] = pid
        e['source_id'] = sid
        e['place_id'] = resolve_place(e.get('place'))
    write_json(p, ev)
    write_csv(c, ev, ccols)
    ev_all += ev

# ============ 自检：外键悬空 ============
print('\n===== 回填自检 =====')
d_ws = sum(1 for w in works if w.get('source_id') and w['source_id'] not in sid_set)
d_wa = sum(1 for w in works if w.get('author_id') not in pid_set)
d_wp = sum(1 for w in works if w.get('place_id') and w['place_id'] not in pl_set)
d_wp_null = sum(1 for w in works if not w.get('place_id'))
print('works: %d 条' % len(works))
print('  source_id 悬空: %d' % d_ws)
print('  author_id 悬空: %d' % d_wa)
print('  place_id 悬空: %d (null: %d)' % (d_wp, d_wp_null))

d_ep = sum(1 for e in ev_all if e.get('person_id') not in pid_set)
d_es = sum(1 for e in ev_all if e.get('source_id') not in sid_set)
d_epl = sum(1 for e in ev_all if e.get('place_id') and e['place_id'] not in pl_set)
d_epl_null = sum(1 for e in ev_all if not e.get('place_id'))
print('events: %d 条' % len(ev_all))
print('  person_id 悬空: %d' % d_ep)
print('  source_id 悬空: %d' % d_es)
print('  place_id 悬空: %d (null: %d)' % (d_epl, d_epl_null))

tot = d_ws + d_wa + d_wp + d_ep + d_es + d_epl
print('\n=== 外键总悬空: %d ===' % tot)
print('基础表条数: persons %d / places %d / sources %d' % (len(persons), len(places), len(sources)))
