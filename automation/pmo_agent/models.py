from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .periods import InspectionPeriod


@dataclass
class DemandItem:
    work_item_id: str
    name: str
    priority: str = ""
    status: str = ""
    owners: List[str] = field(default_factory=list)
    start_time: str = ""
    updated_at: str = ""
    exp_time: str = ""
    actual_person_days: Optional[float] = None
    node_schedule_person_days: Optional[float] = None
    estimated_person_days: Optional[float] = None
    participant_count: Optional[float] = None
    flow_type: str = ""
    schedule_start_time: str = ""
    project_online_date: str = ""
    tech_review_due_date: str = ""
    online_time: str = ""
    business_line: str = ""
    team: str = ""
    demand_type: str = ""
    risk_labels: List[str] = field(default_factory=list)

    @property
    def is_high_priority(self) -> bool:
        return self.priority in {"P0", "P1"}

    @property
    def has_owner(self) -> bool:
        return bool(self.owners)

    @property
    def schedule_complete(self) -> bool:
        if any("排期信息不全" in label for label in self.risk_labels):
            return False
        return bool(self.exp_time)

    @property
    def preferred_person_days(self) -> Optional[float]:
        for value in (self.actual_person_days, self.node_schedule_person_days, self.estimated_person_days):
            if value is not None:
                return value
        return None


@dataclass
class InspectionDataset:
    period: InspectionPeriod
    updated: List[DemandItem] = field(default_factory=list)
    created: List[DemandItem] = field(default_factory=list)
    completed: List[DemandItem] = field(default_factory=list)
    backlog: List[DemandItem] = field(default_factory=list)
    high_priority: List[DemandItem] = field(default_factory=list)
    risk_candidates: List[DemandItem] = field(default_factory=list)
    yearly_completed: List[DemandItem] = field(default_factory=list)


@dataclass
class AgentNarrative:
    markdown: str
    used_llm: bool
    errors: List[str] = field(default_factory=list)


@dataclass
class InspectionResult:
    run_id: str
    status: str
    period: Dict[str, str]
    summary_metrics: Dict[str, Any]
    risk_counts: Dict[str, Any]
    feishu_doc_url: Optional[str]
    markdown_path: Optional[str]
    errors: List[str]
