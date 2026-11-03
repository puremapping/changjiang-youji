# -*- coding: utf-8 -*-
"""
v003 吴船录 —— 纯原文匹配版事件表抽取

输入（只读，不修改）：
  source/吴船录_分段.txt                                   纯原文（繁体，维基文库·四库本）
  source/ocr_out/.../parsed/吴船录_卷上.md / 卷下.md         朱迎平译注本（仅用来查干支→公历日）

输出：
  data/events.json / data/events.csv / METHOD.md 的统计数字由此脚本实算

原则：不编造。地名抽不出 -> null；干支→公历日查不到 -> null。
"""
import csv
import json
import re
from collections import Counter, OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]          # .../travelog_visualization
SRC_PLAIN = ROOT / "source" / "吴船录_分段.txt"
REF_DIR = ROOT / "source" / "ocr_out" / "入蜀记吴船录译注_朱迎平_上海古籍2024" / "ocr" / "parsed"
OUT_DIR = Path(__file__).resolve().parent
DATA_DIR = OUT_DIR / "data"

# ---------------------------------------------------------------- 干支
GAN = "甲乙丙丁戊己庚辛壬癸"
ZHI = "子丑寅卯辰巳午未申酉戌亥"
GANZHI = [GAN[i % 10] + ZHI[i % 12] for i in range(60)]
GZ_SET = set(GANZHI)
# 干支线性序号：甲子=0 … 癸亥=59
GZ_IDX = {gz: i for i, gz in enumerate(GANZHI)}

# 原文/刻本里的形体错误：丙丑当作丙子（丙子后一日为丁丑，可见原刻误）
GZ_ERRATA = {"丙丑": "丙子", "乙子": "乙丑"}

CN_NUM = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8,
          "九": 9, "十": 10, "十一": 11, "十二": 12, "十三": 13, "十四": 14, "十五": 15,
          "十六": 16, "十七": 17, "十八": 18, "十九": 19, "二十": 20, "二十一": 21,
          "二十二": 22, "二十三": 23, "二十四": 24, "二十五": 25, "二十六": 26,
          "二十七": 27, "二十八": 28, "二十九": 29, "三十": 30, "初一": 1}


def cn2int(s):
    s = s.strip()
    if s == "初一":
        return 1
    return CN_NUM.get(s)


# ---------------------------------------------------------------- 一、读原文、切分卷
def load_source():
    text = SRC_PLAIN.read_text(encoding="utf-8")
    start = text.index("石湖居士以淳熙丁酉歲")
    end = text.index("此南宋作品")
    body = text[start:end]
    juan_at = body.index("## 卷下")
    up, down = body[:juan_at], body[juan_at:]
    return up, down


HEAD_PAT = re.compile(
    r"^(?:(?P<season>春|夏|秋|冬)?(?P<month>[甲乙]?[一二三四五六七八九十]{1,2})月)?"
    r"(?P<gz>[甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥子])"
    r"(?:、(?P<gz2>[甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥]))*"
    r"(?:、(?P<gz3>[甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥]))*"
    r"(?:、(?P<gz4>[甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥]))*"
    r"(?:、(?P<gz5>[甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥]))*"
    r"，?(?P<su>[朔晦])?。"
)


def split_entries(juan_text, juan_no):
    """按行切；行首为干支日才起新条目。首条（五月二十九日戊辰）单独处理。"""
    lines = [l.strip() for l in juan_text.replace("## 卷上", "").replace("## 卷下", "").split("\n")]
    lines = [l for l in lines if l]
    entries = []
    cur = None
    for ln in lines:
        m = HEAD_PAT.match(ln)
        if m:
            # 同一行可能含多个干支：丁亥、戊子、己丑、庚寅、辛卯，泊嘉州。
            gzs = re.findall(r"[甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥子]", ln[:m.end()])
            gzs = [GZ_ERRATA.get(g, g) for g in gzs]
            head_gz = gzs[0]
            rest = ln[m.end():]
            if cur:
                entries.append(cur)
            cur = {
                "juan": juan_no,
                "month": cn2int(m.group("month")) if m.group("month") else None,
                "season_month_raw": (m.group("season") or "") + (m.group("month") or ""),
                "gz_list": gzs,
                "day_ganzhi": head_gz,
                "shuo": m.group("su"),
                "date_raw": ln[:m.end()].rstrip("。"),
                "body": rest,
                "merged": len(gzs) > 1,
            }
        else:
            if cur is None:                      # 卷首无日期句（不应出现）
                cur = {"juan": juan_no, "month": None, "season_month_raw": "", "gz_list": [],
                       "day_ganzhi": None, "shuo": None, "date_raw": "", "body": ln, "merged": False}
            else:
                cur["body"] += ln
    if cur:
        entries.append(cur)

    # 卷首「五月二十九日戊辰離成都」不是标准日头格式，单独补一条
    first = {"juan": juan_no, "month": 5, "season_month_raw": "五月", "gz_list": ["戊辰"],
             "day_ganzhi": "戊辰", "shuo": None, "date_raw": "五月二十九日戊辰",
             "body": juan_text.split("\n")[2] if False else None, "merged": False}
    return entries, first


