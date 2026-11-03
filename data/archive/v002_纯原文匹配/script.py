# -*- coding: utf-8 -*-
"""入蜀记 纯原文 → 日期 / 地点 / 活动 事件表

版本：v002_纯原文匹配
只读 source/入蜀记_四库全书本_分段.txt，绝不修改输入文件。

运行：python script.py
输出：data/events.json, data/events.csv，并在 stdout 打印全部统计数字。

处理链：
  1. 切条目   —— 正则找日期行，月份承接
  2. 地名词典 —— 动词+名词候选，经 gazetteer.py 人工筛选
  3. 主地点   —— 按动词层级锚定（行进落点 > 停留活动 > 其余）
  4. 活动类型 —— 关键词多选
"""
import io, os, re, json, csv
from collections import Counter, OrderedDict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
SRC = os.path.join(ROOT, 'source', '入蜀记_四库全书本_分段.txt')
OUTDIR = os.path.join(HERE, 'data')

import gazetteer as GZ

CN = '一二三四五六七八九十'


def cn2int(s):
    """中文数字 1~31。支持 十、二十、二十三、初七 等形式。"""
    if not s:
        return None
    s = s.replace('初', '')
    if s == '十':
        return 10
    if '十' in s:
        a, b = s.split('十', 1)
        tens = CN.index(a) + 1 if a else 1
        ones = CN.index(b) + 1 if b else 0
        return tens * 10 + ones
    if len(s) == 1:
        return CN.index(s) + 1
    return None


# ============================================================ 1. 切条目

DATE_RE = re.compile(r'^(?:\S{1,3}年)?(?P<mon>(?:閏|[%s]|十)+月)?(?P<day>初?[%s]+日)' % (CN, CN))


def read_source():
    """读原文并切日期行。

    两个源文件层面的已知瑕疵（非本脚本造成，已在 METHOD.md 记明）：
      1. L79「至蕪湖縣泊舟吳波亭…」是 L78「十九日…」的硬折行续接，需并回上一日。
      2. L26「時可讀蘇州刺史于頔書…」是某日的残段，其日期行在底本中即作〈闕〉，
         无法归属任何一天，因此不成条，只在统计中报告。
    """
    raw = io.open(SRC, encoding='utf-8').read().replace('\r\n', '\n')
    body = []
    juan = 0
    for ln in raw.split('\n'):
        s = ln.strip()
        if not s:
            continue
        if s.startswith('## 卷'):
            juan = int(re.search(r'\d', s).group())
            continue
        if s.startswith('#') or s.startswith('>') or s == '---':
            continue
        if s.startswith('欽定四庫全書') or s.startswith('宋陸') or re.match(r'^入蜀記卷', s):
            continue
        body.append((juan, s))

    recs, orphans = [], []
    for juan, s in body:
        m = DATE_RE.match(s)
        if m:
            recs.append({'juan': juan, 'date_raw': m.group(0),
                         'mon_raw': m.group('mon'), 'day_raw': m.group('day'),
                         'text': s})
        elif recs and not recs[-1].get('_wrapped'):
            # 无日期行 → 上一日的硬折行续接（只并一次，防止把残段也并走）
            recs[-1]['text'] += s
            recs[-1]['_wrapped'] = True
        else:
            orphans.append(s)
    for r in recs:
        r.pop('_wrapped', None)
    return recs, orphans


# ============================================================ 2. 地名候选

VERBS = '至過泊入發宿抵憩遊游登謁望離到經出留駐次集餞'
VTIER = {'至': 1, '過': 1, '泊': 1, '入': 1, '發': 1, '宿': 1, '抵': 1, '次': 1,
         '憩': 2, '遊': 2, '游': 2, '登': 2, '謁': 2, '留': 2, '駐': 2,
         '集': 2, '餞': 2,
         '望': 3, '離': 3, '到': 3, '經': 3, '出': 3}

TIER_NAME = {1: '行进落点', 2: '停留活动', 3: '远望离开经过'}

# 动词后若先出现这些虚字，说明后面不是紧接地名
SKIP = set('所以此之是得而乃遂因亦皆已今爾焉然且則可能有不未又并將其與於夫'
           '矣也乎哉者一廿餘幾數多往自至還'
           '一二三四五六七八九十百')
# 地名首字不可能是这些
BAD_HEAD = SKIP | set('舟船岸城山中上下見來去行為以有無皆復即與及云曰言謂說記按蓋盖傳舊石碑刻志道時日國事')

GAZ_LIST = sorted(GZ.GAZ, key=len, reverse=True)   # 最长优先
GAZSET = set(GZ.GAZ)


def han_after(text, i, n=12):
    out = []
    for j in range(i, min(len(text), i + n)):
        ch = text[j]
        if not ('\u4e00' <= ch <= '\u9fff'):
            break
        out.append(ch)
    return ''.join(out)


