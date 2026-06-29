# Project Delivery Cycle Server Deployment

The server job refreshes the Feishu Base table `项目交付周期` every Monday at 08:00.

The table keeps only the latest current-quarter cumulative metrics by demand category.

## Output Grain

```text
current quarter + demand category
```

Expected managed rows:

```text
中小需求
大/超大需求
```

## Runtime Flow

1. Collect Feishu Project demand data through MCP.
2. Export the local efficiency data mart.
3. Generate `current_quarter_delivery_metrics.csv`.
4. Upsert Feishu Base records by `季度 + 需求分类`.
5. Clear `周次`.
6. Skip formula/auto fields.
7. Remove stale or duplicate managed records.

## Manual Run

```bash
PYTHON_BIN=/opt/feishu-project-delivery-intelligence/.venv/bin/python \
BITABLE_PUBLISHER=/opt/feishu-project-delivery-intelligence/feishu-online-sheets/scripts/publish_bitable.py \
bash scripts/refresh_project_delivery_cycle_weekly.sh
```

Backfill:

```bash
bash scripts/refresh_project_delivery_cycle_weekly.sh 2026-06-28
```

## Cron

```cron
0 8 * * 1 cd /opt/feishu-project-delivery-intelligence/automation && PYTHON_BIN=/opt/feishu-project-delivery-intelligence/.venv/bin/python BITABLE_PUBLISHER=/opt/feishu-project-delivery-intelligence/feishu-online-sheets/scripts/publish_bitable.py /bin/bash scripts/refresh_project_delivery_cycle_weekly.sh
```

## Key Config

```json
{
  "unique_fields": ["季度", "需求分类"],
  "clear_fields": ["周次"],
  "skip_fields": ["研发时长/测试时长", "created_at", "执行日期"]
}
```

## Logs

```bash
tail -n 200 logs/project_delivery_cycle_weekly.log
```
