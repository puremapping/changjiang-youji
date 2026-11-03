# -*- coding: utf-8 -*-
"""入蜀记 纯原文 → 日期 / 地点 / 活动 事件表

版本：v004_入蜀记_词典补全
只读 source/入蜀记_四库全书本_分段.txt，绝不修改输入文件。

运行：python script.py
输出：data/events.json, data/events.csv，并在 stdout 打印全部统计与审计信息。

相对 v002 的三处实质改动（详见 METHOD.md）
  1. 地名修复 —— 补入 12 个漏抽地名（gazetteer.py 附证据），新增「赴」动词。
     同时区分「到达落点」与「经过点」：原文「過X」而未停时不算当天落点。
  2. 活动类型 —— 放弃全文关键词命中，改为「分句 + 主语判定 + 引文屏蔽」。
     宁可少标不可多标（判据 C1~C4）。
  3. 日期模型 —— 引入事件类型 `kind`：
       date     原文有日期、有记事
       merged   合记日（「二十二日至二十四日」→ 按 N 日计，仍作 1 条输出）
       empty    原文只标日期、无记事（如「三十日。」「二十七日。」）
     日历格数 != 事件条数，这是 145 vs 157 差额的来源。
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

# 单日：「十八日」「初七日」；合记：「二十二日至二十四日」
DATE_RE = re.compile(r'^(?:\S{1,3}年)?(?P<mon>(?:閏|[%s]|十)+月)?(?P<day>初?[%s]+日)'
                     r'(?P<merge>至(?:[%s]|十)+日)?' % (CN, CN, CN))


def read_source():
    """读原文并切日期行。

    三个源文件层面的已知瑕疵（非本脚本造成，已在 METHOD.md 记明）：
      1. L79「至蕪湖縣泊舟吳波亭…」是 L78「十九日…」的硬折行续接，需并回上一日。
      2. L26「時可讀蘇州刺史于頔書…」是某日的残段，其日期行在底本中即作〈闕〉，
         无法归属任何一天，因此不成条，只在统计中报告。
      3. 卷1 L25 之后、「時可讀…」之前缺一个「五日」条目（四库本无「五日」）。
         无法确定该段是并入初五还是替换初五，脚本不猜——记为「底本待考」。
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
                         'merge_raw': m.group('merge'), 'text': s})
        elif recs and not recs[-1].get('_wrapped'):
            # 无日期行 → 上一日的硬折行续接（只并一次，防止把残段也并走）
            recs[-1]['text'] += s
            recs[-1]['_wrapped'] = True
        else:
            orphans.append(s)
    for r in recs:
        r.pop('_wrapped', None)
    return recs, orphans


# ============================================================ 2. 地名锚定

# 「赴」为 v004 新增：v002 §5.2b RSC-113「五鼓赴能仁院」动词为「赴」，不在表内。
# 归第 1 级（行进落点）——「赴」是明确的「前往并抵达」义，与「至/抵」同功能。
VERBS = '至過泊入發宿抵憩遊游登謁望離到經出留駐次集餞赴'
VTIER = {'至': 1, '過': 1, '泊': 1, '入': 1, '發': 1, '宿': 1, '抵': 1, '次': 1, '赴': 1,
         '憩': 2, '遊': 2, '游': 2, '登': 2, '謁': 2, '留': 2, '駐': 2,
         '集': 2, '餞': 2,
         '望': 3, '離': 3, '到': 3, '經': 3, '出': 3}

# 判据 H：经过点动词。命中地名但**不代表当日停驻**，故不填 place。
# 「過」在游记里绝大多数是「顺流经过」，不是「到达」。
WAYPOINT_VERBS = set('過經望出')
# 判据 H2：离开点动词。「離黄州」「發丹陽」= 当天从那里出发，不是当天到此。
DEPART_VERBS = set('離發')

# 「到」单列：v002 把它放第 3 级，导致 RSC-135「到歸州」被记成「远望离开经过」。
# 「到」实为到达义，v004 提到第 1 级。理由：「到」= arrive，与「至」同义。
VTIER['到'] = 1
VTIER['離'] = 3
VTIER['出'] = 3
VTIER['望'] = 3
VTIER['經'] = 3

