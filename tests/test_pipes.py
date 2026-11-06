
"""Tests for the cleaning decisions executed in the Pipes EDA."""

import unittest

import geopandas as gpd
import pandas as pd
from shapely.geometry import Polygon

from hydrosight.preprocessing.pipes import clean_pipes


class PipesPolicyTests(unittest.TestCase):
    def setUp(self):
        self.boundary = gpd.GeoDataFrame(
            geometry=[Polygon([(-114.2, 51), (-114, 51), (-114, 51.2), (-114.2, 51.2)])],
            crs="EPSG:4326",
        )

    @staticmethod
    def pipe(identifier, x1, x2, diam=100, year=2000, status="ACTIVE", zone=None):
        return {
            "p_zone": zone,
            "status_ind": status,
            "length": 100.0,
            "diam": diam,
            "material": "PVC",
            "year": year,
            "globalid": identifier,
            "multilinestring": {"type": "MultiLineString", "coordinates": [[[x1, 51.1], [x2, 51.1]]]},
        }

    def test_filters_only_as_eda(self):
        df = pd.DataFrame([
            self.pipe("a", -114.15, -114.12),
            self.pipe("b", -114.24, -114.12),
            self.pipe("c", -114.5, -114.4),
            self.pipe("d", -114.15, -114.12, diam=0),
            self.pipe("e", -114.15, -114.12, year=2029, status="PLANNED"),
            self.pipe("f", -114.15, -114.12, status="INACTIVE"),
        ])
        cleaned, summary = clean_pipes(df, self.boundary)
        self.assertEqual(set(cleaned.globalid), {"a", "b", "f"})
        self.assertEqual(summary["outside_pipes_removed"], 1)
        self.assertEqual(summary["partially_inside_pipes_retained"], 1)
        self.assertEqual(summary["nonpositive_diameters_removed"], 1)
        self.assertEqual(summary["future_planned_pipes_removed"], 1)
        self.assertTrue(cleaned.p_zone.eq("Undefined").all())
        self.assertIn("length_difference_m", cleaned.columns)

    def test_no_automatic_deduplication(self):
        first = self.pipe("same", -114.15, -114.12)
        df = pd.DataFrame([first, dict(first)])
        cleaned, _ = clean_pipes(df, self.boundary)
        self.assertEqual(len(cleaned), 2)


if __name__ == "__main__":
    unittest.main()
