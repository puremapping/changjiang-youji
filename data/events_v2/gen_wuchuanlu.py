# -*- coding: utf-8 -*-
"""吳船錄 events_v2 — 標點本（欽定四庫全書本·二卷，維基文庫）→ 事件級數據表

方法承 v003（吴船录_纯原文匹配）：切条目 + 干支→序数日换算 + 地名锚定 + 活动 5 标签。
本次（v2）：
  1. 主文本用**标点本**（断句明确），orig 逐字取自标点本，一字不改；
  2. 富化字段：landscape / weather / emotion / imagery（仅标原文明确出现者，不推衍）；
  3. 干支→序数日：月首「月+干支+朔」= 1 日锚；卷首「五月廿九日戊辰」= 29 日锚；
     同 60 甲子周期内偏移 ≤30 推序数日；超过 30 判为跨周期，不推（记 out_of_cycle）。
     公式：day_num = anchor_day + ((gz_idx - anchor_gz_idx) mod 60)。
  4. 条目按「干支日头」切（逐行），月头朔/卷首 各开一条；并联干支（丁亥、戊子）记 1 条、
     多干支并列在 date_raw 全记、主干支取首日；非日头内容并入上一条（不单独成条）。
  5. 与 v003（四库本 109 条）比对：v2 标点本切 110 条 = 109 条一一对应 + 1 条净增——
     系补回 v003 卷上漏切的「六月廿 丁亥、戊子、己丑、庚寅、辛卯」并联 5 日条目
     （v003 六月自「丙戌」直跳「壬辰」，漏此条）。卷上 31 / 卷下 79；v003 卷上 30 / 卷下 79，
     差异仅在卷上 +1。明细见 METHOD。
只读源文件，绝不修改输入。输出 JSON（UTF-8 无 BOM）+ CSV（UTF-8-BOM）。
"""
import io, os, re, json, csv, sys
from collections import Counter, OrderedDict

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.abspath(os.path.join(HERE, '..', '..', 'source', 'text', '范成大_吳船錄.md'))

GAN = '甲乙丙丁戊己庚辛壬癸'
ZHI = '子丑寅卯辰巳午未申酉戌亥'
GANZHI = [GAN[i % 10] + ZHI[i % 12] for i in range(60)]
GZ_IDX = {gz: i for i, gz in enumerate(GANZHI)}
GZ_SET = set(GANZHI)
# 干支正字纠错：「丙丑」→丙子（丙后必配子）、「乙子」→乙丑（乙后必配丑），均系标点本形误
GZ_ERRATA = {'丙丑': '丙子', '乙子': '乙丑'}
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


# 月首干支日头：「六月己巳朔」/「秋七月戊戌，朔」/「冬十月丁卯，朔」
# 月数用 CN 数字；干支后可能跟「，」或「。」「朔」（六月 形如「六月己巳朔。」，无分隔）
GZPAT = r'[甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥]'
MONTH_HEAD = re.compile(r'^(?:秋|冬)?([%s]+月)\s*%s\s*[，。]?朔?' % (CN, GZPAT))
# 卷首特殊：「石湖居士以淳熙丁酉歲五月二十九日戊辰離成都」
HEAD_DAY = re.compile(r'淳熙丁酉歲([%s]+月)([%s]+日)%s' % (CN, CN, GZPAT))
# 普通干支日头：行首「庚午。」「丁亥、戊子」「戊寅、己卯。」「乙子、丙寅。」
GZ_HEAD = re.compile(r'^%s(?:、%s)*[，。、]' % (GZPAT, GZPAT))


def _er(gz):
    """干支形误→正字。"""
    return GZ_ERRATA.get(gz, gz)