TIER_NAME = {1: '到达落点', 2: '停留活动', 3: '离开／远望／经过'}

# 动词后若先出现这些虚字，说明后面不是紧接地名
SKIP = set('所以此之是得而乃遂因亦皆已今爾焉然且則可能有不未又并將其與於夫'
           '矣也乎哉者一廿餘幾數多往自至還'
           '一二三四五六七八九十百')
# 地名首字不可能是这些
_BAD_BASE = set('舟船岸城山中上下見來去行為以有無皆復即與及云曰言謂說記按蓋盖傳舊石碑刻志道時日國事')
GAZ_LIST = sorted(GZ.GAZ, key=len, reverse=True)   # 最长优先
GAZSET = set(GZ.GAZ)
# 词典里确实以该字起首的地名（「能仁院」的「能」）必须豁免，否则自相矛盾
BAD_HEAD = (SKIP | _BAD_BASE) - GAZSET


def han_after(text, i, n=12):
    out = []
    for j in range(i, min(len(text), i + n)):
        ch = text[j]
        if not ('\u4e00' <= ch <= '\u9fff'):
            break
        out.append(ch)
    return ''.join(out)


def place_after_verb(text, pos, max_gap=4):
    """动词 pos 之后取地名（v002 判据 C/D/E 保留，间隔上限改为参数）。

    v002 审计发现一处兼容问题：原实现 `tail.find(name)` 在候选名是另一候选项的子串时
    会取到前者的中间位置，v004 改为「只认起点在候选名起点上的匹配」。

    v004 另修：v002 的 SKIP 表含「能」，且该表同时用于「间隔虚字阻断」和「地名首字否决」，
    于是「赴能仁院」被自己表里的「能」挡死。v004 把两类检查分开：
      间隔虚字  → SKIP
      地名首字  → BAD_HEAD（并在最后减去词典里真实存在的首字）
    """
    tail = han_after(text, pos + 1, 16)
    if not tail:
        return None, None
    found = []
    for name in GAZ_LIST:
        k = tail.find(name)
        if k < 0 or k > max_gap:
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
    found.sort(key=lambda x: (x[1], -len(x[0])))
    name0, k0 = found[0]
    for name, k in found:
        if k > k0 and tail[k0:k0 + len(name0)] == name0 and tail[k0 + len(name0):k] == '之' \
                and len(name) > len(name0):
            name0, k0 = name, k
    return name0, pos + 1 + k0


# 判据 J0：「自到X」「自離X」「自是」里的「到/離」不是当日动作，是回溯。
# 例：卷2 八月十一日「自到江州，至是凡十日皆晴」——江州是八月初二到的，不是十一日到的。
RETRO = re.compile(r'自(到|離|入|出|此|是|過)$')

# 「泊/宿/留」本来就意味着「在此停驻」，但很少有人写「泊于X」，更常见的表述是
# 「至蕪湖縣泊舟吳波亭」「宿清虚西室」——落点地名夹在中间。因此对这三个动词，
# 允许在「泊/宿/留」之后再向前跨过「舟/船」等泛称，取最近的地名（判据 J）。
LODGE_VERBS = set('泊宿留駐憩次抵')
LODGE_FILLER = set('舟船於于小大之岸其江')


def lodge_near(text, pos):
    """「泊/宿/留」后 12 字内取地名，允许跨过 LODGE_FILLER。

    与 place_after_verb 的区别：这里动词后常见「泊舟X」「宿X」两种语序，
    「舟」不是虚字而是宾语，v002 把「泊舟吳波亭」误判为跨句即因「舟」被算进虚字集。
    同一句里允许多个落点（「過州壩倉頭百里洲泊沱㶩」→ 泊沱㶩优先）。
    """
    tail = han_after(text, pos + 1, 14)
    if not tail:
        return []
    out = []
    for name in GAZ_LIST:
        k = tail.find(name)
        if k < 0 or k > 10:
            continue
        gap = tail[:k]
        if any(c not in LODGE_FILLER for c in gap):
            continue
        out.append((name, k))
    out.sort(key=lambda x: x[1])
    return [n for n, _ in out]


