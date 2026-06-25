#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ROOT_DIR}/.env.local"
CONFIG_FILE="${ROOT_DIR}/config/feishu_bitable_publish.json"
LOG_DIR="${ROOT_DIR}/logs"
END_DATE="${1:-}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
BITABLE_PUBLISHER="${BITABLE_PUBLISHER:-${HOME}/.codex/skills/feishu-online-sheets/scripts/publish_bitable.py}"

mkdir -p "${LOG_DIR}"

if [[ -f "${ENV_FILE}" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
  set +a
fi

if [[ -z "${END_DATE}" ]]; then
  END_DATE="$("${PYTHON_BIN}" - <<'PY'
from datetime import date, timedelta
today = date.today()
days_since_sunday = (today.weekday() + 1) % 7
print(today - timedelta(days=days_since_sunday or 7))
PY
)"
fi

{
  echo "=== refresh_project_delivery_cycle_weekly $(date '+%F %T') end=${END_DATE} ==="
  cd "${ROOT_DIR}"
  "${PYTHON_BIN}" scripts/collect_efficiency_enhanced.py --force-base --end "${END_DATE}"
  "${PYTHON_BIN}" scripts/export_efficiency_datamart.py
  "${PYTHON_BIN}" scripts/build_quarter_week_cumulative_metrics.py --end "${END_DATE}" --latest-week-only
  "${PYTHON_BIN}" "${BITABLE_PUBLISHER}" --config "${CONFIG_FILE}" --upsert
} >> "${LOG_DIR}/project_delivery_cycle_weekly.log" 2>&1
