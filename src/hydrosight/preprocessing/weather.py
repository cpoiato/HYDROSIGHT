
"""Daily weather preprocessing, following 03_eda_weather.ipynb."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed" / "weather"
TEMPERATURE_COLUMNS = ["temp_mean_c", "temp_min_c", "temp_max_c"]


def clean_weather(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Apply the approved 2016-2025 interpolation and consistency corrections."""
    source = df.copy()
    source["date"] = pd.to_datetime(source["date"], errors="coerce")
    df_clean = source.loc[source["date"].dt.year.between(2016, 2025)].copy()
    df_clean = df_clean.sort_values("date").reset_index(drop=True)

    for column in TEMPERATURE_COLUMNS:
        missing_before = df_clean[column].isna()
        estimated = df_clean[column].interpolate(
            method="linear", limit=3, limit_area="inside"
        )
        gap_groups = missing_before.ne(missing_before.shift()).cumsum()
        gap_lengths = missing_before.groupby(gap_groups).transform("sum")
        eligible = missing_before & gap_lengths.le(3)
        df_clean.loc[eligible, column] = estimated.loc[eligible]
        df_clean[f"{column}_imputed"] = (
            eligible & df_clean[column].notna()
        ).astype(int)

    assert df_clean["date"].is_unique
    assert df_clean["date"].is_monotonic_increasing

    invalid_mean = (
        df_clean["temp_mean_c_imputed"].eq(1)
        & (
            df_clean["temp_mean_c"].lt(df_clean["temp_min_c"])
            | df_clean["temp_mean_c"].gt(df_clean["temp_max_c"])
        )
    )
    corrected_count = int(invalid_mean.sum())
    df_clean.loc[invalid_mean, "temp_mean_c"] = (
        df_clean.loc[invalid_mean, "temp_mean_c"].clip(
            lower=df_clean.loc[invalid_mean, "temp_min_c"],
            upper=df_clean.loc[invalid_mean, "temp_max_c"],
        )
    )
    remaining_violations = (
        df_clean["temp_min_c"].gt(df_clean["temp_mean_c"])
        | df_clean["temp_mean_c"].gt(df_clean["temp_max_c"])
    )
    assert not remaining_violations.any()

    summary = {
        "original_records": len(df),
        "study_records": len(df_clean),
        **{
            f"{column}_imputed": int(df_clean[f"{column}_imputed"].sum())
            for column in TEMPERATURE_COLUMNS
        },
        "corrected_imputed_means": corrected_count,
        "precip_missing": int(df_clean["precip_mm"].isna().sum()),
        "snow_missing": int(df_clean["snow_cm"].isna().sum()),
        "clean_records": len(df_clean),
    }
    return df_clean, summary


def process_weather(
    historical: Path, recent: Path, output_dir: Path = OUTPUT_DIR
) -> Path:
    """Combine both real CSV sources and export the cleaned study period."""
    source = pd.concat(
        [pd.read_csv(historical), pd.read_csv(recent)], ignore_index=True
    )
    df_clean, summary = clean_weather(source)
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = output_dir / f"daily_weather_calgary_{timestamp}.jsonl"
    df_clean.to_json(
        output, orient="records", lines=True, date_format="iso", force_ascii=False
    )
    print("=== CALGARY WEATHER CLEANING ===")
    print(f"Historical source: {historical}")
    print(f"Recent source: {recent}")
    for name, value in summary.items():
        print(f"{name}: {value}")
    print(f"Output: {output}")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Process Calgary daily weather.")
    parser.add_argument("--historical", type=Path, required=True)
    parser.add_argument("--recent", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args()
    process_weather(args.historical, args.recent, args.output_dir)


if __name__ == "__main__":
    main()
