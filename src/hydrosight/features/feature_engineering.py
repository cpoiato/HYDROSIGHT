from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
import geopandas as gpd
import pandas as pd
from shapely.geometry import shape
import numpy as np

from hydrosight.preprocessing.break_history import (
    assign_breaks_to_grid,
    aggregate_break_history,
)


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
        .drop_duplicates(subset=["globalid"])
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

    break_match_summary = gdf_pipe_breaks.drop_duplicates(subset=["break_id"])

    print("Match status by break:")
    print(break_match_summary["match"].value_counts())
    print("Original breaks:", len(gdf_water_breaks_grid))

    print("Candidate distances (m):")
    print(gdf_pipe_breaks["distance_m"].describe())

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
    print("Breaks between 2016 and 2025:", df_break_history.loc[df_break_history["month"].dt.year.between(2016, 2025),"break_count"].sum())
    df_cell_breaks =df_break_history.loc[df_break_history["month"].dt.year.between(2016, 2025),"cell_id"].copy()
    print("Cells with breaks between 2016 and 2025:", df_cell_breaks.nunique())

    pipe_cells = set(df_pipe_features["cell_id"].dropna())
    break_cells = set(df_cell_breaks.dropna())

    print("Cells with pipes and breaks:", len(pipe_cells & break_cells))
    print("Cells with breaks but no pipes:", len(break_cells - pipe_cells))
    print("Cells with pipes but no breaks:", len(pipe_cells - break_cells))

    breaks_in_period = df_break_history.loc[
        df_break_history["month"].dt.year.between(2016, 2025)
    ]

    breaks_per_cell = breaks_in_period.groupby("cell_id")["break_count"].sum()

    print("Break recurrence by sector (2016–2025):")
    print("Sectors with exactly one break:", breaks_per_cell.eq(1).sum())
    print("Sectors with two or more breaks:", breaks_per_cell.ge(2).sum())
    print("Highest break count in one sector:", breaks_per_cell.max())

    from math import ceil

    history = df_break_history.loc[
        df_break_history["month"].dt.year.between(2016, 2023)
    ]

    historical_counts = history.groupby("cell_id")["break_count"].sum()

    sector_ranking = (
        historical_counts
        .reindex(pd.Index(sorted(pipe_cells), name="cell_id"), fill_value=0)
        .reset_index()
        .sort_values(["break_count", "cell_id"], ascending=[False, True])
    )

    top_sector_count = ceil(len(sector_ranking) * 0.10)
    priority_cells = sector_ranking.head(top_sector_count)["cell_id"]

    print("Priority sectors:", top_sector_count)

    for year in (2024, 2025):
        year_breaks = df_break_history.loc[
            df_break_history["month"].dt.year.eq(year)
        ]
        total = year_breaks["break_count"].sum()
        captured = year_breaks.loc[
            year_breaks["cell_id"].isin(priority_cells), "break_count"
        ].sum()

        print(f"{year}: {captured}/{total} breaks captured ({captured / total:.1%})")



if __name__ == "__main__":
    main()
