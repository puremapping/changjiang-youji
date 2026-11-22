# -*- coding: utf-8 -*-
"""Step 2: add 3 persons (李渤/酈道元/韓世忠) and generate works-layer intertexts
int-103+ from the 121 alias-hit sentences enumerated in candidates2.json.

Every decision is an explicit entry in DECISIONS keyed by candidate index:
  idx -> [ (target_person_id, relation, note_suffix_or_None), ... ]
Skipped false positives are listed in SKIP with a reason.
"""
import json, csv, os, collections

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
BASE = os.path.join(ROOT, 'data', 'base')
WORKS_J = os.path.join(ROOT, 'data', 'works_v1', 'works.json')

# ---------- persons ----------
NEW_PERSONS = [
    {
        'id': 'p-li-bo', 'name': '李渤', 'dynasty': '唐',
        'birth_year': 773, 'death_year': 831,
        'note': '前賢。蘇軾《石鐘山記》「至唐李渤始訪其遺踪……笑李渤之陋也」。字濬之，號白鹿先生，洛陽人，撰《辨石鐘山記》（貞元十四年798）。生卒 773–831（《舊唐書》卷171；CBDB id 0093071）。'
    },
    {
        'id': 'p-li-daoyuan', 'name': '酈道元', 'dynasty': '北魏',
        'birth_year': None, 'death_year': 527,
        'note': '前賢。蘇軾《石鐘山記》引《水經》「酈元以為下臨深潭，微風鼓浪，水石相搏，聲如洪鐘」。字善長，范陽涿縣人，《水經注》作者；生年諸說不一（466/470/472），故 birth=null，卒 527（孝昌三年，維基百科/中國文化研究院）。'
    },
    {
        'id': 'p-han-shizhong', 'name': '韓世忠', 'dynasty': '南宋',
        'birth_year': 1089, 'death_year': 1151,
        'note': '前賢（宋名將）。張岱《金山夜戲》「唱韓蘄王金山及長江大戰諸劇」。字良臣，孝宗朝追封蕲王，世稱韓蕲王；建炎四年（1130）留守金山/黃天蕩拒金兀朮。生卒 1089–1151（陝西省地方志辦公室、維基百科）。'
    },
]

pj = os.path.join(BASE, 'persons.json')
persons = json.load(open(pj, encoding='utf-8'))
NEW_PERSONS = [p for p in NEW_PERSONS if p['id'] not in {x['id'] for x in persons}]
for p in NEW_PERSONS:
    assert p['id'] not in {x['id'] for x in persons}, p['id']
    persons.append(p)
with open(pj, 'w', encoding='utf-8', newline='\n') as f:
    json.dump(persons, f, ensure_ascii=False, indent=2)
    f.write('\n')

pc = os.path.join(BASE, 'persons.csv')
with open(pc, encoding='utf-8-sig', newline='') as f:
    rows = list(csv.reader(f))
hdr = rows[0]
for p in NEW_PERSONS:
    rows.append([str(p[k]) if p[k] is not None else '' for k in hdr])
with open(pc, 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f, lineterminator='\r\n'); w.writerows(rows)

# ---------- intertexts ----------
SKIP = {
    2:  '「山谷中」為地形語（山山谷之中），非黃庭堅；int-066 同類陷阱，不建條目。',
    81: '「亦山谷間」為地形語（山谷之間），非黃庭堅；同 int-066 陷阱，不建條目。',
}