def first_entry():
    up, _ = load_source()
    for ln in up.split("\n"):
        if "五月二十九日戊辰" in ln:
            return {"juan": 1, "month": 5, "season_month_raw": "五月", "gz_list": ["戊辰"],
                    "day_ganzhi": "戊辰", "shuo": None,
                    "date_raw": "五月二十九日戊辰",
                    "body": ln.strip(),
                    "merged": False, "explicit_day": 29}


# ---------------------------------------------------------------- 二、干支 → 公历日（农历序数日）
def build_gz2day():
    """从译注本译文里取「干支(序数日)」。译文该处若一日并两干支，则两个都记。"""
    mapping = OrderedDict()
    span = {}
    for f in ["吴船录_卷上.md", "吴船录_卷下.md"]:
        t = (REF_DIR / f).read_text(encoding="utf-8")
        for para in t.split("\n"):
            if not re.match(r"^\s*[甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥]", para):
                continue
            # 逐干支捕获：庚申、辛酉(二十三日、二十四日)
            for m in re.finditer(r"([甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥])"
                                 r"(?:、([甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥]))?"
                                 r"\s*[(（]([^)）]{1,24})[)）]", para):
                days = re.findall(r"[一二三四五六七八九十]+日|初一", m.group(3))
                gzs = [m.group(1)] + ([m.group(2)] if m.group(2) else [])
                if len(days) == len(gzs):
                    for g, d in zip(gzs, days):
                        di = cn2int(d.rstrip("日") if d != "初一" else d)
                        mapping.setdefault(g, []).append(di)
                elif len(gzs) == 1 and len(days) == 1:
                    mapping.setdefault(gzs[0], []).append(cn2int(days[0].rstrip("日")))
            # 兜底：「干支，朔日」/「干支(无日子)」→ 不作推断，交给锚月
    return mapping


def build_cycle_anchors(mapping, entries):
    """
    在这本书里，同一干支会在不同月份重复出现，所以干支→日不能全局取一个值。
    办法：以一个明确的「月朔」条目为锚（月+干支+X朔），用它反推整月的干支序号序列；
    同一月内所有干支由锚月推出，全程不跨月外推。
    若译文给了某月某干支的日子，用译文的值为准（并记来源）。
    """
    # 每个条目的月份（沿用上月）
    month = None
    for e in entries:
        if e["month"]:
            month = e["month"]
        e["_month"] = month

    # 月头锚：形如「六月己巳朔」/「八月戊辰，朔」/「冬十月丁卯，朔」
    anchors = {}
    for e in entries:
        if e.get("shuo") == "朔" or e.get("explicit_day") == 29:
            m = e["_month"]
            if e.get("explicit_day") == 29:
                # 五月二十九日戊辰：戊辰为二十九日
                anchors.setdefault(m, None)
                e["_anchor"] = (GZ_IDX[e["day_ganzhi"]], 29)
                continue
            if m not in anchors:
                anchors[m] = (GZ_IDX[e["day_ganzhi"]], 1)
                e["_anchor"] = anchors[m]
    return anchors


