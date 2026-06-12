# Feishu Sheets OpenAPI Notes

## Core Endpoints

- Tenant access token: `POST /open-apis/auth/v3/tenant_access_token/internal`
- Read range: `GET /open-apis/sheets/v2/spreadsheets/:spreadsheetToken/values/:range`
- Write one range: `PUT /open-apis/sheets/v2/spreadsheets/:spreadsheetToken/values`
- Write multiple ranges: `POST /open-apis/sheets/v2/spreadsheets/:spreadsheetToken/values_batch_update`
- Append data: `POST /open-apis/sheets/v2/spreadsheets/:spreadsheetToken/values_append`
- Spreadsheet metadata: `GET /open-apis/sheets/v2/spreadsheets/:spreadsheetToken/metainfo`

Official docs state that `spreadsheetToken` identifies the spreadsheet, `sheetId` identifies a worksheet, and ranges use `<sheetId>!A1:B5` notation.

## Permissions

The Feishu app must have at least one Sheets editing scope enabled and must be authorized for the target tenant and target file. The app identity also needs access to the target spreadsheet if the file is not globally accessible to the app.

Typical capability needed:

- 查看、评论、编辑和管理电子表格
- or 查看、评论、编辑和管理云空间中所有文件

## Limits

For write/append data APIs, use request chunks no larger than 5000 rows and 100 columns. Keep payloads smaller when values are long.

## Recommended Update Strategy

For recurring data mart publishing:

- Use full overwrite for fact and aggregate sheets.
- Write exact data ranges starting at `A1`.
- Clear trailing stale content by writing blank strings across a bounded rectangle before writing new values.
- Keep a `refresh_log` sheet for batch id, refresh time, row counts, and status.

## Troubleshooting

- `99991663` or permission-style errors: check app scopes and file authorization.
- Token success but write failure: confirm the spreadsheet belongs to the same tenant and the app has access.
- URL parsing mistakes: token is after `/sheets/`; sheet ID is the `sheet=` query parameter.
- Slow document creation: switch from Docs table blocks to Sheets APIs; do not publish large tables as document blocks.
