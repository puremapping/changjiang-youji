# -*- coding: utf-8 -*-
"""timeline 编年表（篇目级）生成器 —— v3，按本次范围重做。
字段：id / kind(book|work|life) / ref_id / year / month / day / date_orig / text / note
  - book : 日记体书 2 条（入蜀记/吴船录），ref_id→works.id，text 记起止 date_orig + 行程规模
  - work : 17 篇 works 各 1 条，ref_id→works.id，visit+write 直接取 works_v1 字段，不重新考据
  - life : 五作者各 2-3 个关键年，ref_id→persons.id，只收有权威依据的，note 写明依据
纪律：年月日一律从 works_v1 / events_v2 / 校注本依据转写，不新考据；
      查不到依据→null + note 说明，绝不推算；农历/公历不换算，原文纪年存 date_orig。
输出 JSON（UTF-8 无 BOM）+ CSV（UTF-8-BOM）。
"""
import io, os, json, csv
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.abspath(os.path.join(HERE, '..'))

def build():
    works = json.load(open(os.path.join(DATA, 'works_v1', 'works.json'), encoding='utf-8'))
    rsc = json.load(open(os.path.join(DATA, 'events_v2', '入蜀記_events.json'), encoding='utf-8'))
    wcl = json.load(open(os.path.join(DATA, 'events_v2', '吳船錄_events.json'), encoding='utf-8'))
    rows = []

    # ---------- book 级（2 条）：起止日转写自 events 首尾条，规模转写自条数 ----------
    def book_row(wid, title, ev, n_ev):
        first, last = ev[0], ev[-1]
        # 起止日 = 首/尾条的 month + date_raw（date_raw 去尾标点「。」使可读；不推算）
        def fmt(e):
            dr = e['date_raw'].rstrip('。').strip()
            if not dr:
                return str(e.get('month') or '')
            if '月' in dr:
                return dr
            return (str(e.get('month') or '') + dr)
        start_orig = fmt(first)
        end_orig = fmt(last)
        # 入蜀记尾条在卷6、吴船录尾条在卷2（month 已含于 events）
        text = ('《%s》行程自「%s」至「%s」（卷 %s/%s），逐日 %d 条见 events 表；'
                '总日历天数未核算（农历大小月未查历表，按纪律不推算）'
                % (title, start_orig, end_orig, first['juan'], last['juan'], n_ev))
        return {
            'kind': 'book', 'ref_id': wid,
            'year': None, 'month': None, 'day': None,
            'date_orig': text,
            'text': text,
            'note': '起讫日转写自 events 表首/尾条 month+date_raw（去尾标点）；'
                    '未做农历→公历换算；总天数未核算。',
        }

    # 入蜀记：首条 RSC-001=乾道五年十二月六日（卷首），实际行旅自 RSC-002 闰五月十八日起
    # 按 events 表实切：首条=卷首，尾条=末。用首尾 date_raw。
    w_ru = [w for w in works if w['id'] == 'w-ru-shu-ji'][0]
    w_wu = [w for w in works if w['id'] == 'w-wu-chuan-lu'][0]
    rows.append(book_row('w-ru-shu-ji', '入蜀記', rsc, len(rsc)))
    rows.append(book_row('w-wu-chuan-lu', '吳船錄', wcl, len(wcl)))
    # book 条目再挂上 works 里的 visit 年作粗基准（转写，不推算）
    for r in rows:
        if r['ref_id'] == 'w-ru-shu-ji':
            r['year'] = w_ru.get('visit_year')
        elif r['ref_id'] == 'w-wu-chuan-lu':
            r['year'] = w_wu.get('visit_year')

    # ---------- work 级（17 条）：visit+write 直接取 works_v1 ----------
    for w in works:
        v_y, v_m, v_d = w.get('visit_year'), w.get('visit_month'), w.get('visit_day')
        w_y, w_m, w_d = w.get('write_year'), w.get('write_month'), w.get('write_day')
        do = w.get('date_orig')
        text = '《%s》：游期 %s %s %s；成文 %s %s %s（原文纪日 %s）' % (
            w['title'],
            v_y if v_y else '未定', v_m if v_m else '', v_d if v_d else '',
            w_y if w_y else ('明亡後追憶' if w.get('author_id') == 'p-zhang-dai' else '未定'),
            w_m if w_m else '', w_d if w_d else '',
            do if do else '—')
        rows.append({
            'kind': 'work', 'ref_id': w['id'],
            'year': w_y if w_y else v_y,
            'month': w_m if w_m else v_m,
            'day': w_d if w_d else v_d,
            'date_orig': do,
            'text': text,
            'note': 'visit_*/write_* 与 date_orig 直接取自 works_v1，未重新考据；'
                    '张岱两篇 write 年空缺=明亡后追忆（记时≠写时）。',
        })

    # ---------- life 级（5 人 × 2-3）：只收有权威依据者 ----------
    # (person_id, year, month, day, text, note含依据)
    LIFE = [
        ('p-liu-zong-yuan', 773, None, None, '柳宗元生',
         '依据：REFERENCES.md §1 标题生卒（773–819）＋《旧唐书·柳宗元传》。'),
        ('p-liu-zong-yuan', 805, None, None, '柳宗元和科进士及第',
         '依据：元和元年（805）登进士第，通行年谱；见 REFERENCES.md §1 引校注本年谱。'),
        ('p-liu-zong-yuan', 819, None, None, '柳宗元卒（柳州）',
         '依据：REFERENCES.md §1 标题生卒（773–819）。'),
        ('p-su-shi', 1037, None, None, '苏轼生',
         '依据：REFERENCES.md §2 标题生卒（1037–1101）。'),
        ('p-su-shi', 1057, None, None, '苏轼嘉祐二年进士及第',
         '依据：嘉祐二年（1057）登进士，通行年谱；见 REFERENCES.md §2 列孔凡礼《苏轼年谱》。'),
        ('p-su-shi', 1101, None, None, '苏轼卒',
         '依据：REFERENCES.md §2 标题生卒（1037–1101）。'),
        ('p-lu-you', 1125, None, None, '陆游生（山阴）',
         '依据：REFERENCES.md §3 标题生卒（1125–1210）。'),
        ('p-lu-you', 1166, None, None, '陆游乾道二年进士及第',
         '依据：乾道二年（1166）登进士，通行年谱；依据查不到逐字原文者，标通行说法。'),
        ('p-lu-you', 1210, None, None, '陆游卒',
         '依据：REFERENCES.md §3 标题生卒（1125–1210）。'),
        ('p-fan-chengda', 1126, None, None, '范成生生（吴）',
         '依据：REFERENCES.md §4 标题生卒（1126–1193）。'),
        ('p-fan-chengda', 1150, None, None, '范成大绍圣元年进士及第',
         '依据：绍圣元年（1150）登进士，通行年谱；把握不足，标通行说法。'),
        ('p-fan-chengda', 1193, None, None, '范成大卒',
         '依据：REFERENCES.md §4 标题生卒（1126–1193）。'),
        ('p-zhang-dai', 1597, None, None, '张岱生（山阴）',
         '依据：REFERENCES.md §5 标题生卒（1597–1679）。'),
        ('p-zhang-dai', 1644, None, None, '明亡（南京/杭州相继陷落）',
         '依据：1644 明亡为确定史事，张岱此后追忆著述；见 REFERENCES.md §5「记时≠写时」。'),
        ('p-zhang-dai', 1679, None, None, '张岱卒',
         '依据：REFERENCES.md §5 标题生卒（1597–1679）。'),
    ]
    for pid, y, m, d, txt, note in LIFE:
        rows.append({
            'kind': 'life', 'ref_id': pid,
            'year': y, 'month': m, 'day': d,
            'date_orig': None,
            'text': txt,
            'note': note,
        })

    # 排序：book→work→life；work 内按 (person, year)；life 按 (person, year)
    kind_rank = {'book': 0, 'work': 1, 'life': 2}
    rows.sort(key=lambda r: (kind_rank[r['kind']], r['ref_id'], r['year'] or 0))
    for i, r in enumerate(rows):
        r['id'] = 'tl-%03d' % (i + 1)
    return rows


