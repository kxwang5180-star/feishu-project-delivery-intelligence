# Operations Runbook

This runbook covers normal weekly operation, validation, and failure handling.

## Normal Weekly Run

The production cadence is Monday 09:30.

The default refresh window is:

```text
2025-01-01 through the latest completed Sunday, but only the latest completed week snapshot is written back
```

Cron entry:

```cron
30 9 * * 1 cd /opt/feishu-project-delivery-cycle-updater && PYTHON_BIN=/opt/feishu-project-delivery-cycle-updater/.venv/bin/python BITABLE_PUBLISHER=/opt/feishu-project-delivery-cycle-updater/feishu-online-sheets/scripts/publish_bitable.py /bin/bash server/run_refresh.sh
```

## Manual Run

```bash
cd /opt/feishu-project-delivery-cycle-updater
PYTHON_BIN=/opt/feishu-project-delivery-cycle-updater/.venv/bin/python \
BITABLE_PUBLISHER=/opt/feishu-project-delivery-cycle-updater/feishu-online-sheets/scripts/publish_bitable.py \
/bin/bash server/run_refresh.sh
```

Run through a specific completed Sunday:

```bash
/bin/bash server/run_refresh.sh 2026-06-14
```

## Logs

```bash
tail -n 200 automation/logs/project_delivery_cycle_weekly.log
```

## Pre-Write Validation

Probe fields:

```bash
cd automation
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

Check for:

- `table_fields` includes the expected target fields.
- `skip_fields` includes `执行日期`, `研发时长/测试时长`, and `created_at`.
- `unique_fields` is `季度 + 周次 + 需求分类`.
- `planned_rows` is limited to the latest completed week categories.

## Production Write

```bash
../.venv/bin/python ../feishu-online-sheets/scripts/publish_bitable.py \
  --config config/feishu_bitable_publish.json \
  --upsert
```

Do not use `--sync-stale` in the weekly job. The generated source contains only the latest week, so stale sync would delete historical week rows.

## Common Failures

### `99991672 Access denied` or `91403 Forbidden`

Check:

- The Feishu app ID and secret are the correct app.
- The app has Base permissions.
- The app has access to the target app token and table.

### Missing Generated CSV

Run the full refresh entry point:

```bash
/bin/bash server/run_refresh.sh
```

Then check:

```text
automation/data/efficiency_datamart/quarter_week_cumulative_metrics.csv
```

### Field Mapping Error

Run `--probe-fields`, compare the target Base field names with `automation/config/feishu_bitable_publish.json`, and update only the mapping that is wrong.

### Unexpected Historical Changes

Confirm the weekly job is not using `--sync-stale` and that `build_quarter_week_cumulative_metrics.py` is called with `--latest-week-only`.

## Secret Handling

- Do not commit `.env.local`.
- Do not paste app secrets or MCP tokens into logs.
- Rotate the Feishu app secret if it appears in chat history or persisted logs.
