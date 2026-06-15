from __future__ import annotations

import json
from collections import Counter
from datetime import date, datetime
from math import ceil
from typing import Any, Dict, Iterable, List, Optional, Sequence

from .efficiency_fields import EfficiencyFieldConfig
from .models import DemandItem, InspectionDataset


ENDED_STATUSES = {"已结束", "已终止", "end", "closed"}


def _value_label(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return "、".join(label for label in (_value_label(item) for item in value) if label)
    if isinstance(value, dict):
        for key in ("label", "option_name", "name", "cn_name", "name_cn", "name_en", "value", "id"):
            if value.get(key):
                return str(value[key])
        return ""
    return str(value)


def _owners(value: Any) -> List[str]:
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return [label for label in (_value_label(item) for item in value) if label]
    label = _value_label(value)
    return [label] if label else []


def _risk_labels(value: Any) -> List[str]:
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith("["):
            try:
                parsed = json.loads(stripped)
                if isinstance(parsed, list):
                    return [str(item) for item in parsed]
            except json.JSONDecodeError:
                pass
        return [stripped]
    return [str(value)]


def _first_present(fields: Dict[str, Any], keys: Sequence[str]) -> Any:
    for key in keys:
        if key in fields and fields.get(key) not in (None, ""):
            return fields.get(key)
    return None


def _float_value(value: Any) -> Optional[float]:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, dict):
        extracted = _value_label(value)
        return _float_value(extracted)
    if isinstance(value, list):
        values = [_float_value(item) for item in value]
        values = [item for item in values if item is not None]
        if not values:
            return None
        return float(sum(values))
    text = str(value).strip().replace("人天", "").replace("天", "")
    try:
        return float(text)
    except ValueError:
        return None


def normalize_record(record: Dict[str, Any], efficiency_fields: Optional[EfficiencyFieldConfig] = None) -> DemandItem:
    field_config = efficiency_fields or EfficiencyFieldConfig.from_env()
    if isinstance(record.get("moql_field_list"), list):
        record = moql_field_list_to_record(record["moql_field_list"])
    fields = record.get("fields") if isinstance(record.get("fields"), dict) else record
    risk_value = fields.get("risk_label()")
    if risk_value is None:
        risk_value = fields.get("risk_label")
    return DemandItem(
        work_item_id=str(fields.get("work_item_id") or fields.get("工作项ID") or fields.get("id") or ""),
        name=str(fields.get("name") or fields.get("名称") or fields.get("title") or ""),
        priority=_value_label(fields.get("priority") or fields.get("优先级")),
        status=_value_label(fields.get("work_item_status") or fields.get("需求状态") or fields.get("status")),
        owners=_owners(fields.get("current_status_operator") or fields.get("当前负责人")),
        start_time=str(fields.get("start_time") or fields.get("提出时间") or ""),
        updated_at=str(fields.get("updated_at") or fields.get("更新时间") or ""),
        exp_time=str(fields.get("exp_time") or fields.get("预期完成时间") or ""),
        actual_person_days=_float_value(
            _first_present(
                fields,
                field_config.actual_person_days_keys(),
            )
        ),
        node_schedule_person_days=_float_value(
            _first_present(fields, ("node_schedule_person_days", "schedule_person_days", "排期人天", "节点排期估分", "排期估分"))
        ),
        estimated_person_days=_float_value(
            _first_present(fields, ("estimated_person_days", "estimate_person_days", "估分", "需求估分", "计划人天", "预计人天"))
        ),
        participant_count=_float_value(_first_present(fields, field_config.participant_count_keys())),
        flow_type=_value_label(_first_present(fields, field_config.flow_type_keys())),
        schedule_start_time=str(
            _first_present(fields, field_config.schedule_start_time_keys())
            or ""
        ),
        project_online_date=str(_first_present(fields, field_config.project_online_date_keys()) or ""),
        tech_review_due_date=str(_first_present(fields, field_config.tech_review_due_date_keys()) or ""),
        online_time=str(_first_present(fields, field_config.online_time_keys()) or ""),
        business_line=_value_label(_first_present(fields, ("business_line", "业务线", "业务域", "所属业务"))),
        team=_value_label(_first_present(fields, ("team", "团队", "负责团队", "所属团队"))),
        demand_type=_value_label(_first_present(fields, ("demand_type", "需求类型", "类型", "工作项类型"))),
        risk_labels=_risk_labels(risk_value),
    )


def moql_field_list_to_record(fields: List[Dict[str, Any]]) -> Dict[str, Any]:
    record: Dict[str, Any] = {}
    for field in fields:
        key = field.get("key") or field.get("name")
        if not key:
            continue
        record[str(key)] = extract_moql_value(field)
    return record


