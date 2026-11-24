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

import pandas as pd


def build_target_variable(
    df_grid: pd.DataFrame,
    df_break_history: pd.DataFrame,
    horizon_months: int = 6,
) -> pd.DataFrame:
    """Build monthly binary targets from observed water main breaks."""

    study_start = pd.Period("2016-01", freq="M")

    if horizon_months < 1:
        raise ValueError("Prediction horizon must be positive.")

    # Load acquisition metadata
    manifest_path = (
        PROJECT_ROOT
        / "reports"
        / "latest_download_manifest.json"
    )

    with manifest_path.open(encoding="utf-8") as file:
        manifest = json.load(file)

    source = manifest["sources"]["water_breaks"]

    if source["status"] != "OK":
        raise ValueError("Water break acquisition was unsuccessful.")

    # Get the last fully elapsed month at acquisition time
    acquisition_month = (
        pd.to_datetime(manifest["run_utc"], utc=True)
        .tz_localize(None)
        .to_period("M")
    )

    # Prepare the canonical break history
    history = df_break_history[
        ["cell_id", "month", "break_count"]
    ].copy()

    if history.empty:
        raise ValueError("Break history is empty.")

    history["month"] = (
        pd.to_datetime(history["month"])
        .dt.to_period("M")
        .dt.to_timestamp()
    )

    history["break_count"] = pd.to_numeric(
        history["break_count"],
        errors="raise",
    )

    if (
        history["cell_id"].isna().any()
        or history["break_count"].isna().any()
        or (history["break_count"] < 0).any()
        or (history["break_count"] % 1 != 0).any()
    ):
        raise ValueError("Invalid break history records.")

    if history.duplicated(["cell_id", "month"]).any():
        raise ValueError("Duplicate sector-month records.")

    history["break_count"] = history["break_count"].astype("int64")

    last_observed_month = history["month"].max().to_period("M")

    # Estimate a conservative cutoff from available evidence
    # This is a provisional cutoff, not certified source coverage.
    observation_end = min(
        acquisition_month - 1,
        last_observed_month - 1,
    )

    # Calculate the last reference month with a full future horizon
    last_reference_month = (
        observation_end - (horizon_months - 1)
    )

    if last_reference_month < study_start:
        raise ValueError("Insufficient historical observation period.")

    # Get all spatial sectors
    if (
        df_grid["cell_id"].isna().any()
        or not df_grid["cell_id"].is_unique
    ):
        raise ValueError("Invalid spatial sector identifiers.")

    sector_ids = df_grid["cell_id"].unique()

    if not history["cell_id"].isin(sector_ids).all():
        raise ValueError("Break history contains unknown sectors.")

    # Generate all monthly dates through the observation cutoff
    months = pd.date_range(
        start=study_start.to_timestamp(),
        end=observation_end.to_timestamp(),
        freq="MS",
    )

    # Create one row per sector and month
    df_target = pd.MultiIndex.from_product(
        [sector_ids, months],
        names=["cell_id", "reference_date"],
    ).to_frame(index=False)

    # Join recorded monthly breaks
    df_target = df_target.merge(
        history.rename(columns={"month": "reference_date"}),
        on=["cell_id", "reference_date"],
        how="left",
        validate="one_to_one",
    )

    # No matching record means zero observed breaks in that month
    df_target["break_count"] = (
        df_target["break_count"]
        .fillna(0)
        .astype("int64")
    )

    df_target = df_target.sort_values(
        ["cell_id", "reference_date"]
    ).reset_index(drop=True)

    # Calculate breaks in the current and following months
    grouped = df_target.groupby(
        "cell_id",
        sort=False,
    )["break_count"]

    future_breaks = pd.Series(
        0,
        index=df_target.index,
        dtype="int64",
    )

    for offset in range(horizon_months):
        future_breaks += grouped.shift(
            -offset,
            fill_value=0,
        )

    # Assign binary targets: 1 = break, 0 = no recorded break
    target_column = f"target_{horizon_months}m"

    df_target[target_column] = (
        future_breaks > 0
    ).astype("int8")

    # Keep only complete future observation windows
    df_target = df_target.loc[
        df_target["reference_date"]
        <= last_reference_month.to_timestamp(),
        ["cell_id", "reference_date", target_column],
    ].reset_index(drop=True)

    print("Observation cutoff:", observation_end)
    print("Last valid reference:", last_reference_month)
    print("Total observations:", len(df_target))
    print(df_target[target_column].value_counts())

    return df_target


def calculate_last_available_month(
    df_break_history: pd.DataFrame,
) -> pd.Period:
    """Calculate a conservative provisional observation cutoff."""

    manifest_path = (
        PROJECT_ROOT
        / "reports"
        / "latest_download_manifest.json"
    )

    with manifest_path.open(encoding="utf-8") as file:
        manifest = json.load(file)

    source = manifest["sources"]["water_breaks"]

    if source["status"] != "OK":
        raise ValueError("Water break acquisition was not successful.")

    # Identify the month of the source snapshot
    snapshot_date = pd.to_datetime(
        source["snapshot_utc"],
        format="%Y%m%dT%H%M%SZ",
        utc=True,
    )

    snapshot_month = (
        snapshot_date.tz_localize(None).to_period("M")
    )

    # Identify the latest month containing a recorded break
    history_months = pd.to_datetime(
        df_break_history["month"],
        errors="raise",
    )

    if history_months.empty:
        raise ValueError("Break history is empty.")

    last_observed_month = history_months.max().to_period("M")

    # Exclude the snapshot's ongoing month and
    # the last month with a recorded event
    last_available_month = min(
        snapshot_month - 1,
        last_observed_month - 1,
    )

    return last_available_month








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

    df_target = build_target_variable(grid, df_break_history)

    print("Unique sectors:", df_target["cell_id"].nunique())

    print(
        df_target.groupby(
            df_target["reference_date"].dt.year
        )["target_6m"].agg(
            observations="size",
            positive_targets="sum",
            positive_rate="mean"
        )
    )

    # Load the canonical spatial relationships output
    df_sectors = pd.read_json(
        PROJECT_ROOT
        / "data/pipeline/spatial_relationships/sector_summary.jsonl",
        lines=True
    )

    # Identify sectors containing water mains
    pipe_sector_ids = set(
        df_sectors.loc[
            df_sectors["pipe_length_m"] > 0,
            "cell_id"
        ]
    )

    # Compare targets by pipe presence
    df_analysis = df_target.assign(
        has_pipe=df_target["cell_id"].isin(pipe_sector_ids)
    )

    summary = df_analysis.groupby("has_pipe").agg(
        sectors=("cell_id", "nunique"),
        observations=("target_6m", "size"),
        positive_targets=("target_6m", "sum"),
        positive_rate=("target_6m", "mean")
    )

    print(summary)

   # Load existing DVC spatial relationships
    df_sectors = pd.read_json(
        PROJECT_ROOT
        / "data/pipeline/spatial_relationships/sector_summary.jsonl",
        lines=True,
    )

    # Identify sectors containing water mains
    pipe_sector_ids = set(
        df_sectors.loc[
            df_sectors["pipe_length_m"] > 0,
            "cell_id",
        ]
    )

    # Select model targets for sectors with water infrastructure
    df_target_model = df_target.loc[
        df_target["cell_id"].isin(pipe_sector_ids)
    ].copy()

    print("\n=== MODEL TARGET SUMMARY ===")
    print("Sectors:", df_target_model["cell_id"].nunique())
    print("Observations:", len(df_target_model))
    print(df_target_model["target_6m"].value_counts())

if __name__ == "__main__":
    main()
