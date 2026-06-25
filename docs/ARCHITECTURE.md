# Architecture

This repository packages an end-to-end Feishu Project delivery intelligence pipeline.

The system has four layers:

```text
Feishu Project source
  -> extraction and enrichment
  -> analytical datamart and weekly snapshot generation
  -> Feishu Base archival writeback
```

## Layer 1: Feishu Project Source

The source of truth is Feishu Project demand work items in the `信息科技部` space, with `需求` as the target work item type.

The collector reads:

- Work item identity and status.
- Project online date.
- Total delivery effort estimate.
- RD effort estimate.
- Test effort estimate.
- Role members, node owners, subtask owners, and schedule data where available.

## Layer 2: Extraction and Enrichment

`automation/scripts/collect_efficiency_enhanced.py` collects the base demand rows and enriches them with role and node context through the Feishu Project MCP tools.

Primary output:

```text
automation/data/efficiency_enhanced/enhanced_metrics.jsonl
```

This layer is responsible for turning Feishu Project operational data into demand-level facts. It should not contain dashboard-specific formatting.

## Layer 3: Analytical Datamart

`automation/scripts/export_efficiency_datamart.py` converts enriched demand facts into a local datamart.

Primary outputs:

```text
automation/data/efficiency_datamart/demand_detail.csv
automation/data/efficiency_datamart/field_dictionary.csv
automation/data/efficiency_datamart/efficiency_datamart.xlsx
```

This layer is the inspection and reuse layer. Analysts can review the generated files before publishing to Feishu Base.

## Layer 4: Weekly Snapshot Generation

`automation/scripts/build_quarter_week_cumulative_metrics.py` converts demand-level facts into quarter-to-date weekly snapshots.

Primary output:

```text
automation/data/efficiency_datamart/quarter_week_cumulative_metrics.csv
```

Rows are grouped by:

```text
季度 + 周次 + 需求分类
```

The weekly automation emits only the latest completed week snapshot. Previously written weeks remain as the historical archive and are not corrected by the normal weekly job.

## Layer 5: Feishu Base Archive

`feishu-online-sheets/scripts/publish_bitable.py` writes the generated snapshot CSV into the fixed Feishu Base table `项目交付周期`.

The production write mode is:

```bash
--upsert
```

The script probes fields, maps source columns to Base fields, skips formula and auto-fill fields, updates the latest week row by key, and creates the latest week row if missing. The weekly job does not delete stale keys.

## Automation Entry Point

The weekly server entry point is:

```text
server/run_refresh.sh
```

It delegates to:

```text
automation/scripts/refresh_project_delivery_cycle_weekly.sh
```

That script runs collection, datamart export, weekly snapshot generation, and Feishu Base upsert in one logged operation.