def extract_moql_value(field: Dict[str, Any]) -> Any:
    value = field.get("value")
    if value is None:
        return None
    if not isinstance(value, dict):
        return value
    value_type = field.get("value_type")
    if value_type and value_type in value:
        return value[value_type]
    for key in (
        "string_value",
        "long_value",
        "double_value",
        "bool_value",
        "key_label_value",
        "key_label_value_list",
        "user_value",
        "user_value_list",
        "date_value",
    ):
        if key in value:
            return value[key]
    if len(value) == 1:
        return next(iter(value.values()))
    return value


def unique_items(items: Iterable[DemandItem]) -> List[DemandItem]:
    seen = set()
    unique: List[DemandItem] = []
    for item in items:
        key = item.work_item_id or item.name
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def stage_bucket(status: str) -> str:
    text = status or "未填状态"
    if text in ENDED_STATUSES or "结束" in text or "终止" in text:
        return "结束"
    if "确认需求" in text or text == "开始":
        return "确认"
    if "排期" in text or "启动开发" in text:
        return "排期"
    if "开发" in text or "代码" in text:
        return "开发"
    if "测试" in text or "联调" in text or "提测" in text:
        return "测试"
    if "上线" in text:
        return "上线"
    if "验收" in text or "showcase" in text or "收益评估" in text:
        return "验收"
    if "推广" in text:
        return "推广"
    if "评审" in text or "审批" in text or "门禁" in text or "设计" in text:
        return "评审"
    return "其他"


def contains_label(item: DemandItem, keyword: str) -> bool:
    return any(keyword in label for label in item.risk_labels)


def count_risk(items: Sequence[DemandItem], keyword: str) -> int:
    return len([item for item in unique_items(items) if contains_label(item, keyword)])


def top_owner_risks(items: Sequence[DemandItem]) -> List[Dict[str, Any]]:
    owner_counts = Counter(owner for item in items for owner in item.owners)
    return [
        {"owner": owner, "demand_count": count}
        for owner, count in owner_counts.most_common(10)
        if owner
    ]


def analyze_dataset(dataset: InspectionDataset) -> Dict[str, Any]:
    risks = unique_items(dataset.risk_candidates)
    high_priority = unique_items(dataset.high_priority)
    backlog = unique_items(dataset.backlog)
    all_visible = unique_items(dataset.updated + dataset.created + dataset.completed + backlog + high_priority + risks)

    overdue = [item for item in risks if contains_label(item, "延期")]
    due_today = [item for item in risks if contains_label(item, "今日到期")]
    incomplete_schedule = [item for item in risks if contains_label(item, "排期信息不全")]
    no_owner = [item for item in backlog if not item.has_owner]
    p0_p1_without_schedule = [item for item in high_priority if not item.schedule_complete]

    stage_counts = Counter(stage_bucket(item.status) for item in backlog)
    risk_counts = {
        "overdue_demands": len(overdue),
        "due_today_demands": len(due_today),
        "incomplete_schedule_demands": len(incomplete_schedule),
        "no_owner_demands": len(no_owner),
        "p0_p1_without_schedule": len(p0_p1_without_schedule),
    }
    summary_metrics = {
        "updated_demands": len(unique_items(dataset.updated)),
        "new_demands": len(unique_items(dataset.created)),
        "completed_demands": len(unique_items(dataset.completed)),
        "net_growth": len(unique_items(dataset.created)) - len(unique_items(dataset.completed)),
        "active_backlog": len(backlog),
        "p0_p1_demands": len(high_priority),
        "p0_p1_without_schedule": len(p0_p1_without_schedule),
        "overdue_demands": len(overdue),
        "due_today_demands": len(due_today),
        "incomplete_schedule_demands": len(incomplete_schedule),
        "no_owner_demands": len(no_owner),
        "long_stagnant_demands": 0,
        "resource_overload_people": None,
    }
    efficiency_metrics = build_efficiency_metrics(dataset)
    summary_metrics.update(
        {
            "avg_person_days": efficiency_metrics.get("avg_person_days"),
            "median_person_days": efficiency_metrics.get("median_person_days"),
            "delivery_cycle_avg_days": efficiency_metrics.get("delivery_cycle_avg_days"),
            "delivery_cycle_median_days": efficiency_metrics.get("delivery_cycle_median_days"),
            "delivery_cycle_p75_days": efficiency_metrics.get("delivery_cycle_p75_days"),
            "effort_missing_count": efficiency_metrics.get("effort_missing_count"),
            "effort_missing_rate": efficiency_metrics.get("effort_missing_rate"),
        }
    )
    high_priority_risks = [
        item for item in high_priority if item.work_item_id in {risk.work_item_id for risk in risks} or not item.schedule_complete
    ]
    interventions = build_interventions(high_priority_risks, overdue, due_today, incomplete_schedule, no_owner)
    return {
        "summary_metrics": summary_metrics,
        "efficiency_metrics": efficiency_metrics,
        "risk_counts": risk_counts,
        "stage_distribution": dict(stage_counts),
        "owner_concentration": top_owner_risks(all_visible),
        "high_priority_risks": [item.__dict__ for item in unique_items(high_priority_risks)[:20]],
        "risk_items": [item.__dict__ for item in risks[:30]],
        "interventions": interventions[:20],
        "risk_grading": build_risk_grading(interventions),
    }


