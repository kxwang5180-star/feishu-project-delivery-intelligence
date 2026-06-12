#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ROOT_DIR}/server/.env"
CONFIG_FILE="${ROOT_DIR}/config/feishu_sheets_publish.json"
LOG_DIR="${ROOT_DIR}/logs"

mkdir -p "${LOG_DIR}"

if [[ -f "${ENV_FILE}" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
  set +a
fi

python3 "${ROOT_DIR}/feishu-online-sheets/scripts/publish_sheet.py" \
  --config "${CONFIG_FILE}" \
  >> "${LOG_DIR}/feishu_sheet_refresh.log" 2>&1
