
"""Hospital preprocessing, following 04_eda_hospitals.ipynb."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import shape

from hydrosight.preprocessing.spatial_grid import (
    load_official_boundary,
    load_saved_boundary,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed" / "hospitals"


def clean_hospitals(
    df: pd.DataFrame, boundary: gpd.GeoDataFrame
) -> tuple[pd.DataFrame, dict]:
    """Report EDA geographic checks but preserve every original record."""
    hospitals_gdf = gpd.GeoDataFrame(
        df.copy(),
        geometry=df["features"].apply(
            lambda value: shape(json.loads(value))
            if isinstance(value, str) else shape(value)
        ),
        crs="EPSG:4326",
    ).to_crs(boundary.crs)
    city = boundary.geometry.union_all()
    hospitals_gdf["boundary_status"] = "outside"
    hospitals_gdf.loc[
        hospitals_gdf.geometry.intersects(city), "boundary_status"
    ] = "partially_inside"
    hospitals_gdf.loc[
        hospitals_gdf.geometry.covered_by(city), "boundary_status"
    ] = "inside"
    hashable_cols = [
        column for column in hospitals_gdf.columns if column != "features"
    ]
    summary = {
        "original_records": len(df),
        "valid_geometries": int(hospitals_gdf.geometry.is_valid.sum()),
        "inside_calgary": int(hospitals_gdf["boundary_status"].eq("inside").sum()),
        "outside_calgary": int(hospitals_gdf["boundary_status"].eq("outside").sum()),
        "duplicate_records_excluding_features": int(
            hospitals_gdf.duplicated(subset=hashable_cols).sum()
        ),
        "clean_records": len(df),
    }
    return df.copy(), summary


def process_hospitals(
    source: Path,
    output_dir: Path = OUTPUT_DIR,
    boundary_file: Path | None = None,
) -> Path:
    """Read the original GeoJSON and export unchanged feature rows as JSONL."""
    boundary = (
        gpd.read_file(boundary_file)
        if boundary_file is not None
        else load_saved_boundary()
    )
    if boundary is None:
        boundary = load_official_boundary()

    df_clean, summary = clean_hospitals(pd.read_json(source), boundary)
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = output_dir / f"hospitals_clean_{timestamp}.jsonl"
    df_clean.to_json(
        output, orient="records", lines=True, date_format="iso", force_ascii=False
    )
    print("=== CALGARY HOSPITALS VALIDATION ===")
    print(f"Source: {source}")
    for name, value in summary.items():
        print(f"{name}: {value}")
    print(f"Output: {output}")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Process Calgary hospitals.")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--boundary", type=Path, default=None)
    args = parser.parse_args()
    process_hospitals(args.source, args.output_dir, args.boundary)


if __name__ == "__main__":
    main()
