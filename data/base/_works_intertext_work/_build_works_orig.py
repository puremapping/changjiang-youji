# -*- coding: utf-8 -*-
"""Step 1: add orig field to works.json/csv; dump alias-hit sentences for review."""
import json, csv, os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
WORKS_J = os.path.join(ROOT, 'data', 'works_v1', 'works.json')
WORKS_C = os.path.join(ROOT, 'data', 'works_v1', 'works.csv')

MAP = {
    'w-you-huang-xi': '柳宗元_遊黃溪記.md',
    'w-shi-de-xi-shan': '柳宗元_始得西山宴遊記.md',
    'w-gu-gu-tan': '柳宗元_鈷鉧潭記.md',
    'w-gu-gu-tan-xi-xiao-qiu': '柳宗元_鈷鉧潭西小丘記.md',
    'w-zhi-xiao-qiu-xiao-shi-tan': '柳宗元_至小丘西小石潭記.md',
    'w-yuan-jia-ke': '柳宗元_袁家渴記.md',
    'w-shi-qu-ji': '柳宗元_石渠記.md',
    'w-shi-jian-ji': '柳宗元_石澗記.md',
    'w-xiao-shi-cheng-shan': '柳宗元_小石城山記.md',
    'w-chi-bi-fu': '蘇軾_赤壁賦.md',
    'w-hou-chi-bi-fu': '蘇軾_後赤壁賦.md',
    'w-shi-zhong-shan-ji': '蘇軾_石鐘山記.md',
    'w-you-jin-shan-si': '蘇軾_遊金山寺.md',
    'w-jin-shan-ye-xi': '張岱_金山夜戲.md',
    'w-jin-shan-jing-du': '張岱_金山競渡.md',
    'w-ru-shu-ji': '陸游_入蜀記.md',
    'w-wu-chuan-lu': '范成大_吳船錄.md',
}

# Page-footer lines in the two diary files (wikisource public-domain boilerplate,
# not part of the literary text). Only trailing boilerplate is removed; all
# volume headings (## 卷N) and all dated paragraphs are kept verbatim.
FOOTER = (
    '此南宋作品在全世界都属于公有领域',
    'Public domainPublic domainfalsefalse',
)

def extract_orig(path):
    with open(path, encoding='utf-8') as f:
        lines = f.read().split('\n')
    assert lines[0].startswith('# '), path
    body = lines[1:]                       # drop first-line # metadata only
    while body and (body[-1].strip() == '' ):
        body.pop()
    # drop trailing wiki public-domain boilerplate (keep every text line)
    while body and any(footer in body[-1] for footer in FOOTER):
        body.pop()
        while body and body[-1].strip() == '':
            body.pop()
    orig = '\n'.join(body).rstrip('\n')
    return orig

works = json.load(open(WORKS_J, encoding='utf-8'))
assert len(works) == 17
for w in works:
    src = os.path.join(ROOT, 'source', 'text', MAP[w['id']])
    orig = extract_orig(src)
    if 'orig' in w:
        del w['orig']
    w['orig'] = orig                       # append at end, preserving field order

with open(WORKS_J, 'w', encoding='utf-8', newline='\n') as f:
    json.dump(works, f, ensure_ascii=False, indent=2)
    f.write('\n')

with open(WORKS_C, encoding='utf-8-sig', newline='') as f:
    rows = list(csv.reader(f))
header, datarows = rows[0], rows[1:]
assert 'orig' not in header
header.append('orig')
byid = {w['id']: w for w in works}
for r in datarows:
    assert r[0] in byid
    r.append(byid[r[0]]['orig'])
with open(WORKS_C, 'w', encoding='utf-8-sig', newline='') as f:
    wr = csv.writer(f, lineterminator='\r\n')
    wr.writerow(header)
    wr.writerows(datarows)

# verify orig is contiguous substring of source file (after metadata line)
for w in works:
    src = os.path.join(ROOT, 'source', 'text', MAP[w['id']])
    t = open(src, encoding='utf-8').read()
    assert w['orig'] in t, w['id']

# alias scan; dump sentences containing any alias for manual classification.
ALIAS = ['李白','太白','杜甫','子美','白居易','樂天','蘇軾','東坡','坡公',
         '黃庭堅','山谷','黃魯直','涪翁','諸葛','武侯','顏真卿','顏魯公']

def split_sents(text):
    """Split at 。！？ but not inside 「」『』（）《》 (depth-aware)."""
    depth = 0
    out, cur = [], []
    pairs = {'「': '」', '『': '』', '（': '）', '《': '》'}
    close = {v: k for k, v in pairs.items()}
    for ch in text:
        if ch in pairs:
            depth += 1
        elif ch in close:
            depth = max(0, depth - 1)
        cur.append(ch)
        if ch in '。！？' and depth == 0:
            out.append(''.join(cur))
            cur = []
    if cur:
        out.append(''.join(cur))
    return out

cands = []
for w in works:
    for s in split_sents(w['orig']):
        hits = [a for a in ALIAS if a in s]
        if hits:
            cands.append({'wid': w['id'], 'title': w['title'], 'hits': hits,
                          'quote': s, 'qlen': len(s)})

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'candidates.json')
json.dump(cands, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print('works with orig:', sum(bool(w['orig']) for w in works), '/', len(works))
print('orig chars total:', sum(len(w['orig']) for w in works))
print('candidate sentences:', len(cands))
for w in works:
    print(' ', w['id'], len(w['orig']))
