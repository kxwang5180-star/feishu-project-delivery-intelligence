# Operations

## First-Time Setup

1. Create a Python virtual environment.
2. Install `requirements.txt`.
3. Copy `feishu-online-sheets/` into `~/.codex/skills/` if Codex skill discovery is required.
4. Create `automation/.env.local`.
5. Create `automation/config/feishu_bitable_publish.json`.
6. Run a manual refresh with an explicit date.

## Required Environment Variables

```dotenv
FEISHU_APP_ID=cli_xxx
FEISHU_APP_SECRET=xxx
FEISHU_BASE_URL=https://open.feishu.cn

FEISHU_PROJECT_MCP_URL=xxx
FEISHU_PROJECT_MCP_TOKEN=xxx
MEEGO_PROJECT_KEY=信息科技部
```

## Manual Run

```bash
cd /opt/feishu-project-delivery-cycle-updater/automation
PYTHON_BIN=/opt/feishu-project-delivery-cycle-updater/.venv/bin/python \
BITABLE_PUBLISHER=/opt/feishu-project-delivery-cycle-updater/feishu-online-sheets/scripts/publish_bitable.py \
bash scripts/refresh_project_delivery_cycle_weekly.sh
```

## Backfill

```bash
bash scripts/refresh_project_delivery_cycle_weekly.sh 2026-06-14
```

## Cron

```cron
30 9 * * 1 cd /opt/feishu-project-delivery-cycle-updater/automation && PYTHON_BIN=/opt/feishu-project-delivery-cycle-updater/.venv/bin/python BITABLE_PUBLISHER=/opt/feishu-project-delivery-cycle-updater/feishu-online-sheets/scripts/publish_bitable.py /bin/bash scripts/refresh_project_delivery_cycle_weekly.sh
```

## Logs

```bash
tail -n 200 automation/logs/project_delivery_cycle_weekly.log
```

## Safe Write Procedure

For a new Base/table:

```bash
python feishu-online-sheets/scripts/publish_bitable.py \
  --config automation/config/feishu_bitable_publish.json \
  --probe-fields
```

Then:

```bash
python feishu-online-sheets/scripts/publish_bitable.py \
  --config automation/config/feishu_bitable_publish.json \
  --upsert \
  --sync-stale \
  --dry-run
```

Only after the dry-run looks correct:

```bash
python feishu-online-sheets/scripts/publish_bitable.py \
  --config automation/config/feishu_bitable_publish.json \
  --upsert \
  --sync-stale
```

## Common Failures

### `99991672 Access denied`

The Feishu app is missing required Base scopes or has not been approved/published.

Check:

```text
base:field:read
bitable:app
```

### `91403 Forbidden`

The app can read metadata but cannot create or update records.

Check:

- Base file permissions
- app identity access
- record write scopes

### Missing New Weeks

The local data mart is stale. Run:

```bash
bash scripts/refresh_project_delivery_cycle_weekly.sh <last-sunday>
```

The collection step must pull fresh Feishu Project data before the weekly cumulative CSV is rebuilt.

## Security

- Never commit `.env.local`.
- Rotate app secrets if they were pasted into chat or logs.
- Keep Base tokens and table IDs configurable.
- Keep Feishu Project MCP tokens server-side only.
