from __future__ import annotations

import csv
import importlib.util
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "automation" / "scripts" / "build_quarter_week_cumulative_metrics.py"
spec = importlib.util.spec_from_file_location("build_quarter_week_cumulative_metrics", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


class BuildQuarterWeekCumulativeMetricsTest(unittest.TestCase):
    def test_current_quarter_snapshot_writes_only_demand_category_rows(self) -> None:
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source = tmp_path / "demand_detail.csv"
            output = tmp_path / "current_quarter_delivery_metrics.csv"
            with source.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "online_date",
                        "metric_delivery_effort_days",
                        "metric_rd_days_excl_test",
                        "metric_test_days",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "online_date": "2026-03-29",
                        "metric_delivery_effort_days": "120",
                        "metric_rd_days_excl_test": "80",
                        "metric_test_days": "30",
                    }
                )
                writer.writerow(
                    {
                        "online_date": "2026-04-03",
                        "metric_delivery_effort_days": "20",
                        "metric_rd_days_excl_test": "12",
                        "metric_test_days": "4",
                    }
                )
                writer.writerow(
                    {
                        "online_date": "2026-04-03",
                        "metric_delivery_effort_days": "80",
                        "metric_rd_days_excl_test": "50",
                        "metric_test_days": "10",
                    }
                )
                writer.writerow(
                    {
                        "online_date": "2026-04-20",
                        "metric_delivery_effort_days": "100",
                        "metric_rd_days_excl_test": "70",
                        "metric_test_days": "20",
                    }
                )

            source_rows, output_rows, max_date, quarter = module.build_current_quarter(
                source,
                output,
                date(2026, 1, 1),
                date(2026, 4, 21),
            )

            with output.open(encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(source_rows, 3)
            self.assertEqual(output_rows, 2)
            self.assertEqual(max_date, date(2026, 4, 20))
            self.assertEqual(quarter, "2026-Q2")
            self.assertEqual(len(rows), 2)
            self.assertNotIn("周次", rows[0])
            by_group = {row["需求分类"]: row for row in rows}
            self.assertEqual(by_group["中小需求"]["季度"], "2026-Q2")
            self.assertEqual(by_group["中小需求"]["需求数"], "1")
            self.assertEqual(by_group["中小需求"]["平均交付周期"], "20.0")
            self.assertEqual(by_group["大/超大需求"]["需求数"], "2")
            self.assertEqual(by_group["大/超大需求"]["平均交付周期"], "90.0")


if __name__ == "__main__":
    unittest.main()
