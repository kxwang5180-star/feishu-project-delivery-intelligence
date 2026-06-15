from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pmo_agent.config import Settings
from pmo_agent.feishu_mcp_client import FeishuMCPClient, json_text_payload, mcp_tool_payload
from pmo_agent.metrics import moql_field_list_to_record


PROJECT_KEY = "信息科技部"
REPORT_START = "2025-01-01"
REPORT_END = "2026-06-01"
TARGET_STATUSES = ("待验收", "待推广", "已结束")
DEV_ROLE_KEYS = {"QA", "Server", "FE", "UI", "tech_owner", "role_51a0fc", "role_0627a7"}


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key, value)


def append_jsonl(path: Path, row: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def load_jsonl_by_key(path: Path, key: str) -> Dict[str, Dict[str, Any]]:
    if not path.exists():
        return {}
    rows: Dict[str, Dict[str, Any]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get(key) is not None:
            rows[str(row[key])] = row
    return rows


def payload_from_result(result: Dict[str, Any]) -> Dict[str, Any]:
    return mcp_tool_payload(result)


def mql_records(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    grouped = payload.get("data")
    if isinstance(grouped, dict):
        for rows in grouped.values():
            if isinstance(rows, list):
                records.extend(row for row in rows if isinstance(row, dict))
    return records


def record_fields(record: Dict[str, Any]) -> Dict[str, Any]:
    if isinstance(record.get("moql_field_list"), list):
        return moql_field_list_to_record(record["moql_field_list"])
    return record


def value_label(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        labels = [value_label(item) for item in value]
        return "、".join(label for label in labels if label)
    if isinstance(value, dict):
        for key in ("label", "name", "option_name", "value", "key", "id"):
            if value.get(key) not in (None, ""):
                return str(value[key])
        return ""
    return str(value)


def parse_float(value: Any) -> Optional[float]:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def parse_dt(value: Any) -> Optional[datetime]:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        # Feishu timestamps are milliseconds.
        if value > 10_000_000_000:
            return datetime.fromtimestamp(value / 1000)
        return datetime.fromtimestamp(value)
    if isinstance(value, dict):
        if "iso_time" in value:
            return parse_dt(value["iso_time"])
        if "timestamp" in value:
            return parse_dt(value["timestamp"])
    text = str(value).strip()
    if not text:
        return None
    text = text.replace("Z", "+00:00")
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(text[:19] if "%H" in fmt else text[:10], fmt)
        except ValueError:
            pass
    try:
        parsed = datetime.fromisoformat(text)
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone().replace(tzinfo=None)
        return parsed
    except ValueError:
        return None


def user_key(user: Dict[str, Any]) -> str:
    return str(user.get("user_key") or user.get("key") or user.get("username") or user.get("email") or user.get("name") or "")


def add_user(users: set[str], user: Any) -> None:
    if isinstance(user, dict):
        key = user_key(user)
        if key:
            users.add(key)


def parse_subtask_owner(value: Any) -> Iterable[str]:
    if not value:
        return []
    if isinstance(value, list):
        result = []
        for item in value:
            if isinstance(item, dict):
                result.append(str(item.get("username") or item.get("user_key") or item.get("key") or ""))
        return [item for item in result if item]
    text = str(value)
    try:
        parsed = json.loads(text)
        return parse_subtask_owner(parsed)
    except Exception:
        return re.findall(r'"username"\s*:\s*"([^"]+)"', text)


def role_sets(brief: Dict[str, Any]) -> Tuple[set[str], set[str]]:
    all_users: set[str] = set()
    dev_users: set[str] = set()
    attr = brief.get("payload", {}).get("work_item_attribute") or brief.get("work_item_attribute") or {}
    for role in attr.get("role_members") or []:
        role_key = str(role.get("key") or "")
        for member in role.get("members") or []:
            key = user_key(member)
            if not key:
                continue
            all_users.add(key)
            if role_key in DEV_ROLE_KEYS:
                dev_users.add(key)
    return all_users, dev_users


def node_metrics(node_entry: Dict[str, Any], role_all: set[str], role_dev: set[str]) -> Dict[str, Any]:
    users = set(role_all)
    dev_users = set(role_dev)
    schedule_starts: List[datetime] = []
    payload = node_entry.get("payload") or {}
    for node in payload.get("list") or []:
        assignees = node.get("assignees") or {}
        for owner in assignees.get("owners") or []:
            add_user(users, owner)
        role_assignees = assignees.get("role_assignees") or {}
        if isinstance(role_assignees, dict):
            for role_key, members in role_assignees.items():
                for member in members or []:
                    add_user(users, member)
                    if role_key in DEV_ROLE_KEYS:
                        add_user(dev_users, member)
        schedule = node.get("schedule") or {}
        dt = parse_dt(schedule.get("estimate_start_time"))
        if dt:
            schedule_starts.append(dt)
        for item in node.get("assignee_schedule_list") or []:
            schedule_info = item.get("schedule_info") or {}
            dt = parse_dt(schedule_info.get("estimate_start_time"))
            if dt:
                schedule_starts.append(dt)
        for task in node.get("sub_tasks") or []:
            for key in parse_subtask_owner(task.get("owner")):
                users.add(key)
            dt = parse_dt(task.get("estimate_start_date"))
            if dt:
                schedule_starts.append(dt)
    earliest = min(schedule_starts) if schedule_starts else None
    return {
        "participant_count": len(users),
        "dev_participant_count": len(dev_users),
        "earliest_schedule_start": earliest.isoformat(sep=" ") if earliest else None,
    }


def month_key(dt: datetime) -> str:
    return dt.strftime("%Y-%m")


def quarter_key(dt: datetime) -> str:
    return f"{dt.year}-Q{((dt.month - 1) // 3) + 1}"


def size_band(person_days: Optional[float]) -> str:
    if person_days is None:
        return "未分型"
    if person_days <= 20:
        return "小需求"
    if person_days <= 60:
        return "中需求"
    if person_days <= 120:
        return "大需求"
    return "超大需求"


def avg(values: Sequence[Optional[float]]) -> Optional[float]:
    nums = [float(v) for v in values if v is not None]
    return round(mean(nums), 2) if nums else None


def med(values: Sequence[Optional[float]]) -> Optional[float]:
    nums = [float(v) for v in values if v is not None]
    return round(median(nums), 2) if nums else None


async def call_tool(client: FeishuMCPClient, name: str, args: Dict[str, Any], retries: int = 3) -> Dict[str, Any]:
    last: Optional[Exception] = None
    for attempt in range(retries):
        try:
            return payload_from_result(await client.call_tool(name, args))
        except Exception as exc:
            last = exc
            await asyncio.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"{name} failed after {retries} attempts: {last}")


async def collect_base(client: FeishuMCPClient, out_dir: Path, force: bool = False) -> List[Dict[str, Any]]:
    base_path = out_dir / "demand_base.jsonl"
    if base_path.exists() and not force:
        return list(load_jsonl_by_key(base_path, "work_item_id").values())
    if base_path.exists():
        base_path.unlink()

    mql = f"""
SELECT `work_item_id`, `name`, `work_item_status`, `field_584a64`, `field_fba983`, `field_db341e`, `field_040f76`, `field_715f2b`, `field_142721`, `field_81ce0b`
FROM `信息科技部`.`需求`
WHERE `field_584a64` between '{REPORT_START}' and '{REPORT_END}'
AND `template` = '需求处理流程'
AND `work_item_status` in ('待验收', '待推广', '已结束')
ORDER BY `field_584a64` ASC
""".strip()
    payload = await call_tool(client, "search_by_mql", {"project_key": PROJECT_KEY, "mql": mql})
    session_id = payload.get("session_id")
    total = int((((payload.get("list") or [{}])[0]).get("count")) or 0)
    group_id = str(((((payload.get("list") or [{}])[0]).get("group_infos") or [{}])[0]).get("group_id") or "1")
    records = mql_records(payload)

    page = 1
    while len(records) < total:
        page += 1
        payload_page = await call_tool(
            client,
            "search_by_mql",
            {"project_key": PROJECT_KEY, "session_id": session_id, "group_pagination_list": [{"group_id": group_id, "page_num": page}]},
        )
        page_records = mql_records(payload_page)
        if not page_records:
            break
        records.extend(page_records)

    rows: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for record in records:
        fields = record_fields(record)
        wid = str(fields.get("work_item_id") or "")
        if not wid or wid in seen:
            continue
        seen.add(wid)
        online = parse_dt(fields.get("field_584a64"))
        row = {
            "work_item_id": wid,
            "name": fields.get("name") or "",
            "status": value_label(fields.get("work_item_status")),
            "online_time": online.isoformat(sep=" ") if online else None,
            "person_days": parse_float(fields.get("field_fba983")),
            "dev_person_days": parse_float(fields.get("field_db341e")),
            "ui_person_days": parse_float(fields.get("field_040f76")),
            "qa_person_days": parse_float(fields.get("field_715f2b")),
            "pm_person_days": parse_float(fields.get("field_142721")),
            "algo_person_days": parse_float(fields.get("field_81ce0b")),
        }
        append_jsonl(base_path, row)
        rows.append(row)
    return rows


async def enrich_one(client: FeishuMCPClient, base: Dict[str, Any], brief_cache: Dict[str, Dict[str, Any]], node_cache: Dict[str, Dict[str, Any]], out_dir: Path) -> Dict[str, Any]:
    wid = base["work_item_id"]
    if wid not in brief_cache:
        brief_payload = await call_tool(client, "get_workitem_brief", {"project_key": PROJECT_KEY, "work_item_id": wid})
        brief_cache[wid] = {"work_item_id": wid, "payload": brief_payload}
        append_jsonl(out_dir / "workitem_brief.jsonl", brief_cache[wid])
    if wid not in node_cache:
        all_nodes: List[Dict[str, Any]] = []
        page = 1
        has_more = True
        while has_more:
            node_payload = await call_tool(
                client,
                "get_node_detail",
                {
                    "project_key": PROJECT_KEY,
                    "work_item_id": wid,
                    "field_key_list": ["name", "owner", "schedule", "actual_begin_time"],
                    "need_sub_task": True,
                    "page_num": page,
                },
            )
            all_nodes.extend(node_payload.get("list") or [])
            pagination = node_payload.get("pagination") or {}
            has_more = bool(pagination.get("has_more"))
            page += 1
        node_cache[wid] = {"work_item_id": wid, "payload": {"list": all_nodes}}
        append_jsonl(out_dir / "node_detail.jsonl", node_cache[wid])

    role_all, role_dev = role_sets(brief_cache[wid])
    metrics = node_metrics(node_cache[wid], role_all, role_dev)
    online = parse_dt(base.get("online_time"))
    start = parse_dt(metrics.get("earliest_schedule_start"))
    delivery_days = None
    if online and start and online >= start:
        delivery_days = float((online.date() - start.date()).days)
    return {**base, **metrics, "delivery_cycle_days": delivery_days, "size_band": size_band(base.get("person_days"))}


async def enrich_all(client: FeishuMCPClient, base_rows: List[Dict[str, Any]], out_dir: Path, limit: Optional[int] = None, concurrency: int = 4) -> List[Dict[str, Any]]:
    enhanced_path = out_dir / "enhanced_metrics.jsonl"
    enhanced_cache = load_jsonl_by_key(enhanced_path, "work_item_id")
    brief_cache = load_jsonl_by_key(out_dir / "workitem_brief.jsonl", "work_item_id")
    node_cache = load_jsonl_by_key(out_dir / "node_detail.jsonl", "work_item_id")
    rows: List[Dict[str, Any]] = list(enhanced_cache.values())
    todo = [row for row in base_rows if row["work_item_id"] not in enhanced_cache]
    if limit:
        todo = todo[:limit]
    sem = asyncio.Semaphore(concurrency)
    completed = 0

    async def run(row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        nonlocal completed
        async with sem:
            try:
                enhanced = await enrich_one(client, row, brief_cache, node_cache, out_dir)
                append_jsonl(enhanced_path, enhanced)
                completed += 1
                if completed % 20 == 0:
                    print(f"enriched {completed}/{len(todo)}")
                return enhanced
            except Exception as exc:
                append_jsonl(out_dir / "errors.jsonl", {"work_item_id": row["work_item_id"], "error": str(exc)})
                return None

    new_rows = await asyncio.gather(*(run(row) for row in todo))
    rows.extend(row for row in new_rows if row)
    by_id = {row["work_item_id"]: row for row in rows}
    return list(by_id.values())


def summarize(rows: List[Dict[str, Any]], key: str, include_q2: bool = True) -> List[Dict[str, Any]]:
    groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        online = parse_dt(row.get("online_time"))
        if not online:
            continue
        group_key = month_key(online) if key == "month" else quarter_key(online)
        if key == "quarter" and not include_q2 and group_key == "2026-Q2":
            continue
        groups[group_key].append(row)
    result = []
    for group_key in sorted(groups):
        items = groups[group_key]
        sizes = Counter(item.get("size_band") or "未分型" for item in items)
        result.append(
            {
                key: group_key,
                "demand_count": len(items),
                "avg_delivery_cycle_days": avg([item.get("delivery_cycle_days") for item in items]),
                "median_delivery_cycle_days": med([item.get("delivery_cycle_days") for item in items]),
                "delivery_valid_count": len([item for item in items if item.get("delivery_cycle_days") is not None]),
                "avg_person_days": avg([item.get("person_days") for item in items]),
                "avg_dev_person_days": avg([item.get("dev_person_days") for item in items]),
                "avg_participant_count": avg([item.get("participant_count") for item in items]),
                "avg_dev_participant_count": avg([item.get("dev_participant_count") for item in items]),
                "small": sizes.get("小需求", 0),
                "medium": sizes.get("中需求", 0),
                "large": sizes.get("大需求", 0),
                "xlarge": sizes.get("超大需求", 0),
            }
        )
    return result


def summarize_size(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    order = ["小需求", "中需求", "大需求", "超大需求", "未分型"]
    groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[row.get("size_band") or "未分型"].append(row)
    result = []
    for band in order:
        items = groups.get(band) or []
        if not items:
            continue
        result.append(
            {
                "size_band": band,
                "demand_count": len(items),
                "avg_delivery_cycle_days": avg([item.get("delivery_cycle_days") for item in items]),
                "median_delivery_cycle_days": med([item.get("delivery_cycle_days") for item in items]),
                "avg_person_days": avg([item.get("person_days") for item in items]),
                "avg_dev_person_days": avg([item.get("dev_person_days") for item in items]),
                "avg_participant_count": avg([item.get("participant_count") for item in items]),
                "avg_dev_participant_count": avg([item.get("dev_participant_count") for item in items]),
                "dev_effort_ratio": ratio_sum(items, "dev_person_days", "person_days"),
                "dev_days_per_dev_person": ratio_avg(items, "dev_person_days", "dev_participant_count"),
                "participant_dev_ratio": ratio_avg(items, "participant_count", "dev_participant_count"),
            }
        )
    return result


def summarize_size_monthly(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    groups: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    order = {"小需求": 0, "中需求": 1, "大需求": 2, "超大需求": 3, "未分型": 4}
    for row in rows:
        online = parse_dt(row.get("online_time"))
        if not online:
            continue
        groups[(month_key(online), row.get("size_band") or "未分型")].append(row)
    result = []
    for (month, band), items in sorted(groups.items(), key=lambda item: (item[0][0], order.get(item[0][1], 9))):
        result.append(
            {
                "month": month,
                "size_band": band,
                "demand_count": len(items),
                "avg_delivery_cycle_days": avg([item.get("delivery_cycle_days") for item in items]),
                "median_delivery_cycle_days": med([item.get("delivery_cycle_days") for item in items]),
                "avg_person_days": avg([item.get("person_days") for item in items]),
                "avg_dev_person_days": avg([item.get("dev_person_days") for item in items]),
                "avg_participant_count": avg([item.get("participant_count") for item in items]),
                "avg_dev_participant_count": avg([item.get("dev_participant_count") for item in items]),
                "dev_effort_ratio": ratio_sum(items, "dev_person_days", "person_days"),
                "dev_days_per_dev_person": ratio_avg(items, "dev_person_days", "dev_participant_count"),
            }
        )
    return result


def ratio_sum(rows: Sequence[Dict[str, Any]], numerator: str, denominator: str) -> Optional[float]:
    n = sum(float(row.get(numerator) or 0) for row in rows)
    d = sum(float(row.get(denominator) or 0) for row in rows)
    return round(n / d, 2) if d else None


def ratio_avg(rows: Sequence[Dict[str, Any]], numerator: str, denominator: str) -> Optional[float]:
    n = avg([row.get(numerator) for row in rows])
    d = avg([row.get(denominator) for row in rows])
    return round(n / d, 2) if n is not None and d not in (None, 0) else None


def write_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    keys = list(rows[0].keys())
    lines = [",".join(keys)]
    for row in rows:
        lines.append(",".join("" if row.get(key) is None else str(row.get(key)) for key in keys))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def svg_escape(value: Any) -> str:
    return str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def write_line_svg(
    path: Path,
    rows: List[Dict[str, Any]],
    *,
    x_key: str,
    series_key: str,
    y_key: str,
    title: str,
    y_label: str,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    width, height = 980, 420
    left, right, top, bottom = 70, 30, 48, 78
    xs = sorted({str(row[x_key]) for row in rows})
    series = [item for item in ["小需求", "中需求", "大需求", "超大需求"] if any(row.get(series_key) == item for row in rows)]
    values = [float(row[y_key]) for row in rows if row.get(y_key) is not None]
    if not xs or not values:
        path.write_text("", encoding="utf-8")
        return
    y_max = max(values) * 1.12 or 1
    x_pos = {x: left + (idx * (width - left - right) / max(len(xs) - 1, 1)) for idx, x in enumerate(xs)}

    def y_pos(value: float) -> float:
        return top + (y_max - value) * (height - top - bottom) / y_max

    colors = {"小需求": "#2563eb", "中需求": "#16a34a", "大需求": "#f59e0b", "超大需求": "#dc2626"}
    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="{left}" y="28" font-size="20" font-weight="700" fill="#111827">{svg_escape(title)}</text>',
        f'<text x="18" y="{top + 10}" font-size="12" fill="#6b7280">{svg_escape(y_label)}</text>',
    ]
    for tick in range(5):
        y_value = y_max * tick / 4
        y = y_pos(y_value)
        elements.append(f'<line x1="{left}" x2="{width-right}" y1="{y:.1f}" y2="{y:.1f}" stroke="#e5e7eb"/>')
        elements.append(f'<text x="{left-8}" y="{y+4:.1f}" text-anchor="end" font-size="11" fill="#6b7280">{y_value:.0f}</text>')
    elements.append(f'<line x1="{left}" x2="{width-right}" y1="{height-bottom}" y2="{height-bottom}" stroke="#9ca3af"/>')
    elements.append(f'<line x1="{left}" x2="{left}" y1="{top}" y2="{height-bottom}" stroke="#9ca3af"/>')
    for idx, x in enumerate(xs):
        if idx % 2 == 0 or len(xs) <= 12:
            elements.append(f'<text x="{x_pos[x]:.1f}" y="{height-44}" text-anchor="end" transform="rotate(-35 {x_pos[x]:.1f},{height-44})" font-size="11" fill="#374151">{x}</text>')
    legend_x = left
    for name in series:
        color = colors.get(name, "#6b7280")
        elements.append(f'<circle cx="{legend_x}" cy="{height-18}" r="5" fill="{color}"/>')
        elements.append(f'<text x="{legend_x+10}" y="{height-14}" font-size="12" fill="#374151">{svg_escape(name)}</text>')
        legend_x += 86
        points = []
        lookup = {str(row[x_key]): row for row in rows if row.get(series_key) == name and row.get(y_key) is not None}
        for x in xs:
            row = lookup.get(x)
            if row:
                points.append((x_pos[x], y_pos(float(row[y_key]))))
        if len(points) >= 2:
            point_str = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
            elements.append(f'<polyline fill="none" stroke="{color}" stroke-width="2.5" points="{point_str}"/>')
        for x, y in points:
            elements.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="{color}"/>')
    elements.append("</svg>")
    path.write_text("\n".join(elements), encoding="utf-8")


def write_bar_svg(path: Path, rows: List[Dict[str, Any]], *, title: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    width, height = 900, 420
    left, right, top, bottom = 72, 24, 54, 70
    bands = [row["size_band"] for row in rows]
    metrics = [
        ("avg_delivery_cycle_days", "交付周期", "#2563eb"),
        ("avg_person_days", "投入人天", "#16a34a"),
        ("avg_dev_person_days", "开发人天", "#f59e0b"),
    ]
    values = [float(row[key]) for row in rows for key, _, _ in metrics if row.get(key) is not None]
    y_max = max(values) * 1.15 if values else 1
    group_w = (width - left - right) / max(len(bands), 1)
    bar_w = group_w / 5

    def y_pos(value: float) -> float:
        return top + (y_max - value) * (height - top - bottom) / y_max

    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="{left}" y="30" font-size="20" font-weight="700" fill="#111827">{svg_escape(title)}</text>',
    ]
    for tick in range(5):
        y_value = y_max * tick / 4
        y = y_pos(y_value)
        elements.append(f'<line x1="{left}" x2="{width-right}" y1="{y:.1f}" y2="{y:.1f}" stroke="#e5e7eb"/>')
        elements.append(f'<text x="{left-8}" y="{y+4:.1f}" text-anchor="end" font-size="11" fill="#6b7280">{y_value:.0f}</text>')
    for i, band in enumerate(bands):
        base_x = left + i * group_w + group_w * 0.18
        row = rows[i]
        for j, (key, label, color) in enumerate(metrics):
            value = float(row.get(key) or 0)
            x = base_x + j * (bar_w + 6)
            y = y_pos(value)
            elements.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{height-bottom-y:.1f}" rx="2" fill="{color}"/>')
        elements.append(f'<text x="{left + i * group_w + group_w/2:.1f}" y="{height-38}" text-anchor="middle" font-size="13" fill="#374151">{svg_escape(band)}</text>')
    legend_x = left
    for _, label, color in metrics:
        elements.append(f'<rect x="{legend_x}" y="{height-20}" width="12" height="12" fill="{color}"/>')
        elements.append(f'<text x="{legend_x+18}" y="{height-10}" font-size="12" fill="#374151">{svg_escape(label)}</text>')
        legend_x += 98
    elements.append("</svg>")
    path.write_text("\n".join(elements), encoding="utf-8")


def write_visuals(fig_dir: Path, size_monthly: List[Dict[str, Any]], size_rows: List[Dict[str, Any]]) -> Dict[str, Path]:
    charts = {
        "scale_bar": fig_dir / "size_efficiency_bar.svg",
        "monthly_person_days": fig_dir / "monthly_size_avg_person_days.svg",
        "monthly_dev_person_days": fig_dir / "monthly_size_avg_dev_person_days.svg",
        "monthly_delivery": fig_dir / "monthly_size_avg_delivery_cycle.svg",
        "monthly_dev_people": fig_dir / "monthly_size_avg_dev_people.svg",
    }
    write_bar_svg(charts["scale_bar"], size_rows, title="不同规模需求的效率指标对比")
    write_line_svg(charts["monthly_person_days"], size_monthly, x_key="month", series_key="size_band", y_key="avg_person_days", title="按规模分月平均投入人天", y_label="人天")
    write_line_svg(charts["monthly_dev_person_days"], size_monthly, x_key="month", series_key="size_band", y_key="avg_dev_person_days", title="按规模分月平均开发人天", y_label="人天")
    write_line_svg(charts["monthly_delivery"], size_monthly, x_key="month", series_key="size_band", y_key="avg_delivery_cycle_days", title="按规模分月平均交付周期", y_label="天")
    write_line_svg(charts["monthly_dev_people"], size_monthly, x_key="month", series_key="size_band", y_key="avg_dev_participant_count", title="按规模分月平均研发人数", y_label="人")
    return charts


def md_table(rows: List[Dict[str, Any]], columns: List[Tuple[str, str]]) -> str:
    lines = ["| " + " | ".join(label for _, label in columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    for row in rows:
        lines.append("| " + " | ".join("" if row.get(key) is None else str(row.get(key)) for key, _ in columns) + " |")
    return "\n".join(lines)


def render_report(
    rows: List[Dict[str, Any]],
    monthly: List[Dict[str, Any]],
    quarterly: List[Dict[str, Any]],
    size_monthly: List[Dict[str, Any]],
    charts: Dict[str, Path],
) -> str:
    valid_delivery = [r for r in rows if r.get("delivery_cycle_days") is not None]
    size_counts = Counter(r.get("size_band") or "未分型" for r in rows)
    title = "2025-01-01 至 2026-06-01 部门需求效率增强版分析"
    top_long = sorted(valid_delivery, key=lambda r: r["delivery_cycle_days"], reverse=True)[:10]
    top_effort = sorted([r for r in rows if r.get("person_days") is not None], key=lambda r: r["person_days"], reverse=True)[:10]
    size_summary = summarize_size(rows)
    cols = [
        ("quarter", "季度"),
        ("demand_count", "需求数"),
        ("avg_delivery_cycle_days", "平均交付周期"),
        ("avg_person_days", "平均投入人天"),
        ("avg_dev_person_days", "平均开发人天"),
        ("avg_participant_count", "平均参与人数"),
        ("avg_dev_participant_count", "平均研发人数"),
        ("small", "小"),
        ("medium", "中"),
        ("large", "大"),
        ("xlarge", "超大"),
    ]
    mcols = [(c if c[0] != "quarter" else ("month", "月份")) for c in cols]
    top_cols = [
        ("work_item_id", "ID"),
        ("name", "需求"),
        ("online_time", "上线时间"),
        ("size_band", "分类"),
        ("person_days", "投入人天"),
        ("delivery_cycle_days", "交付周期"),
        ("participant_count", "参与人数"),
        ("dev_participant_count", "研发人数"),
    ]
    size_cols = [
        ("size_band", "分类"),
        ("demand_count", "需求数"),
        ("avg_delivery_cycle_days", "平均交付周期"),
        ("median_delivery_cycle_days", "交付周期中位数"),
        ("avg_person_days", "平均投入人天"),
        ("avg_dev_person_days", "平均开发人天"),
        ("avg_participant_count", "平均参与人数"),
        ("avg_dev_participant_count", "平均研发人数"),
        ("dev_effort_ratio", "开发人天占比"),
        ("dev_days_per_dev_person", "研发人均开发人天"),
        ("participant_dev_ratio", "参与/研发人数比"),
    ]
    size_month_cols = [
        ("month", "月份"),
        ("size_band", "分类"),
        ("demand_count", "需求数"),
        ("avg_person_days", "平均投入人天"),
        ("avg_dev_person_days", "平均开发人天"),
        ("avg_delivery_cycle_days", "平均交付周期"),
        ("avg_participant_count", "平均参与人数"),
        ("avg_dev_participant_count", "平均研发人数"),
        ("dev_effort_ratio", "开发人天占比"),
        ("dev_days_per_dev_person", "研发人均开发人天"),
    ]
    chart_lines = "\n\n".join(
        [
            f"![不同规模需求的效率指标对比]({charts['scale_bar']})",
            f"![按规模分月平均投入人天]({charts['monthly_person_days']})",
            f"![按规模分月平均开发人天]({charts['monthly_dev_person_days']})",
            f"![按规模分月平均交付周期]({charts['monthly_delivery']})",
            f"![按规模分月平均研发人数]({charts['monthly_dev_people']})",
        ]
    )
    small = next((row for row in size_summary if row["size_band"] == "小需求"), {})
    xlarge = next((row for row in size_summary if row["size_band"] == "超大需求"), {})
    scale_delivery_gap = None
    if small.get("avg_delivery_cycle_days") and xlarge.get("avg_delivery_cycle_days"):
        scale_delivery_gap = round(xlarge["avg_delivery_cycle_days"] / small["avg_delivery_cycle_days"], 2)
    scale_people_gap = None
    if small.get("avg_dev_participant_count") and xlarge.get("avg_dev_participant_count"):
        scale_people_gap = round(xlarge["avg_dev_participant_count"] / small["avg_dev_participant_count"], 2)
    return "\n\n".join(
        [
            f"# {title}",
            "生成时间：2026-06-04\n\n数据来源：飞书项目 MCP。本报告不展开验收状态讨论，仅按已确认状态样本合并统计。",
            "## 一、口径\n\n- 周期：2025-01-01 至 2026-06-01。\n- 流程：需求处理流程。\n- 需求状态：已结束、待验收、待推广合并统计。\n- 交付周期：项目上线时间 - 全部节点/子任务最早排期开始时间。\n- 需求分类：小需求 <=20；中需求 21-60；大需求 61-120；超大需求 >120。",
            f"## 二、总体结果\n\n- 样本需求：{len(rows)} 条。\n- 可计算交付周期：{len(valid_delivery)} 条。\n- 平均交付周期：{avg([r.get('delivery_cycle_days') for r in rows])} 天；中位数：{med([r.get('delivery_cycle_days') for r in rows])} 天。\n- 平均投入人天：{avg([r.get('person_days') for r in rows])}。\n- 平均开发人天：{avg([r.get('dev_person_days') for r in rows])}。\n- 平均参与人数：{avg([r.get('participant_count') for r in rows])}。\n- 平均研发人数：{avg([r.get('dev_participant_count') for r in rows])}。\n- 分类分布：小 {size_counts.get('小需求',0)}，中 {size_counts.get('中需求',0)}，大 {size_counts.get('大需求',0)}，超大 {size_counts.get('超大需求',0)}。",
            "## 三、季度趋势\n\n" + md_table(quarterly, cols),
            "## 四、月度趋势\n\n" + md_table(monthly, mcols),
            "## 五、规模分层效率\n\n" + md_table(size_summary, size_cols),
            "## 六、按规模的月度趋势\n\n" + md_table(size_monthly, size_month_cols),
            "## 七、可视化图表\n\n" + chart_lines,
            "## 八、交付周期最长需求 Top 10\n\n" + md_table(top_long, top_cols),
            "## 九、投入人天最高需求 Top 10\n\n" + md_table(top_effort, top_cols),
            "## 十、补充指标与提升点\n\n"
            f"1. 规模放大效应明显：超大需求平均交付周期是小需求的 {scale_delivery_gap or 'N/A'} 倍，平均研发人数是小需求的 {scale_people_gap or 'N/A'} 倍。建议超大需求单独进入专项治理，不纳入普通需求平均值考核。\n"
            "2. 开发人天占比可作为研发投入结构指标。若某月开发人天占比下降但交付周期上升，通常说明非开发环节、跨角色协同或等待时间成为瓶颈。\n"
            "3. 研发人均开发人天可作为并行度指标。人均开发人天过低时，可能存在多人参与但任务拆分不足、沟通成本高的问题；过高时则可能存在关键人员瓶颈。\n"
            "4. 参与/研发人数比可作为协作复杂度指标。比值越高，说明产品、评审、测试、安全、合规等协同角色越多，应加强前置评审和变更控制。\n"
            "5. 月度趋势建议按规模分层看，不建议把小需求和超大需求混成一个平均值判断效率。后续可设置规模分层目标，例如小需求关注交付周期，中/大需求关注开发人天和研发人数，超大需求关注阶段拆分和里程碑治理。\n"
            "6. 后续复用本地缓存可直接增量补齐，不需要重复查询已完成需求明细。",
        ]
    ) + "\n"


async def main() -> None:
    global REPORT_START, REPORT_END
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--force-base", action="store_true")
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--start", default=REPORT_START)
    parser.add_argument("--end", default=REPORT_END)
    args = parser.parse_args()

    REPORT_START = args.start
    REPORT_END = args.end

    root = Path(__file__).resolve().parents[1]
    load_env(root / ".env.local")
    out_dir = root / "data" / "efficiency_enhanced"
    out_dir.mkdir(parents=True, exist_ok=True)
    settings = Settings.from_env()
    client = FeishuMCPClient(settings)
    await client.initialize()
    base_rows = await collect_base(client, out_dir, force=args.force_base)
    print(f"base rows: {len(base_rows)}")
    rows = await enrich_all(client, base_rows, out_dir, limit=args.limit, concurrency=args.concurrency)
    print(f"enhanced rows: {len(rows)}")

    monthly = summarize(rows, "month")
    quarterly = summarize(rows, "quarter", include_q2=True)
    size_rows = summarize_size(rows)
    size_monthly = summarize_size_monthly(rows)
    write_csv(out_dir / "monthly_summary.csv", monthly)
    write_csv(out_dir / "quarterly_summary.csv", quarterly)
    write_csv(out_dir / "size_summary.csv", size_rows)
    write_csv(out_dir / "size_monthly_summary.csv", size_monthly)
    charts = write_visuals(root / "reports" / "figures", size_monthly, size_rows)
    report = render_report(rows, monthly, quarterly, size_monthly, charts)
    report_path = root / "reports" / "2025-01-01至2026-06-01 部门需求效率增强版分析.md"
    report_path.write_text(report, encoding="utf-8")
    print(str(report_path))


if __name__ == "__main__":
    asyncio.run(main())
