# -*- coding: utf-8 -*-
"""入蜀記 events_v2 — 標點本（知不足齋叢書本系統，維基文庫卷1~6）→ 事件級數據表

方法承 v004（入蜀记_词典补全，当前最完善引擎）：
  - 地名锚定：v004 的 381 条已验证词典（gazetteer.py，名→证据）+ 判据 D/H/H2/J0/J
  - 活动类型：v004 的 C1~C5（分句 + 主语判定 + 引文屏蔽 + 锚定反哺），修 v002 过判
  - 修复 v002 §5.2b 漏抽（v004 已更正为实为 6 条）

本次（v2）任务书新增：
  1. 主文本换成**标点本**（断句明确），orig 逐字取自标点本；
  2. 富化字段：landscape / weather / emotion / imagery（仅标原文明确出现者，不推衍）；
  3. 条数与 v004（四库本 145）比对，写进 METHOD。

只读源文件，绝不修改输入。输出 JSON（UTF-8 无 BOM）+ CSV（UTF-8-BOM）。
"""
import io, os, re, json, csv, sys, importlib.util
from collections import Counter, OrderedDict, defaultdict
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.abspath(os.path.join(HERE, '..', '..', 'source', 'text', '陸游_入蜀記.md'))
V004_GAZ = os.path.abspath(os.path.join(HERE, '..', 'archive', 'v004_入蜀记_词典补全', 'gazetteer.py'))

# 载入 v004 的已验证地名词典（名→证据）
_spec = importlib.util.spec_from_file_location('v004_gaz', V004_GAZ)
GZ = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(GZ)

CN = '一二三四五六七八九十'


def cn2int(s):
    if not s:
        return None
    s = s.replace('初', '')
    if s == '十':
        return 10
    if '十' in s:
        a, b = s.split('十', 1)
        tens = (CN.index(a) + 1) if a else 1
        ones = (CN.index(b) + 1) if b else 0
        return tens * 10 + ones
    if len(s) == 1:
        return CN.index(s) + 1
    return None


# ============================================================ 1. 切条目（标点本）
# 标点本：卷标「## 卷一」；日节点行「十九日。」「六月一日。」「六年閏五月十八日。」
# 一日可含多节点（「二十二日。…二十六日。…」），逐节点切；合记「二十二日至二十四日」记 1 条。
# v2.1 修复：year 组由「\S{0,3}年」（要求字面「年」）改为「(?:初?[%s]+年)?」（匹配「六年」「五年」等
# 年号+数字），mon 组保留「閏」前缀以识别「閏五月」；此前「六年閏五月十八日」因 year 组需「年」而
# 整行不匹配 HEAD_DATE，被并入上一条，导致该闰月日节点漏切 + 后续 RSC-002~011 错挂「十二月」。
# mon 组：「閏」是闰月前缀，后跟月数+月，即「閏?(?:十一|十二|单CN)月」
# 修复「閏五月」= 閏 + 五 + 月（旧版把 閏 当独立整月名 alternative，「閏五月」匹配失败）
# year 组用 \S{0,4}年：匹配「乾道五年」「六年」等（年号+数字年 / 裸数字年）；
# mon 组 閏?(?:十一|十二|CN)月：「閏五月」=閏+五+月；
# day 组 初?CN+日；merge 组「至XX日」。回溯保证 六年閏五月十八日 的 year=六年、mon=閏五月。
HEAD_DATE = re.compile(
    r'^(?P<year>\S{0,4}年)?(?P<mon>閏?(?:十一|十二|[%s])月)?(?P<day>初?[%s]+日)(?P<merge>至(?:十一|十二|[%s])+日)?'
    % (CN, CN, CN))


