"""Regression tests for six-month sector targets and observation cutoffs."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from hydrosight.features import feature_engineering as features


class TargetVariableTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        root = Path(self.temporary_directory.name)
        reports = root / "reports"
        reports.mkdir()
        manifest = {
            "run_utc": "2025-10-24T15:31:07+00:00",
            "sources": {
                "water_breaks": {
                    "status": "OK",
                    "snapshot_utc": "20251024T153107Z",
                }
            },
        }
        (reports / "latest_download_manifest.json").write_text(
            json.dumps(manifest), encoding="utf-8"
        )
        root_patch = patch.object(features, "PROJECT_ROOT", root)
        root_patch.start()
        self.addCleanup(root_patch.stop)

        self.grid = pd.DataFrame({"cell_id": ["A", "B"]})
        self.history = pd.DataFrame({
            "cell_id": ["A", "A", "A"],
            "month": ["2024-12-01", "2025-01-01", "2025-08-01"],
            "break_count": [1, 2, 1],
        })

    def test_provisional_cutoff_uses_snapshot_and_last_event(self):
        self.assertEqual(
            str(features.calculate_last_available_month(self.history)),
            "2025-07",
        )

    def test_target_respects_six_month_window_and_year_boundary(self):
        result = features.build_target_variable(self.grid, self.history)
        targets = result.set_index(["cell_id", "reference_date"])["target_6m"]

        def target(cell, date):
            return int(targets.loc[(cell, pd.Timestamp(date))])

        self.assertEqual(target("A", "2024-06-01"), 0)
        self.assertEqual(target("A", "2024-07-01"), 1)
        self.assertEqual(target("A", "2024-08-01"), 1)
        self.assertEqual(target("A", "2024-12-01"), 1)
        self.assertEqual(target("A", "2025-02-01"), 0)
        self.assertEqual(target("B", "2024-12-01"), 0)

        self.assertEqual(result["reference_date"].min(), pd.Timestamp("2016-01-01"))
        self.assertEqual(result["reference_date"].max(), pd.Timestamp("2025-02-01"))
        self.assertEqual(len(result), 2 * 110)
        self.assertTrue(result["target_6m"].isin([0, 1]).all())
        self.assertFalse(result.duplicated(["cell_id", "reference_date"]).any())

    def test_rejects_duplicate_sector_month(self):
        repeated = pd.concat([self.history, self.history.iloc[[0]]], ignore_index=True)
        with self.assertRaisesRegex(ValueError, "Duplicate sector-month"):
            features.build_target_variable(self.grid, repeated)

    def test_rejects_invalid_horizon(self):
        with self.assertRaisesRegex(ValueError, "Prediction horizon"):
            features.build_target_variable(self.grid, self.history, horizon_months=0)

    def test_rejects_unknown_sector(self):
        unknown = self.history.copy()
        unknown.loc[0, "cell_id"] = "UNKNOWN"
        with self.assertRaisesRegex(ValueError, "unknown sectors"):
            features.build_target_variable(self.grid, unknown)


if __name__ == "__main__":
    unittest.main()
