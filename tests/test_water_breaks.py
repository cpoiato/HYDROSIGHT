
"""Tests for the EDA-approved water main breaks cleaning policy."""

import unittest

import pandas as pd

from hydrosight.preprocessing.water_breaks import clean_water_breaks


class WaterBreaksPolicyTests(unittest.TestCase):
    def test_incomplete_and_five_field_duplicate_removed(self):
        df = pd.DataFrame([
            {"break_date": "2022-01-01", "break_type": "A", "status": "ACTIVE", "point": {"coordinates": [-114.1, 51.0]}, "other": 1},
            {"break_date": "2022-01-01", "break_type": "A", "status": "ACTIVE", "point": {"coordinates": [-114.1, 51.0]}, "other": 2},
            {"break_date": "2022-01-02", "break_type": None, "status": "ACTIVE", "point": {"coordinates": [-114.1, 51.0]}, "other": 3},
            {"break_date": "1999-01-01", "break_type": "B", "status": "ACTIVE", "point": {"coordinates": [-114.2, 51.1]}, "other": 4},
        ])
        cleaned, summary = clean_water_breaks(df)
        self.assertEqual(summary["incomplete_removed"], 1)
        self.assertEqual(summary["probable_duplicates_removed"], 1)
        self.assertEqual(len(cleaned), 2)
        self.assertEqual(set(cleaned.other), {1, 4})

    def test_invalid_coordinates_are_missing_not_new_geographic_filter(self):
        df = pd.DataFrame([
            {"break_date": "2022-01-01", "break_type": "A", "status": "ACTIVE", "point": None},
            {"break_date": "2022-01-02", "break_type": "B", "status": "ACTIVE", "point": {"coordinates": [-179, 30]}},
        ])
        cleaned, _ = clean_water_breaks(df)
        self.assertEqual(len(cleaned), 1)
        self.assertEqual(cleaned.iloc[0]["longitude"], -179)


if __name__ == "__main__":
    unittest.main()
