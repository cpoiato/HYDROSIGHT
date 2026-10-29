"""HYDROSIGHT — EDA des ruptures de conduites d'eau de Calgary.

Point d'entrée à exécuter dans PyCharm. Conserve la politique de nettoyage
existante (dropna + dédoublonnage des cinq attributs). Les exclusions
probables ne constituent pas une preuve d'identité des événements.
"""
from __future__ import annotations

import base64
import html
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from hydrosight.eda.visualization.visualize_water_breaks import (
    visualize_water_breaks,
    visualize_spatial_distribution,
    visualize_monthly_comparison
)

ROOT_DIR = Path(__file__).resolve().parents[3]
RAW_DIR = ROOT_DIR / "data" / "raw" / "water_breaks"
REPORT_DIR = ROOT_DIR / "reports" / "eda" / "results"
FIGURES_DIR = ROOT_DIR / "reports" / "eda" / "figures"
HTML_REPORT = ROOT_DIR / "reports" / "eda" / "water_breaks_eda_report.html"

DUPLICATE_COLUMNS = ["break_date", "break_type", "status", "longitude", "latitude"]
SEASONS = ["Hiver", "Printemps", "Été", "Automne"]


def load_data() -> pd.DataFrame:
    """Load the most recent timestamped JSONL snapshot (not newest file edit)."""
    files = sorted(RAW_DIR.glob("water_main_breaks_*.jsonl"))
    if not files:
        raise FileNotFoundError(f"No water main breaks dataset found in {RAW_DIR}")
    input_file = files[-1]  # YYYYMMDDTHHMMSSZ is lexically chronological
    df = pd.read_json(input_file, lines=True)
    print(f"\nLoaded file: {input_file}\nOriginal records: {len(df)}")
    return df


def transform_data(df: pd.DataFrame) -> pd.DataFrame:
    """Convert source break date and GeoJSON point to typed coordinates."""
    result = df.copy()
    result["break_date"] = pd.to_datetime(result["break_date"], errors="coerce")

    def coordinates(point):
        if not isinstance(point, dict):
            return (float("nan"), float("nan"))
        values = point.get("coordinates")
        if not isinstance(values, (tuple, list)) or len(values) < 2:
            return (float("nan"), float("nan"))
        return (values[0], values[1])

    coords = result["point"].map(coordinates)
    result["longitude"] = pd.to_numeric(coords.map(lambda p: p[0]), errors="coerce")
    result["latitude"] = pd.to_numeric(coords.map(lambda p: p[1]), errors="coerce")
    return result.drop(columns=["point"])


def validate_data(df: pd.DataFrame) -> dict:
    print("\n=== DATAFRAME INFORMATION ===")
    df.info()
    missing = df.isna().sum()
    missing_rows = df[df.isna().any(axis=1)]
    now = pd.Timestamp.now()
    invalid_dates = df["break_date"].isna()
    future_dates = df["break_date"] > now
    valid_global = df["longitude"].between(-180, 180) & df["latitude"].between(-90, 90)
    valid_calgary = df["longitude"].between(-114.5, -113.5) & df["latitude"].between(50.5, 51.5)
    invalid_coordinates = (~valid_global).sum()
    suspicious_coordinates = (valid_global & ~valid_calgary).sum()
    print("\n=== MISSING VALUES ===\n", missing)
    print("\n=== INCOMPLETE RECORDS ===\n", missing_rows.to_string())
    print(f"\n=== DATE VALIDATION ===\nInvalid dates: {invalid_dates.sum()}\nFuture dates: {future_dates.sum()}")
    print(f"\n=== COORDINATE VALIDATION ===\nInvalid coordinates: {invalid_coordinates}\nSuspicious Calgary coordinates: {suspicious_coordinates}")
    earliest, latest = df["break_date"].min(), df["break_date"].max()
    return {
        "missing_values": {"counts_by_column": {k: int(v) for k, v in missing.items()}, "incomplete_records": int(len(missing_rows))},
        "date_validation": {"invalid_dates": int(invalid_dates.sum()), "future_dates": int(future_dates.sum()),
                            "earliest_date": earliest.isoformat() if pd.notna(earliest) else None,
                            "latest_date": latest.isoformat() if pd.notna(latest) else None},
        "coordinate_validation": {"invalid_coordinates": int(invalid_coordinates),
                                  "suspicious_coordinates": int(suspicious_coordinates),
                                  "validation_method": "Global and approximate Calgary bounds",
                                  "note": "The approximate bounding box is not the official city boundary."},
    }


