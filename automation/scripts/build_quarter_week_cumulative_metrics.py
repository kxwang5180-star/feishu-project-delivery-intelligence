from __future__ import annotations

import argparse
import csv
import math
import statistics
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "data" / "efficiency_datamart" / "demand_detail.csv"
DEFAULT_OUTPUT = ROOT / "data" / "efficiency_datamart" / "quarter_week_cumulative_metrics.csv"
DEFAULT_CURRENT_OUTPUT = ROOT / "data" / "efficiency_datamart" / "current_quarter_delivery_metrics.csv"


def parse_date(value: str) -> date | None:
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(value[:19] if "%H" in fmt else value[:10], fmt).date()
        except ValueError:
            continue
    return None


def parse_float(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def quarter_bounds(d: date) -> tuple[str, date, date]:
    q = (d.month - 1) // 3 + 1
    start = date(d.year, 3 * (q - 1) + 1, 1)
    end = date(d.year + 1, 1, 1) - timedelta(days=1) if q == 4 else date(d.year, 3 * q + 1, 1) - timedelta(days=1)
    return f"{d.year}-Q{q}", start, end


def percentile(values: Iterable[float], p: float) -> float:
    nums = sorted(values)
    if not nums:
        return 0.0
    if len(nums) == 1:
        return nums[0]
    pos = (len(nums) - 1) * p
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return nums[lo]
    return nums[lo] * (hi - pos) + nums[hi] * (pos - lo)


def last_sunday(today: date | None = None) -> date:
    today = today or date.today()
    # Monday=0. On Monday, this returns yesterday; on other days, the most recent Sunday.
    days_since_sunday = (today.weekday() + 1) % 7
    return today - timedelta(days=days_since_sunday or 7)


def build(source: Path, output: Path, start: date, end: date) -> tuple[int, int, date | None]:
    rows: list[dict[str, Any]] = []
    with source.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            online = parse_date(row.get("online_date") or row.get("online_time") or "")
            if not online or online < start or online > end:
                continue
            delivery = parse_float(row.get("metric_delivery_effort_days"))
            rd = parse_float(row.get("metric_rd_days_excl_test"))
            test = parse_float(row.get("metric_test_days"))
            quarter, q_start, q_end = quarter_bounds(online)
            rows.append(
                {
                    **row,
                    "date": online,
                    "quarter": quarter,
                    "q_start": q_start,
                    "q_end": q_end,
                    "group": "中小需求" if delivery <= 60 else "大/超大需求",
                    "delivery": delivery,
                    "rd": rd,
                    "test": test,
                }
            )
    max_date = max((row["date"] for row in rows), default=None)
    results: list[dict[str, Any]] = []
    for quarter in sorted({row["quarter"] for row in rows}):
        q_rows = [row for row in rows if row["quarter"] == quarter]
        q_start = q_rows[0]["q_start"]
        q_end = min(q_rows[0]["q_end"], end)
        week = 1
        while q_start + timedelta(days=(week - 1) * 7) <= q_end:
            week_end = min(q_start + timedelta(days=week * 7 - 1), q_end)
            for group in ("中小需求", "大/超大需求"):
                subset = [row for row in q_rows if row["group"] == group and row["date"] <= week_end]
                if not subset:
                    continue
                delivery = [row["delivery"] for row in subset]
                rd = [row["rd"] for row in subset]
                test = [row["test"] for row in subset]
                results.append(
                    {
                        "季度": quarter,
                        "周次": f"W{week:02d}（截至{week_end.isoformat()}）",
                        "需求分类": group,
                        "需求数": len(subset),
                        "平均交付周期": round(sum(delivery) / len(delivery), 2),
                        "交付中位数": round(statistics.median(delivery), 2),
                        "交付P90": round(percentile(delivery, 0.9), 2),
                        "平均研发时长": round(sum(rd) / len(rd), 2),
                        "平均测试时长": round(sum(test) / len(test), 2),
                    }
                )
            week += 1
    output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["季度", "周次", "需求分类", "需求数", "平均交付周期", "交付中位数", "交付P90", "平均研发时长", "平均测试时长"]
    with output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)
    return len(rows), len(results), max_date


def build_current_quarter(source: Path, output: Path, start: date, end: date) -> tuple[int, int, date | None, str]:
    current_quarter, q_start, _ = quarter_bounds(end)
    rows: list[dict[str, Any]] = []
    with source.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            online = parse_date(row.get("online_date") or row.get("online_time") or "")
            if not online or online < start or online > end:
                continue
            quarter, _, _ = quarter_bounds(online)
            if quarter != current_quarter or online < q_start:
                continue
            delivery = parse_float(row.get("metric_delivery_effort_days"))
            rows.append(
                {
                    "date": online,
                    "group": "中小需求" if delivery <= 60 else "大/超大需求",
                    "delivery": delivery,
                    "rd": parse_float(row.get("metric_rd_days_excl_test")),
                    "test": parse_float(row.get("metric_test_days")),
                }
            )
    max_date = max((row["date"] for row in rows), default=None)
    results: list[dict[str, Any]] = []
    for group in ("中小需求", "大/超大需求"):
        subset = [row for row in rows if row["group"] == group]
        if not subset:
            continue
        delivery = [row["delivery"] for row in subset]
        rd = [row["rd"] for row in subset]
        test = [row["test"] for row in subset]
        results.append(
            {
                "季度": current_quarter,
                "需求分类": group,
                "需求数": len(subset),
                "平均交付周期": round(sum(delivery) / len(delivery), 2),
                "交付中位数": round(statistics.median(delivery), 2),
                "交付P90": round(percentile(delivery, 0.9), 2),
                "平均研发时长": round(sum(rd) / len(rd), 2),
                "平均测试时长": round(sum(test) / len(test), 2),
            }
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["季度", "需求分类", "需求数", "平均交付周期", "交付中位数", "交付P90", "平均研发时长", "平均测试时长"]
    with output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)
    return len(rows), len(results), max_date, current_quarter


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default=str(DEFAULT_SOURCE))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--current-output", default=str(DEFAULT_CURRENT_OUTPUT))
    parser.add_argument("--start", default="2025-01-01")
    parser.add_argument("--end", default=None, help="Inclusive end date. Defaults to most recent Sunday.")
    parser.add_argument("--latest-current-quarter", action="store_true", help="Only write the current quarter snapshot by demand category.")
    args = parser.parse_args()
    start = datetime.strptime(args.start, "%Y-%m-%d").date()
    end = datetime.strptime(args.end, "%Y-%m-%d").date() if args.end else last_sunday()
    if args.latest_current_quarter:
        source_rows, output_rows, max_date, quarter = build_current_quarter(Path(args.source), Path(args.current_output), start, end)
        print(f"quarter={quarter}")
        output_path = args.current_output
    else:
        source_rows, output_rows, max_date = build(Path(args.source), Path(args.output), start, end)
        output_path = args.output
    print(f"source_rows={source_rows}")
    print(f"output_rows={output_rows}")
    print(f"max_date={max_date}")
    print(f"end={end}")
    print(output_path)


if __name__ == "__main__":
    main()