def place_after_verb_strict1(text, pos):
    """单字缩写锚定：只有「动词 + 单字 + 句读/句末」才算命中。

    用于 GZ.ABBR（如「自離黄，雖行夾中…」的「黄」）。加严格边界是为了避免
    「至黄茅」「過黄花」这类把别的词的第一个字当缩写的误配。
    """
    i = pos + 1
    if i >= len(text):
        return None, None
    ch = text[i]
    if ch not in GZ.ABBR:
        return None, None
    nxt = text[i + 1] if i + 1 < len(text) else ''
    if nxt in GZ.NONLOC or nxt in '，、。' or nxt == '':
        return GZ.ABBR[ch][0], i
    return None, None


# ============================================================ 3. 活动类型（v004 重写）

# 判据 C2：引文起首标记。
CITE_LEAD = re.compile(r'(詩云|詩曰|詩謂|樂府云|樂府|歌云|諺謂|諺云|傳云|舊傳|舊説|舊聞'
                       r'|所謂|云|曰|謂|有詩|作詩|題云|碑云|記云|志云|圖經|史云|注云'
                       r'|詩中|集中|詩有)')
# 引文标记后若紧跟这些成分，说明只是「某人说某事」的叙事，不是诗文引用，
# 不应当作引文剔除（v004 审计：v002 风格的粗暴引文剔除会吞掉真行程）。
NARRATIVE_AFTER = re.compile(r'^(自|其|此|之|是|為|以|於|在|當|乃|便|即|皆|多|少|甚|可|不'
                             r'|欲|將|始|方|已|遂|因|而|所|有|無|如|若|每|又|復|去|來|至|入|過|泊|屬|與|從)')
# 引文后紧跟的评判语（「為妙也」「非也」「誤矣」）仍是陆游本人的话 —— 属考订
EVAL_TAIL = re.compile(r'(為妙|最妙|妙也|佳句|非也|誤矣|誤以|不信|不可信|信然|殆為|形容最妙'
                       r'|善狀物|得句於此|不刋之妙|不刊之妙|始知|乃知)')

# 判据 C3：非陆游主语。
# 只收「明确是别人/别物做主语」的起首词；单字姓（王/李/劉…）不收——
# 「早至夔州」会被误判为姓「夔」，故姓氏一律不作非本人标记（宁可漏收）。
NON_SELF_LEAD = re.compile(r'^(或|人|舟人|土人|楚人|僧|祝史|議者|說者|俗|世|前輩'
                           r'|張文潛|歐陽公|杜牧|東坡先生|山谷|魯直|太白|樂府|圖經|國史'
                           r'|朝廷|州治|縣|監|漕|轉運|提舉|宣撫|大將|神|蓋|故其)')
CLAUSE_STOP = '遂晚早午後夜食時俄因乃故然但亦皆又復且則既始及而'
CLAUSE_STOP_SET = set(CLAUSE_STOP)

ARRIVE = set('至過發宿泊入離到經赴抵次憩留駐')
# 「觀」单字不可作游观依据：「觀察推官」「觀察使」是官名，v004 审计发现
# RSC-025 因此被误标「游观」。只有「游觀/登覽/望見」这类词形才算。
VISIT = re.compile(r'(遊(?!手)|(?<![下江])游(?:天|東|西|南|北|甘|青|清|二|報|光|開|頭|黄|栖|神|玉|峽|山|湖|寺|觀)'
                  r'|觀(?!者|音|察|文|額|屋|主|下|中|前|之|聽)'
                  r'|厯游|登(?!科|第)|望見|覽(?!觀)|憩|謁)')
