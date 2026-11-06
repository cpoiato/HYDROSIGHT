
"""Tests for exact school-location consolidation in the EDA."""

import unittest

import geopandas as gpd
import pandas as pd
from shapely.geometry import Polygon

from hydrosight.preprocessing.schools import clean_schools


class SchoolsPolicyTests(unittest.TestCase):
    def setUp(self):
        self.boundary = gpd.GeoDataFrame(
            geometry=[Polygon([(-114.2, 51), (-114, 51), (-114, 51.2), (-114.2, 51.2)])],
            crs="EPSG:4326",
        )

    @staticmethod
    def school(identifier, x, name="Access Academy", address="Same Address"):
        return {
            "type": "Feature",
            "id": identifier,
            "geometry": {"type": "Point", "coordinates": [x, 51.1]},
            "properties": {"NAME": name, "ADDRESS": address},
        }

    def test_consolidates_identical_location_not_name_alone(self):
        features = [
            self.school(1, -114.10),
            self.school(2, -114.10),
            self.school(3, -114.10),
            self.school(4, -114.11),
        ]
        df = pd.DataFrame({
            "type": ["FeatureCollection"] * 4,
            "features": features,
        })
        cleaned, summary = clean_schools(df, self.boundary)
        self.assertEqual(summary["duplicate_locations_removed"], 2)
        self.assertEqual(len(cleaned), 2)
        self.assertEqual(cleaned.iloc[0]["features"]["id"], 1)
        self.assertIn("boundary_status", cleaned.columns)

    def test_preserves_missing_name_or_address(self):
        features = [
            self.school(1, -114.10, name=None, address="A"),
            self.school(2, -114.11, name=None, address="A"),
        ]
        df = pd.DataFrame({
            "type": ["FeatureCollection"] * 2,
            "features": features,
        })
        cleaned, _ = clean_schools(df, self.boundary)
        self.assertEqual(len(cleaned), 2)

    def test_keeps_duplicate_ids_with_distinct_locations(self):
        df = pd.DataFrame({
            "type": ["FeatureCollection"] * 2,
            "features": [
                self.school(1, -114.1),
                self.school(1, -114.12),
            ],
        })
        cleaned, summary = clean_schools(df, self.boundary)
        self.assertEqual(len(cleaned), 2)
        self.assertEqual(summary["duplicate_feature_ids"], 1)


if __name__ == "__main__":
    unittest.main()
