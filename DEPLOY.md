# Server Deployment

## 1. Prepare Feishu App Permissions

In Feishu Open Platform, enable and approve these scopes for the app:

```text
sheets:spreadsheet
drive:drive.metadata:readonly
```

Grant the app access to the target spreadsheet if the file is not accessible tenant-wide.

## 2. Install On Server

```sh
cd /opt
git clone <your-github-repo-url> feishu-online-sheets-skill
cd feishu-online-sheets-skill
```

Python 3 is enough for CSV publishing. Install `openpyxl` only if you publish XLSX sources:

```sh
python3 -m pip install openpyxl
```

## 3. Configure Secrets

```sh
cp server/env.example server/.env
chmod 600 server/.env
```

Edit `server/.env`:

```dotenv
FEISHU_APP_ID=cli_xxx
FEISHU_APP_SECRET=xxx
FEISHU_BASE_URL=https://open.feishu.cn
FEISHU_SPREADSHEET_TOKEN=xxx
```

## 4. Configure Sheet Mapping

```sh
mkdir -p config
cp examples/feishu_sheets_publish.example.json config/feishu_sheets_publish.json
```

Edit `config/feishu_sheets_publish.json` and replace:

- `spreadsheet_token`
- every `sheet_id`
- every local `source` path

## 5. Probe Access

```sh
set -a
source server/.env
set +a

python3 feishu-online-sheets/scripts/publish_sheet.py \
  --config config/feishu_sheets_publish.json \
  --probe-spreadsheet
```

Expected result:

```json
{
  "ok": true
}
```

If you see `99991672 No permission`, fix Feishu app scopes or file authorization.

## 6. Dry Run

```sh
python3 feishu-online-sheets/scripts/publish_sheet.py \
  --config config/feishu_sheets_publish.json \
  --dry-run
```

## 7. Publish Once

```sh
bash server/run_refresh.sh
```

Check logs:

```sh
tail -n 100 logs/feishu_sheet_refresh.log
```

## 8. Enable Monthly Cron

```sh
crontab -e
```

Add:

```cron
30 9 5 * * cd /opt/feishu-online-sheets-skill && /bin/bash server/run_refresh.sh
```

This runs at 09:30 on the 5th day of every month.

## 9. Update The Skill In Codex

If the server also runs Codex:

```sh
mkdir -p ~/.codex/skills
cp -R feishu-online-sheets ~/.codex/skills/
```

Restart Codex after copying the skill.
