"""Regression tests for past-only, sector-specific temporal features.

Synthetic event counts are used only in automated tests. Production features
must consume the canonical observed sector-month history from DVC.
"""

import unittest

import pandas as pd

from hydrosight.features.feature_engineering import build_temporal_features


class TemporalFeatureTests(unittest.TestCase):
    def setUp(self):
        # Intentionally unsorted, sparse observed sector-month records.
        # December 2022 is outside the 12-month window for January 2024.
        self.df_break_history = pd.DataFrame(
            [
                ("CELL_B", "2024-01-01", 8),
                ("CELL_A", "2024-01-01", 5),
                ("CELL_A", "2022-12-01", 7),
                ("CELL_B", "2023-12-01", 4),
                ("CELL_A", "2023-12-01", 1),
                ("CELL_A", "2023-01-01", 2),
                ("CELL_A", "2024-03-01", 9),
            ],
            columns=["cell_id", "month", "break_count"],
        )
        self.df_break_history["month"] = pd.to_datetime(
            self.df_break_history["month"]
        )

        # Exactly the sector/reference-month pairs to be returned.
        self.df_target = pd.DataFrame(
            [
                ("CELL_A", "2024-01-01", 1),
                ("CELL_A", "2024-02-01", 0),
                ("CELL_B", "2024-01-01", 0),
                ("CELL_B", "2024-02-01", 1),
                ("CELL_C", "2024-01-01", 0),
                ("CELL_C", "2024-02-01", 0),
            ],
            columns=["cell_id", "reference_date", "target_6m"],
        )
        self.df_target["reference_date"] = pd.to_datetime(
            self.df_target["reference_date"]
        )

    def get_results(self):
        result = build_temporal_features(
            self.df_break_history.copy(),
            self.df_target.copy(),
        )
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(
            list(result.columns),
            ["cell_id", "reference_date", "breaks_last_12m"],
        )
        self.assertFalse(
            result.duplicated(["cell_id", "reference_date"]).any()
        )
        self.assertEqual(len(result), len(self.df_target))
        self.assertFalse(result["breaks_last_12m"].isna().any())
        self.assertTrue((result["breaks_last_12m"] >= 0).all())
        self.assertEqual(
            set(zip(result["cell_id"], result["reference_date"])),
            set(zip(self.df_target["cell_id"], self.df_target["reference_date"])),
        )
        return result.set_index(["cell_id", "reference_date"])

    def test_exact_previous_12_months_excludes_current_and_future(self):
        result = self.get_results()

        # For January 2024, January–December 2023 contributes 2 + 1.
        # December 2022 (7), January 2024 (5), March 2024 (9)
        # must not contribute.
        self.assertEqual(
            result.loc[("CELL_A", pd.Timestamp("2024-01-01")), "breaks_last_12m"],
            3,
        )

        # For February 2024, February 2023–January 2024 contributes
        # December 2023 (1) plus January 2024 (5). January 2023 (2)
        # is now outside the rolling window.
        self.assertEqual(
            result.loc[("CELL_A", pd.Timestamp("2024-02-01")), "breaks_last_12m"],
            6,
        )

    def test_sector_isolation_and_months_without_recorded_breaks(self):
        result = self.get_results()

        self.assertEqual(
            result.loc[("CELL_B", pd.Timestamp("2024-01-01")), "breaks_last_12m"],
            4,
        )
        self.assertEqual(
            result.loc[("CELL_B", pd.Timestamp("2024-02-01")), "breaks_last_12m"],
            12,
        )

        # CELL_C has no recorded breaks, but must still have a feature
        # for each requested reference month.
        self.assertEqual(
            result.loc[("CELL_C", pd.Timestamp("2024-01-01")), "breaks_last_12m"],
            0,
        )
        self.assertEqual(
            result.loc[("CELL_C", pd.Timestamp("2024-02-01")), "breaks_last_12m"],
            0,
        )

    def test_target_is_not_used_as_an_input_feature(self):
        original_target = self.df_target.copy(deep=True)
        result = self.get_results()

        self.assertNotIn("target_6m", result.columns)
        pd.testing.assert_frame_equal(self.df_target, original_target)

        changed_target = self.df_target.copy()
        changed_target["target_6m"] = 1 - changed_target["target_6m"]
        with_changed_labels = build_temporal_features(
            self.df_break_history.copy(),
            changed_target,
        )

        expected = result.reset_index().sort_values(
            ["cell_id", "reference_date"]
        ).reset_index(drop=True)
        actual = with_changed_labels.sort_values(
            ["cell_id", "reference_date"]
        ).reset_index(drop=True)

        pd.testing.assert_frame_equal(actual, expected)


if __name__ == "__main__":
    unittest.main()