def read_source():
    """读标点本，逐行按「干支日头」切条目。

    日头形态（按行首判定）：
      A. 月首朔：「六月己巳朔」/「秋七月戊戌，朔」/「冬十月丁卯，朔」→ 新月 + 1 日锚
      B. 卷首：「淳熙丁酉歲五月廿九日戊辰離成都」→ 五月廿九（戊辰），head 锚
      C. 普通干支：「庚午」「丁亥、戊子」（并联）→ 本干支日，干支取首日、并联全记
    非日头行并入前一条（不单独成条）。月/日由当前月锚 + 60 周期偏移推。
    """
    raw = io.open(SRC, encoding='utf-8').read().replace('\r\n', '\n')
    lines = []
    cur_juan = 1
    for ln in raw.split('\n'):
        s = ln.strip()
        if not s:
            continue
        if s.startswith('#') or s.startswith('>') or s == '---' or s.startswith('!['):
            m = re.search(r'卷([上下])', s)
            if m:
                cur_juan = 1 if m.group(1) == '上' else 2
            continue
        if '來源' in s[:16] or '来源' in s[:16] or '南宋作品' in s or 'Public' in s:
            continue
        lines.append((cur_juan, s))

    entries = []
    # 月锚：{月名: (锚干支, 锚序数日)}；卷首 五月 用 head 锚
    month_anchor = {}          # 月名 -> (锚gz正字, 锚day)
    cur_month = None
    for juan, s in lines:
        mA = MONTH_HEAD.match(s)
        if mA:
            mon = mA.group(1)
            gz = _er(re.search(GZPAT, s).group(0))
            cur_month = mon
            month_anchor[mon] = (gz, 1)
            entries.append({'juan': juan, 'month': mon, 'ganzhi': gz, 'day_num': 1,
                            'day_src': 'anchor', 'date_raw': mA.group(0),
                            'body': s[mA.end():].strip()})
            continue
        mB = HEAD_DAY.search(s)
        if mB:
            # 卷首唯一特殊条：「淳熙丁酉歲五月廿九日戊辰離成都」→ 五月廿九（戊辰）
            # 廿九 非 CN 正字，序数日直接取 29（卷首句固定）
            mon = '五月'
            day = 29
            gz = '戊辰'  # 日干支固定为戊辰；「淳熙丁酉」系岁次（年干支），非日干支
            cur_month = mon
            month_anchor[mon] = (gz, day)
            entries.append({'juan': juan, 'month': mon, 'ganzhi': gz, 'day_num': day,
                            'day_src': 'head', 'date_raw': mB.group(0),
                            'body': s[mB.end():].strip()})
            continue
        mC = GZ_HEAD.match(s)
        if mC:
            head_txt = mC.group(0)
            gzs = [_er(g) for g in re.findall(GZPAT, head_txt)]
            gz0 = gzs[0]
            merged = len(gzs) > 1
            # head 之后正文：head 形如「庚午。」「丁亥、戊子、」「戊寅、己卯。」
            # date_raw 保留行内原标点（一字不改）；body 取 head 之后剩余。
            body = s[len(head_txt):].strip()
            entries.append({'juan': juan, 'month': cur_month, 'ganzhi': gz0,
                            'day_num': None, 'day_src': 'pending',
                            'date_raw': head_txt,
                            'body': body, 'gz_list': gzs, 'merged': merged})
            continue
        # 非日头行：并入前一条
        if entries:
            entries[-1]['body'] = (entries[-1]['body'] + s).strip()
        else:
            entries.append({'juan': juan, 'month': None, 'ganzhi': None, 'day_num': None,
                            'day_src': 'orphan', 'date_raw': '', 'body': s})

    # 定序数日（锚 + 60 周期偏移）
    for e in entries:
        if e['day_src'] in ('anchor', 'head'):
            continue
        mon = e.get('month')
        gz = e.get('ganzhi')
        has_anchor = mon in month_anchor and gz in GZ_SET
        if not has_anchor:
            e['day_src'] = 'no_anchor'
            e['day_num'] = None
            continue
        base_gz, base_day = month_anchor[mon]
        off = (GZ_IDX.get(gz, 0) - GZ_IDX.get(base_gz, 0)) % 60
        if off <= 30:
            e['day_num'] = base_day + off
            e['day_src'] = 'anchor'
        else:
            e['day_num'] = None
            e['day_src'] = 'out_of_cycle'
        if e.get('merged'):
            e['note_merged'] = '本行并列 %d 干支（%s），首日 %s 为主' % (
                len(e.get('gz_list', [gz])), '、'.join(e.get('gz_list', [gz])), gz)
    # 拼 orig（date_raw + body，保持原文逐字）
    for e in entries:
        e['orig'] = (e.get('date_raw', '') + e.get('body', '')).strip()
        e.pop('body', None)
    return entries


