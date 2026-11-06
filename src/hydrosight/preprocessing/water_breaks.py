
"""Water main breaks preprocessing, following 01_eda_water_breaks.ipynb."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed" / "water_breaks"
DUPLICATE_COLUMNS = [
    "break_date", "break_type", "status", "longitude", "latitude"
]


def clean_water_breaks(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Remove incomplete records and probable duplicates, exactly as in the EDA."""
    records = df.copy()
    records["break_date"] = pd.to_datetime(records["break_date"], errors="coerce")

    point_coordinates = records["point"].map(
        lambda point: point.get("coordinates") if isinstance(point, dict) else None
    )
    records["longitude"] = pd.to_numeric(
        point_coordinates.map(
            lambda coords: coords[0]
            if isinstance(coords, (list, tuple)) and len(coords) >= 2 else np.nan
        ),
        errors="coerce",
    )
    records["latitude"] = pd.to_numeric(
        point_coordinates.map(
            lambda coords: coords[1]
            if isinstance(coords, (list, tuple)) and len(coords) >= 2 else np.nan
        ),
        errors="coerce",
    )
    records = records.drop(columns=["point"])

    incomplete = records.isna().any(axis=1)
    df_clean = records.dropna().copy()
    duplicate_excess = int(
        df_clean.duplicated(subset=DUPLICATE_COLUMNS, keep="first").sum()
    )
    df_clean = df_clean.drop_duplicates(
        subset=DUPLICATE_COLUMNS, keep="first"
    ).copy()

    summary = {
        "original_records": len(records),
        "incomplete_removed": int(incomplete.sum()),
        "incomplete_removed_2016_2025": int(
            (incomplete & records["break_date"].dt.year.between(2016, 2025)).sum()
        ),
        "probable_duplicates_removed": duplicate_excess,
        "clean_records": len(df_clean),
    }
    assert len(df_clean) == (
        summary["original_records"]
        - summary["incomplete_removed"]
        - summary["probable_duplicates_removed"]
    )
    return df_clean, summary


def process_water_breaks(source: Path, output_dir: Path = OUTPUT_DIR) -> Path:
    """Read the real raw JSONL snapshot and export the cleaned JSONL snapshot."""
    df_clean, summary = clean_water_breaks(pd.read_json(source, lines=True))
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = output_dir / f"water_main_breaks_clean_{timestamp}.jsonl"
    df_clean.to_json(
        output, orient="records", lines=True, date_format="iso", force_ascii=False
    )
    print("=== WATER MAIN BREAKS CLEANING ===")
    print(f"Source: {source}")
    for name, value in summary.items():
        print(f"{name}: {value}")
    print(f"Output: {output}")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Process Calgary water main breaks.")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args()
    process_water_breaks(args.source, args.output_dir)


if __name__ == "__main__":
    main()