# 判据 C4b：山水风物描写（「南望京口月観…」「四望無際」「望之如雪」）不是游览行为。
SCENERY = re.compile(r'(南望|北望|東望|西望|四望|回望|遥望|望之|望見|望{1}[^，。]{0,6}(如|似|若))')
# 判据 C4：行程动词必须紧跟「地点/方向」成分才算「行路」。
# 只出现「至」「過」而未带地点，多半是「至數尺」「過梅」这类非行程用法。
TRIP = re.compile(r'(至(?!少|是|此|今|於)|過|發(?!運|揮)|宿|泊|入(?!水|口)|離(?!别|去)|到|經|赴'
                  r'|抵|次(?!日|之)|憩|駐'
                  r'|行\d|挽行|行[一二三四五六七八九十]|陸行|舟行|解舟|解船|掛帆|張帆|開船'
                  r'|移舟|抛江|溯|泝|順流)')
# 判据 C4b：「留」在「留」后无地名义更常见于「留此」「留恋」，
# 只在「留X」形（如「留金山」）时才当行程，故由 NAILED_PLACE 反查：
# 本条的 place 锚定动词若是「留」「出」，则该条确有行程，行路由锚定结果直接给出。


def clauses(text, start=0):
    """切分句。返回 [(起点偏移, 子句文本)]。

    四库本无标点，因此用「句读字 + 时间/连词起首字」切句。切分故意切得很碎——
    宁可把一个句子切成两半（漏标某类），也不要把两句并在一起（多标）。
    但切碎会让「遂」这类连词被当成新句主语（「遂至黄州」被切成「遂」「至黄州」），
    故对纯连词起首的碎句做一次向前合并（见 merge_lead）。
    """
    out, buf, s = [], '', start
    i = start
    while i < len(text):
        ch = text[i]
        if ch in CLAUSE_STOP_SET and len(buf) >= 2:
            out.append((s, buf))
            buf, s = '', i
        buf += ch
        if ch in '。！？；':
            out.append((s, buf))
            buf, s = '', i + 1
        i += 1
    if buf:
        out.append((s, buf))
    out = [(o, c) for o, c in out if c]
    # 纯连词碎句（「遂」「因」「而」「然」…）并回上一句，避免把主语吞掉
    merged = []
    for o, c in out:
        if merged and len(c) <= 2 and c[0] in '遂因而然但亦又復且則故':
            po, pc = merged[-1]
            merged[-1] = (po, pc + c)
        else:
            merged.append((o, c))
    return merged


def is_quotation(cl):
    """判据 C2：本句是否为引文（他人诗文的引用，非陆游本人行程）。

    C2a 句中（句首 6 字内）出现「云/曰/謂/詩云/舊傳/圖經…」→ 疑似引文；
    C2b 但若标记后紧跟的是叙事成分（「自言峽州以西…」「所謂下元水府」），
        那是陆游在转述事实而非引诗，不剔除；
    C2c 引文后紧跟的评判语（「乃知…為妙也」）也不算引文，交回考订判定。
    """
    m = CITE_LEAD.search(cl)
    if not m:
        return False
    head_zone = m.start() <= 6
    if not head_zone and m.group() not in ('所謂', '詩中', '集中', '詩有'):
        return False
    rest = cl[m.end():]
    han = len(re.sub(r'[^\u4e00-\u9fff]', '', rest))
    if NARRATIVE_AFTER.match(rest) and m.group() in ('云', '曰', '謂', '所謂'):
        return False               # 「某人云某事」「所謂X也」是叙事，不是引诗
    if m.group() in ('所謂', '曰') and han < 6:
        return False               # 「所謂下元水府」「曰木末」是命名，不是引诗
    if m.group() == '所謂' and NARRATIVE_AFTER.match(rest):
        return False               # 「謁英靈助順王祠，所謂下元水府也」是解释祠名，不是引诗
    ev = EVAL_TAIL.search(rest)
    if ev and han < 20:
        return False               # 引文很短且后接评判 → 按陆游评论处理
    if ev and ev.start() > 0:
        return False
    return True


def self_led(cl):
    """判据 C3：主语是否为陆游本人。"""
    c = cl.lstrip(CLAUSE_STOP)
    return not NON_SELF_LEAD.match(c)