# ============================================================ 地名锚定（v003 逻辑 + 标点本别名）
GAZ = [
    '小東郭合江亭', '合江亭', '芳華樓', '板橋灘', '彭山縣', '眉州', '郫縣', '犀浦鎮',
    '犀浦', '安德鎮', '永康軍', '崇德廟', '玉壘關', '浮雲亭', '懷古亭', '伏龍觀',
    '離堆', '都江', '洛水', '繩橋', '白石渡', '羅漢院', '青城山', '寶仙九室洞天',
    '丈人觀', '上清宮', '芙蓉平', '長生觀', '味江龍', '範氏莊園', '雅州', '蜀州',
    '聖佛院', '周家莊', '西湖', '四相堂', '江原縣', '善頌堂', '新津縣', '脩覺',
    '彭山', '眉州城外江', '蟆頤', '玻璃江', '景疏樓', '起文堂', '元佑學堂',
    '眉山館', '中巖', '喚魚潭', '慈姥巖', '三石峰', '寶瓶峰', '湖瀼峽', '平羌',
    '嘉州', '問月堂', '犍為郡', '九頂寺', '雪堂', '淩雲', '淩雲寺', '天寧閣',
    '佛頭灘', '萬景樓', '烏尤', '安樂園', '涪翁亭', '廣福院', '方響洞', '峨眉',
    '符文鎮', '峨眉縣', '慈福', '普安', '白水莊', '蜀村店', '龍神堂', '華嚴院',
    '青竹橋', '峨眉新觀', '梅樹埡', '兩龍堂', '中峰院', '普賢閣', '茂真尊者庵',
    '樟木', '牛心嶺', '牛心院', '雙溪橋', '菩薩閣', '白水普賢寺', '白水寺',
    '光相寺', '七寶巖', '點心山', '茅亭觜', '石子雷', '駱駝嶺', '簇店', '峰門',
    '羅漢店', '木皮里', '胡孫梯', '雷洞平', '新店', '八十四盤', '娑羅平', '思佛亭',
    '軟草平', '洗腳溪', '天仙橋', '光明巖', '瓦屋山', '大瓦屋', '雪山', '雷洞山',
    '小金橋', '黑水', '虎溪橋', '牛心寺', '白雲峽', '青蓮峰', '白雲閣', '青蓮閣',
    '孫仙煉丹竈', '淘珠泉', '龍門', '龍門峽', '龍洞', '蘇稽鎮', '燕渡水', '犍為縣',
    '下壩', '敘州', '宣化縣', '大死庵', '鎖江亭', '南廣江', '南溪縣', '瀘州',
    '江安縣', '張旗三灘', '南定樓', '來風亭', '合江縣', '登天王廟', '劉仙觀',
    '安樂山', '楊商卿', '譚季壬', '江津縣', '漁洞', '泥培村', '恭州', '報恩寺',
    '涪州', '樂溫縣', '張益德廟', '蒲氏墨', '排亭', '黔江', '妃子園', '群豬灘',
    '忠州', '酆都縣', '平都山', '仙都觀', '景德', '陰君丹爐', '竹平', '四賢閣',
    '荔枝樓', '萬州', '武寧縣', '西山', '岑公洞', '開江口', '下巖', '瑞光閣',
    '雲安軍', '夔州', '魚復', '臥龍山泉', '瞿唐', '灩滪', '三峽堂', '高齋',
    '瞿唐口', '黑石灘', '大溪口', '巫山縣', '巫峽', '神女廟', '陽雲臺', '高唐觀',
    '來鶴峰', '東奔灘', '歸州', '巴東縣', '寇忠愍公祠', '咤灘', '人鲊甕', '秭歸',
    '清烈公祠', '宋玉宅', '明妃廟', '望洋軒', '歸鄉沱', '玉虛洞', '新灘',
    '黃牛峽', '黃牛廟', '扇子峽', '蝦蟆碚', '平善壩', '峽州', '至喜亭', '楚塞樓',
    '爾雅臺', '甘泉寺', '楊木寨', '枝江縣', '松滋縣', '沙頭', '沙市', '荊南',
    '渚官', '絳帳臺', '章華臺', '龍山落帽臺', '息壤', '江瀆廟', '公安縣',
    '二聖寺', '石首縣', '魯家洑', '沌', '百里荒', '鄂渚', '鷹鳥洲', '南布堤',
    '南市', '南樓', '黃鶴山', '大慈樓', '鄂州', '壓雲亭', '雅歌堂', '整暇堂',
    '漢口', '三江口', '赤壁', '黃州', '臨皋亭', '雪堂東坡', '竹樓', '棲霞樓',
    '桐木溝', '馬頭', '江州', '琵琶亭', '庾樓', '思白堂', '雙劍峰', '濂溪',
    '周先生祠堂', '太平興國宮', '香爐峰', '獅子峰', '蓮花峰', '東林寺', '虎溪',
    '蓮社', '五杉閣', '舍利塔', '聰明泉', '白樂天草堂', '西林寺', '東林',
    '過溪亭', '太平宮', '草市', '清虛庵', '撥雲峰', '湖口', '大孤', '交石夾',
    '澎浪磯', '滶背洲', '馬當', '波斯夾', '皖口', '牛磯', '雁汊', '長風沙',
    '池州', '池口', '望淮亭', '九華樓', '齊山', '翠微亭', '南湖口', '非水亭',
    '清溪口', '清溪', '太平州', '淩歊臺', '建康府', '賞心亭', '玉麟堂', '伏龜樓',
    '清溪閣', '長蘆', '一葦堂', '鎮江府', '常州', '滸墅', '盤門',
]
GAZ = sorted(set(GAZ), key=len, reverse=True)

