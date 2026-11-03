# -*- coding: utf-8 -*-
"""persons + sources 基础表生成器。
纪律：坐标/生卒不推断——生卒不确定写 null + note 说明；
人物只收有明确称谓/姓名的，不推断身份。
输出 JSON（UTF-8 无 BOM）+ CSV（UTF-8-BOM），CSV 与 JSON 逐字段一致。
"""
import io, os, json, csv
HERE = os.path.dirname(os.path.abspath(__file__))

def dump(table, name):
    jp = os.path.join(HERE, name + '.json')
    io.open(jp, 'w', encoding='utf-8', newline='\n').write(
        json.dumps(table, ensure_ascii=False, indent=2) + '\n')
    cp = os.path.join(HERE, name + '.csv')
    with io.open(cp, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(list(table[0].keys()))
        for row in table:
            w.writerow([
                ('|'.join(v) if isinstance(v, list) else (v if v is not None else ''))
                for v in row.values()])
    print('%s: %d 条 -> %s / %s' % (name, len(table), jp, cp))

# ============================================================ persons
# 字段（按任务书）：id / name / dynasty / birth_year / death_year / note
# 生卒不确定写 null + note 说明存疑依据；不推断身份。
PERSONS = [
    # —— 5 作者（生卒取自 REFERENCES.md，确定值）——
    {'id': 'p-lu-you', 'name': '陸游', 'dynasty': '南宋', 'birth_year': 1125,
     'death_year': 1210, 'note': '作者。字務觀，號放翁，世稱陸放翁。入蜀記作者；淳熙五年（1178）入蜀赴職。'},
    {'id': 'p-fan-chengda', 'name': '范成大', 'dynasty': '南宋', 'birth_year': 1126,
     'death_year': 1193, 'note': '作者。字希文，號石湖居士。吳船錄作者；淳熙丁酉（1177）自成都東歸記。'},
    {'id': 'p-liu-zong-yuan', 'name': '柳宗元', 'dynasty': '唐', 'birth_year': 773,
     'death_year': 819, 'note': '作者。字子厚，謚文，世稱柳柳州。永州八記、游黃溪記作者，永州司馬任上。'},
    {'id': 'p-su-shi', 'name': '蘇軾', 'dynasty': '北宋', 'birth_year': 1037,
     'death_year': 1101, 'note': '作者。字子瞻，號東坡居士，謚文忠。赤壁賦、后赤壁賦、石鐘山記（文）與游金山寺（詩）作者。'},
    {'id': 'p-zhang-dai', 'name': '張岱', 'dynasty': '明末', 'birth_year': 1597,
     'death_year': 1679, 'note': '作者。字宗子，號陶庵，別號蝶夢園客。金山夜戲、金山競渡作者；明亡後追憶之筆（記時≠寫時，見 REFERENCES §5）。'},

    # —— 同代人物（書中有明確姓名/官職，不推断身份；生卒未考一律 null+note）——
    # 入蜀記・陸游同路/交游
    {'id': 'p-xu-weizheng', 'name': '徐稙', 'dynasty': '南宋', 'birth_year': None, 'death_year': None,
     'note': '同代，入蜀記（吳）卷。官階「檢正」「檢校」，招飲。字未明，生卒未考。'},
    {'id': 'p-ye-mengxi', 'name': '葉夢錫', 'dynasty': '南宋', 'birth_year': None, 'death_year': None,
     'note': '同代，入蜀記巻一。「葉夢錫侍郎衡」（衡，字），招飲。生卒未考。'},
    {'id': 'p-rui-cheng', 'name': '芮偁', 'dynasty': '南宋', 'birth_year': None, 'death_year': None,
     'note': '同代，入蜀記巻一。「芮國器司業曄」（曄，字），招飲。生卒未考。'},
    {'id': 'p-zhan-daozi', 'name': '詹大著', 'dynasty': '南宋', 'birth_year': None, 'death_year': None,
     'note': '同代，入蜀記巻一。「詹道子大著亢宗」，同集。生卒未考。'},
    {'id': 'p-zhang-shuqian', 'name': '張叔潛', 'dynasty': '南宋', 'birth_year': None, 'death_year': None,
     'note': '同代，入蜀記巻一。「張叔潛編修淵」（淵，字）。生卒未考。'},
    {'id': 'p-ge-xun', 'name': '葛郇', 'dynasty': '南宋', 'birth_year': None, 'death_year': None,
     'note': '同代，入蜀記巻三。官階「右奉議郎簽書節度判官廳公事」「觀察推官右文林郎」。生卒未考。'},
    {'id': 'p-xu-wuzi', 'name': '徐務滋', 'dynasty': '南宋', 'birth_year': None, 'death_year': None,
     'note': '同代，入蜀記巻三。「觀察推官右文林郎徐務滋」。生卒未考。'},
    # 吳船録・范成大同代同僚/幕客/前賢
    {'id': 'p-ge-jing', 'name': '葛郇', 'dynasty': '南宋', 'birth_year': None, 'death_year': None,
     'note': '同代，吳船錄巻上。「觀察推官葛郇」，眉州。生卒未考。'},
    {'id': 'p-chen-liang', 'name': '陳亮', 'dynasty': '南宋', 'birth_year': 1143, 'death_year': 1195,
     'note': '同代，吳船錄前賢。「正仲」即何正仲（陳亮字同甫，與范成大同年？原文「何正仲」存疑，此条仅记陈亮为参照，范同行者存疑不立）——存疑占位，待核。'},
    {'id': 'p-he-zhengzhong', 'name': '何正仲', 'dynasty': '南宋', 'birth_year': None, 'death_year': None,
     'note': '同代，吳船錄巻上（眉州）。「何正仲子方來見」，范成大同年/同僚。生卒未考。'},
    {'id': 'p-wang-kang', 'name': '王亢', 'dynasty': '南宋', 'birth_year': None, 'death_year': None,
     'note': '同代，吳船錄巻上。「嘉守王亢子蒼」，嘉州守，留看月榭（月榭為前權守陸遊所作）。生卒未考。'},
    {'id': 'p-ma-jun', 'name': '馬騏', 'dynasty': '南宋', 'birth_year': None, 'death_year': None,
     'note': '同代，吳船錄巻上。「瀘帥馬騏德駿」，瀘州帥。生卒未考。'},
    {'id': 'p-chao-gongwu', 'name': '晁公武', 'dynasty': '南宋', 'birth_year': None, 'death_year': None,
     'note': '同代，吳船錄巻上。「前帥晁公武子止」，作南定樓（瀘州）。生卒未考。'},
    {'id': 'p-xin-qixi', 'name': '辛棄疾', 'dynasty': '南宋', 'birth_year': 1140, 'death_year': 1207,
     'note': '同代，吳船錄巻下。「江陵帥辛棄疾幼安」，招遊渚官。生卒 1140–1207（通行，存疑未逐字核年譜）。'},
    {'id': 'p-caoxun', 'name': '曹訓', 'dynasty': '南宋', 'birth_year': None, 'death_year': None,
     'note': '同代，吳船錄巻下。「前守曹訓子序」，新作琵琶亭（江州）。生卒未考。'},
    {'id': 'p-lu-shengji', 'name': '呂勝己', 'dynasty': '南宋', 'birth_year': None, 'death_year': None,
     'note': '同代，吳船錄巻下。「通判呂勝己」，隸書《琵琶行》。生卒未考。'},
    {'id': 'p-pan-bolong', 'name': '潘伯龍', 'dynasty': '南宋', 'birth_year': None, 'death_year': None,
     'note': '同代，吳船錄巻下。「郡守潘慈明伯龍」，新作周先生祠堂（江州濂溪）。生卒未考。'},
    {'id': 'p-liu-gonghu', 'name': '劉恭父', 'dynasty': '南宋', 'birth_year': None, 'death_year': None,
     'note': '同代，吳船錄巻下。「見知府資政殿學士劉恭父珙」，荊南（荊門）。生卒未考。'},
    {'id': 'p-hu-yuanzhi', 'name': '胡元質', 'dynasty': '南宋', 'birth_year': None, 'death_year': None,
     'note': '同代，吳船錄幕客（v003 人工核）。生卒未考。'},
    {'id': 'p-hu-changwen', 'name': '胡長文', 'dynasty': '南宋', 'birth_year': None, 'death_year': None,
     'note': '同代，吳船錄幕客。「長文自峽山陸行」（帰州），固留范成大。生卒未考。'},
    # —— 前賢（書中引稱的已故/前代人物；生卒確定者填，未考者 null）——
    {'id': 'p-du-fu', 'name': '杜甫', 'dynasty': '唐', 'birth_year': 712, 'death_year': 770,
     'note': '前賢，吳船錄巻上引「杜子美」（西川供客句）。生卒 712–770。'},
    {'id': 'p-li-bai', 'name': '李白', 'dynasty': '唐', 'birth_year': 701, 'death_year': 762,
     'note': '前賢，吳船錄巻下引「李太白」（峨眉山月句）；入蜀記亦引。生卒 701–762（一說 701）。'},
    {'id': 'p-huang-ti', 'name': '黃庭堅', 'dynasty': '北宋', 'birth_year': 1045, 'death_year': 1105,
     'note': '前賢，吳船錄引「山谷」「涪翁」（涪翁亭、山谷所名）。生卒 1045–1105。'},
    {'id': 'p-bai-juyi', 'name': '白居易', 'dynasty': '唐', 'birth_year': 772, 'death_year': 846,
     'note': '前賢，吳船錄忠州「荔枝樓，樂天所種」、四賢閣「白居易像」。生卒 772–846。'},
    {'id': 'p-zhuge-liang', 'name': '諸葛亮', 'dynasty': '蜀漢', 'birth_year': 181, 'death_year': 234,
     'note': '前賢，吳船錄夔州「八陣在水中」（瞿唐）。生卒 181–234。'},
    {'id': 'p-li-bing', 'name': '李冰', 'dynasty': '秦', 'birth_year': None, 'death_year': None,
     'note': '前賢，吳船錄「離堆」「李冰父子廟」（都江癏）。生卒不詳（約前256–前191年任蜀守，未逐字核，不填）。'},
    {'id': 'p-yu-yan', 'name': '顏真卿', 'dynasty': '唐', 'birth_year': 709, 'death_year': 784,
     'note': '前賢，吳船錄巻下「永泰丙午，真卿佐吉州」（九華/太平）。生卒 709–784。'},
    {'id': 'p-cai-wenji', 'name': '蔡文姬', 'dynasty': '漢', 'birth_year': None, 'death_year': None,
     'note': '存疑占位：原文若有「文姬」引，須核是蔡琰抑或他，暂不立实条。待核后删。'},
]

# ============================================================ sources
# 字段（按任务书）：id / title / author_id / edition / holding / note
# 版本信息取自 REFERENCES.md + source/text 实际文件（不编造）
SOURCES = [
    # —— 柳宗元 9 篇（记游散文 + 游黄溪记）——
    {'id': 'src-liu-zong-yuan-wg', 'title': '柳宗元 永州八記・游黃溪記（9篇）', 'author_id': 'p-liu-zong-yuan',
     'edition': '維基文庫（繁體標點本）；校註底本：尹占華、韓文奇《柳宗元集校註》中華書局 2013',
     'holding': 'source/text/柳宗元_*.md（9件）；校註抽自 source/annotated/柳宗元_*_注释.md',
     'note': '主校注本尹占华本；通行吴文治点校本中华书局1979。引用须标本子。'},
    # —— 苏轼 4 篇 ——
    {'id': 'src-su-shi-wj', 'title': '蘇軾 赤壁賦/后赤壁賦/石鐘山記（文3篇）', 'author_id': 'p-su-shi',
     'edition': '維基文庫（繁體標點本）；校註底本：孔凡禮《蘇軾文集》中華書局 1986',
     'holding': 'source/text/蘇軾_赤壁賦/后赤壁賦/石鐘山記.md',
     'note': '孔凡礼本无文字层，注释改用 ctext《古文观止》古注+施元之《施註蘇詩》；诗/文分家。'},
    {'id': 'src-su-shi-shi', 'title': '蘇軾 游金山寺（七言古詩）', 'author_id': 'p-su-shi',
     'edition': '維基文庫（繁體標點本）；校註底本：王文誥輯注、孔凡禮《蘇軾詩集》中華書局 1982',
     'holding': 'source/text/蘇軾_遊金山寺.md',
     'note': '游金山寺为诗（苏轼诗集），非赋。'},
    # —— 张岱 2 篇 ——
    {'id': 'src-zhang-dai-wg', 'title': '張岱 金山夜戲（卷一）/金山競渡（卷五）', 'author_id': 'p-zhang-dai',
     'edition': '維基文庫（繁體標點本）；校註底本：夏鹹淳《陶庵夢憶（譯註）》上海古籍 2001',
     'holding': 'source/text/張岱_金山夜戲/金山競渡.md',
     'note': '夏咸淳本 PDF 文字层损坏（乱码），注释改用网络公开权威注本整合（国学吧等），非逐字转录；记时≠写时。'},
    # —— 陆游 入蜀记 ——
    {'id': 'src-lu-you-wg', 'title': '陸游 入蜀記（卷1~6）', 'author_id': 'p-lu-you',
     'edition': '維基文庫 知不足斋叢書本系統（有標點繁體）；校註底本：朱迎平《入蜀記・吳船錄譯註》上海古籍 2024；校註本：蔣方《入蜀記校註》湖北人民 2004',
     'holding': 'source/text/陸游_入蜀記.md（32,912 字符）；譯注 source/annotated/陸游_入蜀記_譯注全本.md',
     'note': '四库本书前提要作「四卷」、总目作「六卷」、渭南文集本占卷四十三–四十八；引用须带本子。'},
    # —— 范成大 吴船录 ——
    {'id': 'src-fan-chengda-wg', 'title': '范成大 吳船錄（卷上/下）', 'author_id': 'p-fan-chengda',
     'edition': '維基文庫 欽定四庫全書本（二卷，有標點）；校註底本：朱迎平《入蜀記・吳船錄譯註》上海古籍 2024；校註本：孔凡禮《范成大筆記六種》中華書局 2012',
     'holding': 'source/text/范成大_吳船錄.md（21,343 字符）；譯注 source/annotated/范成大_吳船錄_譯注全本.md',
     'note': '吴船录四库本本身即有标点；干支纪日已全部转序数日（v003）。'},
]

if __name__ == '__main__':
    dump(PERSONS, 'persons')
    dump(SOURCES, 'sources')