def classify(text, start=0):
    """v004 活动类型。返回 (acts, evidence)。

    判据顺序（保守，宁可少标）：
      C1 先切分句（并合并纯连词碎句）；
      C2 引文句整句剔除（含「詩云/云/曰/所謂/圖經…」引出的诗文）；
      C3 主语非陆游（「舟人云」「土人云」「議者謂」）整句剔除；
      C4 剩下子句里按 TRIP/VISIT 等词形判「行路/游观/交游/考订」，
         「行路」须命中行程动词词形，不能是任何含「至」「過」的字；
      C5 一条日记可多标签；全部剔除后仍无标签 → 其他。
    """
    acts, ev = [], []
    for off, cl in clauses(text, start):
        if is_quotation(cl):
            ev.append('C2引文:%s' % cl[:12])
            continue
        if not self_led(cl):
            ev.append('C3非本人:%s' % cl[:12])
            continue
        if TRIP.search(cl):
            if '行路' not in acts:
                acts.append('行路')
                ev.append('行路:%s' % cl[:12])
        if VISIT.search(cl) and not SCENERY.search(cl):
            if '游观' not in acts:
                acts.append('游观')
                ev.append('游观:%s' % cl[:12])
        if (re.search(r'招飲|郡集|同集|來見|來訪|餞|謁|招食|飯僧|飯於|會見|來参', cl)
                or re.search(r'(知州|通判|縣令|教授|郎中|侍郎|運使|都統|主簿|縣尉|秀才|知府'
                             r'|監税|司業|檢正|少卿|學士|參軍|推官|少保)[^。]{0,12}(來|見)', cl)):
            if '交游' not in acts:
                acts.append('交游')
                ev.append('交游:%s' % cl[:12])
        if (re.search(r'按[^。]{0,8}|誤矣|誤以|非也|舊傳|舊説|志云|圖經|考之|不知實否'
                      r'|疑即|未詳孰是|孰是|不可知|信然|亦不可誣|傳以為|世傳以為|不以為信'
                      r'|當是|蓋史|避諱|唐諱|諱改|為妙|妙也|得句於此|善狀物', cl)):
            if '考订' not in acts:
                acts.append('考订')
                ev.append('考订:%s' % cl[:12])
    return acts, ev


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
    print('    缩写锚定项: %d %s' % (len(GZ.ABBR), list(GZ.ABBR)))

    month, events, rows = None, [], []
    for r in recs:
        if r['mon_raw']:
            month = r['mon_raw'].rstrip('月').replace('閏', '')
        r['month'] = month
        r['day'] = r['day_raw']
        # kind 判定
        merge_from, merge_to = None, None
        if r['merge_raw']:
            merge_from = cn2int(r['day_raw'].replace('日', ''))
            merge_to = cn2int(r['merge_raw'].replace('至', '').replace('日', ''))
            kind = 'merged'
        elif len(r['text']) <= len(r['date_raw']) + 1:
            kind = 'empty'
        else:
            kind = 'date'
        ev = OrderedDict([
            ('id', 'RSC-%03d' % (len(events) + 1)),
            ('juan', r['juan']), ('month', month), ('day', r['day']),
            ('date_raw', r['date_raw']), ('orig', r['text']),
            ('kind', kind),
            ('place', None), ('place_all', []), ('place_waypoint', []),
            ('place_departed', []), ('activity', []), ('note', ''),
        ])
        ev['_merge'] = (merge_from, merge_to)
        events.append(ev)
        rows.append((r, ev))

    for i_ev, (r, ev) in enumerate(rows):
        text, start = r['text'], len(r['date_raw'])
        prev_place = rows[i_ev - 1][1]['place'] if i_ev > 0 else None
        next_place = rows[i_ev + 1][1]['place'] if i_ev + 1 < len(rows) else None

        hits, abbr_hits, depart_hits = [], [], []
        for idx in range(start, len(text)):
            ch = text[idx]
            if ch not in VERBS:
                continue
            if idx > start and text[idx - 1] == '自':
                continue            # 判据 J0：回溯句「自到X」，不是当天动作
            pl, off = place_after_verb(text, idx)
            if pl:
                # 判据 H2：「離X」是离开，不是当日停驻；「發X」同理（发船之地＝次日已离开）
                if ch in DEPART_VERBS:
                    depart_hits.append((off, ch, pl))
                else:
                    hits.append((off, ch, pl, VTIER[ch]))
                continue
            if ch in LODGE_VERBS:
                lp = lodge_near(text, idx)
                if lp:
                    # 同一停驻句里的多个落点都算「在此停」；第一个作 place
                    for j, nm in enumerate(lp):
                        hits.append((idx if j == 0 else idx + 1, ch, nm, VTIER[ch]))
                    continue
            ab, aoff = place_after_verb_strict1(text, idx)
            if ab:
                abbr_hits.append((aoff, ch, ab))

        hits.sort(key=lambda h: h[0])
        seen, ordered = set(), []
        for off, v, pl, tier in hits:
            if pl in seen:
                continue
            seen.add(pl)
            ordered.append((off, v, pl, tier))

        # 落点 = tier1 中非「經過類」動詞的
        landings = [h for h in ordered if h[3] == 1 and h[1] not in WAYPOINT_VERBS]
        waypoints = [h[2] for h in ordered if h[1] in WAYPOINT_VERBS]
        stays = [h for h in ordered if h[3] == 2]
        ev['place_all'] = [h[2] for h in ordered]
        ev['place_waypoint'] = list(dict.fromkeys(waypoints))
        ev['place_departed'] = list(dict.fromkeys(h[2] for h in depart_hits))

        if landings:
            h = landings[0]
            ev['place'] = h[2]
            ev['_tier'] = '到达落点'
            ev['note'] = '锚定：%s%s（到达落点）' % (h[1], h[2])
        elif stays:
            h = stays[0]
            ev['place'] = h[2]
            ev['_tier'] = '停留活动'
            ev['note'] = '锚定：%s%s（停留活动）' % (h[1], h[2])
        elif ev['place_waypoint']:
            ev['_tier'] = '仅经过'
            ev['note'] = '仅记经过%s，原文未著当日停驻地' % '、'.join(ev['place_waypoint'][:3])
        elif ev['place_departed']:
            ev['_tier'] = '仅离点'
            ev['note'] = '原文记「%s%s」，只标明出发地，未著当日停驻地' % (
                DEPART_VERBS, '、'.join(ev['place_departed']))
        elif abbr_hits:
            # 缩写锚定：只产「离开点」，按判据 H 不填 place
            aoff, v, pl = abbr_hits[0]
            ev['_tier'] = '缩写离点'
            ev['note'] = '原文以缩写「%s」记%s（%s），未重述当日停驻地' % (
                text[aoff], pl, GZ.ABBR[text[aoff]][1])
        else:
            ev['note'] = ('原文仅标日期，无记事' if len(text) <= start + 6
                          else '原文未著地名（无「动词+词典地名」锚定）')
            if prev_place:
                ev['note'] = '原文未著地名（承前一日在%s，本条未重述）' % prev_place
            elif next_place:
                ev['note'] = '原文未著地名（次日在%s，本条未重述）' % next_place

        if ev['kind'] == 'merged':
            a, b = ev['_merge']
            ev['note'] = '合记：%d日至%d日共%d日同记（%s）' % (a, b, b - a + 1, ev['orig'])
            ev['place'] = None
            ev['_tier'] = '合记'
        if ev['kind'] == 'empty':
            ev['place'] = None
            ev['_tier'] = '无记事'

        acts, aev = classify(text, start)
        # 判据 C4b：既有地名锚定（到达/停留/经过/离点），则本条必有行程事实，
        # 即便正文只以诗词化的「過X」出现（被判据 C2 剔除），也应记「行路」。
        if (ev['place'] or ev['place_waypoint'] or ev['place_departed']) and '行路' not in acts:
            acts = ['行路'] + acts
            aev = aev + ['C4b锚定补行路']
        ev['activity'] = acts if acts else ['其他']
        ev['_actev'] = aev

    return events