def clean_data(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Preserve the existing documented dropna/drop_duplicates policy."""
    original_count = len(df)
    missing_rows = df[df.isna().any(axis=1)]
    missing_removed = len(missing_rows)
    removed_study_period = int(missing_rows["break_date"].dt.year.between(2016, 2025).sum())
    df_clean = df.dropna().copy()
    duplicated = df_clean[df_clean.duplicated(subset=DUPLICATE_COLUMNS, keep=False)].sort_values(DUPLICATE_COLUMNS)
    duplicate_excess = int(df_clean.duplicated(subset=DUPLICATE_COLUMNS, keep="first").sum())
    print(f"\n=== DUPLICATE ANALYSIS ===\nRecords involved: {len(duplicated)}\nExcess records: {duplicate_excess}")
    print(duplicated.to_string())
    df_clean = df_clean.drop_duplicates(subset=DUPLICATE_COLUMNS, keep="first").copy()
    print(f"\n=== CLEANING RESULTS ===\nOriginal records: {original_count}\nMissing records removed: {missing_removed}\nDuplicate records removed: {duplicate_excess}\nTotal removed: {missing_removed + duplicate_excess}\nRemaining records: {len(df_clean)}")
    return df_clean, {
        "original_records": int(original_count), "missing_records_removed": int(missing_removed),
        "removed_in_study_period": removed_study_period,
        "duplicates": {"records_involved": int(len(duplicated)), "removed_records": duplicate_excess,
                       "comparison_columns": DUPLICATE_COLUMNS, "method": "drop_duplicates", "keep": "first",
                       "justification": "Records identical across the selected attributes were treated as probable duplicates. One occurrence per group was retained. Distinct real events cannot be ruled out without a unique event identifier."},
        "total_removed_records": int(missing_removed + duplicate_excess),
        "remaining_records": int(len(df_clean)), "cleaning_method": "dropna and drop_duplicates",
        "justification": f"{missing_removed} incomplete records were removed; {removed_study_period} belonged to 2016–2025. An additional {duplicate_excess} probable duplicates were removed. The original source file remains unchanged.",
        "warning": "Policy preserved from current HYDROSIGHT implementation; removing missing break_type and probable duplicates may exclude actual rupture records.",
    }


def describe_data(df: pd.DataFrame) -> None:
    print("\n=== SAMPLE DATA ===\n", df.sample(10))
    print("\n=== NUMERICAL DESCRIPTION ===\n", df.describe())
    print("\n=== CATEGORICAL DESCRIPTION ===\n", df.describe(include=["object", "string"]))


def analyze_annual_outliers(df: pd.DataFrame) -> dict:
    annual = df["break_date"].dt.year.value_counts().sort_index()
    annual = annual.loc[annual.index < datetime.now().year]
    q1, q3 = annual.quantile([0.25, 0.75])
    low, high = max(0, q1 - 1.5 * (q3 - q1)), q3 + 1.5 * (q3 - q1)
    outliers = annual[(annual < low) | (annual > high)]
    print(f"\n=== ANNUAL OUTLIER ANALYSIS ===\nLower bound: {low:.2f}\nUpper bound: {high:.2f}\n{outliers.to_string()}")
    return {"method": "IQR", "lower_bound": float(low), "upper_bound": float(high),
            "outlier_years": {str(k): int(v) for k, v in outliers.items()}, "action": "Flagged for investigation, not removed"}


def analyze_month_outliers(df: pd.DataFrame) -> dict:
    dates = df.loc[df["break_date"].dt.year < datetime.now().year, "break_date"]
    monthly = dates.dt.to_period("M").value_counts().sort_index()
    if len(monthly):
        calendar = pd.period_range(monthly.index.min(), monthly.index.max(), freq="M")
        monthly = monthly.reindex(calendar, fill_value=0)
    q1, q3 = monthly.quantile([0.25, 0.75])
    low, high = max(0, q1 - 1.5 * (q3 - q1)), q3 + 1.5 * (q3 - q1)
    outliers = monthly[(monthly < low) | (monthly > high)]
    print(f"\n=== MONTHLY OUTLIER ANALYSIS ===\nLower bound: {low:.2f}\nUpper bound: {high:.2f}\n{outliers.to_string()}")
    return {"method": "IQR", "lower_bound": float(low), "upper_bound": float(high),
            "outlier_months": {str(k): int(v) for k, v in outliers.items()},
            "action": "Flagged for investigation, not removed",
            "note": "Zero-event calendar months are included between first and last complete-year observations."}


def analyze_temporal_distribution(df: pd.DataFrame) -> tuple[dict, dict]:
    annual = df["break_date"].dt.year.value_counts().sort_index()
    complete = df[df["break_date"].dt.year < datetime.now().year].copy()
    year_start = int(complete["break_date"].dt.year.min()) if len(complete) else 0
    year_end = int(complete["break_date"].dt.year.max()) if len(complete) else -1
    if year_end >= year_start:
        months = complete.groupby([complete["break_date"].dt.year, complete["break_date"].dt.month]).size()
        month_grid = pd.MultiIndex.from_product([range(year_start, year_end + 1), range(1, 13)])
        month_table = months.reindex(month_grid, fill_value=0).unstack()
        monthly_average = month_table.mean(axis=0)
    else:
        monthly_average = pd.Series(dtype=float)
    day_counts = df["break_date"].dt.day.value_counts().sort_index()
    report = {"annual_counts": {str(k): int(v) for k, v in annual.items()},
              "monthly_seasonal_average": {str(k): round(float(v), 2) for k, v in monthly_average.items()},
              "day_of_month_counts": {str(k): int(v) for k, v in day_counts.items()},
              "note": "Day-of-month counts are for date-precision audit, not daily seasonality; day 31 has fewer calendar opportunities."}
    return report, {"annual": annual, "monthly_average": monthly_average, "day_of_month": day_counts}


def analyze_seasonal_distribution(df: pd.DataFrame) -> tuple[dict, pd.Series]:
    month = df["break_date"].dt.month
    seasons = np.select([month.isin([12, 1, 2]), month.isin([3, 4, 5]), month.isin([6, 7, 8]), month.isin([9, 10, 11])], SEASONS, default="Inconnu")
    counts = pd.Series(seasons, index=df.index).value_counts().reindex(SEASONS, fill_value=0)
    return {"seasonal_counts": {str(k): int(v) for k, v in counts.items()}, "definition": "Meteorological seasons: DJF, MAM, JJA, SON"}, counts


def analyze_categorical_distribution(df: pd.DataFrame) -> tuple[dict, dict]:
    types = df["break_type"].value_counts(dropna=False)
    statuses = df["status"].value_counts(dropna=False)
    report = {"break_type_distribution": {str(k): int(v) for k, v in types.items()},
              "status_distribution": {str(k): int(v) for k, v in statuses.items()},
              "note": "Do not infer meanings for break_type codes or ACTIVE/RETIRED status without an official dictionary."}
    return report, {"break_types": types, "statuses": statuses}


def generate_report(report: dict) -> Path:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report["executed_at"] = datetime.now(timezone.utc).isoformat()
    output = REPORT_DIR / "water_breaks_quality.json"
    output.write_text(json.dumps(report, indent=4, ensure_ascii=False), encoding="utf-8")
    print(f"\nReport saved: {output}")
    return output


def generate_eda_report(report: dict, figure_paths: list[Path], output_file: Path) -> None:
    """Embed only figures created in this run; never glob stale PNG files."""
    sections = []
    for path in figure_paths:
        if not path.is_file():
            raise FileNotFoundError(f"Expected chart missing: {path}")
        title = path.stem.replace("_", " ").title()
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        sections.append(f'<section><h2>{html.escape(title)}</h2><img src="data:image/png;base64,{encoded}" alt="{html.escape(title)}"></section>')
    quality_text = html.escape(json.dumps(report, indent=2, ensure_ascii=False, default=str))
    body = f'''<!DOCTYPE html><html lang="fr"><head><meta charset="UTF-8"><title>HYDROSIGHT — Rapport EDA</title>
<style>body{{font-family:Arial,sans-serif;max-width:1100px;margin:40px auto;padding:20px;background:#f5f7fa;color:#243044}}h1{{color:#163b65}}section{{background:white;padding:25px;border-radius:12px;margin:25px 0;box-shadow:0 2px 8px #00000012}}img{{width:100%;height:auto}}pre{{overflow-x:auto;white-space:pre-wrap}}</style></head><body>
<h1>HYDROSIGHT — Analyse exploratoire des données</h1><p>Ruptures de conduites d'eau — Calgary</p>
<p>Rapport généré le {datetime.now().strftime('%Y-%m-%d %H:%M')}</p><section><h2>Qualité des données et résultats</h2><pre>{quality_text}</pre></section>
{''.join(sections)}</body></html>'''
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(body, encoding="utf-8")
    print(f"EDA report saved: {output_file} ({len(figure_paths)} charts)")

def analyze_high_break_years(df):
    df_period = df[
        df["break_date"].dt.year.between(1982, 1986)
    ].copy()

    monthly_counts = (
        df_period
        .groupby([
            df_period["break_date"].dt.year.rename("year"),
            df_period["break_date"].dt.month.rename("month")
        ])
        .size()
        .unstack(level="year", fill_value=0)
        .reindex(range(1, 13), fill_value=0)
    )

    return monthly_counts

def analyse_day_one_concentration(
    df: pd.DataFrame
) -> tuple[dict, pd.Series]:

    total_annual = (
        df["break_date"]
        .dt.year
        .value_counts()
        .sort_index()
    )

    df_day_one = df[
        df["break_date"].dt.day == 1
    ].copy()

    day_one_concentration = (
        df_day_one.groupby([
            df_day_one["break_date"].dt.year.rename("year"),
            df_day_one["break_date"].dt.month.rename("month")
        ])
        .size()
        .unstack(level="year", fill_value=0)
        .reindex(range(1, 13), fill_value=0)
    )

    day_one_annual = (
        day_one_concentration
        .sum(axis=0)
        .reindex(total_annual.index, fill_value=0)
    )

    day_one_percentage = (
        day_one_annual / total_annual * 100
    )

    report = {
        "description": (
            "Annual concentration of records dated "
            "on the first day of a month"
        ),
        "annual_results": {
            str(year): {
                "total_breaks": int(total_annual.loc[year]),
                "day_one_breaks": int(day_one_annual.loc[year]),
                "percentage": round(
                    float(day_one_percentage.loc[year]), 2
                )
            }
            for year in total_annual.index
        },
        "note": (
            "An unusually high percentage may indicate approximate "
            "dates or administrative date assignment. "
            "This cannot be confirmed from the distribution alone."
        )
    }

    return report, day_one_percentage

def save_processed_data(df):
    # Export cleaned water main break records
    # Export cleaned water main break records as timestamped JSONL
    output_dir = ROOT_DIR / "data" / "processed" / "water_breaks"
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_file = output_dir / f"water_main_breaks_clean_{timestamp}.jsonl"

    df.to_json(
        output_file,
        orient="records",
        lines=True,
        date_format="iso",
        force_ascii=False
    )

    print(f"Cleaned dataset saved: {output_file}")
    print(f"Exported records: {len(df)}")

def main() -> None:
    df = transform_data(load_data())
    validation_report = validate_data(df)
    df_clean, cleaning_report = clean_data(df)
    describe_data(df_clean)

    # Analyses
    temporal_report, temporal = analyze_temporal_distribution(df_clean)
    annual_outlier_report = analyze_annual_outliers(df_clean)
    monthly_outlier_report = analyze_month_outliers(df_clean)
    categorical_report, categorical = analyze_categorical_distribution(df_clean)
    seasonal_report, seasonal = analyze_seasonal_distribution(df_clean)
    day_one_report, day_one_percentage = analyse_day_one_concentration(df_clean)

    # Monthly comparison for the high-break period
    monthly_comparison = analyze_high_break_years(df_clean)

    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []

    def bar(
        series: pd.Series,
        xlabel: str,
        ylabel: str,
        title: str,
        filename: str
    ) -> None:
        output = FIGURES_DIR / filename

        visualize_water_breaks(
            series.index,
            series.values,
            xlabel,
            ylabel,
            title,
            output
        )

        paths.append(output)

    # Temporal charts
    bar(
        temporal["annual"],
        "Année",
        "Nombre de ruptures",
        "Annual Water Main Breaks - Calgary",
        "annual_water_breaks.png"
    )

    bar(
        temporal["monthly_average"],
        "Mois",
        "Nombre moyen de ruptures",
        "Monthly Seasonality - Calgary",
        "monthly_seasonality.png"
    )

    bar(
        temporal["day_of_month"],
        "Jour du mois",
        "Nombre de ruptures",
        "Distribution des jours du mois - Calgary",
        "day_of_month.png"
    )

    # Categorical charts
    bar(
        categorical["break_types"],
        "Type de rupture (code brut)",
        "Nombre de ruptures",
        "Water Main Breaks by Type - Calgary",
        "break_types.png"
    )

    bar(
        categorical["statuses"],
        "Statut (code brut)",
        "Nombre de ruptures",
        "Water Main Breaks by Status - Calgary",
        "break_status.png"
    )

    # Seasonal chart
    bar(
        seasonal,
        "Saison",
        "Nombre de ruptures",
        "Distribution saisonnière - Calgary",
        "seasonal_water_breaks.png"
    )

    bar(
        day_one_percentage,
        "Année",
        "Pourcentage des ruptures (%)",
        "Concentration des ruptures au 1er jour du mois par année - Calgary",
        "day_one_concentration.png"
    )

    # NEW: Monthly comparison between 1982 and 1986
    monthly_comparison_path = FIGURES_DIR / "monthly_comparison_1982_1986.png"

    visualize_monthly_comparison(
        monthly_comparison,
        "Comparaison mensuelle des ruptures - Calgary (1982–1986)",
        monthly_comparison_path
    )

    paths.append(monthly_comparison_path)

    # Spatial chart: complete history
    historic_map = FIGURES_DIR / "spatial_distribution_historic.png"

    visualize_spatial_distribution(
        df_clean,
        "Historic Spatial Distribution of Water Main Breaks - Calgary",
        historic_map
    )

    paths.append(historic_map)

    # Spatial chart: 2016–2025
    recent = df_clean[
        df_clean["break_date"].dt.year.between(2016, 2025)
    ]

    recent_map = FIGURES_DIR / "spatial_distribution_2016_2025.png"

    visualize_spatial_distribution(
        recent,
        "Spatial Distribution of Water Main Breaks - Calgary (2016–2025)",
        recent_map
    )

    paths.append(recent_map)

    # Reports
    report = {
        "analysis": "water_main_breaks_eda",
        "validation": validation_report,
        "cleaning": cleaning_report,
        "temporal_analysis": temporal_report,
        "annual_outlier_analysis": annual_outlier_report,
        "monthly_outlier_analysis": monthly_outlier_report,
        "categorical_analysis": categorical_report,
        "seasonal_analysis": seasonal_report,
        "monthly_comparison_1982_1986": {
            str(year): {
                str(month): int(count)
                for month, count in monthly_comparison[year].items()
            }
            for year in monthly_comparison.columns
        },
            "comment": (
            "Analysis of the Temporal and Seasonal Distribution of Water Main Breaks\n\n"

            "The analysis of the annual distribution of water main breaks in Calgary "
            "reveals a significant increase in the number of events between 1982 and "
            "1986 compared with several other periods in the historical dataset.\n\n"

            "An examination of the monthly distribution during these five years "
            "shows particularly high concentrations during the winter months, "
            "especially in 1982, 1984, and 1985. However, some variations are "
            "observed, such as in 1986, when October exhibits a notable peak.\n\n"

            "Across the entire historical period, January, February, November, "
            "and December are among the months with the highest average number "
            "of water main breaks. The seasonal distribution also confirms that "
            "winter accounts for the highest number of events, followed by spring, "
            "autumn, and summer.\n\n"

            "These observations suggest a possible association between cold "
            "weather conditions and the frequency of water main breaks.\n\n"

            "However, the presented charts do not yet establish a direct "
            "statistical relationship between temperature and water main breaks. "
            "This hypothesis must be investigated using historical meteorological "
            "data, particularly minimum temperatures, freezing events, and "
            "freeze-thaw cycles.\n\n"

            "Finally, the unusually high concentration of water main breaks "
            "between 1982 and 1986 warrants further investigation into the "
            "quality and comparability of historical records. This analysis "
            "will help distinguish actual variations in water main break "
            "occurrences from potential differences in historical data "
            "collection practices."
        ),
        "concentration_analysis": day_one_report,

        "temporal_data_quality_decision": {
            "title": "Justification du choix de la période d'analyse",
            "observation": (
                "Une concentration anormalement élevée des ruptures "
                "enregistrées le premier jour de chaque mois a été observée "
                "entre 1956 et la fin des années 1990."
            ),
            "limitation": (
                "La cause exacte de cette anomalie demeure inconnue. "
                "La précision quotidienne des dates historiques est incertaine."
            ),
            "risk": (
                "L'utilisation de ces dates dans un modèle prédictif intégrant "
                "des variables météorologiques quotidiennes pourrait introduire "
                "un biais."
            ),
            "decision": (
                "Les observations antérieures à 2000 sont conservées dans les "
                "données originales, mais exclues du jeu de données principal "
                "destiné à la modélisation. Les analyses exploratoires sont "
                "reprises pour la période 2000–2025."
            )
        },


    }

    # EDA — Study period 2000–2025
    df_study = df_clean[df_clean["break_date"].dt.year.between(2000, 2025)].copy()

    # Reuse existing analyses
    study_temporal_report, study_temporal = analyze_temporal_distribution(df_study)
    study_seasonal_report, study_seasonal = analyze_seasonal_distribution(df_study)
    study_categorical_report, study_categorical = analyze_categorical_distribution(df_study)

    bar(
        study_temporal["annual"],
        "Année",
        "Nombre de ruptures",
        "Annual Water Main Breaks - Calgary (2000–2025)",
        "annual_water_breaks_2000_2025.png"
    )

    bar(
        study_temporal["monthly_average"],
        "Mois",
        "Nombre moyen de ruptures",
        "Monthly Seasonality - Calgary (2000–2025)",
        "monthly_seasonality_2000_2025.png"
    )

    bar(
        study_seasonal,
        "Saison",
        "Nombre de ruptures",
        "Seasonal Distribution - Calgary (2000–2025)",
        "seasonal_water_breaks_2000_2025.png"
    )

    bar(
        study_categorical["break_types"],
        "Type de rupture",
        "Nombre de ruptures",
        "Water Main Breaks by Type - Calgary (2000–2025)",
        "break_types_2000_2025.png"
    )

    # Add study-period results to the existing report
    report["study_period_2000_2025"] = {
        "records": int(len(df_study)),
        "temporal_analysis": study_temporal_report,
        "seasonal_analysis": study_seasonal_report,
        "categorical_analysis": study_categorical_report
    }

    generate_report(report)
    generate_eda_report(report, paths, HTML_REPORT)
    save_processed_data(df_clean)


if __name__ == "__main__":
    main()
