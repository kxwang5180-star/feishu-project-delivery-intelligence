from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from .config import Settings
from .metrics import normalize_record
from .models import DemandItem, InspectionDataset
from .periods import InspectionPeriod
from . import mql


class MeegoClientError(RuntimeError):
    pass


class MeegoClient:
    """Read-only Meego / Feishu Project client.

    The connector endpoint varies by tenant and gateway. Set MEEGO_MQL_ENDPOINT
    to the exact MQL search URL when the default path does not match.
    """

    def __init__(self, settings: Settings):
        self.settings = settings

    def _endpoint(self) -> str:
        if self.settings.meego_mql_endpoint:
            return self.settings.meego_mql_endpoint
        return f"{self.settings.meego_base_url}/open_api/plugin/v1/search_by_mql"

    async def query_mql(self, query: str) -> List[DemandItem]:
        if not self.settings.meego_plugin_id or not self.settings.meego_plugin_secret:
            raise MeegoClientError("Missing MEEGO_PLUGIN_ID or MEEGO_PLUGIN_SECRET")
        if not self.settings.meego_user_key:
            raise MeegoClientError("Missing MEEGO_USER_KEY")
        try:
            import httpx
        except ImportError as exc:
            raise MeegoClientError("Missing dependency: httpx") from exc

        payload = {
            "project_key": self.settings.project_key,
            "mql": query,
        }
        headers = {
            "Content-Type": "application/json",
            "X-Plugin-ID": self.settings.meego_plugin_id,
            "X-Plugin-Secret": self.settings.meego_plugin_secret,
            "X-User-Key": self.settings.meego_user_key,
        }
        async with httpx.AsyncClient(timeout=45) as client:
            response = await client.post(self._endpoint(), json=payload, headers=headers)
        if response.status_code >= 400:
            raise MeegoClientError(f"Meego MQL HTTP {response.status_code}: {response.text[:500]}")
        data = response.json()
        if data.get("code") not in (None, 0):
            raise MeegoClientError(f"Meego MQL error {data.get('code')}: {data.get('msg') or data}")
        return [normalize_record(record, efficiency_fields=self.settings.efficiency_fields) for record in extract_records(data)]

    async def collect_dataset(self, period: InspectionPeriod) -> InspectionDataset:
        project_name = self.settings.project_name
        work_item_type = self.settings.work_item_type
        return InspectionDataset(
            period=period,
            updated=await self.query_mql(mql.updated_demands(project_name, work_item_type, period)),
            created=await self.query_mql(mql.created_demands(project_name, work_item_type, period)),
            completed=await self.query_mql(mql.completed_demands(project_name, work_item_type, period)),
            backlog=await self.query_mql(mql.active_backlog(project_name, work_item_type)),
            high_priority=await self.query_mql(mql.high_priority(project_name, work_item_type)),
            risk_candidates=await self.query_mql(mql.risk_candidates(project_name, work_item_type, period)),
            yearly_completed=await self.collect_efficiency_completed(period),
        )

    async def collect_efficiency_completed(self, period: InspectionPeriod) -> List[DemandItem]:
        project_name = self.settings.project_name
        work_item_type = self.settings.work_item_type
        items: List[DemandItem] = []
        for start, end in mql.daily_ranges(period.start, period.end):
            items.extend(
                await self.query_mql(
                    mql.completed_efficiency_demands(project_name, work_item_type, start, end, self.settings.efficiency_fields)
                )
            )
        return items


def extract_records(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    grouped_data = data.get("data")
    if isinstance(grouped_data, dict):
        grouped_records: List[Dict[str, Any]] = []
        for rows in grouped_data.values():
            if isinstance(rows, list):
                grouped_records.extend(item for item in rows if isinstance(item, dict))
        if grouped_records:
            return grouped_records

    candidates: List[Any] = []
    for path in (
        ("data", "list"),
        ("data", "items"),
        ("data", "records"),
        ("list",),
        ("items",),
        ("records",),
    ):
        value: Optional[Any] = data
        for key in path:
            if not isinstance(value, dict):
                value = None
                break
            value = value.get(key)
        if isinstance(value, list):
            candidates.extend(value)
            break

    if not candidates:
        groups = data.get("data", {}).get("group_infos") or data.get("group_infos") or []
        if isinstance(groups, list):
            for group in groups:
                if isinstance(group, dict):
                    rows = group.get("list") or group.get("items") or []
                    if isinstance(rows, list):
                        candidates.extend(rows)

    records: List[Dict[str, Any]] = []
    for item in candidates:
        if isinstance(item, dict):
            records.append(item)
    return records
