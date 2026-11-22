from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from math import ceil
from pathlib import Path
import geopandas as gpd
import pandas as pd
from shapely.geometry import shape

from hydrosight.preprocessing.spatial_relationships import aggregate_pipe_features, assign_pipes_to_grid
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





def aggregate_weather_features(df_weather: pd.DataFrame) -> pd.DataFrame:
    dates = pd.to_datetime(df_weather["date"])
    weather = df_weather.loc[dates.dt.year.between(2016, 2025)].copy()
    weather["month"] = dates.loc[weather.index].dt.to_period("M")

    monthly = weather.groupby("month").agg(
        precipitation_days=("precip_mm", "count"),
        snowfall_days=("snow_cm", "count"),
        precipitation_mm=("precip_mm", lambda values: values.sum(min_count=1)),
        snowfall_cm=("snow_cm", lambda values: values.sum(min_count=1)),
    )
    monthly.insert(0, "calendar_days", monthly.index.days_in_month)
    return monthly


def print_weather_summary(monthly_weather: pd.DataFrame) -> None:
    print("\n=== Monthly weather coverage (2016–2025) ===")
    print("Months covered:", len(monthly_weather))

    for label, column in [
        ("Precipitation", "precipitation_days"),
        ("Snowfall", "snowfall_days"),
    ]:
        missing_days = monthly_weather["calendar_days"] - monthly_weather[column]
        print(f"{label}: {missing_days.gt(0).sum()} months with missing measurements")

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




def print_historical_baseline(
    breaks_in_period: pd.DataFrame,
    pipe_cells: set[str],
) -> None:
    history = breaks_in_period.loc[breaks_in_period["month"].dt.year.le(2023)]
    historical_counts = history.groupby("cell_id")["break_count"].sum()

    sector_ranking = (
        historical_counts
        .reindex(pd.Index(sorted(pipe_cells), name="cell_id"), fill_value=0)
        .reset_index()
        .sort_values(["break_count", "cell_id"], ascending=[False, True])
    )

    top_sector_count = ceil(len(sector_ranking) * 0.10)
    priority_cells = sector_ranking.head(top_sector_count)["cell_id"]

    print("\n=== Historical baseline: top 10% of sectors ===")
    print(f"Priority sectors: {top_sector_count:,} (ranked using breaks from 2016–2023)")
    print()
    print(f"{'Test year':<10} {'Captured breaks':>16} {'Total breaks':>13} {'Capture rate':>13}")

    for year in (2024, 2025):
        year_breaks = breaks_in_period.loc[breaks_in_period["month"].dt.year.eq(year)]
        total = year_breaks["break_count"].sum()
        captured = year_breaks.loc[
            year_breaks["cell_id"].isin(priority_cells), "break_count"
        ].sum()

        print(f"{year:<10} {captured:>16,} {total:>13,} {captured / total:>13.1%}")


def main() -> None:
    grid = load_spatial_grid()
    gdf_hospitals_grid = assign_hospitals_to_grid(load_processed_data("hospitals"), grid)
    gdf_schools_grid = assign_schools_to_grid(load_processed_data("schools"), grid)
    gdf_pipes_grid = assign_pipes_to_grid(load_processed_data("pipes"), grid)
    gdf_water_breaks_grid = assign_breaks_to_grid(load_processed_data("water_breaks"), grid)
    df_weather = load_processed_data("weather")


    df_pipe_features = aggregate_pipe_features(gdf_pipes_grid, grid)

    df_break_history = aggregate_break_history(gdf_water_breaks_grid)
    breaks_in_period = df_break_history.loc[
        df_break_history["month"].dt.year.between(2016, 2025)
    ]
    pipe_cells = set(df_pipe_features["cell_id"].dropna())

    print_historical_baseline(breaks_in_period, pipe_cells)

    monthly_weather = aggregate_weather_features(df_weather)
    print_weather_summary(monthly_weather)

if __name__ == "__main__":
    main()
