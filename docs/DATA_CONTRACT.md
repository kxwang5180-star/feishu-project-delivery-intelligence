# Data Contract

This document defines the Feishu Base output contract for `项目交付周期`.

## Grain

One row represents:

```text
current quarter + demand category
```

The table should normally contain two managed rows:

```text
current quarter / 中小需求
current quarter / 大/超大需求
```

## Idempotency Key

```text
季度 + 需求分类
```

## Published Fields

| Field | Type | Required | Source |
|---|---:|---:|---|
| `季度` | Text | Yes | Current quarter from online date |
| `需求分类` | Single select | Yes | Derived from delivery effort |
| `需求数` | Number | Yes | Current-quarter cumulative demand count |
| `平均交付周期` | Number | Yes | Average delivery effort |
| `交付中位数` | Number | Yes | Median delivery effort |
| `交付P90` | Number | Yes | P90 delivery effort |
| `平均研发时长` | Number | Yes | Average development effort |
| `平均测试时长` | Number | Yes | Average testing effort |

## Cleared Or Skipped Fields

| Field | Handling |
|---|---|
| `周次` | Cleared on write. The table no longer keeps weekly rows. |
| `执行日期` | Formula field, skipped |
| `研发时长/测试时长` | Formula field, skipped |
| `created_at` | Auto-fill field, skipped |

## Source Field IDs

| Metric | Source Field |
|---|---|
| Online date | `field_584a64` |
| Delivery effort | `field_fba983` |
| Development effort | `field_db341e` |
| Testing effort | `field_715f2b` |

## Refresh Window

Default refresh:

```text
current quarter through the most recent Sunday
```

The job is scheduled for Monday 08:00, so the default cutoff is the previous Sunday.

## Stale Record Handling

With `--upsert --sync-stale`, the publisher:

- updates the two current-quarter category rows
- creates them if missing
- deletes old weekly/history rows whose managed key is stale or duplicated

This is a controlled cleanup, not a blind full-table replacement.
