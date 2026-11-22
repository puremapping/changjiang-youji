# 可视化方法调研 —— 课堂分享延伸

> 整理：2026-11-22
> 触发：组员提供《课堂分享.pdf》文字纪要（陈思明，复旦 FDU-VIS），点名要查 InfoAlign、信达雅五环评测、CohortVA，以及历史人物可视化方向的 LifeMountains、OldVis、BioVistory、HoagsOLife。
> 方法：PDF 纪要 + 网上检索（arXiv / 期刊页 / 会议页 / 实验室主页）交叉核对。
> 标注约定：**[已核实]** = 找到论文/官方页；**[推断]** = 名称对不上，按线索匹配，未确证。

---

## 总览：这七个工作属于同一个体系

它们几乎都出自**陈思明（复旦大数据学院 FDU-VIS）及其合作者**（曹楠-同济、屈华民-港科大等）。课堂分享本身就是这个组的方法综述。所以这不是七个孤立工具，是一条完整链条：

```
分析 → 叙事生成 → 人文应用 → 评测
LightVA/ProactiveVA → Narrative Player/InfoAlign → CohortVA/LifeMountains/BioVistory/HoagsOLife → 信达雅五环
```

我们的项目（五人文选、两条粒度、展板可视化）落在**人文应用 + 叙事生成 + 评测**三块，下面按对项目的用处排序。

---

## 1. InfoAlign —— 最该深挖（[已核实] CHI 2026）

- 论文：*InfoAlign: A Human-AI Co-Creation System for Storytelling with Infographics*，Jielin Feng, Xinwu Ye, …, Yun Wang, Siming Chen*，CHI 2026
- arXiv：2602.22901；微软研究院页面、FDU-VIS 出版物页均收录

**核心**：把长文本组织成信息图，创作拆成三个可改的决定——**讲什么 / 用什么表达 / 怎样排在一页**；对应「组织内容（长文本拆片段单元）→ 选择视觉表达（图表/图标/强调）→ 安排版面（层次与阅读顺序）」。关键主张：**生成以后内容与版面都能改**，且全过程要保持 story consistency（三个研究问题 RQ1/RQ2/RQ3 全在问「一致性」）。

**对我们的用处（直接对口）**：我们现在手里就是一堆长文本（17 篇的处境/主旨/意象/情绪 + 266 天原文），要变成一张展板。InfoAlign 给了可操作的三步拆解，而且「生成后可改」正好匹配我们「数据先行、视觉后置」的分层结构。

---

## 2. 信达雅五环评测 —— 给了数据纪律一个理论名分（部分已核实）

**课堂 PDF 的表述**：五环翻译链 = **数据之信、表达之信、足、达、雅**；核心论点是「别让基准从『人看懂了吗』滑向『数值对上了吗』——更好测，但不是最重要的」。覆盖图显示「足」整行空白，「表达之信、达、雅」的元素与关系层几乎没人做。

**[已核实] 相关基准**：
- **VisJudge-Bench**（arXiv 2510.22373，ICLR 2026，港科广）：第一个评测多模态大模型评估可视化美学/质量的基准，3090 个专家标注样本、32 种图表类型。框架是 **Fidelity / Expressiveness / Aesthetics**（正好对应信/达/雅）。关键数字：GPT-5 与人类评分相关系数仅 **0.428**、MAE 0.553；他们训练的 VisJudge 把一致性提到 0.687。
- ChartBench（清华 + 上海 AI Lab）：图表描述的 Faithfulness / Expressiveness / Aesthetics 三维。
- 课堂 PDF 另提到 ChartQA 系、VisEval、ChartInsighter（时序摘要幻觉率 0.39）、DataReel（执行失败率上限 39.8%）、Misviz（12 类误导手法）、DVBench。

**[未独立核实]**：「五环」（尤其「足」这一环）作为完整框架，网上没搜到独立论文，目前只见于课堂 PDF。不要当成已发表成果引用，只能说「课堂材料提出的框架」。

**对我们的用处**：我们守的三条纪律（原文一字不改 / 查不到留空 / 错误留痕）就是「数据之信」。这套框架能写进汇报当方法论依据，也能当展板自检表——比自说自话「我们很严谨」有力。

---

## 3. CohortVA —— 方法上与我们同构（[已核实] VIS 2022 / TVCG）

- 论文：*CohortVA: A Visual Analytic System for Interactive Exploration of Cohorts based on Historical Data*，Wei Zhang, Jason K. Wong, …, Siming Chen, Wei Chen
- arXiv 2208.09237；IEEE VIS 2022；TVCG vol.29 no.1 pp.756-766，DOI 10.1109/TVCG.2022.3209483

**核心**：历史研究中的「群体分析」（prosopography）。用预建知识图谱生成**候选群体**，历史学者**逐步核对与调整**。四个组件：范围设定 → 候选群体与特征 → 多角度验证 → 人物详情。三视图：Event Map / Event Timeline / Figure Feature Validation。

**为什么同构**：我们建 intertexts 表的形状完全一样——程序从 266 条原文粗判出 102 条互文候选（relation 是关键词规则），需要人工核对。它的论文能给「人机协作核验」这个做法提供正式学术依据，也能提醒我们：候选≠结论，界面要让人能改。

---

## 4. BioVistory —— 传记叙事自动生成（[已核实] 中文期刊）

