# 确定性全量审计报告

判据数 19，失败 0。

| 判据 | 结果 | 说明 |
|---|---|---|
| 八表条数 | PASS | 156/110/17/383/34/6/34/223 |
| events.orig 连续子串(266) | PASS | 越界0 [] |
| works.orig 连续子串(17) | PASS | 越界0 [] |
| intertexts.quote 连续子串(223) | PASS | 越界0 [] |
| 外键悬空=0 | PASS | 0 [] |
| 坐标无半null | PASS | 0 [] |
| 坐标全在中国范围 | PASS | 0 [] |
| intertexts id 连续(允许int-066作废缺号) | PASS | 条数223 缺号{'int-066'} |
| events id 连续 | PASS |  |
| persons id 无重复 | PASS | 重复[] |
| relation 全在枚举内 | PASS | 0 [] |
| CSV works.csv | PASS | rows=17 json=17 |
| CSV intertexts.csv | PASS | rows=223 json=223 |
| CSV persons.csv | PASS | rows=34 json=34 |
| CSV places.csv | PASS | rows=383 json=383 |
| CSV sources.csv | PASS | rows=6 json=6 |
| CSV timeline.csv | PASS | rows=34 json=34 |
| CSV 入蜀記_events.csv | PASS | rows=156 json=156 |
| CSV 吳船錄_events.csv | PASS | rows=110 json=110 |
