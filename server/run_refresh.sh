#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AUTOMATION_DIR="${ROOT_DIR}/automation"
END_DATE="${1:-}"

cd "${AUTOMATION_DIR}"
PYTHON_BIN="${PYTHON_BIN:-${ROOT_DIR}/.venv/bin/python}" \
BITABLE_PUBLISHER="${BITABLE_PUBLISHER:-${ROOT_DIR}/feishu-online-sheets/scripts/publish_bitable.py}" \
/bin/bash scripts/refresh_project_delivery_cycle_weekly.sh "${END_DATE}"