# 动词语义优先级（v003 §五）：发>泊宿>至过抵>登游谒憩望>入出离到经渡>顿；「赴」=到达义归 1 级（承 v004 判据 B）
VERBS_PRI = [('發', 1), ('泊', 2), ('宿', 2), ('次', 2), ('駐', 2),
             ('至', 3), ('過', 3), ('抵', 3), ('登', 4), ('遊', 4), ('游', 4),
             ('謁', 4), ('憩', 4), ('望', 4), ('入', 5), ('出', 5), ('離', 5),
             ('到', 5), ('經', 5), ('渡', 5), ('頓', 6), ('赴', 1)]
SKIP = set('所以此之是得而乃遂因亦皆已今爾焉然且則可能有不未又并將其與於夫'
           '矣也乎哉者一廿餘幾數多往自至還一二三四五六七八九十百舟船岸城山')


def han_after(text, i, n=12):
    out = []
    for j in range(i, min(len(text), i + n)):
        ch = text[j]
        if not ('\u4e00' <= ch <= '\u9fff'):
            break
        out.append(ch)
    return ''.join(out)


def anchor_places(text, start):
    """在 text[start:] 内找「动词+附近(≤4字)地名」，取优先级最高者为主地点。"""
    hits = []
    for v, pri in VERBS_PRI:
        idx = start
        while True:
            idx = text.find(v, idx)
            if idx < 0:
                break
            tail = han_after(text, idx + 1, 16)
            if tail:
                for name in GAZ:
                    k = tail.find(name)
                    if 0 <= k <= 4:
                        gap = tail[:k]
                        if not any(c in SKIP and c not in '於于' for c in gap):
                            hits.append((idx + 1 + k, pri, name))
            idx += 1
    if not hits:
        return None, []
    hits.sort(key=lambda h: (h[1], h[0]))
    place = hits[0][2]
    allp = list(dict.fromkeys(h[2] for h in hits))
    return place, allp


