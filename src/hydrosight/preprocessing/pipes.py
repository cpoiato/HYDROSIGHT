
"""Public water mains preprocessing, following 02_eda_pipes.ipynb."""

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
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed" / "pipes"


def clean_pipes(
    df: pd.DataFrame, boundary: gpd.GeoDataFrame
) -> tuple[pd.DataFrame, dict]:
    """Apply only the removal and transformation steps executed in the EDA."""
    df_clean = df.copy()
    df_clean["p_zone"] = df_clean["p_zone"].fillna("Undefined")

    pipes_gdf = gpd.GeoDataFrame(
        df_clean.copy(),
        geometry=df_clean["multilinestring"].apply(
            lambda value: shape(json.loads(value))
            if isinstance(value, str) else shape(value)
        ),
        crs="EPSG:4326",
    )
    pipes = pipes_gdf.to_crs(boundary.crs)
    city = boundary.geometry.union_all()
    pipes["boundary_status"] = "outside"
    pipes.loc[pipes.geometry.intersects(city), "boundary_status"] = "partially_inside"
    pipes.loc[pipes.geometry.covered_by(city), "boundary_status"] = "inside"

    outside = pipes["boundary_status"].eq("outside")
    partly_inside = int(pipes["boundary_status"].eq("partially_inside").sum())
    df_clean = df_clean.drop(index=pipes.index[outside]).copy()

    # The EDA calculates these diagnostics without changing recorded lengths.
    df_clean["geometry_length_m"] = (
        pipes_gdf.loc[df_clean.index].to_crs("EPSG:32611").geometry.length
    )
    df_clean["length_difference_m"] = (
        df_clean["length"] - df_clean["geometry_length_m"]
    ).abs()

    count_before_diameter = len(df_clean)
    df_clean = df_clean[df_clean["diam"] > 0].copy()
    diameters_removed = count_before_diameter - len(df_clean)

    future_planned = (
        df_clean["year"].gt(2026) & df_clean["status_ind"].eq("PLANNED")
    )
    planned_removed = int(future_planned.sum())
    df_clean = df_clean.loc[~future_planned].copy()

    summary = {
        "original_records": len(df),
        "missing_pressure_zones_filled": int(df["p_zone"].isna().sum()),
        "outside_pipes_removed": int(outside.sum()),
        "partially_inside_pipes_retained": partly_inside,
        "nonpositive_diameters_removed": diameters_removed,
        "future_planned_pipes_removed": planned_removed,
        "clean_records": len(df_clean),
    }
    return df_clean, summary


def process_pipes(
    source: Path,
    output_dir: Path = OUTPUT_DIR,
    boundary_file: Path | None = None,
) -> Path:
    """Read a real snapshot and export the same JSONL fields as the EDA."""
    boundary = (
        gpd.read_file(boundary_file)
        if boundary_file is not None
        else load_saved_boundary()
    )
    if boundary is None:
        boundary = load_official_boundary()

    df_clean, summary = clean_pipes(pd.read_json(source, lines=True), boundary)
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = output_dir / f"public_water_mains_clean_{timestamp}.jsonl"
    df_clean.to_json(
        output, orient="records", lines=True, date_format="iso", force_ascii=False
    )
    print("=== PUBLIC WATER MAINS CLEANING ===")
    print(f"Source: {source}")
    for name, value in summary.items():
        print(f"{name}: {value}")
    print(f"Output: {output}")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Process Calgary public water mains.")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--boundary", type=Path, default=None)
    args = parser.parse_args()
    process_pipes(args.source, args.output_dir, args.boundary)


if __name__ == "__main__":
    main()
