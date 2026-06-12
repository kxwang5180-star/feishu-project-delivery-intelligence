# Feishu Online Sheets Skill

This repository packages a Codex skill and a reusable publishing script for writing local CSV/XLSX data into a fixed Feishu/Lark online spreadsheet.

It is designed for recurring data mart refreshes where the spreadsheet must stay stable and monthly jobs must overwrite the same sheets instead of creating new Feishu documents.

## Contents

```text
feishu-online-sheets/
  SKILL.md
  scripts/publish_sheet.py
  references/sheets-openapi.md
  references/example-config.json
examples/
  feishu_sheets_publish.example.json
server/
  env.example
  monthly-refresh.cron
  run_refresh.sh
```

## What It Does

- Authenticates with Feishu OpenAPI by app ID and app secret.
- Reads local CSV or XLSX tables.
- Writes data into a fixed Feishu spreadsheet by `spreadsheet_token` and `sheet_id`.
- Supports dry-run and spreadsheet access probing.
- Supports full overwrite by clearing a bounded range before writing new data.

## Required Feishu Permissions

The Feishu app must have spreadsheet permissions enabled and approved.

Minimum recommended scopes:

```text
sheets:spreadsheet
drive:drive.metadata:readonly
```

If the file-level permission is restricted, grant the app access to the target spreadsheet.

## Local Usage

Copy the example config:

```sh
cp examples/feishu_sheets_publish.example.json config/feishu_sheets_publish.json
```

Edit:

```json
{
  "spreadsheet_token": "replace_with_fixed_feishu_spreadsheet_token",
  "sheets": [
    {
      "sheet_id": "replace_fact_sheet_id",
      "source": "../data/efficiency_datamart/demand_detail.csv"
    }
  ]
}
```

Probe spreadsheet access:

```sh
python3 feishu-online-sheets/scripts/publish_sheet.py \
  --config config/feishu_sheets_publish.json \
  --probe-spreadsheet
```

Dry run:

```sh
python3 feishu-online-sheets/scripts/publish_sheet.py \
  --config config/feishu_sheets_publish.json \
  --dry-run
```

Publish:

```sh
python3 feishu-online-sheets/scripts/publish_sheet.py \
  --config config/feishu_sheets_publish.json
```

## Install As A Codex Skill

Copy the skill folder into Codex skills:

```sh
mkdir -p ~/.codex/skills
cp -R feishu-online-sheets ~/.codex/skills/
```

Restart Codex so the skill metadata is reloaded.

## Current Known Blocker

The Feishu app credentials currently authenticate successfully, but spreadsheet probing returned:

```text
99991672 No permission
```

Open the required Sheets/Drive scopes in Feishu Open Platform, then rerun `--probe-spreadsheet`.