- 论文：*BioVistory: An End-to-End Visualization Generation System to Support Storytelling with Biographical Text Data*，费彦琳、高天、李俨达、石洋、曹楠（复旦/同济/上海数据科学重点实验室）
- 《计算机辅助设计与图形学学报》2024-08-22 网络首发，37 卷 8 期（2025-08）；DOI 10.3724/SP.J.1089.2023-00626；数字人文网 DHCN 有中文摘要

**核心**：传记文本 → NLP 预处理 → 提取事件，分**职业生涯 / 人物行迹 / 人际关系 / 时间信息**四视角，并划分人生阶段 → 用**视觉隐喻**自动生成传记可视化 → 三种交互（事件 / 视角 / 阶段）。

**对我们的用处**：这是「人物传记 → 可视化」最直接的参考。我们的 timeline 表只有 34 条（17 篇 + 15 生平锚点 + 2 书），BioVistory 提示可以把五人的数据按「行迹 / 交游 / 仕途 / 时间」四视角重组——尤其「人物行迹」正是我们地层图的横轴。

---

## 5. LifeMountains —— [推断] 对应「历史人物时空事件的不确定性推理」

- 最可能对应：*Visual Reasoning for Uncertainty in Spatio-Temporal Events of Historical Figures*，Wei Zhang, Siwei Tan, Siming Chen, …, Wei Chen，IEEE TVCG vol.29 no.6 pp.3009-3023，DOI 10.1109/TVCG.2022.3146508
- 一篇 univariate 时间序列综述里明确写作「Life Mountain (Zhang et al., 20…)」，指向该文

**[推断依据]** 课堂 PDF 的 OCR 正文里没有直接出现「Life Mountain」字样（是组员记得课堂上有）；网上以 "Life Mountain" 直搜会混进大量无关的艺术作品。按「历史人物 + 时空事件 + 陈思明组」三条线索，这篇 TVCG 最匹配。

**核心**：用 CBDB（中国历代人物传记资料库）与佛教研究权威数据库，处理历史人物时空事件中的**不确定性**并做可视推理。

**对我们的用处**：我们的地名表里 237 条坐标是 null（「查不到就留空」），这正是**不确定性**。这篇给了「怎么把不确定性本身表达出来」的方法——展板上那 237 个点不是缺陷，可以是「史籍记载但今地未定」的一层，这比藏着更有价值。⚠️ 因是推断对应，引用前需再看论文正文确认视觉形式。

---

## 6. OldVis / OldVisOnline —— 历史可视化数据集（[已核实]）

- 论文：*OldVisOnline: Curating a Dataset of Historical Visualizations*，Yu Zhang, Ruike Jiang, Liwenhan Xie, Yuheng Zhao, Can Liu, Tianhong Ding, Siming Chen, Xiaoru Yuan，arXiv 2308.16053
- 项目站：oldvis.github.io；数据集含约 **13,000 张历史可视化图像**，来自 David Rumsey 地图收藏等数字图书馆，用半自动标注区分「可视化」与其他图像

**对我们的用处**：偏素材/工具，不是方法。但两点可借鉴：①它证明了「历史材料的可视化整理」是个正当研究方向，可作课程作业的领域定位依据；②它的半自动标注 + 人工核验流程，跟我们 intertexts 表的做法同源。

---

## 7. HoagsOLife —— 苏东坡一生（[已核实] PacificVis 2021 冠军）

- 作者：李翊瑄（复旦本科），指导教师含石洋、陈思明
- 奖项：IEEE PacificVis 2021 **Visual Data Storytelling Contest 冠军（Winner）**
- B 站有作者演示视频；陈思明主页列为 "Storytelling: Life of Su Dongpo"——讲苏东坡政治生涯的起落、美食与诗词

**为什么最值得看**：这是**同题材、同方法组、已获奖的成品**。我们做「五人文选、长江流域、跨时代」，它就是「一个人、一生、宋代、诗词与仕途」。直接可借鉴：①怎么把一个人的时间线做出戏剧性（起落）；②怎么把诗词这种非结构化文本嵌进时间轴；③叙事比赛的评审看重什么。建议组内看一遍 B 站演示视频。

---

## 优先级建议

| 优先 | 工作 | 理由 |
|---|---|---|
| 1 | InfoAlign | 直接回答「数据怎么变成展板」，三步法可照做 |
| 2 | HoagsOLife | 同题材获奖成品，看视频即可，成本最低、启发最大 |
| 3 | CohortVA | 给 intertexts 表的人机核验提供学术依据 |
| 4 | 信达雅五环 + VisJudge | 给数据纪律一个理论名分，写进汇报 |
| 5 | BioVistory | 若要把五人数据按四视角重组，再看 |
| 6 | LifeMountains | 若决定把 237 条不确定性显式表达，再看（先确认论文对应） |
| 7 | OldVis | 领域定位与素材，可略 |

---

## 诚实边界

1. 「五环」完整框架只见于课堂 PDF，未找到独立论文；相关基准（VisJudge-Bench 等）已核实，但不能等同于五环本身。
2. LifeMountains 的论文对应是**推断**，引用前需确认。
3. 以上论文的**详细方法章节**多数只读了摘要/首页，未逐段精读；本文件是「值不值得深挖」的判断，不是方法综述的终稿。
4. OCR 纪要里的英文异常（Forment、Mlo、用械分析等）按原样保留，未据以推断方法含义。

---

*jiya 整理，2026-11-22*
