from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterable, List, Sequence


@dataclass(frozen=True)
class EfficiencyFieldConfig:
    flow_type: str = "template"
    schedule_start_time: str = ""
    project_online_date: str = ""
    tech_review_due_date: str = ""
    online_time: str = "field_584a64"
    participant_count: str = ""
    actual_person_days: str = "field_fba983"
    flow_type_value: str = "需求处理流程"

    @classmethod
    def from_env(cls) -> "EfficiencyFieldConfig":
        return cls(
            flow_type=os.environ.get("EFFICIENCY_FLOW_TYPE_FIELD", cls.flow_type),
            schedule_start_time=os.environ.get("EFFICIENCY_SCHEDULE_START_FIELD", cls.schedule_start_time),
            project_online_date=os.environ.get("EFFICIENCY_PROJECT_ONLINE_DATE_FIELD", cls.project_online_date),
            tech_review_due_date=os.environ.get("EFFICIENCY_TECH_REVIEW_DUE_FIELD", cls.tech_review_due_date),
            online_time=os.environ.get("EFFICIENCY_ONLINE_TIME_FIELD", cls.online_time),
            participant_count=os.environ.get("EFFICIENCY_PARTICIPANT_COUNT_FIELD", cls.participant_count),
            actual_person_days=os.environ.get("EFFICIENCY_ACTUAL_PERSON_DAYS_FIELD", cls.actual_person_days),
            flow_type_value=os.environ.get("EFFICIENCY_FLOW_TYPE_VALUE", cls.flow_type_value),
        )

    def select_fields(self) -> List[str]:
        return unique_non_empty(
            [
                self.flow_type,
                self.online_time,
                self.actual_person_days,
            ]
        )

    def actual_person_days_keys(self) -> Sequence[str]:
        return unique_non_empty(
            [
                "actual_person_days",
                "actual_effort",
                self.actual_person_days,
                "field_fba983",
                "实际投入总人天",
                "实际人天",
                "实际投入人天",
                "实际工时",
            ]
        )

    def participant_count_keys(self) -> Sequence[str]:
        return unique_non_empty(["participant_count", self.participant_count, "参与人数", "参与人数量", "需求参与人数"])

    def flow_type_keys(self) -> Sequence[str]:
        return unique_non_empty(["flow_type", self.flow_type, "template", "流程类型", "流程", "处理流程"])

    def schedule_start_time_keys(self) -> Sequence[str]:
        return unique_non_empty(
            [
                "schedule_start_time",
                self.schedule_start_time,
                "全部节点排期开始时间",
                "节点排期开始时间",
                "排期开始时间",
                "开始时间",
            ]
        )

    def project_online_date_keys(self) -> Sequence[str]:
        return unique_non_empty(["project_online_date", self.project_online_date, "项目上线日期", "上线日期"])

    def tech_review_due_date_keys(self) -> Sequence[str]:
        return unique_non_empty(["tech_review_due_date", self.tech_review_due_date, "技术评审节点截止日期", "技术评审截止日期"])

    def online_time_keys(self) -> Sequence[str]:
        return unique_non_empty(["online_time", self.online_time, "field_584a64", "上线时间", "实际上线时间"])


def unique_non_empty(values: Iterable[str]) -> List[str]:
    seen = set()
    result: List[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
