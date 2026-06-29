# Operations

## Normal Run

The production job runs every Monday at 08:00 and publishes only the latest current-quarter cumulative snapshot.

```bash
cd /opt/feishu-project-delivery-intelligence/automation
PYTHON_BIN=/opt/feishu-project-delivery-intelligence/.venv/bin/python \
BITABLE_PUBLISHER=/opt/feishu-project-delivery-intelligence/feishu-online-sheets/scripts/publish_bitable.py \
bash scripts/refresh_project_delivery_cycle_weekly.sh
```

## Manual Backfill

```bash
bash scripts/refresh_project_delivery_cycle_weekly.sh 2026-06-28
```

## Expected Output

The generated source file is:

```text
automation/data/efficiency_datamart/current_quarter_delivery_metrics.csv
```

It should contain two rows:

```text
中小需求
大/超大需求
```

## Safe Write Procedure

Probe:

```bash
python feishu-online-sheets/scripts/publish_bitable.py \
  --config automation/config/feishu_bitable_publish.json \
  --probe-fields
```

Dry-run:

```bash
python feishu-online-sheets/scripts/publish_bitable.py \
  --config automation/config/feishu_bitable_publish.json \
  --upsert \
  --sync-stale \
  --dry-run
```

Publish:

```bash
python feishu-online-sheets/scripts/publish_bitable.py \
  --config automation/config/feishu_bitable_publish.json \
  --upsert \
  --sync-stale
```

## Cron

```cron
0 8 * * 1 cd /opt/feishu-project-delivery-intelligence/automation && PYTHON_BIN=/opt/feishu-project-delivery-intelligence/.venv/bin/python BITABLE_PUBLISHER=/opt/feishu-project-delivery-intelligence/feishu-online-sheets/scripts/publish_bitable.py /bin/bash scripts/refresh_project_delivery_cycle_weekly.sh
```

## Common Checks

- `unique_fields` must be `季度 + 需求分类`.
- `clear_fields` must include `周次`.
- `planned_rows` should normally be `2`.
- The Base table should normally have `2` managed rows after sync.

## Common Failures

### Duplicate rows remain

Run with:

```bash
--upsert --sync-stale
```

The publisher removes duplicate managed keys.

### Week text still appears

Confirm config includes:

```json
"clear_fields": ["周次"]
```

### Missing latest demands

Refresh Feishu Project data first:

```bash
bash scripts/refresh_project_delivery_cycle_weekly.sh <latest-sunday>
```
