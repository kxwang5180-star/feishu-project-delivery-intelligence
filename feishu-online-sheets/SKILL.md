---
name: feishu-online-sheets
description: Publish, overwrite, and refresh fixed Feishu/Lark online spreadsheets from local CSV or XLSX data using Feishu Sheets OpenAPI. Use when the user asks to create a reusable Feishu online table workflow, update an existing fixed spreadsheet, write monthly data into the same cloud sheet, publish a local datamart to 飞书电子表格, or avoid creating new Feishu documents for recurring spreadsheet reports.
---

# Feishu Online Sheets

## Purpose

Use this skill for fixed Feishu online spreadsheet publishing. Prefer it over document-block creation when the output is tabular, large, recurring, or needs to be connected by dashboards.

It also includes a Base/Bitable publisher for `/base/<app_token>?table=<table_id>` URLs when the target is a Feishu 多维表格 rather than a Sheets spreadsheet.

## Decision Rules

- Use an existing fixed spreadsheet when the user says “不要产生新的文档”, “固定文档”, “月度自动更新”, or provides a `/sheets/` URL.
- Use full overwrite for fact and aggregate tables unless the user explicitly requests append-only.
- Keep formulas, definitions, and source field IDs in dictionary sheets instead of embedding them only in report prose.
- Do not use Feishu Docs table blocks for large data tables; they are slow and fragile for many rows.
- Never print `FEISHU_APP_SECRET` or tenant access tokens.

## Required Configuration

Load credentials from `.env.local`, `.env`, `feishu.env`, or `feishu.env.md` in the active workspace.

Required:

```dotenv
FEISHU_APP_ID=cli_xxx
FEISHU_APP_SECRET=replace_locally
FEISHU_BASE_URL=https://open.feishu.cn
```

For fixed spreadsheet updates, provide either a config file or environment variables:

```dotenv
FEISHU_SPREADSHEET_TOKEN=shtcn...
FEISHU_DOC_HOST=https://tenant.feishu.cn
```

Extract `spreadsheet_token` from a URL like:

```text
https://tenant.feishu.cn/sheets/shtcnxxxxxxxx?sheet=xxxx
```

The token is the path segment after `/sheets/`; `sheet_id` is the query value after `sheet=`.

## Standard Workflow

1. Read `references/sheets-openapi.md` when checking endpoints, limits, or permissions.
2. Prepare a JSON config mapping each fixed sheet to one source file.
3. Run a dry run first:

```sh
python3 /Users/kk/.codex/skills/feishu-online-sheets/scripts/publish_sheet.py \
  --config config/feishu_sheets_publish.json \
  --dry-run
```

Probe spreadsheet access before writing when a new token is provided:

```sh
python3 /Users/kk/.codex/skills/feishu-online-sheets/scripts/publish_sheet.py \
  --config config/feishu_sheets_publish.json \
  --probe-spreadsheet
```

4. Run the real update:

```sh
python3 /Users/kk/.codex/skills/feishu-online-sheets/scripts/publish_sheet.py \
  --config config/feishu_sheets_publish.json
```

5. Verify the response summary includes successful writes for every configured sheet.

## Base/Bitable Workflow

For a Feishu Base URL, extract:

```text
https://tenant.feishu.cn/base/<app_token>?table=<table_id>&view=<view_id>
```

Then prepare a config and probe fields:

```sh
python3 /Users/kk/.codex/skills/feishu-online-sheets/scripts/publish_bitable.py \
  --config config/feishu_bitable_publish.json \
  --probe-fields
```

Dry run:

```sh
python3 /Users/kk/.codex/skills/feishu-online-sheets/scripts/publish_bitable.py \
  --config config/feishu_bitable_publish.json \
  --dry-run
```

Publish:

```sh
python3 /Users/kk/.codex/skills/feishu-online-sheets/scripts/publish_bitable.py \
  --config config/feishu_bitable_publish.json
```

Skip formula and auto fields with `skip_fields`, for example:

```json
{
  "skip_fields": ["研发时长/测试时长", "created_at", "执行日期"]
}
```

## Config Shape

```json
{
  "spreadsheet_token": "shtcnxxxxxxxx",
  "clear_before_write": true,
  "max_clear_rows": 2000,
  "sheets": [
    {
      "sheet_id": "abc123",
      "name": "fact_demand_efficiency",
      "source": "data/efficiency_datamart/demand_detail.csv"
    },
    {
      "sheet_id": "def456",
      "name": "agg_period_efficiency",
      "source": "data/efficiency_datamart/monthly_metrics.csv"
    }
  ]
}
```

`sheet_id` is required for writes. `name` is for logs and human readability.

## Data Rules

- Put headers in row 1.
- Use stable English field names in the first row; put Chinese display names in a dictionary sheet.
- Use `work_item_id` as the primary key for demand detail tables.
- For recurring analytics, write these tabs by convention:
  - `fact_demand_efficiency`
  - `agg_period_efficiency`
  - `dim_metric`
  - `dim_field_source`
  - `dim_size_rule`
  - `refresh_log`
- Split very large tables into chunks of 5000 rows or fewer per request.

## Monthly Automation Pattern

For monthly refreshes:

1. Generate local CSV/XLSX data from the source system.
2. Publish to the same Feishu spreadsheet token.
3. Overwrite fact and aggregate sheets.
4. Append or overwrite `refresh_log` according to the user’s audit requirement.
5. Keep cloud docs and reports linked to the fixed spreadsheet.

Use app automations or server cron for scheduling; the skill only defines the publishing workflow.
