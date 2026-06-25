# Data Contract

This document defines the stable source, metric, and Feishu Base write contracts for the delivery intelligence pipeline.

## Source Scope

```text
Feishu Project space: 信息科技部
Work item type: 需求
Start date: 2025-01-01
Default end date: latest completed Sunday
```

The collector focuses on demand work items with usable online dates and delivery-effort fields.

## Core Source Fields

```text
field_584a64  project online time
field_fba983  total delivery effort estimate
field_db341e  RD effort estimate
field_715f2b  test effort estimate
```

Additional role, node, subtask, and schedule fields are collected for traceability and extended analysis.

## Derived Demand Metrics

```text
metric_delivery_effort_days  = field_fba983
metric_rd_days_excl_test     = field_db341e
metric_test_days             = field_715f2b
```

Demand category:

```text
中小需求     metric_delivery_effort_days <= 60
大/超大需求  metric_delivery_effort_days > 60
```

## Weekly Snapshot Grain

The final Base archive grain is:

```text
季度 + 周次 + 需求分类
```

Example:

```text
季度: 2026-Q2
周次: W11（截至2026-06-14）
需求分类: 中小需求
```

Each row is quarter-to-date, not a simple weekly delta. A row for `W11` includes all demands in that quarter up to the `W11` cutoff date.

## Output Fields Written to Feishu Base

```text
季度
周次
需求分类
需求数
平均交付周期
交付中位数
交付P90
平均研发时长
平均测试时长
```

## Fields Intentionally Skipped

```text
执行日期
研发时长/测试时长
created_at
```

These fields are maintained by Feishu Base formula or automatic fill behavior and should not be written by the updater.

## Upsert Contract

The Feishu Base publisher uses this unique key:

```text
季度 + 周次 + 需求分类
```

Expected behavior:

- Existing keys are updated.
- Missing keys are created.
- Weekly automation writes only the latest completed week key set.
- Historical week keys are retained and are not recalculated by the weekly job.
- Full-table replacement is not the normal refresh mode.

## Target Base

```text
Base app_token: NgEPbbtokaswvBstu0DcMYMlnKg
Table name: 项目交付周期
table_id: tblPz1BLjGbtQymz
```
