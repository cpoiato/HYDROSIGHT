"""Regression contracts for the canonical HYDROSIGHT DVC command entry points.

Only automated tests use temporary or synthetic values. Production processing
continues to read the existing real-data DVC dependencies.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from unittest.mock import patch

from hydrosight import main as app
from hydrosight.preprocessing import break_history, spatial_relationships


def test_break_history_command_forwards_existing_contract(capsys):
    args = argparse.Namespace(
        water_breaks=Path("breaks.jsonl"),
        grid=Path("grid.geojson"),
        grid_manifest=Path("manifest.json"),
        output_dir=Path("history"),
    )
    with patch.object(
        break_history, "build_and_save_break_history", return_value={"grid_cells": 2}
    ) as build:
        app.run_break_history(args)

    build.assert_called_once_with(
        args.water_breaks, args.grid, args.grid_manifest, args.output_dir
    )
    assert "grid_cells: 2" in capsys.readouterr().out


def test_spatial_relationships_command_forwards_existing_contract(capsys):
    args = argparse.Namespace(
        pipes=Path("pipes.jsonl"),
        breaks=Path("breaks.jsonl"),
        grid=Path("grid.geojson"),
        manifest=Path("manifest.json"),
        history_dir=Path("history"),
        output=Path("sector_summary.jsonl"),
    )
    with patch.object(
        spatial_relationships, "export_sector_summary", return_value=3615
    ) as export:
        app.run_spatial_relationships(args)

    export.assert_called_once_with(
        args.pipes,
        args.breaks,
        args.grid,
        args.manifest,
        args.history_dir,
        args.output,
    )
    assert "Saved 3,615 sectors" in capsys.readouterr().out


def test_break_history_cli_uses_existing_module_defaults():
    with patch.object(app, "run_break_history") as run, patch.object(
        sys, "argv", ["hydrosight", "break-history"]
    ):
        app.main()

    args = run.call_args.args[0]
    assert args.water_breaks == break_history.WATER_BREAKS_PATH
    assert args.grid == break_history.GRID_PATH
    assert args.grid_manifest == break_history.GRID_MANIFEST_PATH
    assert args.output_dir == break_history.OUTPUT_DIR


def test_spatial_relationships_cli_accepts_existing_required_arguments():
    argv = [
        "hydrosight",
        "spatial-relationships",
        "--pipes", "pipes.jsonl",
        "--breaks", "breaks.jsonl",
        "--grid", "grid.geojson",
        "--manifest", "manifest.json",
        "--history-dir", "history",
        "--output", "summary.jsonl",
    ]
    with patch.object(app, "run_spatial_relationships") as run, patch.object(
        sys, "argv", argv
    ):
        app.main()

    args = run.call_args.args[0]
    assert args.pipes == Path("pipes.jsonl")
    assert args.breaks == Path("breaks.jsonl")
    assert args.grid == Path("grid.geojson")
    assert args.manifest == Path("manifest.json")
    assert args.history_dir == Path("history")
    assert args.output == Path("summary.jsonl")


def test_dvc_commands_point_to_main_without_duplicate_stage_implementations():
    dvc = (Path(__file__).resolve().parents[1] / "dvc.yaml").read_text(
        encoding="utf-8"
    )
    assert "python -m hydrosight.main preprocess" in dvc
    assert "python -m hydrosight.main break-history" in dvc
    assert "python -m hydrosight.main spatial-relationships" in dvc
    assert "python -m hydrosight.preprocessing.break_history" not in dvc
    assert "python -m hydrosight.preprocessing.spatial_relationships" not in dvc
    for stage in ("break_history:", "spatial_relationships:"):
        section = dvc.split("\n  " + stage, 1)[1].split("\n  ", 1)[0]
        assert "      - src/hydrosight/main.py" in section


def test_features_command_not_exposed_before_implementation():
    # Do not claim feature engineering is executable until US-13 is implemented.
    assert not hasattr(app, "run_features")
