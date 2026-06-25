# Project Delivery Cycle Weekly Refresh Deployment

This document describes the production server workflow for refreshing the Feishu Base table `项目交付周期` every Monday.

## Goal

The job publishes the latest completed week's cumulative demand delivery-cycle metrics using source data from `2025-01-01` through that week.

Each output row is split by demand category:

```text
中小需求
大/超大需求
```

## Workflow

1. Collect demand work items from Feishu Project through the MCP endpoint.
2. Enrich the demand rows with role, node, schedule, and effort information.
3. Export the local efficiency datamart.
4. Generate `quarter_week_cumulative_metrics.csv`.
5. Read the target Feishu Base table fields.
6. Match existing Base records by `季度 + 周次 + 需求分类`.
7. Update existing latest-week records or create them if missing.

Normal weekly refreshes do not delete, rewrite, or correct historical week rows.

## Recommended Server Directory

```bash
/opt/feishu-project-delivery-cycle-updater
```

## Environment Variables

Create `automation/.env.local`:

```dotenv
FEISHU_APP_ID=cli_xxx
FEISHU_APP_SECRET=replace_on_server
FEISHU_BASE_URL=https://open.feishu.cn

FEISHU_PROJECT_MCP_URL=replace_with_project_mcp_url
FEISHU_PROJECT_MCP_TOKEN=replace_with_project_mcp_token
MEEGO_PROJECT_KEY=信息科技部
MEEGO_PROJECT_NAME=信息科技部
MEEGO_WORK_ITEM_TYPE=需求
```

The Feishu app credentials must belong to an app with Base write permission for the target table. Do not commit `.env.local`.

## Python Dependencies

The datamart export needs `openpyxl`.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

The refresh scripts use these optional environment variables:

```bash
export PYTHON_BIN=/opt/feishu-project-delivery-cycle-updater/.venv/bin/python
export BITABLE_PUBLISHER=/opt/feishu-project-delivery-cycle-updater/feishu-online-sheets/scripts/publish_bitable.py
```

## Feishu Base Publish Config

Copy the example config:

```bash
cd /opt/feishu-project-delivery-cycle-updater/automation
cp config/feishu_bitable_publish.example.json config/feishu_bitable_publish.json
```

Current target:

```text
app_token = NgEPbbtokaswvBstu0DcMYMlnKg
table_id  = tblPz1BLjGbtQymz
```

Unique upsert key:

```text
季度 + 周次 + 需求分类
```

Skipped fields:

```text
执行日期
研发时长/测试时长
created_at
```

These fields are managed by Feishu formulas or automatic fill behavior.

## Manual Run

Default: update the latest completed Sunday snapshot.

```bash
cd /opt/feishu-project-delivery-cycle-updater
PYTHON_BIN=/opt/feishu-project-delivery-cycle-updater/.venv/bin/python \
BITABLE_PUBLISHER=/opt/feishu-project-delivery-cycle-updater/feishu-online-sheets/scripts/publish_bitable.py \
/bin/bash server/run_refresh.sh
```

Run through a specific Sunday:

```bash
/bin/bash server/run_refresh.sh 2026-06-14
```

## Validation

Probe fields:

```bash
cd /opt/feishu-project-delivery-cycle-updater/automation
../.venv/bin/python ../feishu-online-sheets/scripts/publish_bitable.py \
  --config config/feishu_bitable_publish.json \
  --probe-fields
```

Dry-run:

```bash
../.venv/bin/python ../feishu-online-sheets/scripts/publish_bitable.py \
  --config config/feishu_bitable_publish.json \
  --dry-run
```

Publish:

```bash
../.venv/bin/python ../feishu-online-sheets/scripts/publish_bitable.py \
  --config config/feishu_bitable_publish.json \
  --upsert
```

## Cron

Run every Monday at 09:30:

```cron
30 9 * * 1 cd /opt/feishu-project-delivery-cycle-updater && PYTHON_BIN=/opt/feishu-project-delivery-cycle-updater/.venv/bin/python BITABLE_PUBLISHER=/opt/feishu-project-delivery-cycle-updater/feishu-online-sheets/scripts/publish_bitable.py /bin/bash server/run_refresh.sh
```

## Logs

```bash
tail -n 200 /opt/feishu-project-delivery-cycle-updater/automation/logs/project_delivery_cycle_weekly.log
```

## Failure Handling

- `99991672 Access denied` or `91403 Forbidden`: check the Feishu app credentials and Base/table permissions.
- Missing or empty `quarter_week_cumulative_metrics.csv`: run the collection and datamart export steps first, or run `server/run_refresh.sh`.
- Field mapping mismatch: run `--probe-fields` and compare the Base field names with `automation/config/feishu_bitable_publish.json`.
- Unexpected historical changes: confirm the weekly job uses `--latest-week-only` and does not pass `--sync-stale`.