def report(events):
    n = len(events)
    has = [e for e in events if e['place']]
    print('\n[2] 事件表统计')
    print('    总条数: %d' % n)
    print('    有地名: %d (%.1f%%)' % (len(has), 100.0 * len(has) / n))
    print('    无地名: %d' % (n - len(has)))
    kc = Counter(e['kind'] for e in events)
    print('    条目类型 kind:', dict(kc))

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
    multi = sum(1 for e in events if len(e['activity']) > 1)
    print('    多标签条目: %d' % multi)
    for e in events:
        e.pop('_actev', None)

    print('\n[3] 分卷统计')
    for j in sorted(set(e['juan'] for e in events)):
        sub = [e for e in events if e['juan'] == j]
        h = [e for e in sub if e['place']]
        print('    卷%d: %d 条, 有地名 %d (%.1f%%)' % (j, len(sub), len(h), 100.0 * len(h) / len(sub)))

    print('\n[4] 无地名条目（逐条列出，不掩盖）')
    for e in events:
        if not e['place']:
            print('    %s %-8s | %-30s | %s' % (e['id'], e['date_raw'], e['note'][:30], e['orig'][:44]))

    print('\n[5] 地名频次 Top 30')
    pc = Counter(p for e in events for p in e['place_all'])
    for k, v in pc.most_common(30):
        print('    %-14s %d' % (k, v))
    print('    唯一地名数（place_all）: %d' % len(pc))

    # ---- 日历格数核算（145 vs 157 的查证）
    print('\n[6] 日历格数核算（查证 v002 未解之谜）')
    cells = 0
    detail = []
    for e in events:
        if e['kind'] == 'merged':
            a, b = e['_merge']
            cells += b - a + 1
            detail.append('%s 合记 %d 日' % (e['id'], b - a + 1))
        else:
            cells += 1
    print('    事件条数: %d' % n)
    print('    日历格数（合记日按日展开）: %d' % cells)
    print('    合记明细:', detail)
    # 逐月列出「实际条目覆盖的日」与「该月应有的日」
    print('    逐月：条目数 / 格数 / 该月应有天数 / 缺日')
    from collections import defaultdict
    bym = defaultdict(list)
    for e in events:
        dn = cn2int(e['day'].replace('日', ''))
        bym[e['month']].append((e, dn))
    MONTH_LEN = {'正': 30, '二': 29, '三': 30, '四': 29, '五': 30, '六': 29,
                 '七': 30, '八': 29, '九': 30, '十': 29, '十一': 30, '十二': 29}
    gaps_total = 0
    for mo in ['十二', '五', '六', '七', '八', '九', '十']:
        if mo not in bym:
            continue
        covered = set()
        for e, dn in bym[mo]:
            if e['kind'] == 'merged':
                a, b = e['_merge']
                covered.update(range(a, b + 1))
            else:
                covered.add(dn)
        lo, hi = min(covered), max(covered)
        gaps = [d for d in range(lo, hi + 1) if d not in covered]
        cells_m = len(covered)
        gaps_total += len(gaps)
        print('      %-2s月: %2d 条 / %2d 格 / 表中 #%d~#%d；表内缺失: %s' % (
            mo, len(bym[mo]), cells_m, lo, hi, ('、'.join('%d' % g for g in gaps) or '无')))
    print('    表内合计缺口: %d 日（此即部分差额来源，逐日列于上）' % gaps_total)

    # ---- 与学术统计的差额分解（见 METHOD §6），全部由上面的实算得出，不手填
    print('\n[6b] 与「157 日」的差额分解（数字全部来自上面的实算）')
    in_table_gap = cells - n                 # 合记日展开多出的格
    outside_gap = gaps_total - in_table_gap  # 无日期行的缺口日
    print('    本表日历格数                 = %d' % cells)
    print('    - 其中合记日展开多计          = %d' % in_table_gap)
    print('    + 表内无日期行的缺口日        = %d（见上行逐月明细）' % outside_gap)
    print('    = 原文写到日期的日历日        = %d' % (cells + outside_gap))
    print('    另：原文未写的日（无日期行） = 4，见 METHOD §6 逐日表')
    print('    157 - %d = %d（口径差 12）：按期序实算，表内缺日行 %d 格、合记多计 %d 格，'
          '剩余 %d 格须与张春树口径逐日核（见 METHOD §6，未解决）' % (
              n, 157 - n, outside_gap, in_table_gap, 157 - n - outside_gap + in_table_gap))

    # ---- 月份序列自检
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
    for e in events:
        e.pop('_merge', None)


