# Data Contract

This document defines the expected data contract for the Feishu Base table `项目交付周期`.

## Target Grain

One row represents:

```text
quarter + week-in-quarter + demand category
```

Example:

```text
2026-Q2 / W11（截至2026-06-14） / 大/超大需求
```

## Idempotency Key

```text
季度 + 周次 + 需求分类
```

The publisher uses this key to decide whether to update an existing record or create a new one.

## Published Fields

| Field | Type | Required | Source |
|---|---:|---:|---|
| `季度` | Text | Yes | Generated from online date |
| `周次` | Text | Yes | Generated from quarter start and week cutoff |
| `需求分类` | Single select | Yes | Derived from delivery effort |
| `需求数` | Number | Yes | Count of cumulative demands |
| `平均交付周期` | Number | Yes | Average total delivery effort |
| `交付中位数` | Number | Yes | Median total delivery effort |
| `交付P90` | Number | Yes | P90 total delivery effort |
| `平均研发时长` | Number | Yes | Average development effort |
| `平均测试时长` | Number | Yes | Average testing effort |

## Fields Not Written

| Field | Reason |
|---|---|
| `执行日期` | Feishu Base formula field |
| `研发时长/测试时长` | Feishu Base formula field |
| `created_at` | Auto-filled timestamp |

## Metric Source Fields

| Metric | Source Field |
|---|---|
| Online date | `field_584a64` |
| Delivery effort | `field_fba983` |
| Development effort | `field_db341e` |
| Testing effort | `field_715f2b` |

## Demand Category Rule

| Category | Rule |
|---|---|
| `中小需求` | `delivery_effort <= 60` |
| `大/超大需求` | `delivery_effort > 60` |

## Refresh Window

Default refresh window:

```text
2025-01-01 through the most recent Sunday
```

Manual backfills can pass an explicit end date:

```bash
bash scripts/refresh_project_delivery_cycle_weekly.sh 2026-06-14
```

## Stale Record Handling

With `--upsert --sync-stale`, the publisher:

- updates matched records
- creates missing records
- deletes records whose idempotency key is not present in the current source data

This is not a full-table replacement. It only removes stale managed keys.
