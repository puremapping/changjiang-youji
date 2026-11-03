# 数据模型 Schema v1 — 长江流域五人文选

> 项目转向后的事实基础：小组定五位作者（柳宗元、苏轼、陆游、范成大、张岱），
> 两个数据粒度（事件级 / 篇目级），三张基础表（时间 / 地名 / 人物），一张前贤链条表。
> 本文件是全部数据工作的**契约**：所有子 Agent 按此 schema 交付，主 session 按此验收。

---

## 0. 实体关系总览

```
persons 人物 ──────────┬── 作者 ──→ works 书/篇
                       └── 前贤 ←── intertexts 互文（附引文）
                                        ↑
works 书/篇 ──┬── 含 ──→ events 事件（事件级叶子）
              └── 本身即叙事单元（篇目级定性）

places 地名 ←── events.place / works.place
timeline 编年 ←── works 与 events 的时间锚点
```

**核心关系三条**：
1. **书（book）与篇（pian）是 works 表的两种记录**，用 `type` 字段区分。
2. **事件（events）是叶子**，通过 `source_type` + `source_id` 挂到书或篇下。
3. **互文（intertexts）是跨表连接**，一头是「谁在哪个文本里」，一头是「提到了谁/引了什么」，**每条必附引文**。

---

## 1. 字段命名与类型约定

- 字段名统一 snake_case 小写英文，值除明文外尽量用受控词表（枚举）。
- 时间字段三分：`year`（int，公元）、`month`（int 1-12，可空）、`day`（int 1-31，可空）。**能考到月日就写，考不到回退到年，再不行标「约」并写 `time_note`。**
- 原文字段一律繁体、一字不改，出处字段标注版本。
- `null` = 明确未考 / 原文无；`""` = 无此项。二者不许混用。
- 维度策略：**先收全，后期裁剪**。标注 `[核心]` 的必填，`[可选]` 的可后补。

---

## 2. 表 1：persons（人物表）

收录：五作者 + 所有被提及的前贤与同代人物。

| 字段 | 类型 | 说明 | 等级 |
|---|---|---|---|
| id | str | 主键，如 `p-su-shi` | 核心 |
| name | str | 姓名（繁体） | 核心 |
| name_alt | str[] | 别名/字号/谥号（东坡、子瞻、文忠…） | 核心 |
| dynasty | str | 朝代 | 核心 |
| birth | int | 生年（公元） | 核心 |
| death | int | 卒年（公元） | 核心 |
| role | enum | 作者 / 前贤 / 同代 | 核心 |
| native_place | str | 籍贯（古今对照，挂 places） | 可选 |
| bio_note | str | 一句话定位 | 可选 |
| note | str | 备注（生平争议等） | 可选 |

**去重纪律**：同一人的别名必须归一。例：`苏子瞻` `东坡居士` `苏轼` `东坡` 都是 `p-su-shi`。

---

## 3. 表 2：places（地名表）

| 字段 | 类型 | 说明 | 等级 |
|---|---|---|---|
| id | str | 主键，如 `pl-jin-shan` | 核心 |
| name_ancient | str | 古地名（繁体） | 核心 |
| name_modern | str | 今地名 | 核心 |
| alt_names | str[] | 其他古称/别名 | 可选 |
| basin | enum | 干流 / 支流 / 其他（区分长江干流与湘江等支流） | 核心 |
| lat | float | 纬度 | 可选 |
| lng | float | 经度 | 可选 |
| coord_conf | enum | exact / approx / unknown（**坐标置信度，宁缺勿猜**） | 核心 |
| type | enum | 州/县/山/寺/亭/矶/滩/江/湖/楼… | 可选 |
| note | str | 沿革备注 | 可选 |

**去重纪律**：同名异称归一。例：`金陵` `建康` `江宁` 同属一处。坐标未定的 `coord_conf=unknown`，绝不填近似值冒充精确。

---

## 4. 表 3：timeline（编年表）

收录：五作者生平关键节点 + 各篇写作时间。**统一公元年，原文纪日另存。**

| 字段 | 类型 | 说明 | 等级 |
|---|---|---|---|
| id | str | 主键 | 核心 |
| person_id | str | 挂 persons | 核心 |
| year | int | 公元年 | 核心 |
| month | int | 月（可空） | 核心 |
| day | int | 日（可空） | 核心 |
| date_orig | str | 原文纪日（如「乾道六年闰五月十八日」） | 核心 |
| event_type | enum | 生平大事 / 仕宦 / 贬谪 / 出游 / 写作 | 核心 |
| work_id | str | 关联 works（若是写作事件） | 可选 |
| note | str | 备注 | 可选 |

**跨 800 年（柳 805 → 张 1644）的时间轴，统一用公元年做基准。**

---

## 5. 表 4：works（书 / 篇目表）—— 篇目级主表

这是「叙事单元」的定性层。**书与篇都用这张表，`type` 区分。**