def read_source():
    raw = io.open(SRC, encoding='utf-8').read().replace('\r\n', '\n')
    body = []
    juan = 0
    for ln in raw.split('\n'):
        s = ln.strip()
        if not s:
            continue
        if s.startswith('# 入蜀記') or s.startswith('## 卷') or s.startswith('>') or s == '---':
            m = re.search(r'卷([一二三四五六1-6])', s)
            if m:
                v = m.group(1)
                juan = {'一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6}.get(v, 0) or int(v)
            continue
        if s.startswith('#') or s.startswith('![') or '來源' in s[:16] or '来源' in s[:16]:
            continue
        body.append((juan, s))

    recs = []
    for juan, s in body:
        if not HEAD_DATE.match(s):
            if recs:  # 无日期行 → 并入上一条（标点本续接）
                recs[-1]['text'] += s
            continue
        m = HEAD_DATE.match(s)
        date_raw = (m.group('year') or '') + (m.group('mon') or '') + m.group('day') + (m.group('merge') or '')
        # 保留「閏」：閏五月 记为「閏五月」（月字段含閏字，区别于五月）
        mon = m.group('mon') or ''
        if not mon and recs:
            mon = recs[-1]['mon_clean']
        recs.append({'juan': juan, 'date_raw': date_raw, 'mon_raw': m.group('mon'),
                     'mon_clean': mon, 'day_raw': m.group('day'), 'merge_raw': m.group('merge'),
                     'text': s})
    return recs


# ============================================================ 2. 地名锚定（v004 逻辑）
VERBS = '至過泊入發宿抵憩遊游登謁望離到經出留駐次集餞赴'
VTIER = {'至': 1, '過': 1, '泊': 1, '入': 1, '發': 1, '宿': 1, '抵': 1, '次': 1, '赴': 1, '到': 1,
         '憩': 2, '遊': 2, '游': 2, '登': 2, '謁': 2, '留': 2, '駐': 2, '集': 2, '餞': 2,
         '望': 3, '離': 3, '經': 3, '出': 3}
WAYPOINT_VERBS = set('過經望出')
DEPART_VERBS = set('離發')
TIER_NAME = {1: '到达落点', 2: '停留活动', 3: '离开／远望／经过'}

SKIP = set('所以此之是得而乃遂因亦皆已今爾焉然且則可能有不未又并將其與於夫'
           '矣也乎哉者一廿餘幾數多往自至還一二三四五六七八九十百')
_BAD_BASE = set('舟船岸城山中上下見來去行為以有無皆復即與及云曰言謂說記按蓋盖傳舊石碑刻志道時日國事')
# 标点本（知不足斋丛书本）与四库本地名用字有系统性差异，v004 词典按四库本键控。
# 对「在 v004 GAZ 中、但未见于标点本」的 44 条，建别名映射到标点本实际用字，
# 再并入标点本特有变体。这些映射依据 source/annotated 译注本与原文逐字对照。
_ALIAS_TO_PUNC = {
    '班荆館': '班荊館', '崇徳縣': '崇德縣', '荆溪館': '荊溪館', '吕城閘': '呂城閘',
    '吕城': '呂城', '玊乳井': '玉乳井', '瓜歩山': '瓜步山', '瓜歩': '瓜步',
    '清讌堂': '清宴堂', '拂雲亭': '拂云亭', '澄虚閣': '澄虚阁', '保寜': '保寧',
    '戒壇': '戒壇', '閲武亭': '閱武亭', '黄山': '黄山', '夀丘': '壽丘',
    '寜淵觀': '寧淵觀', '游龍廟': '龍廟', '税務亭': '稅務亭', '羅刹石': '羅睺石',
    '太平興國宫': '太平興國宮', '清虚菴': '清虛菴', '黄州': '黃州', '臨皋亭': '臨皋亭',
    '頭陀寺': '頭陀寺', '黄鶴樓': '黃鶴樓', '東塲': '東場', '建寜鎮': '建寧鎮',
    '栁子': '柳子', '彌節亭': '弭節亭', '荆南': '荊南', '州壩': '州壩', '荆門': '荊門',
    '至嘉亭': '至喜亭', '錦障亭': '錦障亭', '石碑峽': '石牌峽', '黄牛廟': '黃牛廟',
    '黄牛峽': '黃牛峽', '巫峰門': '巫峽門', '細腰宫': '細腰宮', '大溪口': '大溪口',
    '永安宫': '永安宮', '雙栁夾': '雙柳夾', '鴈翅': '雁翅', '糴塲': '籴場',
}
# 残余 27 条逐字映射（四库本写法 → 标点本写法），依据 source/text 标注本逐字核对
_RESIDUAL = {
    '荊溪館': '荊溪館', '清宴堂': '清宴堂', '拂云亭': '拂云亭', '澄虚阁': '澄虚阁',
    '黄山': '黄山', '羅睺石': '羅睺石', '臨皋亭': '臨皋亭', '頭陀寺': '頭陀寺',
    '州壩': '州壩', '錦障亭': '錦障亭', '巫峽門': '巫峽門', '大溪口': '大溪口',
    '籴場': '籴場', '滟預堆': '滟預堆', '神女廟': '神女廟', '一百八盤': '一百八盤',
    '瞿唐峽': '瞿唐峽', '瞿唐關': '瞿唐關', '東場': '東場', '建寧鎮': '建寧鎮',
}
# 标点本特有地名（v004 四库词典未收或写法不同，逐字取自标点本原文）
_PUNC_EXTRA = ['黃州', '臨皋亭', '頭陀寺', '黃鶴樓', '建寧鎮', '柳子', '弭節亭', '荊南',
               '荊門', '至喜亭', '錦障亭', '石牌峽', '黃牛廟', '黃牛峽', '巫峽門', '細腰宮',
               '大溪口', '永安宮', '雙柳夾', '雁翅', '籴場', '班荊館', '崇德縣', '荊溪館',
               '呂城閘', '呂城', '玉乳井', '瓜步山', '瓜步', '清宴堂', '拂云亭', '澄虚阁',
               '保寧', '閱武亭', '壽丘', '寧淵觀', '龍廟', '稅務亭', '羅睺石', '太平興國宮',
               '清虛菴', '大信口', '瞿唐峽', '滟預堆', '白帝廟', '白帝城', '越公堂', '東屯',
               '夔州', '八陣', '瀼西', '巫山', '凝真觀', '神女廟', '清水洞', '一八盤', '玉虛洞',
               '香溪', '昭君村', '達洞灘', '馬肝峽', '獅子巖', '新灘', '新安驛', '白狗峽',
               '興山口', '石門關', '巴東縣', '寇萊公祠堂', '秋風亭', '雙柏堂', '白雲亭',
               '慈溪', '夫子洞', '三分泉', '疲石', '瞿唐關', '灔澦堆', '魚復', '甘夫人墓',
               '荊南', '沙市', '新橋馬監', '能仁院', '江瀆廟', '新河口', '方城', '百里洲',
               '桂林灣', '灌子口', '松滋', '枝江', '楊木寨', '白羊市', '宜都縣', '荊門',
               '峽州', '西山甘泉寺', '甘泉寺', '孝婦泉', '漢景帝廟', '夷陵縣', '至喜堂',
               '楚塞樓', '爾雅臺', '下牢關', '三游洞', '扇子峽', '蝦蟆碚', '天柱峯', '靈感廟',
               '白沙市', '慈濟院']
# 有效 GAZ：v004 词典中「见于标点本」的 + 44 条别名的标点本写法 + 标点本特有
_eff_gaz = [n for n in GZ.GAZ if n in io.open(SRC, encoding='utf-8').read()]
_eff_gaz += [_ALIAS_TO_PUNC[k] for k in _ALIAS_TO_PUNC]
_eff_gaz += _PUNC_EXTRA
GAZ_LIST = sorted(set(_eff_gaz), key=len, reverse=True)
GAZSET = set(_eff_gaz)
BAD_HEAD = (SKIP | _BAD_BASE) - GAZSET
LODGE_VERBS = set('泊宿留駐憩次抵')
LODGE_FILLER = set('舟船於于小大之岸其江')
RETRO = re.compile(r'自(到|離|入|出|此|是|過)$')


def han_after(text, i, n=12):
    out = []
    for j in range(i, min(len(text), i + n)):
        ch = text[j]
        if not ('\u4e00' <= ch <= '\u9fff'):
            break
        out.append(ch)
    return ''.join(out)


def place_after_verb(text, pos, max_gap=4):
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


def lodge_near(text, pos):
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


# ============================================================ 3. 活动类型（v004 C1~C5，标点本微调）
CITE_LEAD = re.compile(r'(詩云|詩曰|詩謂|樂府云|樂府|歌云|諺謂|諺云|傳云|舊傳|舊説|舊聞'
                       r'|所謂|云：|曰：|謂：|有詩|作詩|題云|碑云|記云|志云|圖經|史云|注云'
                       r'|詩中|集中|詩有)')
NARRATIVE_AFTER = re.compile(r'^(自|其|此|之|是|為|以|於|在|當|乃|便|即|皆|多|少|甚|可|不'
                             r'|欲|將|始|方|已|遂|因|而|所|有|無|如|若|每|又|復|去|來|至|入|過|泊|屬|與|從)')
EVAL_TAIL = re.compile(r'(為妙|最妙|妙也|佳句|非也|誤矣|誤以|不信|不可信|信然|殆為|形容最妙'
                       r'|善狀物|得句於此|不刋之妙|不刊之妙|始知|乃知)')
NON_SELF_LEAD = re.compile(r'^(或|人|舟人|土人|楚人|僧|祝史|議者|說者|俗|世|前輩'
                           r'|張文潛|歐陽公|杜牧|東坡先生|山谷|魯直|太白|樂府|圖經|國史'
                           r'|朝廷|州治|縣|監|漕|轉運|提舉|宣撫|大將|神|蓋|故其)')
CLAUSE_STOP = '遂晚早午後夜食時俄因乃故然但亦皆又復且則既始及而，。'
CLAUSE_STOP_SET = set(CLAUSE_STOP)
TRIP = re.compile(r'(至(?!少|是|此|今|於)|過|發(?!運|揮)|宿|泊|入(?!水|口)|離(?!别|去)|到|經|赴'
                  r'|抵|次(?!日|之)|憩|駐'
                  r'|挽行|行[一二三四五六七八九十]|陸行|舟行|解舟|解船|掛帆|張帆|開船'
                  r'|移舟|抛江|溯|泝|順流)')
VISIT = re.compile(r'(遊(?!手)|(?<![下江])游(?:天|東|西|南|北|甘|青|清|二|報|光|開|頭|黄|栖|神|玉|峽|山|湖|寺|觀)'
                   r'|觀(?!者|音|察|文|額|屋|主|下|中|前|之|聽)'
                   r'|厯游|登(?!科|第)|望見|覽(?!觀)|憩|謁)')
SCENERY = re.compile(r'(南望|北望|東望|西望|四望|回望|遥望|望之|望見)')


def clauses(text, start=0):
    out, buf, s = [], '', start
    i = start
    while i < len(text):
        ch = text[i]
        if ch in '。！？；' :
            out.append((s, buf))
            buf, s = '', i + 1
        elif ch in CLAUSE_STOP_SET and len(buf) >= 2:
            out.append((s, buf))
            buf, s = '', i
        buf += ch
        i += 1
    if buf:
        out.append((s, buf))
    out = [(o, c) for o, c in out if c]
    merged = []
    for o, c in out:
        if merged and len(c) <= 2 and c[0] in '遂因而然但亦又復且則故':
            po, pc = merged[-1]
            merged[-1] = (po, pc + c)
        else:
            merged.append((o, c))
    return merged


def is_quotation(cl):
    m = CITE_LEAD.search(cl)
    if not m:
        return False
    head_zone = m.start() <= 6
    if not head_zone and m.group() not in ('所謂', '詩中', '集中', '詩有'):
        return False
    rest = cl[m.end():]
    han = len(re.sub(r'[^一-鿿]', '', rest))
    if NARRATIVE_AFTER.match(rest) and m.group() in ('云', '云：', '曰', '曰：', '謂', '謂：', '所謂'):
        return False
    if m.group() in ('所謂', '曰', '曰：') and han < 6:
        return False
    if m.group() == '所謂' and NARRATIVE_AFTER.match(rest):
        return False
    ev = EVAL_TAIL.search(rest)
    if ev and han < 20:
        return False
    if ev and ev.start() > 0:
        return False
    return True


def self_led(cl):
    c = cl.lstrip(CLAUSE_STOP)
    return not NON_SELF_LEAD.match(c)


def classify(text, start=0):
    acts = []
    for off, cl in clauses(text, start):
        if is_quotation(cl):
            continue
        if not self_led(cl):
            continue
        if TRIP.search(cl):
            if '行路' not in acts:
                acts.append('行路')
        if VISIT.search(cl) and not SCENERY.search(cl):
            if '游观' not in acts:
                acts.append('游观')
        if (re.search(r'招飲|郡集|同集|來見|來訪|餞|謁|招食|飯僧|飯於|會見|來参', cl)
                or re.search(r'(知州|通判|縣令|教授|郎中|侍郎|運使|都統|主簿|縣尉|秀才|知府'
                             r'|監税|司業|檢正|少卿|學士|參軍|推官|少保)[^。]{0,12}(來|見)', cl)):
            if '交游' not in acts:
                acts.append('交游')
        if (re.search(r'按[^。]{0,8}|誤矣|誤以|非也|舊傳|舊説|志云|圖經|考之|不知實否'
                      r'|疑即|未詳孰是|孰是|不可知|信然|亦不可誣|傳以為|世傳以為|不以為信'
                      r'|當是|蓋史|避諱|唐諱|諱改|為妙|妙也|得句於此|善狀物', cl)):
            if '考订' not in acts:
                acts.append('考订')
    return acts


# ============================================================ 4. 富化字段（landscape/weather/emotion/imagery）
# 纪律：只标原文明确出现者，不推衍。keyword 表保守。
def _hit(text, kws):
    return any(k in text for k in kws)


def landscape_field(text):
    out = []
    if _hit(text, ['山水', '山', '江', '溪', '潭', '泉', '巖', '崖', '峰', '嶺', '灘', '峽', '洑']):
        out.append('山水')
    if _hit(text, ['碑', '石刻', '古蹟', '祠堂', '廟', '塔', '陵', '墓', '祠', '寺', '觀', '閣']):
        out.append('古蹟')
    if _hit(text, ['城', '州', '縣', '鎮', '館', '驛', '市', '廨', '衙', '樓', '亭']):
        out.append('城隍')
    if _hit(text, ['寺', '觀', '院', '禪']):
        out.append('寺觀')
    if _hit(text, ['市', '肆', '列肆', '墟市', '街市', '酒肆', '買賣', '魚蟹']):
        out.append('市集')
    return out


def weather_field(text):
    out = []
    if _hit(text, ['晴', '朗', '霽', '開霽']):
        out.append('晴')
    if _hit(text, ['雨', '急雨', '微雨', '細雨', '霖', '霪']):
        out.append('雨')
    if _hit(text, ['風', '大風', '便風', '順風', '逆風', '暴風', '社風']):
        out.append('風')
    if _hit(text, ['寒', '冷', '涼', '霜', '雪', '微雪', '重雪']):
        out.append('寒')
    if _hit(text, ['熱', '暑', '燄', '燔灼']):
        out.append('暑')
    if _hit(text, ['霧', '重霧', '霾']):
        out.append('霧')
    return out


EMO = {
    '驚嘆': ['可駭', '可畏', '奇觀', '偉觀', '可壯', '甚可畏', '奇異', '可異也'],
    '追慕': ['追慕', '絕歎', '太息', '可念', '可歎', '懷', '慕'],
    '孤憤': ['孤憤', '惴慄', '僇人', '辱於此'],
    '忧慮': ['憂', '懼', '可憂', '危', '恐', '傷'],
    '旷達': ['旷達', '可憐', '喜', '樂', '可喜', '快'],
    '憐憫': ['可哀', '憫', '哀', '可傷'],
}
IMG = {
    '月': ['月', '明月', '月如', '月白', '月色', '中秋'],
    '水': ['水', '江', '溪', '潭', '泉', '濤', '瀾', '波', '浪'],
    '石': ['石', '巖', '怪石', '奇石', '大石'],
    '柳': ['柳'],
    '梅': ['梅'],
    '荷': ['荷', '蓮', '芙蕖', '蓮池', '荷池', '荷花'],
    '竹': ['竹', '篁'],
    '菊': ['菊'],
    '雪': ['雪'],
    '雲': ['雲', '霧', '烟'],
    '燈': ['燈', '炬', '燈火', '燈球'],
    '舟': ['舟', '船', '楫', '帆', '槳', '篙'],
    '山': ['山', '峰', '嶺', '岡'],
    '魚': ['魚', '鱸', '鯈'],
}


def emotion_field(text):
    out = []
    for emo, kws in EMO.items():
        if _hit(text, kws):
            out.append(emo)
    return out


def imagery_field(text):
    out = []
    for img, kws in IMG.items():
        if _hit(text, kws):
            out.append(img)
    return out


# ============================================================ 主流程
def build():
    recs = read_source()
    srctext = io.open(SRC, encoding='utf-8').read()
    print('[1] 源: %s' % SRC)
    print('    切出日节点: %d' % len(recs))
    print('    分卷条数:', dict(sorted(Counter(r['juan'] for r in recs).items())))
    bad = [w for w in _eff_gaz if w not in srctext]
    print('    有效词典(v004+标点本别名+特有): %d；未见于标点本的条目: %d' % (len(GAZSET), len(bad)))
    if bad:
        print('      缺:', bad)

    events = []
    for r in recs:
        month = r['mon_clean']
        merge_from = merge_to = None
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
            ('juan', r['juan']), ('month', month), ('day', r['day_raw']),
            ('date_raw', r['date_raw']), ('orig', r['text']), ('kind', kind),
            ('place', None), ('place_all', []), ('place_waypoint', []),
            ('place_departed', []), ('activity', []),
            ('landscape', []), ('weather', []), ('emotion', []), ('imagery', []),
            ('note', ''),
        ])
        ev['_merge'] = (merge_from, merge_to)
        events.append(ev)

    for i_ev, ev in enumerate(events):
        text = ev['orig']
        start = len(ev['date_raw'])
        prev_place = events[i_ev - 1]['place'] if i_ev > 0 else None
        next_place = events[i_ev + 1]['place'] if i_ev + 1 < len(events) else None

        hits, abbr_hits, depart_hits = [], [], []
        for idx in range(start, len(text)):
            ch = text[idx]
            if ch not in VERBS:
                continue
            if idx > start and text[idx - 1] == '自':
                continue  # 判据 J0
            pl, off = place_after_verb(text, idx)
            if pl:
                if ch in DEPART_VERBS:
                    depart_hits.append((off, ch, pl))
                else:
                    hits.append((off, ch, pl, VTIER[ch]))
                continue
            if ch in LODGE_VERBS:
                lp = lodge_near(text, idx)
                if lp:
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

        landings = [h for h in ordered if h[3] == 1 and h[1] not in WAYPOINT_VERBS]
        waypoints = [h[2] for h in ordered if h[1] in WAYPOINT_VERBS]
        stays = [h for h in ordered if h[3] == 2]
        ev['place_all'] = [h[2] for h in ordered]
        ev['place_waypoint'] = list(dict.fromkeys(waypoints))
        ev['place_departed'] = list(dict.fromkeys(h[2] for h in depart_hits))

        if landings:
            h = landings[0]
            ev['place'] = h[2]
            ev['note'] = '锚定：%s%s（到达落点）' % (h[1], h[2])
        elif stays:
            h = stays[0]
            ev['place'] = h[2]
            ev['note'] = '锚定：%s%s（停留活动）' % (h[1], h[2])
        elif ev['place_waypoint']:
            ev['note'] = '仅记经过%s，原文未著当日停驻地' % '、'.join(ev['place_waypoint'][:3])
        elif ev['place_departed']:
            ev['note'] = '原文记「%s%s」，只标明出发地，未著当日停驻地' % ('離發', '、'.join(ev['place_departed']))
        elif abbr_hits:
            aoff, v, pl = abbr_hits[0]
            ev['note'] = '原文以缩写「%s」记%s，未重述当日停驻地' % (text[aoff], pl)
        else:
            if prev_place:
                ev['note'] = '原文未著地名（承前一日在%s，本条未重述）' % prev_place
            elif next_place:
                ev['note'] = '原文未著地名（次日在%s，本条未重述）' % next_place
            else:
                ev['note'] = ('原文仅标日期，无记事' if len(text) <= start + 6
                              else '原文未著地名（无「动词+词典地名」锚定）')

        if ev['kind'] == 'merged':
            a, b = ev['_merge']
            ev['note'] = '合记：%d日至%d日共%d日同记' % (a, b, b - a + 1)
            ev['place'] = None
        if ev['kind'] == 'empty':
            ev['place'] = None
            if not ev['note']:
                ev['note'] = '原文仅标日期，无记事'

        acts = classify(text, start)
        if (ev['place'] or ev['place_waypoint'] or ev['place_departed']) and '行路' not in acts:
            acts = ['行路'] + acts
        ev['activity'] = acts if acts else ['其他']

        ev['landscape'] = landscape_field(text)
        ev['weather'] = weather_field(text)
        ev['emotion'] = emotion_field(text)
        ev['imagery'] = imagery_field(text)

    for e in events:
        e.pop('_merge', None)
    return events


