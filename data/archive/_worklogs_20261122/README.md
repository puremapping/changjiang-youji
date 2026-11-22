# 归档：2026-11-22 并行过程稿与临时脚本

> 整理日期：2026-11-22。本目录收容 2026-11-22 一批并行子代理产生的**过程稿**（方法分稿 / WORKLOG / 复现脚本），
> 均非最终权威文档。唯一权威方法文档为 `data/base/METHOD.md`（其 §8 任务D、§9、§10 已并入本批结论）。
> 数据文件（works/events/intertexts/places/persons/json/csv）不在本目录，本次整理未改动其内容。

## 目录内容

### 方法 / 日志分稿（原在 `data/base/`，现移至此）
| 文件 | 性质 | 原路径 |
|---|---|---|
| `METHOD_BCD_20261122.md` | B/C/D 三任务方法分稿（并行过程稿，C 分布已被 scholar 版覆盖作废） | `data/base/` |
| `METHOD_WORKS_INTERTEXT.md` | works 层互文方法分稿，独特内容已并入 `METHOD.md` §10 | `data/base/` |
| `WORKLOG_20261122.md` | A/B/C/D 批工作日志 | `data/base/` |
| `WORKLOG_BCD_20261122.md` | B/C/D 分稿日志 | `data/base/` |
| `WORKLOG_WORKS_INTERTEXT.md` | works 互文逐条决策日志（122 条逐条依据） | `data/base/` |

### 复现脚本（原在 `data/base/_works_intertext_work/`，现整体移至此）
`scripts/_works_intertext_work/`：`_build_works_orig.py`、`_scan_works_alias.py`、
`_build_works_intertexts.py`、`_check_works_intertexts.py`、`_gen_worklog.py`、
`_intertext_decisions.json`、`candidates.json`、`candidates2.json`。
其中 `METHOD.md` §10 提到的脚本旧路径 `data/base/_works_intertext_work/` 即指此处。

## 旧路径引用说明（引用方未改，仅在归档原件顶部加指针）
- `data/audit/intertexts_works.md` 第 3 行引用 `METHOD_WORKS_INTERTEXT §5`——
  该原件已移至此目录，文件顶部已加归档指针。
- `data/audit/SUMMARY.md` 第 66 行提及 `_works_intertext_work/`——
  即本目录 `scripts/_works_intertext_work/`。

## 与最终数据的关系
本批 122 条 works 互文（int-103…int-224）、3 名新增 person（p-li-bo / p-li-daoyuan /
p-han-shizhong）、审校修复（intertexts 223 条、works 硬错误、places 坐标、events 标注）
均已落盘在 `data/base/` 与 `data/events_v2/`、works_v1 数据表中；本目录只留方法与过程留痕，
不构成第二套口径。审校报告与修复记录见 `data/audit/`（README / 8 份分片报告 / SUMMARY / 3 份 FIX）。
