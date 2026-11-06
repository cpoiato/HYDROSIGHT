
"""HYDROSIGHT application entry point."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory

import geopandas as gpd

from hydrosight.preprocessing.spatial_grid import (
    BOUNDARY_PATH,
    GRID_PATH,
    activate_grid,
    boundaries_equal,
    generate_grid,
    grid_version,
    grids_equal,
    load_manifest,
    load_official_boundary,
    load_saved_boundary,
    show_grid,
)


PIPELINE_FILENAMES = {
    "water_breaks": "water_breaks.jsonl",
    "pipes": "pipes.jsonl",
    "weather": "weather.jsonl",
    "hospitals": "hospitals.jsonl",
    "schools": "schools.jsonl",
}


def run_grid() -> None:
    """Manage the versioned Calgary spatial grid."""
    print("=== HYDROSIGHT — SPATIAL GRID ===")
    print("Checking official Calgary boundary...")

    try:
        current = load_official_boundary()
    except Exception as exc:
        if not BOUNDARY_PATH.exists() or not GRID_PATH.exists():
            raise RuntimeError(
                "Official boundary unavailable and no saved grid exists."
            ) from exc

        print(f"Official boundary unavailable: {exc}")
        print("Displaying saved grid without verifying its freshness.")
        show_grid(
            gpd.read_file(BOUNDARY_PATH),
            gpd.read_file(GRID_PATH),
        )
        return

    saved = load_saved_boundary()
    existing_grid = (
        gpd.read_file(GRID_PATH)
        if GRID_PATH.exists()
        else None
    )
    manifest = load_manifest()
    candidate = generate_grid(current)

    boundary_matches = (
        saved is not None
        and boundaries_equal(saved, current)
    )
    grid_matches = (
        existing_grid is not None
        and grids_equal(existing_grid, candidate)
    )
    version_matches = (
        manifest is not None
        and manifest.get("active_version") == grid_version(current)
    )

    if boundary_matches and grid_matches and version_matches:
        print("Boundary status: UNCHANGED")
        print("Grid status: CURRENT")
        print(f"Grid cells: {len(existing_grid)}")
        print("Displaying existing spatial grid.")
        show_grid(saved, existing_grid)
        return

    if saved is None:
        print("No saved boundary snapshot exists.")
    elif not boundary_matches:
        print("Boundary status: CHANGED")
    else:
        print("Boundary status: UNCHANGED")

    if existing_grid is None:
        print("Grid status: MISSING")
    elif not grid_matches:
        print("Grid status: OUTDATED OR MODIFIED")
    else:
        print(
            "Grid geometry matches; version metadata "
            "needs initialization or update."
        )

    print(
        f"Existing grid cells: "
        f"{len(existing_grid) if existing_grid is not None else 0}"
    )
    print(f"Proposed grid cells: {len(candidate)}")

    response = input(
        "Archive existing files and activate the proposed grid? [y/N]: "
    ).strip().lower()

    if response != "y":
        print("No changes applied. Existing files were preserved.")
        if saved is not None and existing_grid is not None:
            show_grid(saved, existing_grid)
        return

    version = activate_grid(current, candidate)
    print(f"Grid activated. Version: {version}")
    print(f"Grid cells: {len(candidate)}")
    print(f"Saved to: {GRID_PATH}")
    show_grid(current, candidate)


def run_preprocessing(args: argparse.Namespace) -> None:
    """Execute existing preprocessing functions on explicit real sources."""
    from hydrosight.preprocessing.hospitals import process_hospitals
    from hydrosight.preprocessing.pipes import process_pipes
    from hydrosight.preprocessing.schools import process_schools
    from hydrosight.preprocessing.water_breaks import process_water_breaks
    from hydrosight.preprocessing.weather import process_weather

    sources = {
        "water_breaks": args.water_breaks,
        "pipes": args.pipes,
        "weather_historical": args.weather_historical,
        "weather_recent": args.weather_recent,
        "hospitals": args.hospitals,
        "schools": args.schools,
        "boundary": args.boundary,
    }

    missing = [
        f"{name}: {path}"
        for name, path in sources.items()
        if not path.is_file()
    ]

    if missing:
        raise FileNotFoundError(
            "Required source files are missing:\n"
            + "\n".join(missing)
        )

    def process_all(output_root: Path | None) -> dict[str, Path]:
        """Call each canonical preprocessing implementation once."""

        def output_options(name: str) -> dict[str, Path]:
            if output_root is None:
                return {}
            return {"output_dir": output_root / name}

        return {
            "water_breaks": process_water_breaks(
                args.water_breaks,
                **output_options("water_breaks"),
            ),
            "pipes": process_pipes(
                args.pipes,
                boundary_file=args.boundary,
                **output_options("pipes"),
            ),
            "weather": process_weather(
                args.weather_historical,
                args.weather_recent,
                **output_options("weather"),
            ),
            "hospitals": process_hospitals(
                args.hospitals,
                boundary_file=args.boundary,
                **output_options("hospitals"),
            ),
            "schools": process_schools(
                args.schools,
                boundary_file=args.boundary,
                **output_options("schools"),
            ),
        }

    print("=== HYDROSIGHT — PREPROCESSING ===")

    if args.pipeline_output_dir is None:
        outputs = process_all(output_root=None)
    else:
        destination = args.pipeline_output_dir

        with TemporaryDirectory(
            prefix="hydrosight-preprocessing-"
        ) as temporary_directory:
            generated = process_all(
                output_root=Path(temporary_directory)
            )

            destination.mkdir(parents=True, exist_ok=True)
            outputs = {}

            for name, source in generated.items():
                target = destination / PIPELINE_FILENAMES[name]
                temporary_target = target.with_name(
                    f".{target.name}.tmp"
                )

                try:
                    shutil.copyfile(source, temporary_target)
                    temporary_target.replace(target)
                finally:
                    temporary_target.unlink(missing_ok=True)

                outputs[name] = target

    print("=== PREPROCESSING COMPLETED ===")

    for name, output in outputs.items():
        print(f"{name}: {output}")


def main() -> None:
    """Dispatch application commands."""
    parser = argparse.ArgumentParser(
        description="HYDROSIGHT application."
    )

    commands = parser.add_subparsers(dest="command")

    commands.add_parser(
        "grid",
        help="Manage the Calgary spatial grid.",
    )

    preprocessing = commands.add_parser(
        "preprocess",
        help="Process real source datasets.",
    )

    preprocessing.add_argument(
        "--water-breaks",
        type=Path,
        required=True,
    )
    preprocessing.add_argument(
        "--pipes",
        type=Path,
        required=True,
    )
    preprocessing.add_argument(
        "--weather-historical",
        type=Path,
        required=True,
    )
    preprocessing.add_argument(
        "--weather-recent",
        type=Path,
        required=True,
    )
    preprocessing.add_argument(
        "--hospitals",
        type=Path,
        required=True,
    )
    preprocessing.add_argument(
        "--schools",
        type=Path,
        required=True,
    )
    preprocessing.add_argument(
        "--boundary",
        type=Path,
        default=BOUNDARY_PATH,
    )
    preprocessing.add_argument(
        "--pipeline-output-dir",
        type=Path,
        default=None,
        help="Write stable outputs for a reproducible DVC pipeline.",
    )

    args = parser.parse_args()

    if args.command in (None, "grid"):
        run_grid()
    elif args.command == "preprocess":
        run_preprocessing(args)


if __name__ == "__main__":
    main()
