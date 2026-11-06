
"""School preprocessing, following 5_eda_schools.ipynb."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import mapping, shape

from hydrosight.preprocessing.spatial_grid import (
    load_official_boundary,
    load_saved_boundary,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed" / "schools"


def clean_schools(
    df: pd.DataFrame, boundary: gpd.GeoDataFrame
) -> tuple[gpd.GeoDataFrame, dict]:
    """Consolidate only repeated name, address and coordinate combinations."""
    schools = gpd.GeoDataFrame(
        df.copy(),
        geometry=df["features"].apply(
            lambda value: shape(json.loads(value))
            if isinstance(value, str) else shape(value)
        ),
        crs="EPSG:4326",
    ).to_crs(boundary.crs)
    city = boundary.geometry.union_all()
    schools["boundary_status"] = "outside"
    schools.loc[schools.geometry.intersects(city), "boundary_status"] = "partially_inside"
    schools.loc[schools.geometry.covered_by(city), "boundary_status"] = "inside"

    properties = []
    for index, feature in schools["features"].items():
        if isinstance(feature, dict):
            data = feature.get("properties", {}).copy()
            data["feature_id"] = feature.get("id")
            data["geometry_type"] = feature.get("geometry", {}).get("type")
            data["coordinates"] = str(
                feature.get("geometry", {}).get("coordinates")
            )
            properties.append((index, data))

    df_features = pd.DataFrame(
        [data for _, data in properties],
        index=[index for index, _ in properties],
    )
    duplicate_mask = df_features.duplicated(
        subset=["NAME", "ADDRESS", "coordinates"], keep="first"
    )
    df_clean = schools.loc[~duplicate_mask].copy()

    summary = {
        "original_records": len(df),
        "duplicate_feature_ids": int(
            df_features.duplicated(subset=["feature_id"]).sum()
        ),
        "duplicate_locations_removed": int(duplicate_mask.sum()),
        "clean_records": len(df_clean),
    }
    return df_clean, summary


def process_schools(
    source: Path,
    output_dir: Path = OUTPUT_DIR,
    boundary_file: Path | None = None,
) -> Path:
    """Export the same newline-delimited record structure used in the EDA."""
    boundary = (
        gpd.read_file(boundary_file)
        if boundary_file is not None
        else load_saved_boundary()
    )
    if boundary is None:
        boundary = load_official_boundary()

    df_clean, summary = clean_schools(pd.read_json(source), boundary)
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    # The EDA uses this extension for newline-delimited JSON records.
    output = output_dir / f"schools_clean_{timestamp}.geojson"
    with output.open("w", encoding="utf-8") as stream:
        for _, row in df_clean.iterrows():
            record = {}
            for column in df_clean.columns:
                value = row[column]
                if column == "geometry" and value is not None:
                    record[column] = mapping(value)
                elif isinstance(value, (dict, list)):
                    record[column] = value
                elif hasattr(value, "item"):
                    record[column] = value.item()
                else:
                    record[column] = (
                        str(value)
                        if not isinstance(value, (int, float, bool, type(None)))
                        else value
                    )
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")

    print("=== CALGARY SCHOOLS CLEANING ===")
    print(f"Source: {source}")
    for name, value in summary.items():
        print(f"{name}: {value}")
    print(f"Output: {output}")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Process Calgary schools.")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--boundary", type=Path, default=None)
    args = parser.parse_args()
    process_schools(args.source, args.output_dir, args.boundary)


if __name__ == "__main__":
    main()
