from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from .efficiency_fields import EfficiencyFieldConfig
from .periods import InspectionPeriod


DEFAULT_SPACE = "信息科技部"
DEFAULT_TYPE = "需求"
EFFICIENCY_TARGET_STATUSES = ("待验收", "待推广", "已结束")


def _table(project_name: str, work_item_type: str) -> str:
    return f"`{project_name or DEFAULT_SPACE}`.`{work_item_type or DEFAULT_TYPE}`"


def _date_range(field: str, period: InspectionPeriod) -> str:
    return f"`{field}` between '{period.start.isoformat()}' and '{period.end.isoformat()}'"


def efficiency_status_clause() -> str:
    return ", ".join(f"'{status}'" for status in EFFICIENCY_TARGET_STATUSES)


def updated_demands(project_name: str, work_item_type: str, period: InspectionPeriod) -> str:
    return f"""
SELECT `work_item_id`, `name`, `work_item_status`, `current_status_operator`, `priority`, `start_time`, `updated_at`, `exp_time`
FROM {_table(project_name, work_item_type)}
WHERE {_date_range("updated_at", period)}
ORDER BY `updated_at` DESC
""".strip()


def created_demands(project_name: str, work_item_type: str, period: InspectionPeriod) -> str:
    return f"""
SELECT `work_item_id`, `name`, `work_item_status`, `current_status_operator`, `priority`, `start_time`, `updated_at`, `exp_time`
FROM {_table(project_name, work_item_type)}
WHERE {_date_range("start_time", period)}
ORDER BY `start_time` DESC
""".strip()


def completed_demands(project_name: str, work_item_type: str, period: InspectionPeriod) -> str:
    return f"""
SELECT `work_item_id`, `name`, `work_item_status`, `current_status_operator`, `priority`, `updated_at`, `exp_time`
FROM {_table(project_name, work_item_type)}
WHERE {_date_range("updated_at", period)}
AND `work_item_status` in ('已结束', '已终止')
ORDER BY `updated_at` DESC
""".strip()


def yearly_completed_demands(project_name: str, work_item_type: str, period: InspectionPeriod) -> str:
    return completed_efficiency_demands(project_name, work_item_type, period.start, period.end)


def completed_efficiency_demands(
    project_name: str,
    work_item_type: str,
    start: date,
    end: date,
    fields: Optional[EfficiencyFieldConfig] = None,
) -> str:
    field_config = fields or EfficiencyFieldConfig.from_env()
    base_fields = [
        "work_item_id",
        "name",
        "work_item_status",
        "current_status_operator",
        "priority",
        "start_time",
        "updated_at",
        "exp_time",
    ]
    select_fields = base_fields + [field for field in field_config.select_fields() if field not in base_fields]
    select_clause = ", ".join(f"`{field}`" for field in select_fields)
    return f"""
SELECT {select_clause}
FROM {_table(project_name, work_item_type)}
WHERE `{field_config.online_time}` between '{start.isoformat()}' and '{end.isoformat()}'
AND `work_item_status` in ({efficiency_status_clause()})
AND `{field_config.flow_type}` = '{field_config.flow_type_value}'
ORDER BY `{field_config.online_time}` ASC
""".strip()


def efficiency_field_probe_query(project_name: str, work_item_type: str, start: date, end: date, field: str) -> str:
    return f"""
SELECT `work_item_id`, `name`, `work_item_status`, `updated_at`, `{field}`
FROM {_table(project_name, work_item_type)}
WHERE `field_584a64` between '{start.isoformat()}' and '{end.isoformat()}'
AND `work_item_status` in ({efficiency_status_clause()})
ORDER BY `field_584a64` ASC
""".strip()


def monthly_ranges(start: date, end: date) -> list[tuple[date, date]]:
    ranges: list[tuple[date, date]] = []
    current = start
    while current <= end:
        if current.month == 12:
            next_month = date(current.year + 1, 1, 1)
        else:
            next_month = date(current.year, current.month + 1, 1)
        month_end = min(end, next_month - timedelta(days=1))
        ranges.append((current, month_end))
        current = month_end + timedelta(days=1)
    return ranges


def daily_ranges(start: date, end: date) -> list[tuple[date, date]]:
    ranges: list[tuple[date, date]] = []
    current = start
    while current <= end:
        ranges.append((current, current))
        current += timedelta(days=1)
    return ranges


def active_backlog(project_name: str, work_item_type: str) -> str:
    return f"""
SELECT `work_item_id`, `name`, `work_item_status`, `current_status_operator`, `priority`, `start_time`, `updated_at`, `exp_time`
FROM {_table(project_name, work_item_type)}
WHERE `work_item_status` not in ('已结束', '已终止')
ORDER BY `updated_at` DESC
""".strip()


def high_priority(project_name: str, work_item_type: str) -> str:
    return f"""
SELECT `work_item_id`, `name`, `work_item_status`, `current_status_operator`, `priority`, `start_time`, `updated_at`, `exp_time`
FROM {_table(project_name, work_item_type)}
WHERE `work_item_status` not in ('已结束', '已终止')
AND `priority` in ('P0', 'P1')
ORDER BY `updated_at` DESC
""".strip()


def risk_candidates(project_name: str, work_item_type: str, period: InspectionPeriod) -> str:
    return f"""
SELECT `work_item_id`, `name`, risk_label(), `current_status_operator`, `work_item_status`, `priority`, `updated_at`, `exp_time`
FROM {_table(project_name, work_item_type)}
WHERE {_date_range("updated_at", period)}
AND risk_label() is not null
ORDER BY `updated_at` DESC
""".strip()
