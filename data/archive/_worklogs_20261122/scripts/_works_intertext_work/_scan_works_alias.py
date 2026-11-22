# -*- coding: utf-8 -*-
"""Re-scan all 17 orig with expanded alias table; dump numbered candidates."""
import json, os, collections

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
works = json.load(open(os.path.join(ROOT, 'data', 'works_v1', 'works.json'), encoding='utf-8'))

# alias -> target persons id.  Seven 前贤 from events flow (METHOD.md §9)
# + task-mandated additions that appear in works originals.
ALIAS = {
    # 李白
    '李白': 'p-li-bai', '太白': 'p-li-bai', '李太白': 'p-li-bai',
    # 杜甫
    '杜甫': 'p-du-fu', '子美': 'p-du-fu', '杜子美': 'p-du-fu',
    '少陵': 'p-du-fu', '老杜': 'p-du-fu',
    # 白居易
    '白居易': 'p-bai-juyi', '樂天': 'p-bai-juyi', '白樂天': 'p-bai-juyi',
    # 蘇軾
    '蘇軾': 'p-su-shi', '東坡': 'p-su-shi', '坡公': 'p-su-shi',
    '蘇公': 'p-su-shi',
    # 黃庭堅
    '黃庭堅': 'p-huang-ti', '山谷': 'p-huang-ti', '黃魯直': 'p-huang-ti',
    '涪翁': 'p-huang-ti', '魯直': 'p-huang-ti',
    # 諸葛亮
    '諸葛': 'p-zhuge-liang', '武侯': 'p-zhuge-liang',
    '諸葛孔明': 'p-zhuge-liang',
    # 顏真卿
    '顏真卿': 'p-yu-yan', '顏魯公': 'p-yu-yan', '真卿': 'p-yu-yan',
    # task-mandated additions (new persons)
    '李渤': 'p-li-bo',
    '酈元': 'p-li-daoyuan', '酈道元': 'p-li-daoyuan',
    '韓蘄王': 'p-han-shizhong', '韓世忠': 'p-han-shizhong',
}

def split_sents(text):
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
        hits = sorted({ALIAS[a] for a in ALIAS if a in s})
        if hits:
            cands.append({'wid': w['id'], 'title': w['title'],
                          'hits': hits, 'quote': s.strip(),
                          'raw': s, 'qlen': len(s.strip())})
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'candidates2.json')
json.dump(cands, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print('total candidate sentences:', len(cands))
print('by work:', dict(collections.Counter(x['wid'] for x in cands)))
print('by target:', dict(collections.Counter(t for x in cands for t in x['hits'])))
for i, x in enumerate(cands):
    print(i, x['wid'], x['hits'], 'len', x['qlen'])
    print('   ', x['quote'][:170].replace('\n', '⏎'))
