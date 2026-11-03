# changjiang-youji（长江游记）

长江流域五人文选的信息可视化项目。

## 五位作者

柳宗元 · 苏轼 · 陆游 · 范成大 · 张岱

## 两个数据粒度

- **事件级（events）**：记录单元，客观可数——某年某月某日某人到某地做某事
- **篇目级（works）**：叙事单元，主观定性——处境、主旨、情感、意象、笔法

## 目录

```
SCHEMA.md            数据模型契约（6 张表）
data/archive/        各数据版本（v001~v004，旧版不删）
data/playlist_时间交集/  时间交集查证
proto/               交互原型（地图×时间线双视图）
research/            历史研究结论（findings）
source/              原文（不入库，见 .gitignore）
docs/                文档
```

## 数据纪律

1. 每一版数据 = 一个目录，内含 METHOD.md + data/（见 data/README.md）
2. 原文繁体一字不改；引用回原典核对，标注版本
3. 地名坐标宁缺勿猜（coord_conf 区分 exact/approx/unknown）
4. 互文记录必附引文

## 当前状态

- 入蜀记事件表：events_v2（156 条，标点本切分；v001~v004 存 archive）
- 吴船录事件表：events_v2（110 条；v003 存 archive）
- schema：v1，待小组确认后冻结