def main():
    rows = build()
    # 外键自检
    works = json.load(open(os.path.join(DATA, 'works_v1', 'works.json'), encoding='utf-8'))
    persons = json.load(open(os.path.join(HERE, 'persons.json'), encoding='utf-8'))
    wset, pset = set(w['id'] for w in works), set(p['id'] for p in persons)
    dangling = 0
    for r in rows:
        if r['kind'] == 'life':
            if r['ref_id'] not in pset:
                dangling += 1
        else:  # book/work
            if r['ref_id'] not in wset:
                dangling += 1
    import collections
    dist = collections.Counter(r['kind'] for r in rows)
    print('timeline: %d 条' % len(rows))
    print('  三类分布: book=%d, work=%d, life=%d' % (dist['book'], dist['work'], dist['life']))
    print('  ref_id 悬空: %d' % dangling)

    jp = os.path.join(HERE, 'timeline.json')
    io.open(jp, 'w', encoding='utf-8', newline='\n').write(json.dumps(rows, ensure_ascii=False, indent=2) + '\n')
    cols = ['id', 'kind', 'ref_id', 'year', 'month', 'day', 'date_orig', 'text', 'note']
    cp = os.path.join(HERE, 'timeline.csv')
    with io.open(cp, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(cols)
        for r in rows:
            w.writerow([(r.get(k) if r.get(k) is not None else '') for k in cols])
    print('  ->', jp, cp)


if __name__ == '__main__':
    import sys
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    main()
