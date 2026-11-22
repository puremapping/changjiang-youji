# -*- coding: utf-8 -*-
"""Independent self-check. Reads disk fresh; does not trust builder outputs."""
import json, csv, os, collections, re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
BASE = os.path.join(ROOT, 'data', 'base')
MAP = {
 'w-you-huang-xi':'柳宗元_遊黃溪記.md','w-shi-de-xi-shan':'柳宗元_始得西山宴遊記.md',
 'w-gu-gu-tan':'柳宗元_鈷鉧潭記.md','w-gu-gu-tan-xi-xiao-qiu':'柳宗元_鈷鉧潭西小丘記.md',
 'w-zhi-xiao-qiu-xiao-shi-tan':'柳宗元_至小丘西小石潭記.md','w-yuan-jia-ke':'柳宗元_袁家渴記.md',
 'w-shi-qu-ji':'柳宗元_石渠記.md','w-shi-jian-ji':'柳宗元_石澗記.md',
 'w-xiao-shi-cheng-shan':'柳宗元_小石城山記.md','w-chi-bi-fu':'蘇軾_赤壁賦.md',
 'w-hou-chi-bi-fu':'蘇軾_後赤壁賦.md','w-shi-zhong-shan-ji':'蘇軾_石鐘山記.md',
 'w-you-jin-shan-si':'蘇軾_遊金山寺.md','w-jin-shan-ye-xi':'張岱_金山夜戲.md',
 'w-jin-shan-jing-du':'張岱_金山競渡.md','w-ru-shu-ji':'陸游_入蜀記.md',
 'w-wu-chuan-lu':'范成大_吳船錄.md'}

works = json.load(open(os.path.join(ROOT,'data','works_v1','works.json'),encoding='utf-8'))
persons = json.load(open(os.path.join(BASE,'persons.json'),encoding='utf-8'))
intertexts = json.load(open(os.path.join(BASE,'intertexts.json'),encoding='utf-8'))
ok = True
def check(label, cond, detail=''):
    global ok
    print(('PASS' if cond else 'FAIL'), label, detail)
    if not cond: ok = False

# 1. works orig
check('works count 17', len(works)==17, str(len(works)))
has = sum(bool(w.get('orig')) for w in works)
check('works with orig', has==17, '%d/17'%has)
contig = 0
for w in works:
    t = open(os.path.join(ROOT,'source','text',MAP[w['id']]),encoding='utf-8').read()
    if w['orig'] in t: contig += 1
    else: print('   NOT SUBSTRING', w['id'])
check('orig contiguous substring of source file', contig==17, '%d/17'%contig)
check('orig field is last key in every work', all(list(w.keys())[-1]=='orig' for w in works))

# 2. intertexts new
new = [e for e in intertexts if e['id'] >= 'int-103' and e['source_table']=='works']
old = [e for e in intertexts if e['source_table']!='works']
check('old int-001..102 intact', len(old)==102 and all(e['source_table']=='events' for e in old))
check('new count', len(new)==122, str(len(new)))
check('new ids contiguous int-103..224',
      [e['id'] for e in new]==['int-%03d'%i for i in range(103,103+len(new))])
wid = {w['id'] for w in works}; pid = {p['id'] for p in persons}
check('new source_id all in works', all(e['source_id'] in wid for e in new))
check('new target_person_id all in persons', all(e['target_person_id'] in pid for e in new))
wm = {w['id']:w for w in works}
qok = [e for e in new if e['quote'] in wm[e['source_id']]['orig']]
check('new quote contiguous substring of works.orig', len(qok)==len(new), '%d/%d'%(len(qok),len(new)))
check('relation in SCHEMA enum', all(e['relation'] in ('追慕','质疑','考订','唱和','纪其遗迹') for e in new))
check('source_table all works', all(e['source_table']=='works' for e in new))
check('book == source_id', all(e['book']==e['source_id'] for e in new))

# 3. persons additions
for pid_ in ('p-li-bo','p-li-daoyuan','p-han-shizhong'):
    check('person '+pid_+' present', any(p['id']==pid_ for p in persons))

# 4. CSV parity
def csvcheck(name, j):
    path = os.path.join(BASE,name+'.csv')
    raw = open(path,'rb').read(3)
    check(name+'.csv UTF-8 BOM', raw==b'\xef\xbb\xbf', repr(raw))
    rows = list(csv.reader(open(path,encoding='utf-8-sig',newline='')))
    hdr, data = rows[0], rows[1:]
    check(name+'.csv rows == json', len(data)==len(j), '%d/%d'%(len(data),len(j)))
    check(name+'.csv header == json keys', hdr==list(j[0].keys()))
    # full cell-by-cell parity (int fields may be '' for null)
    mm=0
    for r,o in zip(data,j):
        for i,k in enumerate(hdr):
            exp = '' if o[k] is None else str(o[k])
            if r[i]!=exp: mm+=1
    check(name+'.csv cells == json values', mm==0, 'mismatches=%d'%mm)
csvcheck('persons', persons)
csvcheck('intertexts', intertexts)
wpath = os.path.join(ROOT,'data','works_v1','works.csv')
check('works.csv UTF-8 BOM', open(wpath,'rb').read(3)==b'\xef\xbb\xbf')
wrows = list(csv.reader(open(wpath,encoding='utf-8-sig',newline='')))
check('works.csv rows == 17', len(wrows)-1==17, str(len(wrows)-1))
check('works.csv header orig last', wrows[0][-1]=='orig', str(wrows[0][-3:]))
check('works.csv orig matches works.json', all(r[-1]==w['orig'] for r,w in zip(wrows[1:],works)))

# 5. stats
print('\n=== STATS ===')
print('new intertexts:', len(new))
print('by target:', dict(collections.Counter(e['target_name'] for e in new)))
print('by relation:', dict(collections.Counter(e['relation'] for e in new)))
doubt = [e for e in new if '存疑' in e['note']]
print('存疑 flagged:', len(doubt), [e['id'] for e in doubt])
print('works char total:', sum(len(w['orig']) for w in works))
print('\nRESULT:', 'ALL CHECKS PASS' if ok else 'SOME CHECKS FAILED')
