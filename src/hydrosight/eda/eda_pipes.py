from __future__ import annotations

import base64
import html
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[3]
RAW_DIR = ROOT_DIR / "data" / "raw" / "pipes"
REPORT_DIR = ROOT_DIR / "reports" / "eda" / "results"
FIGURES_DIR = ROOT_DIR / "reports" / "eda" / "figures"
HTML_REPORT = ROOT_DIR / "reports" / "eda" / "pipes_eda_report.html"

def load_data() -> pd.DataFrame:
    """Load data from a JSONL file into a pandas DataFrame."""
    files = sorted(RAW_DIR.glob("public_water_mains_*.jsonl"))
    if not files:
        raise FileNotFoundError(f"No pipe dataset found in {RAW_DIR}")
    input_file = files[-1]  # YYYYMMDDTHHMMSSZ is lexically chronological
    df = pd.read_json(input_file, lines=True)
    print(f"\nLoaded file: {input_file}\nOriginal records: {len(df)}")
    return df

def transform_data(df: pd.DataFrame) -> pd.DataFrame:

    return df

def clean_data(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    df_clean = df.copy()

    # Identify missing values before replacement
    missing_mask = df_clean["p_zone"].isna()
    missing_count = int(missing_mask.sum())

    # Preserve the original missing-value information
    df_clean["p_zone_was_missing"] = missing_mask

    # Replace missing pressure zones
    df_clean["p_zone"] = df_clean["p_zone"].fillna("Undefined")

    cleaning_report = {
        "p_zone": {
            "missing_records": missing_count,
            "missing_percentage": round(
                missing_count / len(df_clean) * 100, 2
            ) if len(df_clean) else 0.0,
            "replacement_value": "Undefined",
            "records_after_cleaning": int(len(df_clean)),
            "records_removed": 0,
            "method": "fillna",
            "justification": (
                "Missing pressure zone values were replaced with "
                "'Undefined' because their actual values could not "
                "be reliably determined from the available data."
            ),
            "limitation": (
                "'Undefined' represents missing information, "
                "not an actual pressure zone."
            ),
            "original_data_preserved": True
        }
    }

    print("\n=== P_ZONE CLEANING ===")
    print(f"Missing values identified: {missing_count}")
    print(f"Missing values replaced: {missing_count}")
    print(f"Remaining missing values: {df_clean['p_zone'].isna().sum()}")

    return df_clean, cleaning_report

def describe_data(df: pd.DataFrame) -> None:
    print("\n=== NUMERICAL DESCRIPTION ===")
    print(df.describe())

    print("\n=== CATEGORICAL DESCRIPTION ===")
    categorical_columns = [
        "p_zone",
        "status_ind",
        "material"
    ]

    print(df[categorical_columns].describe())

def validate_data(df: pd.DataFrame) -> None:
    print("\n=== SAMPLE DATA")
    print(df.sample(10))
    print("\n=== DATAFRAME INFORMATION ===")
    df.info()
    missing = df.isna().sum()
    missing_rows = df[df.isna().any(axis=1)]

    geometry = df["multilinestring"].iloc[0]

    if isinstance(geometry, dict):
        print("Key:", geometry.keys())
        print("Type:", geometry.get("type"))
        print("Coordinates:", geometry.get("coordinates"))


    print("\n=== MISSING VALUES ===\n", missing)
    print("\n=== MISSING VALUES PERCENT===\n", missing/len(df)*100)

def analyze_missing_p_zone(df: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    missing = df[df["p_zone"].isna()].copy()
    known = df[df["p_zone"].notna()].copy()

    def geometry_key(geometry):
        if not isinstance(geometry, dict):
            return None
        return json.dumps(
            geometry,
            sort_keys=True,
            separators=(",", ":")
        )

    missing["_geometry_key"] = missing["multilinestring"].map(geometry_key)
    known["_geometry_key"] = known["multilinestring"].map(geometry_key)

    # Uma geometria pode aparecer associada a mais de uma zona.
    zone_matches = (
        known.dropna(subset=["_geometry_key"])
        .groupby("_geometry_key")["p_zone"]
        .agg(lambda values: sorted(set(values)))
    )

    matches = missing["_geometry_key"].map(zone_matches)

    unique_matches = matches.map(
        lambda zones: isinstance(zones, list) and len(zones) == 1
    )

    ambiguous_matches = matches.map(
        lambda zones: isinstance(zones, list) and len(zones) > 1
    )

    report = {
        "missing_p_zone": int(len(missing)),
        "exact_geometry_unique_zone": int(unique_matches.sum()),
        "exact_geometry_ambiguous_zone": int(ambiguous_matches.sum()),
        "without_exact_match": int(
            len(missing)
            - unique_matches.sum()
            - ambiguous_matches.sum()
        ),
        "method": "Exact GeoJSON geometry comparison",
        "action": "Analysis only. No values modified."
    }

    candidates = missing.loc[unique_matches].copy()
    candidates["suggested_p_zone"] = matches.loc[
        unique_matches
    ].map(lambda zones: zones[0])

    print("\n=== MISSING P_ZONE ANALYSIS ===")
    print(json.dumps(report, indent=4, ensure_ascii=False))

    print("\n=== CANDIDATES FOR P_ZONE RECOVERY ===")

    if not candidates.empty:
        print(
            candidates[
                ["globalid", "suggested_p_zone"]
            ].to_string(index=False)
        )
    else:
        print("No exact geometry matches found.")

    return report, candidates.drop(columns=["_geometry_key"])




def main() -> None:
    df = load_data()
    describe_data(df)
    validate_data(df)
    analyze_missing_p_zone(df)
    df_clean, report_clean = clean_data(df)



if __name__ == "__main__":
    main()


