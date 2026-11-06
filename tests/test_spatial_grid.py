"""Regression tests. Synthetic geometry is used only inside automated tests."""

import unittest

import geopandas as gpd
from shapely.geometry import box

from hydrosight.preprocessing.spatial_grid import (
    boundaries_equal,
    boundary_fingerprint,
    generate_grid,
    grid_version,
    grids_equal,
)


class SpatialGridTests(unittest.TestCase):
    @staticmethod
    def boundary(geometry):
        return gpd.GeoDataFrame(geometry=[geometry], crs="EPSG:32611")

    def test_equivalent_boundary_geometry(self):
        first = self.boundary(box(500100, 5600100, 501100, 5601100))
        second = first.to_crs("EPSG:4326")
        self.assertTrue(boundaries_equal(first, second))
        self.assertEqual(boundary_fingerprint(first), boundary_fingerprint(second))

    def test_changed_boundary_geometry(self):
        first = self.boundary(box(500100, 5600100, 501100, 5601100))
        second = self.boundary(box(500100, 5600100, 501600, 5601100))
        self.assertFalse(boundaries_equal(first, second))
        self.assertNotEqual(grid_version(first), grid_version(second))

    def test_grid_is_deterministic(self):
        boundary = self.boundary(box(500100, 5600100, 501100, 5601100))
        first = generate_grid(boundary)
        second = generate_grid(boundary)
        self.assertTrue(grids_equal(first, second))
        self.assertTrue(first.cell_id.is_unique)

    def test_cells_do_not_extend_outside_boundary(self):
        boundary = self.boundary(box(500100, 5600100, 501100, 5601100))
        grid = generate_grid(boundary).to_crs("EPSG:32611")
        city = boundary.geometry.union_all()
        self.assertTrue(all(cell.difference(city).area < 0.001 for cell in grid.geometry))
        self.assertEqual(len(grid), 9)

    def test_different_cell_ids_fail_comparison(self):
        boundary = self.boundary(box(500100, 5600100, 501100, 5601100))
        first = generate_grid(boundary)
        second = first.copy()
        second.loc[second.index[0], "cell_id"] = "CHANGED"
        self.assertFalse(grids_equal(first, second))

    def test_legacy_full_cells_are_detected_as_outdated(self):
        boundary = self.boundary(box(500100, 5600100, 501100, 5601100))
        clipped = generate_grid(boundary)
        old = clipped.to_crs("EPSG:32611")
        first = old.geometry.iloc[0]
        x = int(first.bounds[0] // 500) * 500
        y = int(first.bounds[1] // 500) * 500
        old.loc[old.index[0], "geometry"] = box(x, y, x + 500, y + 500)
        self.assertFalse(grids_equal(clipped, old))


if __name__ == "__main__":
    unittest.main()
