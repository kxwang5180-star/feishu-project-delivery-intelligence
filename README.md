# Feishu Project Delivery Intelligence

Recommended repository name: **`feishu-project-delivery-intelligence`**

This repository packages a delivery intelligence workflow for Feishu Project. It is not just a Feishu table writer or a Codex skill.

Its role is to turn Feishu Project demand workflow data into a small, governed, always-current management signal:

```text
Feishu Project work items
  -> governed metric extraction
  -> local analytical data mart
  -> current-quarter delivery snapshot
  -> Feishu Base operational table
  -> review, visualization, and management insight
```

## Current Product Decision

The Feishu Base table should only show the **latest cumulative data for the current quarter**.

It should not keep one row per week. It should not recalculate or rewrite historical weekly snapshots.

Current grain:

```text
current quarter + demand category
```

So the table normally contains two managed rows:

```text
2026-Q2 / 中小需求
2026-Q2 / 大/超大需求
```

The `周次` field is deliberately cleared because the table is no longer weekly-grained.

## Why This Exists

Feishu Project contains the raw operational facts, but management review needs a stable analytical layer:

- one delivery effort definition
- one demand classification rule
- one current-quarter view
- one Base table for visualization and archive
- one automated Monday refresh

The goal is not to produce more files. The goal is to provide a dependable signal for delivery review:

- current-quarter demand accumulation
- large-demand pressure
- P90 long-tail risk
- development/testing effort structure
- category-level delivery scale

## Core Metrics

| Metric | Source | Meaning |
|---|---|---|
| Online date | `field_584a64` | Determines current quarter attribution |
| Delivery effort | `field_fba983` | Total estimated person-days across all roles |
| Development effort | `field_db341e` | R&D effort excluding testing |
| Testing effort | `field_715f2b` | QA/testing effort |

The older natural-day delivery cycle is not used in this Base output.

## Demand Classification

| Category | Rule |
|---|---|
| `中小需求` | delivery effort <= 60 |
| `大/超大需求` | delivery effort > 60 |

## Feishu Base Contract

Target table:

```text
Base app_token: NgEPbbtokaswvBstu0DcMYMlnKg
Table name: 项目交付周期
Table ID: tblPz1BLjGbtQymz
```

Idempotency key:

```text
季度 + 需求分类
```

Published fields:

| Field | Meaning |
|---|---|
| `季度` | Current quarter, such as `2026-Q2` |
| `需求分类` | `中小需求` or `大/超大需求` |
| `需求数` | Current-quarter cumulative demand count |
| `平均交付周期` | Average delivery effort |
| `交付中位数` | Median delivery effort |
| `交付P90` | Long-tail delivery effort |
| `平均研发时长` | Average development effort |
| `平均测试时长` | Average testing effort |

Fields intentionally skipped or cleared:

| Field | Handling |
|---|---|
| `周次` | Cleared. The table is no longer week-grained. |
| `执行日期` | Feishu Base formula field, not written by the job |
| `研发时长/测试时长` | Feishu Base formula field, not written by the job |
| `created_at` | Auto-filled timestamp, not written by the job |

## Workflow

```text
1. Extract Feishu Project demand data through MCP.
2. Cache raw/enriched demand facts locally.
3. Build the demand efficiency data mart.
4. Generate current_quarter_delivery_metrics.csv.
5. Probe Feishu Base fields.
6. Upsert by 季度 + 需求分类.
7. Delete stale managed records that are not in the current snapshot.
8. Use Feishu Base for visualization, review, and current-state archival.
```

## Directory Layout

```text
.
├── feishu-online-sheets/
│   ├── SKILL.md
│   └── scripts/
│       ├── publish_sheet.py
│       └── publish_bitable.py
├── automation/
│   ├── scripts/
│   │   ├── collect_efficiency_enhanced.py
│   │   ├── export_efficiency_datamart.py
│   │   ├── build_quarter_week_cumulative_metrics.py
│   │   └── refresh_project_delivery_cycle_weekly.sh
│   ├── pmo_agent/
│   ├── config/
│   └── docs/
├── docs/
│   ├── ARCHITECTURE.md
│   ├── DATA_CONTRACT.md
│   ├── OPERATIONS.md
│   └── VALUE_MODEL.md
├── requirements.txt
└── DEPLOY.md
```

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Install the Codex skill:

```bash
mkdir -p ~/.codex/skills
rm -rf ~/.codex/skills/feishu-online-sheets
cp -R feishu-online-sheets ~/.codex/skills/
```

Prepare runtime config:

```bash
cd automation
cp ../server/env.example .env.local
cp config/feishu_bitable_publish.example.json config/feishu_bitable_publish.json
```

Run once:

```bash
PYTHON_BIN=/opt/feishu-project-delivery-intelligence/.venv/bin/python \
BITABLE_PUBLISHER=/opt/feishu-project-delivery-intelligence/feishu-online-sheets/scripts/publish_bitable.py \
bash scripts/refresh_project_delivery_cycle_weekly.sh
```

Backfill to a specific Sunday:

```bash
bash scripts/refresh_project_delivery_cycle_weekly.sh 2026-06-28
```

## Schedule

Run every Monday at 08:00:

```cron
0 8 * * 1 cd /opt/feishu-project-delivery-intelligence/automation && PYTHON_BIN=/opt/feishu-project-delivery-intelligence/.venv/bin/python BITABLE_PUBLISHER=/opt/feishu-project-delivery-intelligence/feishu-online-sheets/scripts/publish_bitable.py /bin/bash scripts/refresh_project_delivery_cycle_weekly.sh
```

## Required Feishu Permissions

For Feishu Base writeback:

```text
base:field:read
bitable:app
```

For Feishu Project extraction:

```text
A working Feishu Project MCP endpoint with access to 信息科技部 / 需求
```

## Operating Principles

- Keep only the latest current-quarter snapshot in the Base table.
- Use `季度 + 需求分类` as the stable key.
- Clear `周次`; do not write formula or auto-fill fields.
- Use upsert and stale-key cleanup, not blind append.
- Keep generated data and secrets out of Git.