def assign_days(entries, anchors, gz2day_from_ref):
    """
    两步走：
    A. 锚月推算：月内以「X月干支朔」为起点，得 day_A。
    B. 日序单调校验：日序必随记录顺序严格递增（同日可重复）。译文直接给出值、
       或由锚月推算得值，一并参与；与义注本「一日并两干支(23日、24日)」联排协调。
       若某条按 A 值与上下文冲突，则以「上一有效日+最小相符干支偏移」重算（day_B）。
    只输出 1~30 区间内的值，其余一律 null。
    """
    if 5 not in anchors:
        anchors[5] = (GZ_IDX["戊辰"], 29)

    # --- A: 锚月推算 + 译注本直接给值
    cur_anchor = None
    for e in entries:
        m = e["_month"]
        if m in anchors:
            cur_anchor = anchors[m]
        e["day_A"] = None
        e["day_ref"] = None
        gz = e["day_ganzhi"]
        if gz is None:
            continue
        if cur_anchor:
            off = (GZ_IDX[gz] - cur_anchor[0]) % 60
            d = cur_anchor[1] + off if off <= 30 else None
            if d and 1 <= d <= 30:
                e["day_A"] = d
        # 译注本逐条译文里明确括注的日子（一日并两干支时一并取）
        ref = gz2day_from_ref.get(gz) if not e.get("merged") else None
        if e.get("explicit_day"):
            ref = [e["explicit_day"]]
        if ref:
            cand = [c for c in ref if 1 <= c <= 30]
            if e["day_A"] is None:
                e["day_ref"] = cand[0] if cand else None
            else:
                # 与锚推值相差 ≤1 才采信，避免由于同月出现两次而造成取值错误
                ok = [c for c in cand if abs(c - e["day_A"]) <= 1]
                e["day_ref"] = ok[0] if ok else None

    # --- B: 跨月日序校验（单调不减；仅在毛刺=1日且下一条立即回落时判为毛刺）
    #    毛刺来源：译注本括注在一日并两干支时给出「下一干支的日子」，被摄合到上一干支。
    outs = [i for i, e in enumerate(entries)
            if e["day_ganzhi"] and (e["day_A"] is not None or e["day_ref"] is not None)]
    for k, i in enumerate(outs):
        e = entries[i]
        v = e["day_A"] if e["day_A"] is not None else e["day_ref"]
        if v is not None and 1 <= v <= 30:
            e["day_num"] = v
        else:
            e["day_num"] = None
    for k in range(1, len(outs) - 1):
        a, b, c = entries[outs[k - 1]], entries[outs[k]], entries[outs[k + 1]]
        if None in (a["day_num"], b["day_num"], c["day_num"]):
            continue
        if b["day_num"] == a["day_num"] + 1 and c["day_num"] <= a["day_num"]:
            b["day_num"] = a["day_num"]      # 毛刺：与上一日同日
    # 「X月干支朔」必须为 1 日；「五月二十九日戊辰」为 29 日 —— 由原文显式给出，置顶覆盖
    for e in entries:
        if e.get("explicit_day"):
            e["day_num"] = e["explicit_day"]
    for e in entries:
        gz = e["day_ganzhi"]
        if not gz or e.get("day_num") is None:
            e["day_src"] = "null"
        elif e["day_ref"] == e["day_num"]:
            e["day_src"] = "ref"
        else:
            e["day_src"] = "anchor"
    return entries


# ---------------------------------------------------------------- 三、地名词典（只从原文动词结构抽）
VERB_TRAVEL = "至過發抵宿泊"          # 行进落点
VERB_VISIT = "登遊謁憩望"             # 登临游观
VERB_ALL = "至過發抵宿泊入出離到經登遊謁望憩渡行"

# 通名/非地名黑名单（动词后不必是地名；或抽出来是通名）
NON_PLACE = set("""
城 城西 城東 城南 城北 山 山上 山下 山頂 山半 山麓 舟 船 岸 家 寺 寺中 院 宮 觀 亭 樓 閣 堂 殿 峰 嶺 溪 江 河 湖 灘 洞
彼 此 之 其 前 後 上 下 中 內 外 東 西 南 北 焉 岸 省 官 山頴 縣 州 郡 府 市 村 莊 鎮
是以 是 亦 云 之 所 可 至 且 又 復 不
""".split())

# 抽出来后明显是普通词语 / 句子成分的
BAD_SUFFIX = ("見", "過", "之", "者", "也", "矣", "云", "時", "日", "夜", "年", "月", "人",
              "客", "船", "舟", "馬", "擔", "夫", "稅", "錢", "米", "酒", "茶", "藥", "水",
              "土", "石", "木", "草", "花", "竹", "葉", "色", "聲", "光", "氣", "風", "雨",
              "雪", "雲", "火", "星", "燈", "香", "物", "事", "處", "所", "既", "已")