def place_after_verb(text, pos):
    """动词 pos 之后取地名。

    判据（按优先级）：
      1. 地名须落在动词后 0~4 字内（超过则视为跨句，弃用）
      2. 间隔段不得含虚字；例外：於/于 为介词；「X之Y」且 X 本身是地名
      3. 同一短语内有多个候选时取**最长**者并-1. （「江陵之建寜鎮」→ 建寜鎮，
         因为之后的「之」表明后者是前者的下辖具体地点）
    """
    tail = han_after(text, pos + 1, 14)
    if not tail or (tail[0] in SKIP and tail[0] not in '於于'):
        return None, None
    found = []
    for name in GAZ_LIST:
        k = tail.find(name)
        if k < 0 or k > 4:
            continue
        if len(name) == 1 and name[0] in BAD_HEAD:
            continue
        gap = tail[:k]
        if any(c in SKIP and c not in '於于' for c in gap):
            if not (gap.endswith('之') and gap[:-1] in GAZSET):
                continue
        found.append((name, k))
    if not found:
        return None, None
    # 起点最近者优先；仅当短名之后紧跟「之」再接地名时（「江陵之建寜鎮」），
    # 才认为后者是前者的下辖具体地点并取之。
    found.sort(key=lambda x: (x[1], -len(x[0])))
    name0, k0 = found[0]
    for name, k in found:
        if k > k0 and tail[k0:k0 + len(name0)] == name0 and tail[k0 + len(name0):k] == '之' \
                and len(name) > len(name0):
            name0, k0 = name, k
    return name0, pos + 1 + k0


# ============================================================ 3. 活动类型

def classify(text):
    acts = []
    if any(c in text for c in '至過發宿泊入離到經活'):
        acts.append('行路')
    if any(c in text for c in '游遊觀登望覽憩'):
        acts.append('游观')
    if (re.search(r'招飲|郡集|同集|來見|來訪|餞|謁', text)
            or re.search(r'(知州|通判|縣令|教授|郎中|侍郎|運使|都統|主簿|縣尉|秀才)[^。]{0,14}(來|見)', text)
            or re.search(r'見[\u4e00-\u9fff]{0,3}(知州|通判|縣令|郎中|侍郎|都統|運使)', text)):
        acts.append('交游')
    if any(k in text for k in ('按', '蓋', '盖', '誤', '非也', '舊傳', '碑', '石刻', '志云')):
        acts.append('考订')
    return acts


# ============================================================ 主流程

def build():
    recs, orphans = read_source()
    srctext = io.open(SRC, encoding='utf-8').read()
    print('[1] 源文件: %s' % SRC)
    print('    字符数: %d' % len(srctext))
    print('    切出日期行: %d' % len(recs))
    print('    分卷条数:', dict(sorted(Counter(r['juan'] for r in recs).items())))
    print('    无法归属的残段: %d 条（底本缺日期行）' % len(orphans))
    for o in orphans:
        print('      - %s' % o[:60])

    # 词典自检：每个地名必须真的出现在原文里
    bad = [w for w in GZ.GAZ if w not in srctext]
    print('    词典条数: %d；未见于原文的条目: %d' % (len(GZ.GAZ), len(bad)))
    if bad:
        print('      缺:', bad)
    dup = [w for w, c in Counter(GZ.GAZ).items() if c > 1]
    print('    词典重复项: %d %s' % (len(dup), dup))

    month, events, rows = None, [], []
    leap_marks = []
    for r in recs:
        if r['mon_raw']:
            month = r['mon_raw'].rstrip('月').replace('閏', '')
            leap = '閏' in r['mon_raw']
            if leap:
                leap_marks.append(len(events) + 1)
        else:
            leap = False
        r['month'] = month
        r['day'] = r['day_raw']
        r['leap'] = leap
        ev = OrderedDict([
            ('id', 'RSC-%03d' % (len(events) + 1)),
            ('juan', r['juan']), ('month', month), ('day', r['day']),
            ('date_raw', r['date_raw']), ('orig', r['text']),
            ('place', None), ('place_all', []), ('activity', []), ('note', ''),
        ])
        ev['_leap'] = leap
        events.append(ev)
        rows.append((r, ev))

    for i_ev, (r, ev) in enumerate(rows):
        text, start = r['text'], len(r['date_raw'])
        prev_place = rows[i_ev - 1][1]['place'] if i_ev > 0 else None
        next_place = rows[i_ev + 1][1]['place'] if i_ev + 1 < len(rows) else None
        hits = []
        for idx in range(start, len(text)):
            ch = text[idx]
            if ch not in VERBS:
                continue
            pl, off = place_after_verb(text, idx)
            if pl:
                hits.append((off, ch, pl, VTIER[ch]))
        hits.sort(key=lambda h: h[0])
        seen, ordered = set(), []
        for off, v, pl, tier in hits:
            if pl in seen:
                continue
            seen.add(pl)
            ordered.append((off, v, pl, tier))

        ev['place_all'] = [h[2] for h in ordered]
        ev['_tier'] = None
        if ordered:
            for tier in (1, 2, 3):
                same = [h for h in ordered if h[3] == tier]
                if same:
                    ev['place'] = same[0][2]
                    ev['_tier'] = TIER_NAME[tier]
                    ev['note'] = '锚定：%s%s（%s）' % (same[0][1], same[0][2], TIER_NAME[tier])
                    break
        else:
            ev['note'] = ('原文仅记日期，未著地名' if len(text) <= start + 6
                          else '原文未著地名（无动词+词典地名锚定）')
            if prev_place:
                ev['note'] = '原文未著地名（承前一日在%s，本条未重述）' % prev_place
            elif next_place:
                ev['note'] = '原文未著地名（次日在%s，本条未重述）' % next_place

        acts = classify(text)
        ev['activity'] = acts if acts else ['其他']

    return events


