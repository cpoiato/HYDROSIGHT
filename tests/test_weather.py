
"""Tests for the imputation and preservation choices of the Weather EDA."""

import unittest

import pandas as pd

from hydrosight.preprocessing.weather import clean_weather


class WeatherPolicyTests(unittest.TestCase):
    def setUp(self):
        self.df = pd.DataFrame({
            "date": pd.date_range("2024-01-01", periods=9),
            "temp_mean_c": [5.0] * 9,
            "temp_min_c": [0.0] * 9,
            "temp_max_c": [10.0] * 9,
            "precip_mm": [0.0] * 9,
            "snow_cm": [0.0] * 9,
        })

    def test_short_gaps_and_unknown_precipitation(self):
        self.df.loc[2:4, "temp_mean_c"] = None
        self.df.loc[2, "precip_mm"] = None
        self.df.loc[3, "snow_cm"] = None
        cleaned, summary = clean_weather(self.df)
        self.assertEqual(summary["temp_mean_c_imputed"], 3)
        self.assertEqual(summary["precip_missing"], 1)
        self.assertEqual(summary["snow_missing"], 1)
        self.assertTrue(pd.isna(cleaned.loc[2, "precip_mm"]))

    def test_long_gaps_are_kept_and_calendar_is_not_forced(self):
        self.df = self.df.drop(index=0).reset_index(drop=True)
        self.df.loc[1:4, "temp_min_c"] = None
        cleaned, summary = clean_weather(self.df)
        self.assertEqual(summary["temp_min_c_imputed"], 0)
        self.assertEqual(cleaned["temp_min_c"].isna().sum(), 4)
        self.assertEqual(len(cleaned), 8)

    def test_clips_only_imputed_mean(self):
        self.df.loc[3, "temp_mean_c"] = None
        self.df.loc[2, "temp_mean_c"] = 10.0
        self.df.loc[4, "temp_mean_c"] = 10.0
        self.df.loc[3, "temp_max_c"] = 7.0
        cleaned, summary = clean_weather(self.df)
        self.assertEqual(cleaned.loc[3, "temp_mean_c"], 7.0)
        self.assertEqual(summary["corrected_imputed_means"], 1)


if __name__ == "__main__":
    unittest.main()