# 人工筛出的地名（从动词后候选里挑，逐条核过原文）
VETTED_PLACES = [
    # —— 成都周边（卷上）
    "小東郭合江亭", "合江亭", "郫縣", "犀浦鎮", "安德鎮", "永康軍", "玉壘關", "浮雲亭",
    "懷古亭", "伏龍觀", "崇德廟", "離堆", "青城", "青城山", "羅漢院", "丈人觀", "上清宮",
    "長生觀", "範氏莊園", "青城縣", "聖佛院", "周家莊", "蜀州", "江原縣", "新津縣",
    "脩覺", "彭山", "眉州", "蟆頤", "景疏樓", "起文堂", "元佑學堂", "眉山館", "中巖",
    "喚魚潭", "深源泉", "慈姥巖", "石筍", "寶瓶峰", "青衣", "湖瀼峽", "平羌", "嘉州",
    "雪堂", "問月堂", "九頂寺", "淩雲", "淩雲寺", "天寧閣", "載酒亭", "萬景樓", "安樂園",
    "廣福院", "方響洞", "大峨", "中峨", "小峨", "蘇稽鎮", "符文鎮", "峨眉縣", "慈福",
    "普安", "白水莊", "蜀村店", "龍神堂", "華嚴院", "青竹橋", "峨眉新觀", "梅樹埡",
    "兩龍堂", "中峰院", "普賢閣", "白崖峰", "呼應峰", "茂真尊者庵", "雙溪橋", "牛心寺",
    "寶現溪", "菩薩閣", "白水普賢寺", "白水寺", "點心山", "茅亭觜", "石子雷", "駱駝嶺",
    "簇店", "峰門", "羅漢店", "木皮里", "胡孫梯", "雷洞平", "新店", "八十四盤", "娑羅平",
    "思佛亭", "軟草平", "洗腳溪", "光相寺", "天仙橋", "光明巖", "黑水", "虎溪橋", "月峰",
    "青蓮峰", "白雲峽", "龍門", "龍門峽", "龍洞", "峨眉",
    # —— 顺流而下（卷下）
    "王波渡", "羅護鎮", "犍為縣", "下壩", "宣化縣", "敘州", "南廣江", "南溪縣", "江安縣",
    "張旗三灘", "瀘州", "南定樓", "來風亭", "合江縣", "登天王", "劉仙觀", "安樂山",
    "江津縣", "漁洞", "泥培村", "恭州", "報恩寺", "樂溫縣", "張益德廟", "涪州", "排亭",
    "黔江", "妃子園", "群豬灘", "酆都縣", "平都山", "仙都道觀", "景德", "竹平", "忠州",
    "四賢閣", "荔枝樓", "武寧縣", "萬州", "西山", "岑公洞", "開江口", "下巖", "瑞光閣",
    "雲安軍", "夔州", "八陣", "瞿唐", "灩滪", "白帝", "三峽堂", "高齋", "瞿唐口", "黑石灘",
    "大溪口", "巫山縣", "巫峽", "神女廟", "陽雲臺", "高唐觀", "來鶴峰", "東奔灘",
    "巴東縣", "寇忠湣公祠", "歸州", "咤灘", "人鲊甕", "秭歸", "清烈公祠", "屈平廟",
    "宋玉宅", "興山縣", "昭君臺", "香溪", "明妃廟", "望洋軒", "懷忠", "歸鄉沱", "麻線堆",
    "白狗峽", "玉虛洞", "新灘", "黃牛峽", "洺川廟", "扇子峽", "蝦蟆碚", "平善壩",
    "至喜亭", "峽州", "楚塞樓", "爾雅臺", "郭道山", "歐陽公草堂", "甘泉寺", "姜詩泉",
    "楊木寨", "枝江縣", "松滋縣", "沙頭", "沙市", "渚官", "渚宮", "絳帳臺", "章華臺",
    "落帽臺", "息壤", "江瀆廟", "公安縣", "二聖寺", "石首縣", "魯家洑", "沌", "百里荒",
    # 只作为「駐泊地」出现的地方（泊鄂州 / 發建康 / 集玉麟堂）
    "鄂州", "鄂州南樓", "南樓", "建康", "鎮江", "玉麟堂", "新津縣廨", "眉山館",
    "郡圃起文堂", "江亭", "沌中", "黃鶴山",
    "鄂渚", "鸚鵡洲", "南布堤", "南市", "南樓", "黃鶴山", "壓雲亭", "雅歌", "漢口",
    "三江口", "赤壁", "黃州", "臨臯亭", "東坡雪堂", "雪堂", "小橋", "高寒", "竹樓",
    "棲霞樓", "慶端堂", "巴河", "桐木溝", "馬頭", "江州", "琵琶亭", "庾樓", "思白堂",
    "濂溪", "周先生祠堂", "太平興國宮", "聖治峰", "香爐", "石頂", "獅子", "蓮花",
    "東林寺", "虎溪", "五杉閣", "舍利塔", "聰明泉", "西林寺", "香谷", "清虛庵", "撥雲峰",
    "湖口", "大孤", "交石夾", "小孤", "澎浪磯", "滶背洲", "馬當", "波斯夾", "皖口",
    "牛磯", "雁汊", "長風沙", "池州", "池口", "望淮亭", "九華樓", "齊山", "翠微亭",
    "九華", "南湖口", "非水亭", "清溪口", "清溪", "太平州", "淩歊臺", "建康府",
    "賞心亭", "玉麟堂", "伏龜樓", "清溪閣", "長蘆", "鎮江府", "常州", "滸墅", "盤門",
    "平江",
]

# 地名规范化：长名优先匹配，短名残余不计（避免「嘉州」吃掉「嘉」）
# 「至」后接这些字是虚词/时间副词，不是地名落点
SKIP_AFTER_ZHI = ("是", "此", "今", "暮", "曉", "夜", "晚", "此", "其", "所", "處", "縣中",
                  "縣", "州", "一處", "峽", "峽口", "壩下", "地", "峰頂", "山頂", "山半",
                  "山麓", "岸", "江步", "州數里", "曉不止", "未", "酉後", "巳時")

VETTED_PLACES = sorted(set(VETTED_PLACES), key=len, reverse=True)

# 动词后紧接这些字，说明不是地名（泊舟/登舟/過渡/至是/至今…）
NONLOC_NEXT = ("舟", "船", "岸", "渡", "是", "此", "今", "縣", "州", "郡", "來", "去",
               "其", "所", "之", "處", "者", "於", "乃", "復", "又", "而", "以", "上",
               "下", "中", "前", "後", "內", "外", "間", "門")