def report(events):
    n = len(events)
    has = [e for e in events if e['place']]
    print('\n[2] 事件表统计')
    print('    总条数: %d' % n)
    print('    有地名: %d (%.1f%%)' % (len(has), 100.0 * len(has) / n))
    print('    无地名: %d' % (n - len(has)))

    tier_c = Counter()
    for e in events:
        tier_c[e.get('_tier') or '未锚定'] += 1
    print('    锚定方式:', dict(tier_c))
    for e in events:
        e.pop('_tier', None)

    ac = Counter()
    for e in events:
        for a in e['activity']:
            ac[a] += 1
    print('    活动类型分布:', dict(ac))

    print('\n[3] 分卷统计')
    for j in sorted(set(e['juan'] for e in events)):
        sub = [e for e in events if e['juan'] == j]
        h = [e for e in sub if e['place']]
        print('    卷%d: %d 条, 有地名 %d (%.1f%%)' % (j, len(sub), len(h), 100.0 * len(h) / len(sub)))

    print('\n[4] 无地名条目（逐条列出，不掩盖）')
    for e in events:
        if not e['place']:
            print('    %s %-8s | %-26s | %s' % (e['id'], e['date_raw'], e['note'], e['orig'][:40]))

    print('\n[5] 地名频次 Top 30')
    pc = Counter(p for e in events for p in e['place_all'])
    for k, v in pc.most_common(30):
        print('    %-10s %d' % (k, v))
    print('    唯一地名数: %d' % len(pc))

    # ---- 月份序列自检
    print('\n[6] 月份序列与闰月')
    ym = Counter((e['juan'], e['month']) for e in events)
    print('    各卷各月条数:', {'卷%d %s月' % (k[0], k[1]) if not k[1].endswith('月') else '卷%d %s' % k: v
                             for k, v in sorted(ym.items(), key=lambda x: str(x[0]))})
    print('    「閏」标记出现在条目: %s' % ([e['id'] for e in events if e.get('_leap')] or '无'))
    for e in events:
        e.pop('_leap', None)

    # ---- 日期自检：日必须 1~31，月必须合法，序列逐卷递增
    print('\n[7] 日期自检')
    MONTHS = set(['正', '二', '三', '四', '五', '六', '七', '八', '九', '十', '十一', '十二'])
    bad_m, bad_d, back = [], [], []
    last = {}
    for e in events:
        if e['month'] not in MONTHS:
            bad_m.append((e['id'], e['month']))
        dn = cn2int(e['day'].replace('日', ''))
        if dn is None or not (1 <= dn <= 31):
            bad_d.append((e['id'], e['day']))
        # 同卷内日序应递增（换月后重置）
        key = e['juan']
        if key in last:
            pm, pd = last[key]
            if pm == e['month'] and dn and pd and dn <= pd:
                back.append((e['id'], e['month'], pd, dn))
        last[key] = (e['month'], dn)
    print('    非法月份: %d %s' % (len(bad_m), bad_m))
    print('    非法日期: %d %s' % (len(bad_d), bad_d))
    print('    同月内日序倒退: %d %s' % (len(back), back[:10]))
    print('    日期全部可解析: %s' % ('是' if not bad_m and not bad_d else '否'))
    print('    原文明书「閏五月」：闰月只影响该条自身的月份标签，其后各条按所书月份承接。')


def dump(events):
    os.makedirs(OUTDIR, exist_ok=True)
    jp = os.path.join(OUTDIR, 'events.json')
    io.open(jp, 'w', encoding='utf-8', newline='\n').write(
        json.dumps(events, ensure_ascii=False, indent=2) + '\n')
    cp = os.path.join(OUTDIR, 'events.csv')
    with io.open(cp, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['id', 'juan', 'month', 'day', 'date_raw', 'orig',
                    'place', 'place_all', 'activity', 'note'])
        for e in events:
            w.writerow([e['id'], e['juan'], e['month'], e['day'], e['date_raw'],
                        e['orig'], e['place'] or '', '|'.join(e['place_all']),
                        '|'.join(e['activity']), e['note']])
    print('\n[6] 输出')
    print('    %s (%d bytes)' % (jp, os.path.getsize(jp)))
    print('    %s (%d bytes)' % (cp, os.path.getsize(cp)))


if __name__ == '__main__':
    ev = build()
    report(ev)
    dump(ev)
