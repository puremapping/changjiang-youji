# -*- coding: utf-8 -*-
"""events_v2.1 + works_v1 最终验收：JSON 有效、id 连续、BOM、逐字、字段合规、闰月首校验。"""
import sys, json, os, re
sys.stdout.reconfigure(encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.abspath(os.path.join(HERE, '..', '..'))
D = os.path.join(BASE, 'data', 'events_v2')
W = os.path.join(BASE, 'data', 'works_v1')
ok = True

def check(label, cond):
    global ok
    print(('  [OK]' if cond else '  [XX]'), label)
    if not cond:
        ok = False

def load_json(p):
    return json.load(open(p, encoding='utf-8'))

def contiguous(orig, src):
    norm = src.replace('\n', '').replace(' ', '')
    return norm.find(orig.replace('\n', '').replace(' ', '')) >= 0

for name in ['入蜀記_events', '吳船錄_events']:
    print('==', name, '==')
    j = os.path.join(D, name + '.json')
    c = os.path.join(D, name + '.csv')
    ev = load_json(j)
    src = open(os.path.join(BASE, 'source', 'text',
            '陸游_入蜀記.md' if '入蜀' in name else '范成大_吳船錄.md'),
            encoding='utf-8').read().replace('\r\n', '\n')
    pref = 'RSC' if '入蜀' in name else 'WCL'
    expected_n = 156 if pref == 'RSC' else 110
    check('JSON 可解析, 条数 %d (期望 %d)' % (len(ev), expected_n),
          isinstance(ev, list) and len(ev) == expected_n)
    check('id 连续 %s-001~%s-%03d' % (pref, pref, len(ev)),
          all(e['id'] == '%s-%03d' % (pref, i + 1) for i, e in enumerate(ev)))
    miss_orig = [e['id'] for e in ev if not contiguous(e.get('orig', ''), src)]
    check('orig 逐字源文件 (%d 越界)' % len(miss_orig), not miss_orig)
    miss_act = [e['id'] for e in ev if not e.get('activity')]
    check('activity 全非空 (%d 缺)' % len(miss_act), not miss_act)
    miss_note = [e['id'] for e in ev if 'note' not in e]
    check('note 字段全在 (%d 缺)' % len(miss_note), not miss_note)
    bom = open(c, 'rb').read(3) == b'\xef\xbb\xbf'
    check('CSV UTF-8-BOM', bom)
    import csv as _csv
    rows = list(_csv.reader(open(c, encoding='utf-8-sig')))
    check('CSV 行数 %d (= %d 条+表头)' % (len(rows), len(ev)), len(rows) == len(ev) + 1)
    # 闰月首校验（入蜀记 v2.1）
    if pref == 'RSC':
        r1 = ev[0]
        gu = [e for e in ev if e['month'] == '閏五月']
        zw = [e for e in ev if e['month'] == '十二月']
        check('RSC-001 = 十二月六日（卷首）', r1['month'] == '十二月' and r1['day'] == '六日')
        check('閏五月条目 11 条（十八日~三十日，全卷一）',
              len(gu) == 11 and gu[0]['day'] == '十八日' and gu[-1]['day'] == '三十日'
              and all(g['juan'] == 1 for g in gu))
        check('十二月仅剩卷首 1 条', len(zw) == 1)

print('== works_v1 ==')
wj = os.path.join(W, 'works.json')
wk = load_json(wj)
check('works.json 可解析, 条数 %d' % len(wk), len(wk) == 17)
ids = [e['id'] for e in wk]
check('works id 无重复', len(set(ids)) == len(ids))
need = ['id', 'title', 'author_id', 'genre', 'visit_year', 'date_orig', 'place_id',
        'situation', 'theme', 'mood', 'structure', 'imagery', 'style', 'note']
miss = [e['id'] for e in wk for f in need if f not in e]
check('works 必填字段全在 (%d 缺)' % len(miss), not miss)
zd = [e for e in wk if e['author_id'] == 'p-zhang-dai']
check('张岱 2 篇 visit≠write + 追忆 note',
      len(zd) == 2 and all(
          (('追憶' in (e.get('note') or '') or '追忆' in (e.get('note') or ''))
           and e.get('write_year') is None and e.get('visit_year')) for e in zd))
books = [e for e in wk if e['genre'] == '日记体书']
check('日记体书(book) 2 条（入蜀记+吴船录）', len(books) == 2)
wbom = open(os.path.join(W, 'works.csv'), 'rb').read(3) == b'\xef\xbb\xbf'
check('works.csv UTF-8-BOM', wbom)
check('works METHOD.md 存在', os.path.exists(os.path.join(W, 'METHOD.md')))
check('events_v2 METHOD.md 存在', os.path.exists(os.path.join(D, 'METHOD.md')))

print('\n=== 验收结论:', '全部通过' if ok else '有未过项 ===')