def extract_places(body):
    """返回 [(place, verb, window)]，按原文出现顺序。"""
    found = []
    for m in re.finditer("[" + VERB_ALL + "]", body):
        v = m.group(0)
        win = body[m.end(): m.end() + 12]
        # 「泊舟」「登舟」：字面宾语是船，不是地名 —— 但「舟下眉州」「舟至X」后面才是落点
        if win[:1] in ("舟", "船", "渡", "岸"):
            win = re.sub(r"^(?:舟|船|渡|岸)?(?:下|至|於|于)?", "", win)
            if not win:
                continue
        if v == "至" and any(win.startswith(x) for x in SKIP_AFTER_ZHI):
            continue
        hit = None
        for p in VETTED_PLACES:
            if win.startswith(p):
                hit = p
                break
        if hit is None and v in ("泊", "宿", "行", "入", "至", "過"):
            # 「泊夾中」「行沌中」：地名后带「中」也算命中（短名如「沌」「夾」）
            for p in VETTED_PLACES:
                if win.startswith(p + "中"):
                    hit = p
                    break
        if hit is None:
            # 介词式：「集於玉麟堂」「泊於夾中」——动词后先见「於/于」
            mm = re.match(r"[於于](.{2,6})", win)
            if mm:
                for p2 in VETTED_PLACES:
                    if mm.group(1).startswith(p2):
                        hit = p2
                        break
        if hit:
            found.append((hit, v, body[m.start(): m.end() + 1 + len(hit)]))
    # 去重保序
    seen = set()
    out = []
    for p, v, w in found:
        if p in seen:
            continue
        seen.add(p)
        out.append((p, v, w))
    return out


# 介词式锚定（动词不含「集/具」等，但原文用「於/于 + 地名」明示场所）
PREP_ANCHORS = ["郡圃起文堂", "眉山館", "玉麟堂", "江亭", "南樓", "起文堂"]
# 「集南樓」「集玉麟堂」「泊夾中」：动词（集/泊/宿）直接+地名，已由 VERB_ALL 覆盖但
# 「集」不在动词表内，故以 CLUB_VERBS 单独锚定
CLUB_VERBS = "集移具駐"
# 「風復作波斯夾」「移舟近東泊」「泊夾中」——补充「作」作动词的落点
WRITE_VERBS = "作"


def extract_club_places(body):
    out = []
    for m in re.finditer("[" + CLUB_VERBS + WRITE_VERBS + "]", body):
        win = body[m.end(): m.end() + 8]
        for p in VETTED_PLACES:
            if win.startswith(p):
                out.append((p, m.group(0), body[max(0, m.start() - 8): m.end() + len(p)]))
                break
    return out


def extract_verb_places(body):
    return extract_places(body)


def extract_prep_places(body):
    out = []
    for p in PREP_ANCHORS:
        for m in re.finditer("[於于]" + p, body):
            out.append((p, "於", body[max(0, m.start() - 10): m.end()]))
    return out


# ---------------------------------------------------------------- 四、活动类型
ACT_RULES = {
    "行路": "至過發抵宿泊入離到經行渡",
    "游观": "遊觀登望覽憩謁",
    "交游": "見來招集餞謁送別",
    "考订": None,   # 关键词
    "风土": None,
}
# 考订：须是「作者自己的考辨/辨误」，不是单纯引用旧说
KAODING_KW = ["按：", "按:", "舊傳", "碑本", "石刻", "蓋非", "非也", "恐後人", "恐其",
              "故辯之", "辯之", "乃知", "未可決", "疑", "不足道", "謂之", "舊記以為",
              "余謂", "余以為", "余觀之"]
# 引用式传说（不算考订，算风土/见闻）——单独统计时可看出差别
LEGEND_KW = ["相傳", "世云", "俗傳", "或云", "舊說", "俗云"]
FENGTU_KW = ["民風", "物產", "習俗", "市", "買", "賣", "飲食", "節令", "荔枝", "荔子",
             "墨", "酒", "茶", "布", "菱", "梅雨", "瘴", "癭", "諺", "俗", "土人", "村婦",
             "田翁", "居民", "井邑", "廛闬", "列肆", "貨物", "歲刲", "屠戶"]


def tag_activity(body):
    acts = []
    if re.search(r"[至過發抵宿泊入離到經行渡]", body):
        acts.append("行路")
    if re.search(r"[遊觀登望覽憩謁]", body):
        acts.append("游观")
    if re.search(r"見|來見|招集|招遊|招至|餞|餞別|送客|送別|相別|謁|敘別|來會|邀|留看|話別|邀飯|相見", body):
        if "交游" not in acts:
            acts.append("交游")
    if any(k in body for k in KAODING_KW) and not (
            sum(body.count(k) for k in LEGEND_KW) > 0
            and not any(k in body for k in ("按：", "按:", "非也", "蓋非", "恐後人", "故辯之", "余謂", "余以為"))):
        acts.append("考订")
    if any(k in body for k in FENGTU_KW):
        acts.append("风土")
    if not acts:
        # 兜底：「集玉麟堂」「開啟法會」这类无行路动词的社交/仪式日
        if re.search(r"集|會|宴|齋|慶|謁|召|招|送", body):
            acts.append("交游")
        else:
            acts.append("行路")
    return acts


