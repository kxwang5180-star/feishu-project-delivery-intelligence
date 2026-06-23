# Feishu Project Delivery Intelligence


This repository packages a delivery intelligence system for Feishu Project. It is not a spreadsheet uploader and it is not merely a Codex skill.

Its purpose is to convert Feishu Project demand workflow data into a reusable management intelligence layer:

```text
Feishu Project work items
  -> governed metric extraction
  -> local analytical data mart
  -> delivery efficiency models
  -> quarter-to-date weekly trend snapshots
  -> Feishu Base archival table
  -> dashboard / review / improvement actions
```

The repository focuses on one operational question:

> How is the department's demand delivery efficiency changing over time, and which demand categories are driving the change?

## Why This Exists

Feishu Project already contains the raw operational data, but raw work item fields are not enough for management review.

Common issues:

- Delivery metrics are mixed with different definitions.
- Natural-day cycle, estimated person-days, development effort, and testing effort are often discussed as if they were the same thing.
- Weekly review data is manually exported or recreated.
- Trend charts lack stable lineage and are hard to audit.
- Feishu Base tables become a dumping ground instead of a governed analytical layer.

This project turns that into a controlled workflow:

- One metric contract.
- One data mart.
- One weekly refresh job.
- One Feishu Base archive.
- One place for accumulated delivery knowledge.

## Product Positioning

This is best understood as a lightweight delivery intelligence product.

| Layer | Role |
|---|---|
| Feishu Project | Source of truth for demand workflow and fields |
| Extraction | Pulls eligible demand work items from Feishu Project MCP |
| Data mart | Stores demand-level facts, field dictionaries, and metric dictionaries |
| Analytics | Produces weekly quarter-to-date cumulative metrics |
| Visualization substrate | Feishu Base table for views, charts, filtering, and review |
| Knowledge archive | Stable historical snapshots for long-term comparison |

## What It Is Not

This repository is not:

- a one-off report generator
- a table-copy utility
- a generic Feishu API wrapper
- a dashboard-only project
- a replacement for Feishu Project

It is the analytical bridge between Feishu Project operations and repeatable delivery management.

## Core Business Logic

The current analytical model intentionally keeps the metric set small and governed.

### Delivery Effort

```text
delivery_effort = field_fba983
```

Meaning:

```text
total estimated person-days across product, frontend, backend, testing, and other participating roles
```

This is the only delivery effort definition used in the Base output. The older natural-day delivery cycle is not used for this table because it mixes calendar waiting time with effort scale.

### Development Effort

```text
development_effort = field_db341e
```

Development effort excludes testing.

### Testing Effort

```text
testing_effort = field_715f2b
```

### Online Date

```text
online_date = field_584a64
```

The online date determines monthly, quarterly, and weekly cumulative attribution.

## Demand Classification

Demand classification is based on delivery effort:

| Category | Rule | Interpretation |
|---|---|---|
| `中小需求` | delivery effort <= 60 | Normal demand flow, used to monitor throughput and stability |
| `大/超大需求` | delivery effort > 60 | High-impact demand, used to monitor long-tail risk and resource concentration |

The Feishu Base field is a single-select field. The writer maps values to the Base options exactly:

```text
中小需求
大/超大需求
```

## Weekly Quarter-To-Date View

The main Base table is `项目交付周期`.

Each record represents:

```text
quarter + week-in-quarter + demand category
```

Example:

```text
2026-Q2 / W11（截至2026-06-14） / 大/超大需求
```

This design supports a quarterly review rhythm while still showing weekly movement.

It answers questions such as:

- Are large demands accumulating faster than small/medium demands?
- Is the quarter's P90 delivery effort rising?
- Is development effort increasing faster than testing effort?
- Are current-quarter numbers improving or deteriorating week by week?
- Is the demand mix changing in a way that will affect delivery capacity?

## Feishu Base Write Contract

Target table:

```text
Base: NgEPbbtokaswvBstu0DcMYMlnKg
Table: 项目交付周期
Table ID: tblPz1BLjGbtQymz
```

Idempotency key:

```text
季度 + 周次 + 需求分类
```