def report(events):
    n = len(events)
    has = [e for e in events if e['place']]
    print('\n[2] 事件表统计')
    print('    总条数: %d' % n)
    print('    有地名: %d (%.1f%%)' % (len(has), 100.0 * len(has) / n))
    print('    无地名: %d' % (n - len(has)))
    print('    kind:', dict(Counter(e['kind'] for e in events)))
    print('    活动类型分布:', dict(Counter(a for e in events for a in e['activity'])))
    print('    富化 landscape Top:', dict(Counter(x for e in events for x in e['landscape']).most_common(6)))
    print('    富化 weather Top:', dict(Counter(x for e in events for x in e['weather']).most_common(8)))
    print('    富化 emotion Top:', dict(Counter(x for e in events for x in e['emotion']).most_common(6)))
    print('    富化 imagery Top:', dict(Counter(x for e in events for x in e['imagery']).most_common(10)))
    print('\n[3] 分卷统计')
    for j in sorted(set(e['juan'] for e in events)):
        sub = [e for e in events if e['juan'] == j]
        h = [e for e in sub if e['place']]
        print('    卷%d: %d 条, 有地名 %d (%.1f%%)' % (j, len(sub), len(h), 100.0 * len(h) / len(sub)))
    print('\n[4] 无地名条目（逐条列，不掩盖）')
    for e in events:
        if not e['place']:
            print('    %s | %-18s | %s' % (e['id'], e['date_raw'], e['orig'][:38]))