# relation: 追慕 / 质疑 / 考订 / 唱和 / 纪其遗迹 (SCHEMA §7)
# tuple = (target, relation, note_suffix or None)
D = {
  0:  [('p-li-daoyuan','考订',None)],
  1:  [('p-li-bo','考订',None)],
  3:  [('p-li-daoyuan','考订','酈元之所見聞與蘇軾同而言之不詳，考其簡略；存疑：可歸追慕。')],
  4:  [('p-li-daoyuan','考订',None), ('p-li-bo','质疑',None)],
  5:  [('p-han-shizhong','追慕','張岱演韓蕲王金山/長江大戰劇以追慕前代名將。')],
  6:  [('p-su-shi','考订',None)],
  7:  [('p-li-bai','考订',None)],
  8:  [('p-li-bai','追慕',None)],
  9:  [('p-li-bai','纪其遗迹',None)],
  10: [('p-li-bai','追慕',None)],
  11: [('p-li-bai','追慕','與謝玄暉並舉登三山題詩，重其詩作而非憑弔遺跡。')],
  12: [('p-li-bai','考订',None), ('p-su-shi','考订',None)],
  13: [('p-li-bai','追慕',None), ('p-su-shi','追慕','東坡以「太白後身」戲郭功父，非直接追慕；relation 取引李白句讚人之義，存疑。')],
  14: [('p-li-bai','考订',None)],
  15: [('p-li-bai','追慕',None)],
  16: [('p-su-shi','追慕',None)],
  17: [('p-li-bai','纪其遗迹',None)],
  18: [('p-li-bai','纪其遗迹','描寫青山太白祠中李白塑像冠袍。')],
  19: [('p-li-bai','追慕',None)],
  20: [('p-li-bai','追慕',None)],
  21: [('p-li-bai','追慕','李白為九華山易名，記其遺澤；非祠墓碑刻，存疑可歸紀遺跡。')],
  22: [('p-li-bai','追慕',None)],
  23: [('p-li-bai','追慕',None)],
  24: [('p-li-bai','考订',None)],
  25: [('p-li-bai','追慕',None)],
  26: [('p-li-bai','追慕',None)],
  27: [('p-li-bai','追慕',None)],
  28: [('p-li-bai','追慕',None)],
  29: [('p-li-bai','追慕',None)],
  30: [('p-su-shi','追慕',None)],
  31: [('p-li-bai','追慕',None)],
  32: [('p-li-bai','考订','辨太白詩石為近時俗書，非唐刻。')],
  33: [('p-bai-juyi','考订',None)],
  34: [('p-yu-yan','纪其遗迹',None)],
  35: [('p-yu-yan','纪其遗迹',None)],
  36: [('p-du-fu','追慕',None)],
  37: [('p-li-bai','考订',None)],
  38: [('p-su-shi','追慕',None)],
  39: [('p-su-shi','纪其遗迹','記蘇轍貶高安時東坡送至巴河之故實；非祠墓碑刻，存疑。')],
  40: [('p-su-shi','追慕','列舉牧之、王元之、東坡、張文潛謫居黃州而進為名邦，重在追慕前賢之宦跡。')],
  41: [('p-su-shi','纪其遗迹',None)],
  42: [('p-su-shi','追慕',None)],
  43: [('p-su-shi','纪其遗迹','「東坡」為黃州地名（蘇軾舊居），非直指本人。')],
  44: [('p-su-shi','纪其遗迹','「東坡」為黃州地名（蘇軾舊居），非直指本人。')],
  45: [('p-su-shi','纪其遗迹',None)],
  46: [('p-su-shi','纪其遗迹',None)],
  47: [('p-su-shi','追慕','亭名見蘇公、張文潛集中，引前賢文字為重，非記其舊居遺跡。')],
  48: [('p-su-shi','纪其遗迹',None)],
  49: [('p-su-shi','追慕',None)],
  50: [('p-su-shi','追慕','記東坡「齎湯蜜汁」之戲，存慕前賢風趣之意。')],
  51: [('p-li-bai','考订',None)],
  52: [('p-su-shi','考订',None)],
  53: [('p-su-shi','纪其遗迹','怪石供為東坡舊物；正值其貶黃州軼事。')],
  54: [('p-li-bai','追慕',None)],
  55: [('p-li-bai','追慕',None)],
  56: [('p-huang-ti','追慕',None)],
  57: [('p-huang-ti','追慕','原句末「蓋戲也」指山谷此語為戲筆。')],
  58: [('p-huang-ti','追慕',None)],
  59: [('p-huang-ti','追慕',None)],
  60: [('p-li-bai','追慕',None)],
  61: [('p-li-bai','追慕',None)],
  62: [('p-huang-ti','追慕',None)],
  63: [('p-du-fu','追慕','「可恨也」惜杜甫卒於耒水。')],
  64: [('p-li-bai','追慕',None)],
  65: [('p-li-bai','追慕',None)],
  66: [('p-su-shi','追慕',None)],
  67: [('p-li-bai','考订',None)],
  68: [('p-li-bai','追慕',None)],
  69: [('p-li-bai','追慕',None)],
  70: [('p-du-fu','追慕',None)],
  71: [('p-li-bai','追慕',None)],
  72: [('p-du-fu','追慕',None)],
  73: [('p-du-fu','追慕',None)],
  74: [('p-du-fu','考订',None)],
  75: [('p-du-fu','追慕',None)],
  76: [('p-li-bai','追慕',None)],
  77: [('p-su-shi','唱和','「丹元子即東坡先生與之醻唱者」——全庫首條唱和實例。')],
  78: [('p-huang-ti','纪其遗迹','《至喜亭記》由山谷書丹，亭在鄂州。')],
  79: [('p-huang-ti','考订',None)],
  80: [('p-li-bai','追慕',None)],
  82: [('p-huang-ti','追慕',None)],
  83: [('p-huang-ti','纪其遗迹',None)],
  84: [('p-huang-ti','纪其遗迹',None)],
  85: [('p-du-fu','纪其遗迹',None)],
  86: [('p-du-fu','纪其遗迹',None)],
  87: [('p-zhuge-liang','纪其遗迹','萬里橋因諸葛孔明送費祎使吳語得名。')],
  88: [('p-du-fu','追慕',None)],
  89: [('p-du-fu','考订',None)],
  90: [('p-du-fu','追慕',None)],
  91: [('p-huang-ti','考订',None)],
  92: [('p-huang-ti','考订','據山谷跋自署考其謫戎州時所書，non-追慕。')],
  93: [('p-du-fu','追慕',None)],
  94: [('p-su-shi','纪其遗迹','起文堂之名為東坡而設。')],
  95: [('p-huang-ti','纪其遗迹',None)],
  96: [('p-huang-ti','纪其遗迹','記山谷貶謫戎州（今敘州）之蹤；非祠碑，存疑可歸追慕。')],
  97: [('p-su-shi','纪其遗迹','後人取東坡語作載酒亭於淩雲山上。')],
  98: [('p-huang-ti','纪其遗迹',None)],
  99: [('p-huang-ti','追慕','「今不足道矣」為范成大之評，target=山谷，取其昔時所尚，存疑。')],
  100:[('p-huang-ti','纪其遗迹',None)],
  101:[('p-huang-ti','追慕','記山谷貶涪州別駕自號涪皤，非古蹟；rel 取追慕，存疑。')],
  102:[('p-huang-ti','纪其遗迹',None)],
  103:[('p-huang-ti','纪其遗迹','鎖江亭舊基、新亭並記；兼及山谷屢有鎖江亭詩。')],
  104:[('p-du-fu','追慕',None)],
  105:[('p-zhuge-liang','纪其遗迹','渡瀘亭；「竟不知諸葛孔明的從何處渡」含考訂語氣，主判紀遺跡。')],
  106:[('p-bai-juyi','纪其遗迹',None)],
  107:[('p-bai-juyi','纪其遗迹',None)],
  108:[('p-huang-ti','纪其遗迹','「山谷題字極稱許之」——既記山谷題字（跡）又稱許其事，存疑可歸追慕。')],
  109:[('p-du-fu','考订',None)],
  110:[('p-du-fu','追慕',None)],
  111:[('p-su-shi','纪其遗迹',None)],
  112:[('p-huang-ti','纪其遗迹',None)],
  113:[('p-su-shi','质疑',None)],
  114:[('p-su-shi','纪其遗迹',None)],
  115:[('p-su-shi','纪其遗迹',None)],
  116:[('p-su-shi','考订','「皆後人旁緣命之」——辨堂額/橋亭名非東坡舊物。')],
  117:[('p-yu-yan','纪其遗迹',None)],
  118:[('p-bai-juyi','纪其遗迹','寺東北隅新作白樂天草堂（非元和故處），存疑可歸追慕。')],
  119:[('p-bai-juyi','纪其遗迹','記樂天元和十年為州司馬時作堂香爐峰北之舊蹟。')],
  120:[('p-yu-yan','纪其遗迹',None)],
}
assert set(D) | set(SKIP) == set(range(121)), (set(range(121)) - set(D) - set(SKIP))