# ============================================================ 活动 5 标签（v003）
def classify(text):
    acts = []
    if any(c in text for c in '至過發抵宿泊入離到經行渡'):
        acts.append('行路')
    if any(c in text for c in '遊觀登望覽憩謁'):
        acts.append('游观')
    if re.search(r'見|招集|招遊|餞|送客|送別|相別|敘別|來會|邀|話別|邀飯|相見', text):
        acts.append('交游')
    if re.search(r'按|舊傳|碑本|石刻|蓋非|非也|恐後人|故辯之|乃知|未可決|余謂|余以為|余觀之', text):
        acts.append('考订')
    if re.search(r'市|買|賣|飲食|節令|荔枝|墨|酒|茶|布|菱|梅雨|瘴|癭|諺|俗|土人|村婦|田翁|居民|井邑|列肆|貨物|屠戶', text):
        acts.append('风土')
    return acts


# ============================================================ 富化字段
def _hit(text, kws):
    return any(k in text for k in kws)


def landscape_field(text):
    out = []
    if _hit(text, ['山水', '山', '江', '溪', '潭', '泉', '巖', '崖', '峰', '嶺', '灘', '峽', '岷江', '青衣江']):
        out.append('山水')
    if _hit(text, ['碑', '石刻', '古蹟', '祠堂', '廟', '塔', '陵', '墓', '祠', '寺', '觀', '閣']):
        out.append('古蹟')
    if _hit(text, ['城', '州', '縣', '鎮', '館', '驛', '市', '廨', '衙']):
        out.append('城隍')
    if _hit(text, ['寺', '觀', '院', '禪']):
        out.append('寺觀')
    if _hit(text, ['市', '肆', '列肆', '墟市', '酒肆', '買賣', '魚蟹']):
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
    if _hit(text, ['寒', '冷', '涼', '霜', '雪']):
        out.append('寒')
    if _hit(text, ['熱', '暑', '燄', '燔灼']):
        out.append('暑')
    if _hit(text, ['霧', '重霧', '霾']):
        out.append('霧')
    return out


EMO = {
    '驚嘆': ['可駭', '可畏', '奇觀', '偉觀', '可壯', '甚可畏', '奇異'],
    '追慕': ['追慕', '絕歎', '太息', '可念', '可歎', '懷', '慕'],
    '孤憤': ['孤憤', '惴慄', '僇人', '辱於此'],
    '忧慮': ['憂', '懼', '可憂', '危', '恐', '傷'],
    '旷達': ['旷達', '可憐', '喜', '樂', '可喜', '快'],
    '憐憫': ['可哀', '憫', '哀'],
}
IMG = {
    '月': ['月', '明月', '月色', '中秋'], '水': ['水', '江', '溪', '潭', '泉', '濤', '瀾', '波', '浪'],
    '石': ['石', '巖', '怪石', '奇石'], '梅': ['梅'], '荷': ['荷', '蓮', '芙蕖', '蓮池'],
    '竹': ['竹', '篁'], '菊': ['菊'], '雪': ['雪'], '雲': ['雲', '霧', '烟'],
    '燈': ['燈', '炬', '燈火'], '舟': ['舟', '船', '楫', '帆', '槳', '篙'],
    '山': ['山', '峰', '嶺', '岡'],
}


def emotion_field(text):
    return [e for e, kws in EMO.items() if _hit(text, kws)]


def imagery_field(text):
    return [im for im, kws in IMG.items() if _hit(text, kws)]