# ---------------------------------------------------------------- 五、人物
HUANG = ["黃庭堅", "山谷", "魯直", "涪翁", "涪皤"]
SU = ["蘇軾", "東坡", "坡翁", "坡公"]
DU = ["杜甫", "杜子美", "子美"]
LIBAI = ["李白", "李大白", "大白"]
# 官员：上下文含官职词时视为官员
OFFICE_KW = ("守", "倅", "通判", "憲使", "帥", "制置", "漕", "監司", "使臣", "郡將",
             "留守", "監司帥守", "郡守", "前守", "前權守", "檢討", "給事", "侍郎", "按察")
OFFICE_NAME_RE = re.compile(
    r"(?:知州|通判|憲使|郡守|郡將|太守|前守|前權守|帥|留守|制置使|漕|縣尉|縣令|監司)"
    r"(?P<name>[\u4e00-\u9fa5]{2,3}?)(?=[子文潛德蒼駿潛之序])"
)

# 人工核过的官员表（name, 依据片段关键词）——从原文官职+姓名结构取
OFFICIALS = [
    ("李燾", "李燾仁父適為禮部侍郎"),
    ("程詠之", "謁憲使程詠之於雪堂"),
    ("何正仲", "同年雅州守何正仲子方來見"),
    ("吳廣仲", "郡守吳廣仲撒舊四相堂新之"),
    ("張縯", "前館職張縯季長招至其曾祖所作善頌堂上"),
    ("劉焞", "劉焞文潛招集於郡圃起文堂"),
    ("王亢", "嘉守王亢子蒼留看月榭"),
    ("陸遊", "前權守陸遊務觀所作"),
    ("馬騏", "瀘帥馬騏德駿移具江亭"),
    ("晁公武", "前帥晁公武子止所作"),
    ("梁介", "梁介子輔所作"),
    ("王陽英", "前守王陽英昭祖所作也"),
    ("李石", "前守李石知幾所作"),
    ("辛棄疾", "江陵帥辛棄疾幼安招遊渚官"),
    ("劉邦翰", "監司帥守劉邦翰子宣而下"),
    ("李川", "統帥李川邀看新寨"),
    ("曹訓", "前守曹訓子序新作"),
    ("呂勝己", "通判呂勝己隸書"),
    ("潘慈明", "郡守潘慈明伯龍新作周先生祠堂"),
    ("管鑒", "乃告峽州守管鑒"),
    ("葉默", "歸州守葉默"),
    ("熊浩", "倅熊浩"),
    ("沈作礪", "夔漕沈作礪"),
    ("孫某", "縣尉孫某作小記"),
    ("劉公", "從留守樞密劉公行視新修外城"),
    ("胡長文", "交代胡長文給事已至夷陵"),
    ("胡元質", "胡元質堅持挽留"),
    ("章森", "知石泉軍章森德茂"),
    ("馮輔", "遣郡丞馮輔攝水祠下"),
    ("李蘩", "李蘩清叔守郡時所作"),
]
# 僚属/幕客（同行者，不含具体官职时归官员之下的僚属）
STAFF = [
    ("簡世傑", "幕客簡世傑伯雋"),
    ("楊光", "楊光商卿"),
    ("周傑德", "周傑德俊萬"),
    ("虞植", "進士虞植子建"),
    ("楊愻", "同年楊愻伯勉"),
    ("李嘉謀", "幕客李嘉謀良仲"),
    ("範謨", "幕客範謨季申"),
    ("郭明復", "郭明復中行"),
    ("楊輔", "楊輔嗣勛"),
    ("楊商卿", "楊商卿父子"),
    ("譚季壬", "譚季壬德稱"),
]
# 僧道
MONKS = [
    ("繼業", "牛心寺三藏師繼業"),
    ("惠遠", "晉惠遠師道場也"),
    ("惠永", "惠永師道場也"),
    ("法才", "余囑主僧法才作亭"),
    ("茂真", "茂真尊者庵"),
    ("諾矩那", "諾矩那庵也"),
    ("海通", "浮屠海通始鑿山"),
    ("孫思邈", "孫思邈隱於峨眉"),

    ("張又新", "張又新《水品》"),
    ("劉道者", "昔有劉道者創之"),
    ("劉珍", "劉仙名珍，隋開皇時人"),
    ("張果老", "張果老、孫思邈二像"),

    ("呂光", "相傳為呂光廟"),
    ("王方平", "前漢王方平"),
    ("陰長生", "後漢陰長生"),
    ("岑叟", "岑叟事見嚴挺之碑"),
    ("法寶", "有浮屠法寶於山腳刊木開路"),
]
# 亲友家人
FAMILY = [
    ("范成大自稱（石湖居士）", "石湖居士以淳熙丁酉歲"),
    ("家弟成績", "及家弟成績"),
    ("孥累（妻兒家小）", "發孥累"),
    ("田翁", "道見田翁"),
    ("費祎", "諸葛孔明送費祎使吳"),

]
# 前贤（历史人物）
FORESAGES = [
    ("杜甫", ["杜子美", "子美"]),
    ("蘇軾", ["東坡", "坡翁", "坡公", "坡、谷"]),
    ("黃庭堅", ["山谷", "魯直", "涪翁", "涪皤"]),
    ("李白", ["李大白", "大白"]),
    ("諸葛亮", ["諸葛孔明", "諸葛孔明", "孔明"]),
    ("李冰", ["李太守", "李冰", "李氏父子"]),
    ("唐玄宗", ["唐玄宗", "玄宗"]),
    ("歐陽修", ["歐陽公"]),
    ("顏真卿", ["顏魯公", "真卿", "魯公"]),
    ("白居易", ["樂天", "白居易"]),
    ("柳公權", ["柳公權"]),
    ("李邕", ["李邕"]),
    ("歐陽詢", ["歐陽詢"]),
    ("張僧繇", ["張僧繇"]),
    ("謝靈運", ["謝靈運"]),
    ("劉晏", ["劉晏"]),
    ("陸贄", ["陸贄"]),
    ("李吉甫", ["李吉甫"]),
    ("段文昌", ["段文昌"]),
    ("孫太古", ["孫太古", "孫知微"]),
    ("盧楞伽", ["盧楞伽"]),
    ("鳩摩羅什", ["鳩摩羅什"]),
    ("宋玉", ["宋玉"]),
    ("屈原", ["屈平", "屈原"]),
    ("王昭君", ["王嬙", "昭君"]),
    ("曹彬", ["曹彬"]),
    ("李煜", ["李煜"]),
    ("陸遜", ["陸遜"]),
    ("宋武帝", ["宋武帝"]),
    ("郭璞", ["郭景純"]),
    ("商仲堪", ["商仲堪"]),
    ("達磨", ["達磨"]),
    ("韋臯", ["韋臯"]),
    ("張益德", ["張益德"]),
    ("宋徽宗", ["宣和間"]),
    ("杜牧", ["杜牧"]),
    ("蘇頌", ["蘇頌"]),
]
UNNAMED_KW = [("船工/篙工", ["舟師", "篙工", "搖櫓者", "三老", "舟人", "梢船"]),
              ("灘子", ["灘子", "盤灘"]),
              ("村民/土人", ["土人", "村人", "村婦", "村民", "居民", "邑人", "郡人", "眉人",
                            "縣人", "蜀人", "山人", "觀人"]),
              ("送客/從人", ["送客", "從人", "同行皆", "同行者", "諸賓", "送兵", "從船"]),
              ("考生/蜀士", ["蜀士", "進士"]),
              ("婢子", ["婢子"]),
              ("道士", ["道士", "羽流", "方士", "羽衣"]),
              ("僧", ["寺僧", "主僧", "僧人", "僧徒", "僧雲", "僧云", "天臺僧", "病僧", "僧"])]