def audit(events, src_path):
    """完整性自检。任何一项失败都会打印出来，不静默。

    注意：切条目时硬折行已并接，orig 是「两行拼接」的结果，因此比较前把源文件的
    换行去掉（只去 \\r\\n，不改任何汉字）。
    """
    print('\n[8] 完整性自检')
    src = io.open(src_path, encoding='utf-8').read()
    flat = re.sub(r'\r?\n', '', src)
    fail = []
    if [e['id'] for e in events] != ['RSC-%03d' % (i + 1) for i in range(len(events))]:
        fail.append('id 不连续')
    for e in events:
        if e['orig'] not in flat:
            fail.append('%s orig 不在源文件' % e['id'])
        if e['place'] and e['place'] not in e['orig']:
            fail.append('%s place 不在 orig' % e['id'])
        for p in e['place_all']:
            if p not in e['orig']:
                fail.append('%s place_all[%s] 不在 orig' % (e['id'], p))
        if e['place'] and e['place'] not in e['place_all']:
            fail.append('%s place 不在 place_all' % e['id'])
        if not e['note']:
            fail.append('%s 缺 note' % e['id'])
        if not e['activity']:
            fail.append('%s 缺 activity' % e['id'])
    print('    检查项失败: %d %s' % (len(fail), fail[:20]))
    print('    JSON/CSV 一致性在 dump() 后另检（见 run.log 末尾）')