# ============================================================ 主流程
def build():
    entries = read_source()
    src = io.open(SRC, encoding='utf-8').read()
    print('[1] 源: %s' % SRC)
    print('    切出干支日头: %d' % len(entries))
    print('    分卷:', dict(sorted(Counter(e['juan'] for e in entries).items())))
    bad = [g for g in set(GAZ) if g not in src]
    print('    有效词典: %d；未见于标点本: %d' % (len(set(GAZ)), len(bad)))
    if bad:
        print('      缺:', bad)

    events = []
    for e in entries:
        text = e['orig']
        start = len(e['date_raw'])
        place, allp = anchor_places(text, start)
        ev = OrderedDict([
            ('id', 'WCL-%03d' % (len(events) + 1)),
            ('juan', e['juan']),
            ('month', e.get('month')),
            ('ganzhi', e.get('ganzhi')),
            ('day_num', e.get('day_num')),
            ('day_src', e.get('day_src')),
            ('date_raw', e['date_raw']),
            ('orig', text),
            ('kind', 'date' if len(text) > start else 'empty'),
            ('place', place),
            ('place_all', allp),
            ('activity', []),
            ('landscape', []), ('weather', []), ('emotion', []), ('imagery', []),
            ('note', ''),
        ])
        acts = classify(text)
        ev['activity'] = acts if acts else ['其他']
        ev['landscape'] = landscape_field(text)
        ev['weather'] = weather_field(text)
        ev['emotion'] = emotion_field(text)
        ev['imagery'] = imagery_field(text)
        if place:
            ev['note'] = '锚定：%s（主地点）' % place
        elif allp:
            ev['note'] = '有地名 %s，无行进动词锚定，主地点记 null' % '、'.join(allp[:3])
        else:
            ev['note'] = '原文未著地名（无「动词+词典地名」锚定）'
        if e.get('merged'):
            ev['note'] += '；' + e.get('note_merged', '')
        if e.get('day_num') is None and e.get('day_src') not in ('head', 'unknown'):
            ev['note'] += '；序数日未推出（%s）' % e.get('day_src', 'unknown')
        events.append(ev)
    return events


def report(events):
    n = len(events)
    has = [e for e in events if e['place']]
    print('\n[2] 统计')
    print('    总条数: %d' % n)
    print('    有主地点: %d (%.1f%%)' % (len(has), 100.0 * len(has) / n))
    print('    有 place_all: %d' % sum(1 for e in events if e['place_all']))
    print('    有 day_num: %d' % sum(1 for e in events if e.get('day_num') is not None))
    print('    month 分布:', dict(sorted(Counter(e.get('month') for e in events).items())))
    print('    day_src 分布:', dict(Counter(e.get('day_src') for e in events)))
    print('    活动分布:', dict(Counter(a for e in events for a in e['activity'])))
    print('    富化 landscape:', dict(Counter(x for e in events for x in e['landscape']).most_common(6)))
    print('    富化 weather:', dict(Counter(x for e in events for x in e['weather']).most_common(8)))
    print('    富化 emotion:', dict(Counter(x for e in events for x in e['emotion']).most_common(6)))
    print('    富化 imagery:', dict(Counter(x for e in events for x in e['imagery']).most_common(10)))


def dump(events):
    outdir = HERE
    jp = os.path.join(outdir, '吳船錄_events.json')
    io.open(jp, 'w', encoding='utf-8', newline='\n').write(
        json.dumps(events, ensure_ascii=False, indent=2) + '\n')
    cp = os.path.join(outdir, '吳船錄_events.csv')
    with io.open(cp, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['id', 'juan', 'month', 'ganzhi', 'day_num', 'day_src', 'date_raw',
                    'orig', 'kind', 'place', 'place_all', 'activity',
                    'landscape', 'weather', 'emotion', 'imagery', 'note'])
        for e in events:
            w.writerow([e['id'], e['juan'], e.get('month') or '', e.get('ganzhi') or '',
                        e.get('day_num') if e.get('day_num') is not None else '',
                        e.get('day_src') or '', e['date_raw'], e['orig'], e['kind'],
                        e['place'] or '', '|'.join(e['place_all']), '|'.join(e['activity']),
                        '|'.join(e['landscape']), '|'.join(e['weather']),
                        '|'.join(e['emotion']), '|'.join(e['imagery']), e['note']])
    print('\n[3] 输出')
    print('    %s (%d bytes)' % (jp, os.path.getsize(jp)))
    print('    %s (%d bytes)' % (cp, os.path.getsize(cp)))


if __name__ == '__main__':
    ev = build()
    report(ev)
    dump(ev)
