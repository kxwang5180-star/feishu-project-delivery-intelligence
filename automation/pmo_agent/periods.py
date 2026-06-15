from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Optional
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class InspectionPeriod:
    start: date
    end: date
    as_of: datetime
    timezone: str

    def as_dict(self) -> dict:
        return {
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "as_of": self.as_of.strftime("%Y-%m-%d %H:%M"),
        }


def parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def compute_period(
    period_type: str,
    *,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    timezone: str = "Asia/Shanghai",
    now: Optional[datetime] = None,
) -> InspectionPeriod:
    tz = ZoneInfo(timezone)
    current = now.astimezone(tz) if now else datetime.now(tz)
    normalized = period_type or "weekly"
    if normalized == "weekly":
        start = current.date() - timedelta(days=current.weekday())
        end = start + timedelta(days=6)
    elif normalized == "custom":
        if not start_date or not end_date:
            raise ValueError("custom period requires start_date and end_date")
        start = parse_date(start_date)
        end = parse_date(end_date)
        if end < start:
            raise ValueError("end_date must be greater than or equal to start_date")
    else:
        raise ValueError("period_type must be weekly or custom")
    return InspectionPeriod(start=start, end=end, as_of=current.replace(second=0, microsecond=0), timezone=timezone)


def day_start(value: date) -> datetime:
    return datetime.combine(value, time.min)

