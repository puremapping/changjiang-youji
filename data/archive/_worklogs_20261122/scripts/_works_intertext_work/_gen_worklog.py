# -*- coding: utf-8 -*-
"""Generate WORKLOG_WORKS_INTERTEXT.md with per-entry decision records."""
import json, os, collections

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(os.path.dirname(BASE))
works = {w['id']: w for w in json.load(open(os.path.join(ROOT,'data','works_v1','works.json'),encoding='utf-8'))}
persons = {p['id']: p for p in json.load(open(os.path.join(BASE,'persons.json'),encoding='utf-8'))}
intertexts = json.load(open(os.path.join(BASE,'intertexts.json'),encoding='utf-8'))
dec = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'_intertext_decisions.json'),encoding='utf-8'))
cands = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'candidates2.json'),encoding='utf-8'))
new = intertexts[102:]

L = []
A = L.append
A('# works 層互文逐條決策記錄（WORKLOG_WORKS_INTERTEXT）\n')
A('> 2026-11-22。專屬本批（works orig + works 互文），不覆蓋 `WORKLOG_20261122.md`。')
A('> 每條含：id / 來源 work / target / relation / 完整 quote / 判據 note。')
A('> 引文均為 `works.orig` 連續子串（程序 122/122 校驗通過）。\n')
A('## A. orig 落盤決策（17 篇）\n')
A('| work id | 篇名 | orig 字數 | 取法 |')
A('|---|---|---:|---|')
for w in works.values():
    note = ('全文（日記體，卷一至卷六全，去網頁公共領域宣告）' if w['id']=='w-ru-shu-ji' else
            '全文（日記體，卷上卷下全，去網頁公共領域宣告）') if w['genre']=='日记体书' else '全文正文（去首行 # 元資訊）'
    A('| %s | %s | %d | %s |' % (w['id'], w['title'], len(w['orig']), note))
A('')
A('兩本日記體**取全文、未節選**：入蜀記 32,913 字、吳船錄 21,254 字（任務書「優先全文」）。')
A('17 篇合計 59,472 字；繁體標點照抄，一字未改。\n')

A('## B. 別名命中與排除\n')
A('- 別名表：events 七前賢（李白/太白；杜甫/子美/少陵/老杜；白居易/樂天；蘇軾/東坡/坡公/蘇公；'
  '黃庭堅/山谷/黃魯直/涪翁/魯直；諸葛/武侯；顏真卿/顏魯公）+ 新增 李渤 / 酈元(酈道元) / 韓蘄王(韓世忠)。')
A('- 逐句切分：遇 。！？ 斷句；「」『』（）《》 內不斷。命中句 121。')
A('- 排除 2 句地形語「山谷」（**不建條目**，避免 int-066 同類誤判）：')
for k, v in dec['skip'].items():
    A('  - 候選 #%s：%s' % (k, v))
A('- 其餘 119 句中，2 句含雙 target 拆為 2 條，合計 **122 條**（int-103…int-224）。\n')

A('## C. 新增 persons（3）\n')
A('| id | 姓名 | 生卒 | 依據 / note |')
A('|---|---|---|---|')
for pid in ['p-li-bo','p-li-daoyuan','p-han-shizhong']:
    p = persons[pid]
    A('| %s | %s | %s–%s | %s |' % (pid, p['name'],
      p['birth_year'] if p['birth_year'] is not None else 'null',
      p['death_year'] if p['death_year'] is not None else 'null',
      p['note']))
A('')

A('## D. 逐條決策（122 條）\n')
A('| id | work | target | relation | quote（原文連續子串） | 判據 / note |')
A('|---|---|---|---|---|---|')
for e in new:
    q = e['quote'].replace('\n', ' ')
    if len(q) > 120: q = q[:117] + '…'
    q = q.replace('|', '｜')
    n = e['note'].replace('\n',' ').replace('|','｜')
    if len(n) > 110: n = n[:107] + '…'
    A('| %s | %s | %s | %s | %s | %s |' % (
        e['id'], e['source_id'], e['target_name'], e['relation'], q, n))
A('')

A('## E. 存疑與最終自檢\n')
doubt = [e for e in new if '存疑' in e['note']]
A('- 存疑 %d 條：%s。' % (len(doubt), '、'.join(e['id'] for e in doubt)))
A('- distribution by target: ' + '、'.join('%s %d'%(k,v) for k,v in
    collections.Counter(e['target_name'] for e in new).most_common()) + '。')
A('- distribution by relation: ' + '、'.join('%s %d'%(k,v) for k,v in
    collections.Counter(e['relation'] for e in new).most_common()) + '。')
A('- 全部 self-check 見 `METHOD_WORKS_INTERTEXT.md` §9，腳本 `data/base/_check_works_intertexts.py`。')
A('- 復現：`python data/base/_build_works_orig.py` → `_scan_works_alias.py` → '
  '`_build_works_intertexts.py` → `_check_works_intertexts.py`。')

out = os.path.join(BASE, 'WORKLOG_WORKS_INTERTEXT.md')
open(out,'w',encoding='utf-8',newline='\n').write('\n'.join(L)+'\n')
print('written', out, 'lines', len(L), 'entries', len(new))