def extract_people(body, prev_people_names):
    ppl = []
    seen = set()

    def add(name, typ, ev):
        if name in seen:
            return
        seen.add(name)
        ppl.append({"name": name, "type": typ, "evidence": ev})

    # 1 前贤（词条命中，含别名）
    for canon, aliases in FORESAGES:
        for a in aliases:
            i = body.find(a)
            if i >= 0:
                add(canon, "前贤", body[max(0, i - 12): i + len(a) + 12])
                break
    # 2 官员
    for name, ev in OFFICIALS:
        i = body.find(name)
        if i >= 0:
            add(name, "官员", body[max(0, i - 14): i + len(name) + 14])
    # 3 僚属
    for name, ev in STAFF:
        i = body.find(name)
        if i >= 0:
            add(name, "官员", body[max(0, i - 14): i + len(name) + 14])
    # 4 僧道
    for name, ev in MONKS:
        i = body.find(name)
        if i >= 0:
            add(name, "僧道", body[max(0, i - 12): i + len(name) + 12])
    # 5 亲友家人
    for name, ev in FAMILY:
        i = body.find(ev)
        if i >= 0:
            add(name, "亲友家人", ev)
    # 6 无名者（若同条已有实名的同类，则不再计一个无名者，避免重复计数）
    has_named_monk = any(p["type"] == "僧道" for p in ppl)
    for label, kws in UNNAMED_KW:
        if label in ("道士", "僧") and has_named_monk:
            continue
        for kw in kws:
            i = body.find(kw)
            if i >= 0:
                add(label, "无名者", body[max(0, i - 10): i + len(kw) + 12])
                break
    return ppl


