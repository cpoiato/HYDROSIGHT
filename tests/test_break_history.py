"""Regression tests for US-03. All synthetic records are confined to tests."""

import json
import tempfile
import unittest
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point, box

from hydrosight.preprocessing.break_history import (
    aggregate_break_history,
    assign_breaks_to_grid,
    build_and_save_break_history,
)


class BreakHistoryTests(unittest.TestCase):
    def test_single_canonical_history_implementation(self):
        """US-03 owns these functions; feature engineering only consumes them."""
        import inspect
        import hydrosight.features.feature_engineering as features
        import hydrosight.preprocessing.break_history as history_module

        for name in ("assign_breaks_to_grid", "aggregate_break_history"):
            canonical = getattr(history_module, name)
            self.assertIs(getattr(features, name), canonical)
            self.assertEqual(inspect.getmodule(canonical), history_module)

    @staticmethod
    def sample_data():
        grid = gpd.GeoDataFrame(
            {"cell_id": ["CELL_LEFT", "CELL_RIGHT"]},
            geometry=[
                box(500000, 5600000, 500500, 5600500),
                box(500500, 5600000, 501000, 5600500),
            ],
            crs="EPSG:32611",
        ).to_crs("EPSG:4326")
        points = gpd.GeoSeries(
            [
                Point(500250, 5600250),
                Point(500750, 5600250),
                Point(500500, 5600250),
                Point(502000, 5600250),
            ],
            crs="EPSG:32611",
        ).to_crs("EPSG:4326")
        breaks = pd.DataFrame({
            "break_date": ["2024-01-03", "2024-01-04", "2024-02-01", "2024-02-06"],
            "longitude": points.x,
            "latitude": points.y,
        })
        return breaks, grid

    def test_border_tie_and_outside_city_are_accounted_for(self):
        breaks, grid = self.sample_data()
        result = assign_breaks_to_grid(breaks, grid)
        self.assertEqual(len(result), len(breaks))
        self.assertEqual(result["cell_id"].tolist()[:3], ["CELL_LEFT", "CELL_RIGHT", "CELL_LEFT"])
        self.assertTrue(pd.isna(result.loc[3, "cell_id"]))
        self.assertEqual(result["candidate_cell_count"].tolist(), [1, 1, 2, 0])
        history = aggregate_break_history(result)
        counts = {(r.cell_id, r.month.strftime("%Y-%m")): r.break_count for r in history.itertuples()}
        self.assertEqual(counts, {
            ("CELL_LEFT", "2024-01"): 1,
            ("CELL_LEFT", "2024-02"): 1,
            ("CELL_RIGHT", "2024-01"): 1,
        })
        self.assertEqual(history["break_count"].sum(), 3)

    def test_monthly_history_is_persisted_and_reproducible(self):
        breaks, grid = self.sample_data()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            input_file = root / "water_breaks.jsonl"
            grid_file = root / "grid.geojson"
            manifest_file = root / "grid_manifest.json"
            output_dir = root / "history"
            breaks.to_json(input_file, orient="records", lines=True)
            grid.to_file(grid_file, driver="GeoJSON")
            manifest_file.write_text(json.dumps({
                "grid_size_meters": 500,
                "cell_count": 2,
                "active_version": "automated-test-version",
            }), encoding="utf-8")
            summary = build_and_save_break_history(input_file, grid_file, manifest_file, output_dir)
            self.assertEqual(summary["source_records"], 4)
            self.assertEqual(summary["assigned_records"], 3)
            self.assertEqual(summary["unassigned_records"], 1)
            self.assertEqual(summary["border_ties_resolved"], 1)
            self.assertEqual(summary["grid_version"], "automated-test-version")
            csv_bytes = (output_dir / "breaks_by_sector_month.csv").read_bytes()
            json_bytes = (output_dir / "break_history_quality.json").read_bytes()
            self.assertEqual(pd.read_csv(output_dir / "breaks_by_sector_month.csv")["break_count"].sum(), 3)
            self.assertEqual(summary, build_and_save_break_history(input_file, grid_file, manifest_file, output_dir))
            self.assertEqual(csv_bytes, (output_dir / "breaks_by_sector_month.csv").read_bytes())
            self.assertEqual(json_bytes, (output_dir / "break_history_quality.json").read_bytes())

    def test_invalid_source_coordinates_are_rejected(self):
        breaks, grid = self.sample_data()
        breaks.loc[0, "longitude"] = 999
        with self.assertRaisesRegex(ValueError, "coordinates"):
            assign_breaks_to_grid(breaks, grid)

    def test_duplicate_grid_identifiers_are_rejected(self):
        breaks, grid = self.sample_data()
        grid.loc[1, "cell_id"] = grid.loc[0, "cell_id"]
        with self.assertRaisesRegex(ValueError, "identifiers"):
            assign_breaks_to_grid(breaks, grid)

    def test_only_500_meter_grid_is_accepted(self):
        breaks, grid = self.sample_data()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = root / "input.jsonl"
            geo = root / "grid.geojson"
            manifest = root / "manifest.json"
            breaks.to_json(raw, orient="records", lines=True)
            grid.to_file(geo, driver="GeoJSON")
            manifest.write_text(json.dumps({
                "grid_size_meters": 1000,
                "cell_count": 2,
                "active_version": "wrong-grid",
            }), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "500 m"):
                build_and_save_break_history(raw, geo, manifest, root / "output")


if __name__ == "__main__":
    unittest.main()