cands = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'candidates2.json'), encoding='utf-8'))
works = {w['id']: w for w in json.load(open(WORKS_J, encoding='utf-8'))}

QUOTE_SOURCE = {
    'w-shi-zhong-shan-ji': '石鐘山記（維基文庫繁體標點本）',
    'w-jin-shan-ye-xi': '金山夜戲（維基文庫繁體標點本，陶庵夢憶）',
    'w-ru-shu-ji': '入蜀記标点本（維基文庫·知不足齋叢書本系統）',
    'w-wu-chuan-lu': '吳船錄标点本（維基文庫·欽定四庫全書本二卷）',
}
PERSON_NAME = {p['id']: p['name'] for p in persons}

# special quote trim: drop the next-day entry tail that shares the sentence's final 。
TRIM = {100: '舊名東丁水，寺亦因名東丁院，山谷更名方響洞，題詩云：「古人名此東丁水，自古丁東直到今。我為更名方響洞，要知山水有清音。」'}

ij = os.path.join(BASE, 'intertexts.json')
intertexts = json.load(open(ij, encoding='utf-8'))
# Re-runnable: strip our own works-layer batch (and its CSV rows) before rebuild.
intertexts = [e for e in intertexts if not (e['id'] >= 'int-103' and e['source_table']=='works')]
assert len(intertexts) == 102 and intertexts[-1]['id'] == 'int-102'
nxt = 103
new = []
for idx, dec in D.items():
    c = cands[idx]
    quote = TRIM.get(idx, c['quote'])
    assert quote in works[c['wid']]['orig'], (idx, quote[:30])
    for target, rel, extra in dec:
        note = 'works 層原文提取；逐句判讀上下文。'
        if extra:
            note += extra
        e = {
            'id': 'int-%03d' % nxt,
            'source_table': 'works',
            'source_id': c['wid'],
            'target_person_id': target,
            'target_name': PERSON_NAME[target],
            'relation': rel,
            'quote': quote,
            'quote_source': QUOTE_SOURCE[c['wid']],
            'book': c['wid'],
            'note': note,
        }
        new.append(e)
        nxt += 1
intertexts.extend(new)
with open(ij, 'w', encoding='utf-8', newline='\n') as f:
    json.dump(intertexts, f, ensure_ascii=False, indent=2)
    f.write('\n')

ic = os.path.join(BASE, 'intertexts.csv')
with open(ic, encoding='utf-8-sig', newline='') as f:
    rows = list(csv.reader(f))
hdr = rows[0]
rows = [r for r in rows if not (r[0] >= 'int-103' and r[1] == 'works')]
assert len(rows) == 103, len(rows)
assert hdr == list(new[0].keys()), (hdr, list(new[0].keys()))
for e in new:
    rows.append([e[k] for k in hdr])
with open(ic, 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f, lineterminator='\r\n'); w.writerows(rows)

print('new intertexts:', len(new), 'ids int-103..int-%03d' % (nxt-1))
print('by target:', dict(collections.Counter(e['target_person_id'] for e in new)))
print('by relation:', dict(collections.Counter(e['relation'] for e in new)))
print('skipped false positives:', SKIP)
json.dump({'new': new, 'skip': {str(k): v for k, v in SKIP.items()},
           'decisions': {str(k): v for k, v in D.items()}},
          open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '_intertext_decisions.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=2)