def build_efficiency_metrics(dataset: InspectionDataset) -> Dict[str, Any]:
    source_items = dataset.yearly_completed or dataset.completed
    closed_items = [
        item
        for item in unique_items(source_items)
        if is_closed(item) and parse_date(item.start_time) and parse_date(item.updated_at)
    ]
    samples = [build_efficiency_sample(item) for item in closed_items]
    samples = [sample for sample in samples if sample]
    cycle_days = [sample["cycle_days"] for sample in samples]
    effort_samples = [sample for sample in samples if sample.get("person_days") is not None]
    person_days = [sample["person_days"] for sample in effort_samples]
    missing_effort = len(samples) - len(effort_samples)
    monthly = build_monthly_efficiency_trend(samples)
    return {
        "sample_count": len(samples),
        "effort_sample_count": len(effort_samples),
        "effort_missing_count": missing_effort,
        "effort_missing_rate": missing_effort / len(samples) if samples else None,
        "avg_person_days": rounded_average(person_days),
        "median_person_days": rounded_median(person_days),
        "person_days_p75": rounded_percentile(person_days, 75),
        "delivery_cycle_avg_days": rounded_average(cycle_days),
        "delivery_cycle_median_days": rounded_median(cycle_days),
        "delivery_cycle_p75_days": rounded_percentile(cycle_days, 75),
        "delivery_cycle_p90_days": rounded_percentile(cycle_days, 90),
        "monthly_efficiency_trend": monthly,
        "quarterly_efficiency_trend": build_period_efficiency_trend(samples, "quarter"),
        "yearly_efficiency_trend": build_period_efficiency_trend(samples, "year"),
        "top_long_cycle_demands": sorted(samples, key=lambda item: item["cycle_days"], reverse=True)[:10],
        "top_high_effort_demands": sorted(effort_samples, key=lambda item: item["person_days"], reverse=True)[:10],
        "missing_effort_demands": [sample for sample in samples if sample.get("person_days") is None][:20],
    }


def build_efficiency_sample(item: DemandItem) -> Dict[str, Any]:
    start = parse_date(item.start_time)
    completed = parse_date(item.updated_at)
    if not start or not completed:
        return {}
    cycle = max((completed - start).days, 0)
    person_days = item.preferred_person_days
    return {
        "work_item_id": item.work_item_id,
        "name": item.name,
        "priority": item.priority,
        "status": item.status,
        "business_line": item.business_line,
        "team": item.team,
        "demand_type": item.demand_type,
        "started_at": start.isoformat(),
        "completed_at": completed.isoformat(),
        "completion_month": completed.strftime("%Y-%m"),
        "cycle_days": float(cycle),
        "person_days": round(person_days, 2) if person_days is not None else None,
    }


