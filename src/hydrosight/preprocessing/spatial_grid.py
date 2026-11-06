"""Versioned Calgary spatial grid built from the official municipal boundary."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from uuid import uuid4

import geopandas as gpd
import numpy as np
from shapely import set_precision
from shapely.geometry import box

PROJECT_ROOT = Path(__file__).resolve().parents[3]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
VERSION_DIR = PROCESSED_DIR / "spatial_grid_versions"
BOUNDARY_PATH = PROCESSED_DIR / "calgary_boundary.geojson"
GRID_PATH = PROCESSED_DIR / "spatial_grid.geojson"
MANIFEST_PATH = PROCESSED_DIR / "spatial_grid_manifest.json"

BOUNDARY_URL = (
    "https://services1.arcgis.com/AVP60cs0Q9PEA8rH/"
    "arcgis/rest/services/City_Boundary/FeatureServer/0/query"
    "?where=1%3D1&outFields=*&outSR=4326&returnGeometry=true&f=geojson"
)
GRID_SIZE_METERS = 500
METRIC_CRS = "EPSG:32611"
OUTPUT_CRS = "EPSG:4326"
GRID_ALGORITHM = "clipped-positive-area-v1"


def validate_boundary(boundary: gpd.GeoDataFrame) -> None:
    """Reject invalid municipal geometry or an undefined reference system."""
    if boundary.empty or boundary.crs is None:
        raise ValueError("Calgary boundary is empty or has no CRS.")
    if boundary.geometry.isna().any() or not boundary.geometry.is_valid.all():
        raise ValueError("Calgary boundary contains missing or invalid geometries.")
    if not boundary.geom_type.isin(["Polygon", "MultiPolygon"]).all():
        raise ValueError("Calgary boundary must contain polygon geometries.")


def load_official_boundary() -> gpd.GeoDataFrame:
    """Retrieve and validate the official municipal boundary."""
    boundary = gpd.read_file(BOUNDARY_URL)
    validate_boundary(boundary)
    return boundary.to_crs(OUTPUT_CRS)


def load_saved_boundary() -> gpd.GeoDataFrame | None:
    if not BOUNDARY_PATH.exists():
        return None
    boundary = gpd.read_file(BOUNDARY_PATH)
    validate_boundary(boundary)
    return boundary.to_crs(OUTPUT_CRS)


def boundary_geometry(boundary: gpd.GeoDataFrame):
    validate_boundary(boundary)
    return boundary.to_crs(METRIC_CRS).geometry.union_all()


def boundaries_equal(left: gpd.GeoDataFrame, right: gpd.GeoDataFrame) -> bool:
    """Compare geographic areas, independent of GeoJSON ordering and metadata."""
    return set_precision(boundary_geometry(left), 0.00001).equals(
        set_precision(boundary_geometry(right), 0.00001)
    )


def boundary_fingerprint(boundary: gpd.GeoDataFrame) -> str:
    geom = set_precision(boundary_geometry(boundary), 0.00001).normalize()
    return hashlib.sha256(geom.wkb).hexdigest()[:16]


def grid_version(boundary: gpd.GeoDataFrame) -> str:
    """Include geometry and generation contract in every version identifier."""
    payload = f"{boundary_fingerprint(boundary)}|{GRID_SIZE_METERS}|{METRIC_CRS}|{GRID_ALGORITHM}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def generate_grid(boundary: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Generate aligned 500 m cells, clipped to the Calgary municipal polygon."""
    city = boundary_geometry(boundary)
    minx, miny, maxx, maxy = city.bounds
    x_start = int(np.floor(minx / GRID_SIZE_METERS) * GRID_SIZE_METERS)
    y_start = int(np.floor(miny / GRID_SIZE_METERS) * GRID_SIZE_METERS)
    x_end = int(np.ceil(maxx / GRID_SIZE_METERS) * GRID_SIZE_METERS)
    y_end = int(np.ceil(maxy / GRID_SIZE_METERS) * GRID_SIZE_METERS)

    rows = []
    for x in range(x_start, x_end, GRID_SIZE_METERS):
        for y in range(y_start, y_end, GRID_SIZE_METERS):
            clipped = box(x, y, x + GRID_SIZE_METERS, y + GRID_SIZE_METERS).intersection(city)
            if not clipped.is_empty and clipped.area > 0:
                rows.append({"cell_id": f"CELL_{x}_{y}", "geometry": clipped})

    if not rows:
        raise ValueError("No spatial grid cells were generated.")
    grid = gpd.GeoDataFrame(rows, geometry="geometry", crs=METRIC_CRS)
    if grid.cell_id.duplicated().any() or not grid.geometry.is_valid.all():
        raise ValueError("Generated grid contains invalid geometries or duplicate identifiers.")
    return grid.to_crs(OUTPUT_CRS)


