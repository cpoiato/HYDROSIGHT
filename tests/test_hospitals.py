
"""Tests for preserving hospitals as in the EDA."""

import unittest

import geopandas as gpd
import pandas as pd
from shapely.geometry import Polygon

from hydrosight.preprocessing.hospitals import clean_hospitals


class HospitalsPolicyTests(unittest.TestCase):
    def setUp(self):
        self.boundary = gpd.GeoDataFrame(
            geometry=[Polygon([(-114.2, 51), (-114, 51), (-114, 51.2), (-114.2, 51.2)])],
            crs="EPSG:4326",
        )

    @staticmethod
    def feature(feature_id, x, name=None):
        return {
            "type": "Feature",
            "id": feature_id,
            "geometry": {"type": "Point", "coordinates": [x, 51.1]},
            "properties": {"NAME": name},
        }

    def test_no_rejection_of_missing_names_or_duplicate_ids(self):
        df = pd.DataFrame({
            "type": ["FeatureCollection"] * 3,
            "features": [
                self.feature(1, -114.1),
                self.feature(1, -114.1),
                self.feature(3, -114.5),
            ],
        })
        cleaned, summary = clean_hospitals(df, self.boundary)
        self.assertEqual(len(cleaned), 3)
        self.assertEqual(summary["outside_calgary"], 1)
        self.assertEqual(summary["clean_records"], 3)


if __name__ == "__main__":
    unittest.main()