| 字段 | 类型 | 说明 | 等级 |
|---|---|---|---|
| id | str | 主键，如 `w-ru-shu-ji` / `w-chi-bi-fu` | 核心 |
| type | enum | book（书） / pian（篇） | 核心 |
| title | str | 书名或篇名（繁体） | 核心 |
| author_id | str | 挂 persons | 核心 |
| parent_id | str | 若为篇，挂所属书（可空） | 核心 |
| genre | enum | 日记体书 / 记游散文 / 赋 / 诗 / 小品 | 核心 |
| visit_year / visit_month / visit_day | int | **游览时间**（精确到月日，考不到回退） | 核心 |
| write_year / write_month / write_day | int | **成文时间**（与游时分离；行时记两值相等） | 核心 |
| date_orig | str | 原文纪日 | 可选 |
| place_id | str | 主地点（挂 places） | 核心 |
| situation | str | **写作处境**（贬谪/赴任/还乡/追忆亡国…） | 核心 |
| theme | str | 主旨（一句话） | 核心 |
| mood | enum | 情感基调（沉郁/明快/孤愤/追慕/旷达…） | 核心 |
| structure | str | 结构笔法（移步换景/托物言志/以论带叙/赋体问答…） | 可选 |
| imagery | str[] | 核心意象（水石/水月/金山/雪…） | 可选 |
| style | str | 风格特征 | 可选 |
| note | str | 备注 | 可选 |

> **注意**：「记了什么 / 不记什么」不单列为维度——那是分析结论，不是元数据。
> 若需要，在 `structure` 或 `note` 里用文字表述，不建字段。

---

## 6. 表 5：events（事件表）—— 事件级主表

这是「记录单元」的客观层。**日记体书拆成事件；单篇按叙事时间跨度决定抽几个事件。**

| 字段 | 类型 | 说明 | 等级 |
|---|---|---|---|
| id | str | 主键，如 `e-ru-001` | 核心 |
| source_type | enum | book / pian | 核心 |
| source_id | str | 挂 works | 核心 |
| person_id | str | 挂 persons（作者） | 核心 |
| year / month / day | int | 事件时间 | 核心 |
| date_orig | str | 原文纪日 | 可选 |
| place_id | str | 挂 places（可空） | 核心 |
| place_type | enum | 地名类型（州/县/山/寺/亭…） | 可选 |
| activity | enum[] | 行路/游观/交游/考订/风土/其他 | 核心 |
| landscape | enum[] | 所记景观：山水/古迹/城邑/祠庙/碑刻/市井 | 可选 |
| weather | enum[] | 晴/雨/风/雪/寒/暑 | 可选 |
| emotion | enum[] | 情感词：惊叹/追慕/孤寂/忧虑/旷达/怅惘 | 可选 |
| imagery | str[] | 物象/意象：月/舟/雪/梅花/石/水 | 可选 |
| orig | str | 原文全文（繁体，一字不改） | 核心 |
| note | str | 备注（日期推算来源等） | 可选 |

---

## 7. 表 6：intertexts（互文/典故/前贤提及表）—— **必附引文**

这是「前贤链条」的落点：谁在哪个文本里，提到了谁、引了什么，**原文怎么写的**。

| 字段 | 类型 | 说明 | 等级 |
|---|---|---|---|
| id | str | 主键 | 核心 |
| source_type | enum | work / event（在篇里还是事件里） | 核心 |
| source_id | str | 挂 works 或 events | 核心 |
| target_person_id | str | 被提及的前贤（挂 persons） | 核心 |
| relation | enum | 追慕 / 质疑 / 考订 / 唱和 / 纪其遗迹 | 核心 |
| quote | str | **引文原文（必附，繁体一字不改）** | 核心 |
| quote_source | str | 引文出处（原典版本） | 核心 |
| note | str | 备注 | 可选 |

**一条铁律：没有引文的互文记录无效。** 「提到苏轼」不够，必须写出「坡西竹林，古氏故物」或「东坡词赋微夸焉」这类原文。

---

## 8. 例：一条完整链路（演示三表怎么咬合）

```
persons:  p-lu-you（陆游,作者）  p-su-shi（苏轼,前贤）
works:    w-ru-shu-ji（入蜀记, book, 陆游, 1170）
events:   e-ru-083（source=w-ru-shu-ji, 八月十九日, place=pl-huang-zhou,
                     activity=[游观,考订], orig=「十九日早游东坡…坡西竹林…」）
intertexts:  source=event e-ru-083, target=p-su-shi, relation=追慕,
             quote=「坡西竹林，古氏故物，号南坡，今已残伐无几」, quote_source=四库本卷三
```

**这一条就同时回答了**：事件级（陆游八月十九到了黄州、游东坡）+ 篇目级（追慕苏轼）+ 前贤链条（引文为证）。

---

## 9. 版本与引用纪律

- 分析提取用**校注本**（典故、处境、地理沿革都在注释里）。
- 原文引用回**原典**核对，标注版本（四库本 / 渭南文集 / 柳河东集 / 苏轼文集 / 陶庵梦忆校本）。
- 五位作者的权威校注本，另列 `REFERENCES.md`（不写进 schema）。

---

*本 schema 由 jiya 整理，2026-11-03。v1，待小组确认后冻结。*