def grids_equal(left: gpd.GeoDataFrame, right: gpd.GeoDataFrame) -> bool:
    """Compare cell IDs and geometries regardless of row order."""
    if "cell_id" not in left or "cell_id" not in right:
        return False
    if len(left) != len(right) or left.cell_id.duplicated().any() or right.cell_id.duplicated().any():
        return False
    a = left.to_crs(METRIC_CRS).set_index("cell_id").geometry
    b = right.to_crs(METRIC_CRS).set_index("cell_id").geometry
    if set(a.index) != set(b.index):
        return False
    return all(set_precision(a.at[key], 0.00001).equals(set_precision(b.at[key], 0.00001)) for key in a.index)


def load_manifest() -> dict | None:
    if not MANIFEST_PATH.exists():
        return None
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _save_geojson(data: gpd.GeoDataFrame, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.stem}-{uuid4().hex}.geojson")
    try:
        data.to_crs(OUTPUT_CRS).to_file(temporary, driver="GeoJSON")
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def _save_manifest(version: str, boundary: gpd.GeoDataFrame, cell_count: int) -> None:
    payload = {
        "active_version": version,
        "boundary_fingerprint": boundary_fingerprint(boundary),
        "grid_algorithm": GRID_ALGORITHM,
        "grid_size_meters": GRID_SIZE_METERS,
        "metric_crs": METRIC_CRS,
        "cell_count": cell_count,
    }
    temporary = MANIFEST_PATH.with_name(f".{MANIFEST_PATH.name}.{uuid4().hex}.tmp")
    try:
        temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, MANIFEST_PATH)
    finally:
        temporary.unlink(missing_ok=True)


def activate_grid(boundary: gpd.GeoDataFrame, grid: gpd.GeoDataFrame) -> str:
    """Archive older active files, then activate the explicitly approved grid."""
    version = grid_version(boundary)
    VERSION_DIR.mkdir(parents=True, exist_ok=True)
    old_manifest = load_manifest()
    if GRID_PATH.exists():
        old_version = (old_manifest or {}).get("active_version", "legacy")
        old_grid = VERSION_DIR / f"grid_{old_version}.geojson"
        if not old_grid.exists():
            old_grid.write_bytes(GRID_PATH.read_bytes())
    if BOUNDARY_PATH.exists():
        old_version = (old_manifest or {}).get("active_version", "legacy")
        old_boundary = VERSION_DIR / f"boundary_{old_version}.geojson"
        if not old_boundary.exists():
            old_boundary.write_bytes(BOUNDARY_PATH.read_bytes())

    version_boundary = VERSION_DIR / f"boundary_{version}.geojson"
    version_grid = VERSION_DIR / f"grid_{version}.geojson"
    if version_boundary.exists() or version_grid.exists():
        if not (version_boundary.exists() and version_grid.exists()):
            raise ValueError("Incomplete archived grid version; manual review required.")
        archived_boundary = gpd.read_file(version_boundary)
        archived_grid = gpd.read_file(version_grid)
        if not boundaries_equal(archived_boundary, boundary) or not grids_equal(archived_grid, grid):
            raise ValueError("Archived version differs from the proposed grid; refusing to overwrite it.")
    else:
        _save_geojson(boundary, version_boundary)
        _save_geojson(grid, version_grid)

    _save_geojson(boundary, BOUNDARY_PATH)
    _save_geojson(grid, GRID_PATH)
    _save_manifest(version, boundary, len(grid))
    return version


def show_grid(boundary: gpd.GeoDataFrame, grid: gpd.GeoDataFrame) -> None:
    """Display the clipped grid and actual Calgary boundary."""
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(12, 12))
    boundary.to_crs(OUTPUT_CRS).boundary.plot(ax=ax, color="black", linewidth=1.2)
    grid.to_crs(OUTPUT_CRS).boundary.plot(ax=ax, color="steelblue", linewidth=0.3)
    ax.set_title("Calgary — 500 m Spatial Grid")
    ax.set_axis_off()
    plt.tight_layout()
    plt.show()
