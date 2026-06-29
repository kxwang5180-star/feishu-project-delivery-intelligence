# Architecture

This repository implements a delivery intelligence pipeline for Feishu Project demand work items.

The current production output is intentionally small: the latest current-quarter snapshot by demand category.

## Flow

```text
Feishu Project MCP
  -> collect_efficiency_enhanced.py
  -> enhanced_metrics.jsonl
  -> export_efficiency_datamart.py
  -> demand_detail.csv / field dictionary / metric dictionary
  -> build_quarter_week_cumulative_metrics.py --latest-current-quarter
  -> current_quarter_delivery_metrics.csv
  -> publish_bitable.py --upsert --sync-stale
  -> Feishu Base: 项目交付周期
```

## Layer Responsibilities

| Layer | Responsibility |
|---|---|
| Feishu Project | Source operational system |
| JSONL cache | Durable raw/enriched extraction cache |
| Data mart | Auditable demand facts and metric dictionaries |
| Snapshot builder | Current-quarter aggregation by demand category |
| Base publisher | Field probing, mapping, upsert, stale cleanup |
| Feishu Base | Collaboration, visualization, and current-state archive |

## Why Not Weekly History

The Base table is now designed for the latest operational state, not a historical weekly snapshot table.

This keeps the review view simple:

```text
current quarter + demand category
```

Historical analysis can still be regenerated from the local data mart when needed.

## Write Model

```text
unique_fields = ["季度", "需求分类"]
clear_fields = ["周次"]
skip_fields = ["执行日期", "研发时长/测试时长", "created_at"]
```

The writer updates matching records, creates missing category records, and removes stale/duplicate managed records.