def build_monthly_efficiency_trend(samples: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    by_month: Dict[str, List[Dict[str, Any]]] = {}
    for sample in samples:
        by_month.setdefault(str(sample["completion_month"]), []).append(sample)
    rows: List[Dict[str, Any]] = []
    for month in sorted(by_month):
        items = by_month[month]
        cycle_days = [item["cycle_days"] for item in items]
        effort_items = [item for item in items if item.get("person_days") is not None]
        person_days = [item["person_days"] for item in effort_items]
        missing = len(items) - len(effort_items)
        rows.append(
            {
                "month": month,
                "completed_count": len(items),
                "avg_person_days": rounded_average(person_days),
                "median_person_days": rounded_median(person_days),
                "delivery_cycle_avg_days": rounded_average(cycle_days),
                "delivery_cycle_median_days": rounded_median(cycle_days),
                "delivery_cycle_p75_days": rounded_percentile(cycle_days, 75),
                "delivery_cycle_p90_days": rounded_percentile(cycle_days, 90),
                "effort_missing_count": missing,
                "effort_missing_rate": missing / len(items) if items else None,
            }
        )
    return rows


def build_period_efficiency_trend(samples: Sequence[Dict[str, Any]], grain: str) -> List[Dict[str, Any]]:
    by_period: Dict[str, List[Dict[str, Any]]] = {}
    for sample in samples:
        completed = parse_date(str(sample.get("completed_at") or ""))
        if not completed:
            continue
        key = period_key(completed, grain)
        by_period.setdefault(key, []).append(sample)
    rows: List[Dict[str, Any]] = []
    for key in sorted(by_period):
        items = by_period[key]
        cycle_days = [item["cycle_days"] for item in items]
        effort_items = [item for item in items if item.get("person_days") is not None]
        person_days = [item["person_days"] for item in effort_items]
        missing = len(items) - len(effort_items)
        label_key = "year" if grain == "year" else "quarter"
        rows.append(
            {
                label_key: key,
                "completed_count": len(items),
                "avg_person_days": rounded_average(person_days),
                "median_person_days": rounded_median(person_days),
                "person_days_p75": rounded_percentile(person_days, 75),
                "delivery_cycle_avg_days": rounded_average(cycle_days),
                "delivery_cycle_median_days": rounded_median(cycle_days),
                "delivery_cycle_p75_days": rounded_percentile(cycle_days, 75),
                "delivery_cycle_p90_days": rounded_percentile(cycle_days, 90),
                "effort_missing_count": missing,
                "effort_missing_rate": missing / len(items) if items else None,
            }
        )
    return rows


def period_key(value: date, grain: str) -> str:
    if grain == "year":
        return f"{value.year}"
    quarter = ((value.month - 1) // 3) + 1
    return f"{value.year}-Q{quarter}"


def is_closed(item: DemandItem) -> bool:
    status = item.status or ""
    return status in ENDED_STATUSES or "结束" in status or "终止" in status


def parse_date(value: str) -> Optional[date]:
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    for candidate in (text, text.replace("Z", "+00:00")):
        try:
            return datetime.fromisoformat(candidate).date()
        except ValueError:
            pass
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y/%m/%d", "%Y/%m/%d %H:%M:%S"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    return None


def rounded_average(values: Sequence[float]) -> Optional[float]:
    if not values:
        return None
    return round(sum(values) / len(values), 2)


def rounded_median(values: Sequence[float]) -> Optional[float]:
    if not values:
        return None
    sorted_values = sorted(values)
    mid = len(sorted_values) // 2
    if len(sorted_values) % 2:
        return round(sorted_values[mid], 2)
    return round((sorted_values[mid - 1] + sorted_values[mid]) / 2, 2)


def rounded_percentile(values: Sequence[float], percentile: int) -> Optional[float]:
    if not values:
        return None
    sorted_values = sorted(values)
    index = max(0, ceil((percentile / 100) * len(sorted_values)) - 1)
    return round(sorted_values[min(index, len(sorted_values) - 1)], 2)


def build_interventions(
    high_priority_risks: Sequence[DemandItem],
    overdue: Sequence[DemandItem],
    due_today: Sequence[DemandItem],
    incomplete_schedule: Sequence[DemandItem],
    no_owner: Sequence[DemandItem],
) -> List[Dict[str, str]]:
    interventions: List[Dict[str, str]] = []
    seen = set()

    def add(item: DemandItem, issue_type: str, action: str) -> None:
        key = (item.work_item_id, issue_type)
        if key in seen:
            return
        seen.add(key)
        owner = "、".join(item.owners) if item.owners else "未明确"
        interventions.append(
            {
                "work_item_id": item.work_item_id,
                "name": item.name,
                "issue_type": issue_type,
                "owner": owner,
                "action": action,
                "priority": item.priority,
                "status": item.status,
                "risk_labels": item.risk_labels,
            }
        )

    for item in high_priority_risks:
        add(item, "高优需求风险", "PMO 需确认负责人、排期和恢复计划")
    for item in overdue:
        add(item, "节点延期", "要求责任人给出恢复计划和新截止时间")
    for item in due_today:
        add(item, "今日到期", "当天跟进是否可完成，不能完成需升级风险")
    for item in incomplete_schedule:
        add(item, "排期信息不全", "补齐负责人、开始/结束时间和估分")
    for item in no_owner:
        add(item, "无负责人", "明确责任人后再进入后续阶段")
    return interventions


def build_risk_grading(interventions: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    levels = {"红色风险": 0, "橙色风险": 0, "黄色关注": 0, "数据治理": 0}
    graded_items = []
    for item in interventions:
        level = classify_intervention_level(item)
        levels[level] = levels.get(level, 0) + 1
        graded = dict(item)
        graded["risk_level"] = level
        graded_items.append(graded)
    return {
        "counts": levels,
        "items": graded_items,
    }


def classify_intervention_level(item: Dict[str, Any]) -> str:
    issue_type = str(item.get("issue_type") or "")
    priority = str(item.get("priority") or "")
    if issue_type == "节点延期" or priority == "P0":
        return "红色风险"
    if issue_type in {"高优需求风险", "今日到期"}:
        return "橙色风险"
    if issue_type == "排期信息不全":
        return "黄色关注"
    if issue_type == "无负责人":
        return "数据治理"
    return "黄色关注"


def enrich_analysis_with_history(
    analysis: Dict[str, Any],
    previous_run: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    if not previous_run:
        analysis["trend"] = {"has_baseline": False}
        analysis["closure_tracking"] = {"has_baseline": False}
        return analysis
    previous = previous_run.get("analysis") if isinstance(previous_run, dict) else None
    if not isinstance(previous, dict):
        analysis["trend"] = {"has_baseline": False}
        analysis["closure_tracking"] = {"has_baseline": False}
        return analysis
    analysis["trend"] = build_trend(analysis, previous, previous_run)
    analysis["closure_tracking"] = build_closure_tracking(analysis, previous, previous_run)
    return analysis


def build_trend(
    current: Dict[str, Any],
    previous: Dict[str, Any],
    previous_run: Dict[str, Any],
) -> Dict[str, Any]:
    metric_keys = [
        "new_demands",
        "completed_demands",
        "net_growth",
        "active_backlog",
        "p0_p1_demands",
        "p0_p1_without_schedule",
        "overdue_demands",
        "due_today_demands",
        "incomplete_schedule_demands",
        "no_owner_demands",
        "avg_person_days",
        "median_person_days",
        "delivery_cycle_avg_days",
        "delivery_cycle_median_days",
        "delivery_cycle_p75_days",
        "effort_missing_count",
    ]
    current_metrics = current.get("summary_metrics", {})
    previous_metrics = previous.get("summary_metrics", {})
    metric_deltas = {}
    for key in metric_keys:
        cur = _as_int(current_metrics.get(key))
        prev = _as_int(previous_metrics.get(key))
        metric_deltas[key] = {"current": cur, "previous": prev, "delta": cur - prev}

    current_stage = current.get("stage_distribution", {})
    previous_stage = previous.get("stage_distribution", {})
    stage_deltas = {}
    for key in sorted(set(current_stage) | set(previous_stage)):
        cur = _as_int(current_stage.get(key))
        prev = _as_int(previous_stage.get(key))
        stage_deltas[key] = {"current": cur, "previous": prev, "delta": cur - prev}

    return {
        "has_baseline": True,
        "previous_run_id": previous_run.get("run_id"),
        "previous_created_at": previous_run.get("created_at"),
        "metric_deltas": metric_deltas,
        "stage_deltas": stage_deltas,
    }


def build_closure_tracking(
    current: Dict[str, Any],
    previous: Dict[str, Any],
    previous_run: Dict[str, Any],
) -> Dict[str, Any]:
    current_items = current.get("interventions", [])
    previous_items = previous.get("interventions", [])
    current_by_key = {intervention_key(item): item for item in current_items if intervention_key(item)}
    previous_by_key = {intervention_key(item): item for item in previous_items if intervention_key(item)}
    current_keys = set(current_by_key)
    previous_keys = set(previous_by_key)
    new_keys = current_keys - previous_keys
    persistent_keys = current_keys & previous_keys
    resolved_keys = previous_keys - current_keys
    return {
        "has_baseline": True,
        "previous_run_id": previous_run.get("run_id"),
        "new_count": len(new_keys),
        "persistent_count": len(persistent_keys),
        "resolved_count": len(resolved_keys),
        "new_items": [current_by_key[key] for key in sorted(new_keys)[:10]],
        "persistent_items": [current_by_key[key] for key in sorted(persistent_keys)[:10]],
        "resolved_items": [previous_by_key[key] for key in sorted(resolved_keys)[:10]],
    }


def intervention_key(item: Dict[str, Any]) -> str:
    work_item_id = item.get("work_item_id")
    issue_type = item.get("issue_type")
    if not work_item_id or not issue_type:
        return ""
    return f"{work_item_id}:{issue_type}"


def _as_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0