Published fields:

| Field | Meaning |
|---|---|
| `季度` | Quarter, for example `2026-Q2` |
| `周次` | Quarter week bucket and cutoff date |
| `需求分类` | `中小需求` or `大/超大需求` |
| `需求数` | Cumulative demand count up to the week cutoff |
| `平均交付周期` | Average delivery effort |
| `交付中位数` | Median delivery effort |
| `交付P90` | Long-tail delivery effort indicator |
| `平均研发时长` | Average development effort |
| `平均测试时长` | Average testing effort |

Skipped fields:

| Field | Reason |
|---|---|
| `执行日期` | Feishu Base formula field |
| `研发时长/测试时长` | Feishu Base formula field |
| `created_at` | Auto-filled timestamp |

## System Workflow

```text
1. Extract Feishu Project demand work items
2. Cache raw and enriched demand facts as JSONL
3. Build CSV/XLSX data mart
4. Generate quarter-week cumulative metric table
5. Probe Feishu Base fields
6. Dry-run mapping and row counts
7. Upsert into Feishu Base by stable key
8. Use Base views/charts as operational dashboard and archive
```

The weekly job does not delete and recreate the whole table. It uses idempotent upsert:

- update existing keys
- create missing keys
- delete stale keys that are no longer in the source

## Repository Layout

```text
.
├── feishu-online-sheets/                  # Codex skill for Feishu Sheets/Base publishing
│   ├── SKILL.md
│   └── scripts/
│       ├── publish_sheet.py               # Feishu Sheets writer
│       └── publish_bitable.py             # Feishu Base writer with upsert support
├── automation/
│   ├── scripts/
│   │   ├── collect_efficiency_enhanced.py
│   │   ├── export_efficiency_datamart.py
│   │   ├── build_quarter_week_cumulative_metrics.py
│   │   └── refresh_project_delivery_cycle_weekly.sh
│   ├── pmo_agent/                         # Feishu Project MCP client and field parsing
│   ├── config/
│   │   └── feishu_bitable_publish.example.json
│   └── docs/
│       └── project-delivery-cycle-server-deploy.md
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

Edit `automation/.env.local`:

```dotenv
FEISHU_APP_ID=cli_xxx
FEISHU_APP_SECRET=xxx
FEISHU_BASE_URL=https://open.feishu.cn

FEISHU_PROJECT_MCP_URL=xxx
FEISHU_PROJECT_MCP_TOKEN=xxx
MEEGO_PROJECT_KEY=信息科技部
```

Run once:

```bash
cd /opt/feishu-project-delivery-cycle-updater/automation
PYTHON_BIN=/opt/feishu-project-delivery-cycle-updater/.venv/bin/python \
BITABLE_PUBLISHER=/opt/feishu-project-delivery-cycle-updater/feishu-online-sheets/scripts/publish_bitable.py \
bash scripts/refresh_project_delivery_cycle_weekly.sh
```

Backfill to a specific date:

```bash
bash scripts/refresh_project_delivery_cycle_weekly.sh 2026-06-14
```

## Weekly Schedule

Run every Monday at 09:30:

```cron
30 9 * * 1 cd /opt/feishu-project-delivery-cycle-updater/automation && PYTHON_BIN=/opt/feishu-project-delivery-cycle-updater/.venv/bin/python BITABLE_PUBLISHER=/opt/feishu-project-delivery-cycle-updater/feishu-online-sheets/scripts/publish_bitable.py /bin/bash scripts/refresh_project_delivery_cycle_weekly.sh
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Data Contract](docs/DATA_CONTRACT.md)
- [Operations](docs/OPERATIONS.md)
- [Value Model](docs/VALUE_MODEL.md)
- [Deployment](DEPLOY.md)

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

- Keep field IDs and metric formulas explicit.
- Keep generated data out of Git.
- Keep Feishu secrets in server-side env files.
- Probe and dry-run before the first write to a new table.
- Preserve Feishu Base formula and auto-fill fields.
- Use upsert, not destructive full-table refresh.
- Treat the Base table as both a dashboard source and a historical archive.

