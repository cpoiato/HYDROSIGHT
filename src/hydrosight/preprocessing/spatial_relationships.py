"""Export the sector-level measures retained in spatial EDA notebook 06."""

import argparse
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import geopandas as gpd
import pandas as pd
from shapely.geometry import shape


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


def export_sector_summary(
    pipes_path: Path, breaks_path: Path, grid_path: Path, manifest_path: Path,
    history_dir: Path, output_path: Path,
) -> int:
    """Join current mapped pipe lengths and recorded 2016–2025 breaks onto every sector."""
    grid = gpd.read_file(grid_path)
    manifest = json.loads(manifest_path.read_text())
    quality = json.loads((history_dir / "break_history_quality.json").read_text())
    if (manifest["grid_size_meters"] != 500 or len(grid) != manifest["cell_count"]
            or quality["grid_version"] != manifest["active_version"]
            or quality["grid_cells"] != len(grid)):
        raise ValueError("Grid and break history must describe the same active 500 m grid.")
    if grid["cell_id"].isna().any() or not grid["cell_id"].is_unique:
        raise ValueError("Expected one non-null identifier per sector.")
    if hashlib.sha256(breaks_path.read_bytes()).hexdigest() != quality["source_sha256"]:
        raise ValueError("Break history does not match the supplied break snapshot.")

    history = pd.read_csv(history_dir / quality["history_file"], parse_dates=["month"])
    if (not history["cell_id"].isin(grid["cell_id"]).all()
            or history["break_count"].sum() != quality["assigned_records"]):
        raise ValueError("Monthly history contains unknown sectors or inconsistent totals.")
    study = history.loc[history["month"].dt.year.between(2016, 2025)]
    observed = study.groupby("cell_id")["break_count"].sum()

    df_clean = pd.read_json(pipes_path, lines=True)
    pipe_pairs = assign_pipes_to_grid(df_clean, grid)
    lengths = aggregate_pipe_features(pipe_pairs, grid).set_index("cell_id")["pipe_length_m"]
    sectors = grid[["cell_id"]].sort_values("cell_id").set_index("cell_id")
    sectors["pipe_length_m"] = lengths.reindex(sectors.index, fill_value=0.0)
    sectors["observed_breaks_2016_2025"] = observed.reindex(sectors.index, fill_value=0)
    sectors["grid_version"] = manifest["active_version"]
    sectors["pipe_snapshot"] = pipes_path.name
    sectors["break_snapshot"] = breaks_path.name

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=output_path.parent) as temporary:
        staged = Path(temporary) / output_path.name
        sectors.reset_index().to_json(staged, orient="records", lines=True, force_ascii=False)
        staged.replace(output_path)
    return len(sectors)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pipes", type=Path, required=True)
    parser.add_argument("--breaks", type=Path, required=True)
    parser.add_argument("--grid", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--history-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    count = export_sector_summary(args.pipes, args.breaks, args.grid, args.manifest,
                                  args.history_dir, args.output)
    print(f"Saved {count:,} sectors to {args.output}")


if __name__ == "__main__":
    main()
