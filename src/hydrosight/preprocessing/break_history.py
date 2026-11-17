"""Persist the observed break history for Calgary's versioned 500 m sectors."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory

import geopandas as gpd
import pandas as pd
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[3]
GRID_PATH = PROJECT_ROOT / "data" / "processed" / "spatial_grid.geojson"
GRID_MANIFEST_PATH = PROJECT_ROOT / "data" / "processed" / "spatial_grid_manifest.json"
WATER_BREAKS_PATH = PROJECT_ROOT / "data" / "pipeline" / "preprocessed" / "water_breaks.jsonl"
OUTPUT_DIR = PROJECT_ROOT / "data" / "pipeline" / "break_history"


def assign_breaks_to_grid(
    df_water_breaks: pd.DataFrame,
    grid: gpd.GeoDataFrame,
) -> gpd.GeoDataFrame:
    """Assign each real break to one 500 m sector, resolving border ties predictably."""
    required = {"longitude", "latitude", "break_date"}
    if not required.issubset(df_water_breaks):
        raise ValueError(f"Water breaks missing columns: {sorted(required - set(df_water_breaks))}")
    if "cell_id" not in grid or grid.crs is None or grid.empty:
        raise ValueError("The sector grid must have cell_id, a CRS, and at least one cell.")
    if grid["cell_id"].isna().any() or not grid["cell_id"].is_unique:
        raise ValueError("Grid sector identifiers must be non-null and unique.")
    if grid.geometry.isna().any() or not grid.geometry.is_valid.all():
        raise ValueError("Sector grid contains missing or invalid geometry.")

    records = df_water_breaks.reset_index(drop=True).copy()
    lon = pd.to_numeric(records["longitude"], errors="coerce")
    lat = pd.to_numeric(records["latitude"], errors="coerce")
    if not lon.between(-180, 180).all() or not lat.between(-90, 90).all():
        raise ValueError("Break coordinates must be valid WGS84 longitude and latitude.")
    if pd.to_datetime(records["break_date"], errors="coerce").isna().any():
        raise ValueError("Water break dates must be valid.")

    records["_source_row"] = np.arange(len(records))
    breaks = gpd.GeoDataFrame(
        records,
        geometry=gpd.points_from_xy(lon, lat),
        crs="EPSG:4326",
    ).to_crs(grid.crs)

    # Perform the join in metres. A 1 cm tolerance prevents floating-point
    # CRS round-trips from losing a point exactly on a shared cell boundary.
    # Border ties are consistently resolved by the smallest stable cell ID.
    metric_crs = "EPSG:32611"
    candidates = gpd.sjoin(
        breaks.to_crs(metric_crs),
        grid[["cell_id", "geometry"]].to_crs(metric_crs),
        how="left",
        predicate="dwithin",
        distance=0.01,
    )
    candidates["candidate_cell_count"] = (
        candidates.groupby("_source_row")["cell_id"].transform("count").astype(int)
    )
    assigned = (
        candidates.sort_values(["_source_row", "cell_id"], kind="mergesort")
        .drop_duplicates("_source_row", keep="first")
        .sort_values("_source_row")
        .reset_index(drop=True)
        .drop(columns=["_source_row", "index_right"], errors="ignore")
    )
    if len(assigned) != len(records):
        raise RuntimeError("Spatial assignment changed the number of source records.")
    return assigned.to_crs(grid.crs)


def aggregate_break_history(gdf_breaks_grid: gpd.GeoDataFrame) -> pd.DataFrame:
    """Count real observed breaks by sector and calendar month (no zero imputation)."""
    required = {"cell_id", "break_date"}
    if not required.issubset(gdf_breaks_grid):
        raise ValueError("Break assignments need cell_id and break_date.")
    breaks = gdf_breaks_grid.dropna(subset=["cell_id"]).copy()
    dates = pd.to_datetime(breaks["break_date"], errors="coerce")
    if dates.isna().any():
        raise ValueError("Assigned breaks contain invalid dates.")
    breaks["month"] = dates.dt.to_period("M").dt.to_timestamp()
    return (
        breaks.groupby(["cell_id", "month"], as_index=False)
        .size()
        .rename(columns={"size": "break_count"})
        .sort_values(["cell_id", "month"])
        .reset_index(drop=True)
    )


def build_and_save_break_history(
    water_breaks_path: Path,
    grid_path: Path,
    grid_manifest_path: Path,
    output_dir: Path,
) -> dict:
    """Write canonical monthly observed counts and a reproducible quality summary."""
    with grid_manifest_path.open(encoding="utf-8") as stream:
        grid_manifest = json.load(stream)
    grid = gpd.read_file(grid_path)
    if (grid_manifest.get("grid_size_meters") != 500
            or grid_manifest.get("cell_count") != len(grid)
            or not grid_manifest.get("active_version")):
        raise ValueError("Grid manifest does not describe the active 500 m sector grid.")

    events = pd.read_json(water_breaks_path, lines=True)
    assignments = assign_breaks_to_grid(events, grid)
    history = aggregate_break_history(assignments)
    assigned_count = int(assignments["cell_id"].notna().sum())
    unassigned_count = len(events) - assigned_count
    if int(history["break_count"].sum()) != assigned_count:
        raise RuntimeError("Monthly break counts do not match spatial assignments.")
    if not set(history["cell_id"]).issubset(set(grid["cell_id"])):
        raise RuntimeError("Monthly history contains unknown sector identifiers.")

    source_hash = hashlib.sha256(water_breaks_path.read_bytes()).hexdigest()
    summary = {
        "grid_version": grid_manifest["active_version"],
        "grid_size_meters": 500,
        "grid_cells": len(grid),
        "source_sha256": source_hash,
        "source_records": len(events),
        "assigned_records": assigned_count,
        "unassigned_records": unassigned_count,
        "border_ties_resolved": int(assignments["candidate_cell_count"].gt(1).sum()),
        "sector_month_records": len(history),
        "first_observed_month": history["month"].min().strftime("%Y-%m") if len(history) else None,
        "last_observed_month": history["month"].max().strftime("%Y-%m") if len(history) else None,
        "history_file": "breaks_by_sector_month.csv",
        "note": "Only observed sector-months are recorded; absent rows are not assumed to be zero.",
    }
    if summary["source_records"] != assigned_count + unassigned_count:
        raise RuntimeError("Source event counts are inconsistent.")

    output_dir.mkdir(parents=True, exist_ok=True)
    history_dest = output_dir / summary["history_file"]
    quality_dest = output_dir / "break_history_quality.json"
    with TemporaryDirectory(prefix=".break-history-", dir=output_dir) as temp:
        tmp_history = Path(temp) / history_dest.name
        tmp_quality = Path(temp) / quality_dest.name
        history.to_csv(tmp_history, index=False, date_format="%Y-%m-%d")
        tmp_quality.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(tmp_history, history_dest)
        os.replace(tmp_quality, quality_dest)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Build observed 500 m sector break history.")
    parser.add_argument("--water-breaks", type=Path, default=WATER_BREAKS_PATH)
    parser.add_argument("--grid", type=Path, default=GRID_PATH)
    parser.add_argument("--grid-manifest", type=Path, default=GRID_MANIFEST_PATH)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args()
    summary = build_and_save_break_history(
        args.water_breaks, args.grid, args.grid_manifest, args.output_dir
    )
    print("=== SECTOR BREAK HISTORY COMPLETED ===")
    for key, value in summary.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
