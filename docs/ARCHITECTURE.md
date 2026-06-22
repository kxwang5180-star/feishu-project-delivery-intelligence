# Architecture

This repository implements a delivery intelligence pipeline for Feishu Project demand work items. The key design decision is to separate raw project operations from governed analytics and from the final Feishu Base archive.

It is intentionally split into four layers:

## 1. Source Layer: Feishu Project

The source of truth is Feishu Project demand work items in the department project space.

The extraction layer reads:

- demand ID
- demand title
- demand status
- online date
- total delivery effort
- development effort
- testing effort
- supporting effort fields

The workflow targets completed or near-completed demand statuses such as:

- `已结束`
- `待验收`
- `待推广`

## 2. Data Mart Layer

The local data mart is generated under:

```text
automation/data/efficiency_datamart/
```

Core tables:

| Table | Purpose |
|---|---|
| `demand_detail.csv` | One row per demand work item |
| `monthly_metrics.csv` | Monthly aggregated metrics |
| `quarterly_metrics.csv` | Quarterly aggregated metrics |
| `size_metrics.csv` | Demand category summary |
| `field_dictionary.csv` | Source field mapping and definitions |
| `metric_dictionary.csv` | Metric formulas and meaning |
| `quarter_week_cumulative_metrics.csv` | Quarter-to-date weekly cumulative output for Feishu Base |

This makes the pipeline inspectable and auditable before anything is written to Feishu Base.

## 3. Analytics Layer

The current weekly Base output focuses on quarter-to-date cumulative movement.

The grain is:

```text
quarter + week-in-quarter + demand category
```

This answers practical management questions:

- Is the current quarter accumulating demand faster than expected?
- Are large demands increasing the long-tail delivery risk?
- Is development effort moving consistently with testing effort?
- Which demand category is driving delivery pressure?
- How do weekly cumulative metrics change as the quarter progresses?

## 4. Archive And Consumption Layer: Feishu Base

The pipeline writes to the fixed Feishu Base table:

```text
项目交付周期
```

This table acts as a durable operational archive and a dashboard source.

The writer uses idempotent upsert with:

```text
季度 + 周次 + 需求分类
```

This avoids destructive full-table replacement and preserves the stability of Feishu Base records.

## End-To-End Flow

```text
Feishu Project MCP
  -> collect_efficiency_enhanced.py
  -> enhanced_metrics.jsonl
  -> export_efficiency_datamart.py
  -> demand_detail.csv / metric dictionaries / workbook
  -> build_quarter_week_cumulative_metrics.py
  -> quarter_week_cumulative_metrics.csv
  -> publish_bitable.py --upsert --sync-stale
  -> Feishu Base: 项目交付周期
```

## Why This Matters

The repository turns operational delivery data into reusable management information. It is built around a weekly review loop:

```text
observe -> compare -> diagnose -> improve -> archive
```

It supports:

- weekly delivery reviews
- quarter-to-date trend tracking
- demand category comparison
- effort distribution monitoring
- stable metric governance
- long-term archival in Feishu Base

## Design Principles

1. Do not use Feishu Base as the computation engine.
   The Base table is the published archive and visualization substrate. Metric computation happens before writing.

2. Do not overwrite formula or auto-fill fields.
   Feishu Base formulas remain owned by the Base schema.

3. Do not use full-table replacement for recurring jobs.
   Weekly refresh uses key-based upsert and stale-key cleanup.

4. Keep the analytical grain stable.
   The core grain is `季度 + 周次 + 需求分类`.

5. Keep field IDs auditable.
   Source field IDs are explicitly represented in the scripts and data dictionary.