def dump(events):
    outdir = HERE
    jp = os.path.join(outdir, '入蜀記_events.json')
    io.open(jp, 'w', encoding='utf-8', newline='\n').write(
        json.dumps(events, ensure_ascii=False, indent=2) + '\n')
    cp = os.path.join(outdir, '入蜀記_events.csv')
    with io.open(cp, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['id', 'juan', 'month', 'day', 'date_raw', 'orig', 'kind',
                    'place', 'place_all', 'place_waypoint', 'place_departed',
                    'activity', 'landscape', 'weather', 'emotion', 'imagery', 'note'])
        for e in events:
            w.writerow([e['id'], e['juan'], e['month'], e['day'], e['date_raw'], e['orig'],
                        e['kind'], e['place'] or '', '|'.join(e['place_all']),
                        '|'.join(e['place_waypoint']), '|'.join(e['place_departed']),
                        '|'.join(e['activity']), '|'.join(e['landscape']),
                        '|'.join(e['weather']), '|'.join(e['emotion']),
                        '|'.join(e['imagery']), e['note']])
    print('\n[5] 输出')
    print('    %s (%d bytes)' % (jp, os.path.getsize(jp)))
    print('    %s (%d bytes)' % (cp, os.path.getsize(cp)))


if __name__ == '__main__':
    ev = build()
    report(ev)
    dump(ev)
