from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
import geopandas as gpd
import pandas as pd
from shapely.geometry import shape
import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[3]
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"
PIPES_DIR = OUTPUT_DIR / "pipes"
WATER_DIR = OUTPUT_DIR / "water"
WEATHER_DIR = OUTPUT_DIR / "weather"
HOSPITALS_DIR = OUTPUT_DIR / "hospitals"
SCHOOLS_DIR = OUTPUT_DIR / "schools"




PROJECT_ROOT = Path(__file__).resolve().parents[3]
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"
PIPELINE_DIR = PROJECT_ROOT / "data" / "pipeline" / "preprocessed"


def load_processed_data(dataset_name: str) -> pd.DataFrame:
    """Load a DVC-managed processed dataset."""
    file_path = PIPELINE_DIR / f"{dataset_name}.jsonl"

    if not file_path.is_file():
        raise FileNotFoundError(f"Dataset not found: {file_path}")

    return pd.read_json(file_path, lines=True)


def load_spatial_grid() -> gpd.GeoDataFrame:
    """Load the existing Calgary spatial grid."""
    grid_path = OUTPUT_DIR / "spatial_grid.geojson"
    return gpd.read_file(grid_path)


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


def assign_pipes_to_grid(
    df_pipes: pd.DataFrame,
    grid: gpd.GeoDataFrame
) -> gpd.GeoDataFrame:
    """Assign pipes to spatial grid cells using their geometries."""

    pipes = gpd.GeoDataFrame(
        df_pipes.copy(),
        geometry=df_pipes["multilinestring"].apply(
            lambda value: shape(json.loads(value))
            if isinstance(value, str)
            else shape(value)
        ),
        crs="EPSG:4326"
    )

    pipes = pipes.to_crs(grid.crs)

    gdf_pipes_grid = gpd.sjoin(
        pipes,
        grid[["cell_id", "geometry"]],
        how="left",
        predicate="intersects"
    )

    return gdf_pipes_grid

def extract_geometry(value):
    if isinstance(value, str):
        value = json.loads(value)
    if value.get("type") == "Feature":
        value = value["geometry"]

    return shape(value)

def assign_hospitals_to_grid(
    df_hospitals: pd.DataFrame,
    grid: gpd.GeoDataFrame
) -> gpd.GeoDataFrame:

    hospitals = gpd.GeoDataFrame(
        df_hospitals.copy(),
        geometry=df_hospitals["features"].apply(extract_geometry),
        crs="EPSG:4326"
    )

    hospitals = hospitals.to_crs(grid.crs)

    gdf_hospitals_grid = gpd.sjoin(
        hospitals,
        grid[["cell_id", "geometry"]],
        how="left",
        predicate="intersects"
    )

    return gdf_hospitals_grid

def assign_schools_to_grid(
    df_schools: pd.DataFrame,
    grid: gpd.GeoDataFrame
) -> gpd.GeoDataFrame:

    schools = gpd.GeoDataFrame(
        df_schools.copy(),
        geometry=df_schools["features"].apply(extract_geometry),
        crs="EPSG:4326"
    )

    schools = schools.to_crs(grid.crs)

    gdf_schools_grid = gpd.sjoin(
        schools,
        grid[["cell_id", "geometry"]],
        how="left",
        predicate="intersects"
    )

    return gdf_schools_grid


def match_breaks_to_pipes(
    gdf_pipes: gpd.GeoDataFrame,
    gdf_water_breaks: gpd.GeoDataFrame,
) -> gpd.GeoDataFrame:
    """Match water main breaks to nearby pipes using metric distances."""

    pipes = (
        gdf_pipes
        .drop(columns=["index_right"], errors="ignore")
        .to_crs("EPSG:32611")
    )

    breaks = (
        gdf_water_breaks
        .drop(columns=["index_right"], errors="ignore")
        .reset_index(drop=True)
        .to_crs("EPSG:32611")
        .copy()
    )

    breaks["break_id"] = breaks.index

    gdf_pipe_breaks = gpd.sjoin_nearest(
        breaks,
        pipes[["globalid", "geometry"]],
        how="left",
        max_distance=30,
        distance_col="distance_m",
    )

    gdf_pipe_breaks = gdf_pipe_breaks.drop(
        columns=["index_right"],
        errors="ignore"
    )

    gdf_pipe_breaks["match"] = np.select(
        [
            gdf_pipe_breaks["globalid"].isna(),
            gdf_pipe_breaks.duplicated(
                subset=["break_id"],
                keep=False
            )
        ],
        [
            "Absent",
            "Ambiguous"
        ],
        default="Unique"
    )

    return gdf_pipe_breaks


def aggregate_pipe_features(
    gdf_pipes_grid: gpd.GeoDataFrame,
    grid: gpd.GeoDataFrame,
) -> pd.DataFrame:
    """Aggregate pipe characteristics by spatial grid cell."""

    pipes = gdf_pipes_grid.dropna(subset=["cell_id"]).copy()

    pipes = pipes.to_crs("EPSG:32611")
    cells = grid.to_crs("EPSG:32611")

    cell_geometries = cells.set_index("cell_id")["geometry"]

    pipes["pipe_length_in_cell_m"] = pipes.apply(
        lambda row: row.geometry.intersection(
            cell_geometries.loc[row["cell_id"]]
        ).length,
        axis=1,
    )

    df_features = (
        pipes.groupby("cell_id")
        .agg(
            pipe_count=("globalid", "nunique"),
            pipe_length_m=("pipe_length_in_cell_m", "sum"),
            avg_diameter=("diam", "mean"),
            material_count=("material", "nunique"),
        )
        .reset_index()
    )

    return df_features


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


def aggregate_weather_features():
    pass
def aggregate_geographic_features():
    pass
def build_temporal_features():
    pass
def build_target_variable():
    pass
def build_feature_dataframe():
    pass
def validate_feature_dataframe():
    pass
def save_feature_dataframe():
    pass

def main():
    grid = load_spatial_grid()
    gdf_hospitals_grid = assign_hospitals_to_grid(load_processed_data("hospitals"),grid)
    gdf_schools_grid = assign_schools_to_grid(load_processed_data("schools"),grid)
    gdf_pipes_grid = assign_pipes_to_grid(load_processed_data("pipes"),grid)
    gdf_water_breaks_grid = assign_breaks_to_grid(load_processed_data("water_breaks"),grid)
    df_weather = load_processed_data("weather")
    gdf_pipe_breaks = match_breaks_to_pipes(gdf_pipes_grid,gdf_water_breaks_grid)

    print(gdf_pipe_breaks["match"].value_counts())
    print(gdf_pipe_breaks["distance_m"].describe())
    print("Original breaks:", len(gdf_water_breaks_grid))
    print("Unique matched break IDs:", gdf_pipe_breaks["break_id"].nunique())

    df_pipe_features = aggregate_pipe_features(
        gdf_pipes_grid,
        grid
    )

    print(df_pipe_features.head())

    print(
        "Duplicate pipe-cell pairs:",
        gdf_pipes_grid.duplicated(
            subset=["globalid", "cell_id"]
        ).sum()
    )

    print(
        "Total network length in grid (m):",
        round(df_pipe_features["pipe_length_m"].sum(), 2)
    )

    print(
        "Cells containing pipes:",
        len(df_pipe_features)
    )

    df_break_history = aggregate_break_history(gdf_water_breaks_grid)

    print(df_break_history.head())
    print("Breaks assigned to grid:", df_break_history["break_count"].sum())

if __name__ == "__main__":
    main()
