# WORKLOG B/C/D — 2026-11-22

> 独立文件，避免与任务 A（237 null 坐标，另一进程独占）共写 WORKLOG。
> 工作目录：`D:\fs\workspace\projects\changjiang-youji`

## B 同名异地拆分

- **查了什么源**：`data/base/places.json`（379 条）、`data/events_v2/入蜀記_events.json`（156 条）、`吳船錄_events.json`（110 条）的全部 `orig`/`place`/`place_all`/`place_waypoint`/`place_departed`/`place_id` 字段；`source/text/陸游_入蜀記.md`、`source/text/范成大_吳船錄.md`；`source/pdf/PIANMU_LOCATIONS.md`、`data/base/gen_places.py`、`data/base/backfill.py`（确认 place_id 生成机制）。
- **做了什么**：
  - 拆 3 组，新增 4 个实例条目：`pl-東坡-黃州`（RSC-089、WCL-073 双证）、`pl-東坡-蘇州`（无直接地望事件，留 null 待考）、`pl-西山-忠州`（WCL-041「甲寅早遊西山。萬有西山及岑公洞」+ 前日忠州→萬州行程）、`pl-西山-建康`（建康段无「西山」地望事件，留 null 待考）。
  - 改 3 组原条目的 note 为分流指南；`pl-xi-shan` note 补明永州系与建康/忠州系互不混指。
  - events 的 place_id 引用改写 **0 处**（两书从未以这三个 id 作为 place_id，全部是 backfill 由中文 place 映射）。
- **条数**：places 379→**383**（+4）。悬空 FK **0**（新增条目均为有效独立 id，works 的 `pl-xi-shan` 引用未动）。
- **仍缺**：蘇州東坡、建康西山的精确坐标（留 null + note 待考）；两书原文未出现可锚定的直接游历事件。
- **未碰**：237 条 null 坐标字段一字未动（任务 A 独占）；写入前对全表 lat/lon 做快照，写入后逐条比对一致。

## C intertexts 102 条 relation 复核

- **查了什么源**：`data/base/intertexts.json` 102 条的 source_id → 两本 events 的完整 `orig` 上下文（本地文件，C 部全程离线可查）；quote 连续子串校验 102/102 通过（程序逐条 `quote in orig`）。
- **做了什么**：按 SCHEMA §7 enum（追慕/质疑/考订/唱和/纪其遗迹）+ 文中显性判据词逐条判读；只改 relation 与 note，quote 一字未改。
- **改动数**：**13 条 relation 改写**（int-001/010/031/032/035/041/054/064/071/072/074 → 考订；int-053/061 → 追慕），均附裁定理由 note；**8 条存疑**（int-029/037/060/073/079/084/091 追加通用存疑语；int-066 特别标注「山谷」为普通名词、疑关键词误匹配），relation 保留原值。
- **仍缺**：「质疑」「唱和」两类本批 0 条（原文无符合者，不是漏判）；8 条存疑若需定论须回到每条的卷次/地望/作者语气作更细辨，本轮按纪律保留。
- **同步**：intertexts.json 102 条、intertexts.csv 102 行（UTF-8 BOM + CRLF）一致。

## D works 层互文

- **查了什么源**：`data/works_v1/works.json` 17 篇全字段（style/theme/structure/note/imagery）；`SCHEMA.md` §7、§9；维基百科「陶渊明」「谢灵运」「扬雄」「司马相如」条查生卒。
- **做了什么**：找出候选 5 处，逐一判性质；结论 **不建 intertexts 条目**——「鎔陶謝之詩、揚馬之賦為一鑪（高步瀛引李剛己）」及「王應麟疑倣太史公」「善學莊子（沈德潛）」「蘇軾評『紛紅駭綠』」等均为**后人评语/接受史材料**，作者本人未引、未追慕、未考订这些前贤；建条目等于把批评者声音冒充作品作者，且 quote_source 不属于 SCHEMA §9 原典版本，会污染引文校验链。任务书 D 允许此分支，已在 METHOD_BCD 写明理由。
- **条数**：0 条新增；persons 未增（四项生卒仅备查记于 METHOD，不落库）。
- **仍缺**：无（不建即结案）。

---

## 自检

| 项目 | 结果 |
|---|---|
| B 拆分组数 | 3 组（東坡／西山／xi-shan） |
| B 新增实例 | 4 条（pl-東坡-黃州、pl-東坡-蘇州、pl-西山-建康、pl-西山-忠州） |
| B events place_id 改写 | 0 处（原数据无引用，已逐字段核实） |
| B 悬空 FK | 0（places 383 条，works 的 pl-xi-shan 引用有效） |
| C relation 改写 | 13 条 |
| C 存疑 | 8 条 |
| C quote 连续子串 | 102/102 通过（原文一字未改） |
| D 结论 | 不建（works 层评语型引用非作者自述），0 条新增 |
| CSV BOM + 行数 | places 383/383、intertexts 102/102、persons 32/32（未改），均 UTF-8 BOM + CRLF |
| 237 null 坐标 | 未触碰（写入前后全表坐标快照一致） |

## 交付文件

- 改动：`data/base/places.json` / `places.csv`（+4 实例，3 note）、`data/base/intertexts.json` / `intertexts.csv`（13 relation + note 修订，8 存疑标注）
- 新增：`data/base/METHOD_BCD_20261122.md`、`data/base/WORKLOG_BCD_20261122.md`
- 未改动：`data/base/persons.json/csv`、`data/works_v1/works.json/csv`、`data/events_v2/*`（B 无改写对象，C 只引原文）、`data/base/METHOD.md`、`data/base/WORKLOG_20261122.md`（与 A 进程隔离）、`data/events_v2/METHOD.md`
