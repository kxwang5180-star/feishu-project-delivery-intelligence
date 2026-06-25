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
    def test_latest_week_only_writes_only_the_end_week_snapshot(self) -> None:
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source = tmp_path / "demand_detail.csv"
            output = tmp_path / "quarter_week_cumulative_metrics.csv"
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

            source_rows, output_rows, max_date = module.build(
                source,
                output,
                date(2026, 1, 1),
                date(2026, 4, 21),
                latest_week_only=True,
            )

            with output.open(encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(source_rows, 2)
            self.assertEqual(output_rows, 1)
            self.assertEqual(max_date, date(2026, 4, 20))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["季度"], "2026-Q2")
            self.assertEqual(rows[0]["周次"], "W03（截至2026-04-21）")
            self.assertEqual(rows[0]["需求分类"], "大/超大需求")
            self.assertEqual(rows[0]["需求数"], "2")


if __name__ == "__main__":
    unittest.main()
