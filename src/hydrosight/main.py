"""Interactive entry point for the versioned Calgary spatial grid."""

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


def main() -> None:
    print("=== HYDROSIGHT — SPATIAL GRID ===")
    print("Checking official Calgary boundary...")
    try:
        current = load_official_boundary()
    except Exception as exc:
        if not BOUNDARY_PATH.exists() or not GRID_PATH.exists():
            raise RuntimeError("Official boundary unavailable and no saved grid exists.") from exc
        print(f"Official boundary unavailable: {exc}")
        print("Displaying saved grid without verifying its freshness.")
        show_grid(gpd.read_file(BOUNDARY_PATH), gpd.read_file(GRID_PATH))
        return

    saved = load_saved_boundary()
    existing_grid = gpd.read_file(GRID_PATH) if GRID_PATH.exists() else None
    manifest = load_manifest()
    candidate = generate_grid(current)

    boundary_matches = saved is not None and boundaries_equal(saved, current)
    grid_matches = existing_grid is not None and grids_equal(existing_grid, candidate)
    version_matches = manifest is not None and manifest.get("active_version") == grid_version(current)

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
        print("Grid geometry matches; version metadata needs initialization or update.")

    print(f"Existing grid cells: {len(existing_grid) if existing_grid is not None else 0}")
    print(f"Proposed grid cells: {len(candidate)}")
    response = input("Archive existing files and activate the proposed grid? [y/N]: ").strip().lower()
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


if __name__ == "__main__":
    main()