# ---------------------------------------------------------------- 六、主地点
def pick_main(places):
    # 「泊」「發」「宿」这类停宿/出发动词优先于泛用的「至」
    for verb_set, note in (("發", "启程地"), ("泊宿", "停宿落点"), ("至過抵", "行进落点"),
                           ("登遊謁憩望", "登临游观"), ("出入離到經渡", "出入经渡")):
        for p, v, w in places:
            if v in verb_set:
                return p, f"锚定：{v}{p}（{note}）"
    return None, "原文未见「动词+地名」结构"


# ---------------------------------------------------------------- 主流程
def main():
    up, down = load_source()
    e_up, _ = split_entries(up, 1)
    e_down, _ = split_entries(down, 2)
    entries = [first_entry()] + e_up + e_down 

    gz2day_ref = build_gz2day()
    anchors = build_cycle_anchors([e for e in entries if e.get("day_ganzhi")], entries)
    assign_days(entries, anchors, gz2day_ref)

    # 去除 merge 日（如「丁亥、戊子…」只保留首干支为主条目，其余记在 gz_list）
    events = []
    # 丢弃无日期的空条目（不应出现；防止切分伪影）
    entries = [e for e in entries if e.get("day_ganzhi")]
    for i, e in enumerate(entries, 1):
        body = e["body"]
        places = extract_places(body)
        for pp in extract_prep_places(body) + extract_club_places(body):
            if pp[0] not in [x[0] for x in places]:
                places.append(pp)
        place, note = pick_main(places)
        if place is None:
            if places:
                note = "仅有非行进落点地名（" + "、".join(p for p, _, _ in places) + "），未取为主地点"
            else:
                note = "原文无「动词+地名」结构，主地点记 null"
        acts = tag_activity(body)
        ppl = extract_people(body, set())
        if e.get("merged"):
            note += f"；本行并为{len(e['gz_list'])}日（{'、'.join(e['gz_list'])}），首日为主"
        if e.get("explicit_day"):
            note += "；卷首日期为「月+序数日+干支」混合形"
        if e.get("gz_list") and any(g in GZ_ERRATA for g in e["gz_list"]):
            note += "；原刻形体有误，已按干支序列校正"
        e["_src"] = e.get("day_src", "null")
        events.append({
            "id": f"WCL-{i:03d}",
            "juan": e["juan"],
            "month": e["_month"],
            "day_ganzhi": e["day_ganzhi"],
            "day_num": e["day_num"],
            "date_raw": e["date_raw"],
            "orig": (e["date_raw"] + body) if not body.startswith(e["date_raw"]) else body,
            "place": place,
            "place_all": [p for p, _, _ in places],
            "activity": acts,
            "people": ppl,
            "note": note,
            "day_src": e["_src"],
        })

    # 统计
    stats = compute_stats(events)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "events.json").write_text(
        json.dumps(events, ensure_ascii=False, indent=2), encoding="utf-8")
    write_csv(events, DATA_DIR / "events.csv")
    print(json.dumps(stats, ensure_ascii=False, indent=1))
    return events, stats


def compute_stats(events):
    n = len(events)
    with_place = sum(1 for e in events if e["place"])
    with_day = sum(1 for e in events if e["day_num"] is not None)
    people_total = sum(len(e["people"]) for e in events)
    tcnt = Counter(p["type"] for e in events for p in e["people"])
    rows_people = sum(1 for e in events if e["people"])
    acnt = Counter(a for e in events for a in e["activity"])
    # 干支→日 来源
    src = Counter("译注本明确" if e["day_src"] == "ref" else "锚月推算" if e["day_src"] == "anchor" else "null"
                  for e in events)
    uniq_gz = len({e["day_ganzhi"] for e in events})
    return {
        "总条数": n,
        "有主地名": with_place,
        "有地名（任何）": sum(1 for e in events if e["place_all"]),
        "有公历日": with_day,
        "日期来源": dict(src),
        "出现不同干支数": uniq_gz,
        "有活动标签": sum(1 for e in events if e["activity"]),
        "活动分布": dict(acnt),
        "有人员提及条数": rows_people,
        "人员提及人次": people_total,
        "人员类型分布": dict(tcnt),
        "卷上条数": sum(1 for e in events if e["juan"] == 1),
        "卷下条数": sum(1 for e in events if e["juan"] == 2),
    }


def write_csv(events, path):
    cols = ["id", "juan", "month", "day_ganzhi", "day_num", "date_raw",
            "place", "place_all", "activity", "people", "note", "orig"]
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, quoting=csv.QUOTE_ALL)
        w.writeheader()
        for e in events:
            r = dict(e)
            r["place_all"] = "|".join(r["place_all"] or [])
            r["activity"] = "|".join(r["activity"] or [])
            r["people"] = "|".join(f'{p["name"]}({p["type"]})' for p in r["people"])
            w.writerow({k: r.get(k) for k in cols})


if __name__ == "__main__":
    main()