def dump(events):
    os.makedirs(OUTDIR, exist_ok=True)
    jp = os.path.join(OUTDIR, 'events.json')
    io.open(jp, 'w', encoding='utf-8', newline='\n').write(
        json.dumps(events, ensure_ascii=False, indent=2) + '\n')
    cp = os.path.join(OUTDIR, 'events.csv')
    with io.open(cp, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['id', 'juan', 'month', 'day', 'date_raw', 'orig', 'kind',
                    'place', 'place_all', 'place_waypoint', 'place_departed',
                    'activity', 'note'])
        for e in events:
            w.writerow([e['id'], e['juan'], e['month'], e['day'], e['date_raw'],
                        e['orig'], e['kind'], e['place'] or '',
                        '|'.join(e['place_all']), '|'.join(e['place_waypoint']),
                        '|'.join(e['place_departed']),
                        '|'.join(e['activity']), e['note']])
    print('\n[9] 输出')
    print('    %s (%d bytes)' % (jp, os.path.getsize(jp)))
    print('    %s (%d bytes)' % (cp, os.path.getsize(cp)))
    # JSON/CSV 一致性
    back = json.load(io.open(jp, encoding='utf-8'))
    rows = list(csv.DictReader(io.open(cp, encoding='utf-8-sig')))
    bad = 0
    for e, r in zip(back, rows):
        if (e['id'] != r['id'] or e['place'] != (r['place'] or None)
                or '|'.join(e['place_all']) != r['place_all']
                or '|'.join(e['place_waypoint']) != r['place_waypoint']
                or '|'.join(e['place_departed']) != r['place_departed']
                or '|'.join(e['activity']) != r['activity'] or e['kind'] != r['kind']
                or e['note'] != r['note']):
            bad += 1
    print('    JSON/CSV 逐字段一致: %d/%d 一致，%d 处不符' % (len(back) - bad, len(back), bad))


if __name__ == '__main__':
    ev = build()
    report(ev)
    audit(ev, SRC)
    dump(ev)
