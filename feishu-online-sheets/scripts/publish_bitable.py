#!/usr/bin/env python3
"""Publish local CSV rows into a fixed Feishu Base/Bitable table."""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


ENV_FILES = [".env.local", ".env", "feishu.env", "feishu.env.md"]


def load_env(cwd: Path) -> dict[str, str]:
    values = dict(os.environ)
    for name in ENV_FILES:
        path = cwd / name
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if not s or s.startswith("#") or "=" not in s:
                continue
            key, value = s.split("=", 1)
            values.setdefault(key.strip(), value.strip().strip('"').strip("'"))
    return values


def request_json(method: str, url: str, token: str | None = None, body: Any | None = None, timeout: int = 30) -> dict[str, Any]:
    headers = {"Content-Type": "application/json; charset=utf-8"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} calling {url}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Network error calling {url}: {exc}") from exc
    return json.loads(raw) if raw else {}


def tenant_access_token(base_url: str, app_id: str, app_secret: str) -> str:
    data = request_json(
        "POST",
        f"{base_url}/open-apis/auth/v3/tenant_access_token/internal",
        body={"app_id": app_id, "app_secret": app_secret},
    )
    if data.get("code") != 0:
        raise RuntimeError(f"Feishu auth failed: code={data.get('code')} msg={data.get('msg')}")
    token = data.get("tenant_access_token")
    if not token:
        raise RuntimeError("Feishu auth response did not include tenant_access_token")
    return token


def list_fields(base_url: str, token: str, app_token: str, table_id: str) -> list[dict[str, Any]]:
    fields: list[dict[str, Any]] = []
    page_token = ""
    while True:
        query = urllib.parse.urlencode({"page_size": 100, **({"page_token": page_token} if page_token else {})})
        url = f"{base_url}/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/fields?{query}"
        data = request_json("GET", url, token=token)
        if data.get("code") != 0:
            raise RuntimeError(f"Feishu bitable field list failed: code={data.get('code')} msg={data.get('msg')}")
        payload = data.get("data", {})
        fields.extend(payload.get("items", []))
        if not payload.get("has_more"):
            break
        page_token = payload.get("page_token") or ""
    return fields


def read_csv_dicts(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = [dict(r) for r in reader]
        headers = list(reader.fieldnames or [])
    return rows, headers


def read_field_dictionary(path: Path | None) -> dict[str, str]:
    if not path or not path.exists():
        return {}
    mapping: dict[str, str] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            col = row.get("column_name")
            biz = row.get("business_name")
            if col and biz:
                mapping[biz] = col
    return mapping


def convert_value(value: str) -> Any:
    if value is None:
        return None
    text = str(value).strip()
    if text == "":
        return None
    if text in {"True", "TRUE", "true"}:
        return True
    if text in {"False", "FALSE", "false"}:
        return False
    try:
        if "." in text:
            return float(text)
        return int(text)
    except ValueError:
        return text


def build_records(
    rows: list[dict[str, str]],
    headers: list[str],
    bitable_fields: list[dict[str, Any]],
    field_map: dict[str, str],
    dictionary_map: dict[str, str],
    skip_fields: set[str],
    limit: int | None,
) -> tuple[list[dict[str, Any]], list[str]]:
    source_headers = set(headers)
    records: list[dict[str, Any]] = []
    mapped_fields: list[str] = []
    for source_row in rows[:limit]:
        target_fields: dict[str, Any] = {}
        for field in bitable_fields:
            name = field.get("field_name") or field.get("name")
            if not name or name in skip_fields:
                continue
            source_col = field_map.get(name) or (name if name in source_headers else dictionary_map.get(name))
            if not source_col or source_col not in source_row:
                continue
            value = convert_value(source_row.get(source_col, ""))
            if value is None:
                continue
            target_fields[name] = value
            if name not in mapped_fields:
                mapped_fields.append(name)
        if target_fields:
            records.append({"fields": target_fields})
    return records, mapped_fields


def batch_create_records(base_url: str, token: str, app_token: str, table_id: str, records: list[dict[str, Any]], chunk_size: int) -> int:
    written = 0
    for i in range(0, len(records), chunk_size):
        part = records[i : i + chunk_size]
        url = f"{base_url}/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_create"
        data = request_json("POST", url, token=token, body={"records": part})
        if data.get("code") != 0:
            raise RuntimeError(f"Feishu bitable batch_create failed: code={data.get('code')} msg={data.get('msg')} data={data.get('data')}")
        written += len(part)
        time.sleep(0.2)
    return written


def resolve_path(path_text: str, base_dir: Path) -> Path:
    p = Path(path_text).expanduser()
    return p if p.is_absolute() else (base_dir / p).resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish local CSV rows to a Feishu Base/Bitable table.")
    parser.add_argument("--config", required=True, help="JSON config for app_token, table_id, source, mappings, and skip fields")
    parser.add_argument("--probe-fields", action="store_true", help="Only list table fields and planned mappings")
    parser.add_argument("--dry-run", action="store_true", help="Build records but do not write")
    parser.add_argument("--limit", type=int, default=None, help="Limit source rows for testing")
    parser.add_argument("--chunk-size", type=int, default=500, help="Records per batch_create call")
    args = parser.parse_args()

    cwd = Path.cwd()
    env = load_env(cwd)
    base_url = env.get("FEISHU_BASE_URL", "https://open.feishu.cn").rstrip("/")
    app_id = env.get("FEISHU_APP_ID")
    app_secret = env.get("FEISHU_APP_SECRET")
    if not app_id or not app_secret:
        raise SystemExit("Missing FEISHU_APP_ID or FEISHU_APP_SECRET in environment files")

    config_path = resolve_path(args.config, cwd)
    config_dir = config_path.parent
    config = json.loads(config_path.read_text(encoding="utf-8"))
    app_token = config["app_token"]
    table_id = config["table_id"]
    source = resolve_path(config["source"], config_dir)
    field_dictionary = resolve_path(config["field_dictionary"], config_dir) if config.get("field_dictionary") else None

    token = tenant_access_token(base_url, app_id, app_secret)
    fields = list_fields(base_url, token, app_token, table_id)
    rows, headers = read_csv_dicts(source)
    dictionary_map = read_field_dictionary(field_dictionary)
    skip_fields = set(config.get("skip_fields", []))
    field_map = dict(config.get("field_map", {}))
    records, mapped_fields = build_records(rows, headers, fields, field_map, dictionary_map, skip_fields, args.limit)

    summary = {
        "ok": True,
        "app_token": app_token,
        "table_id": table_id,
        "source": str(source),
        "source_rows": len(rows),
        "planned_rows": len(records),
        "table_fields": [f.get("field_name") or f.get("name") for f in fields],
        "skip_fields": sorted(skip_fields),
        "mapped_fields": mapped_fields,
    }

    if args.probe_fields or args.dry_run:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0

    written = batch_create_records(base_url, token, app_token, table_id, records, args.chunk_size)
    print(json.dumps({**summary, "written_rows": written}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        raise SystemExit(1)
