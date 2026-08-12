#!/usr/bin/env python3
"""Run manuscript figure builders against a Fire VASE data-lake package."""

from __future__ import annotations

import argparse
import importlib
import os
import shutil
import sys
from pathlib import Path

import matplotlib.pyplot as plt


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
DEFAULT_DATA_LAKE = REPO_ROOT / "data_lake" / "fire-vase-data-lake-v0.1"
FIGURE_SOURCE_DIR = REPO_ROOT / "scripts" / "figures"

MAIN_FIGURES = {
    1: ("make_figure_1", "Figure_1"),
    2: ("make_figure_2", "Figure_2"),
    3: ("make_figure_3", "Figure_3"),
    4: ("make_figure_4", "Figure_4"),
    5: ("make_figure_5", "Figure_5"),
}


def build_parser(description: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "--data-lake",
        type=Path,
        default=DEFAULT_DATA_LAKE,
        help="Path to the Fire VASE data-lake package, its files/ directory, or a restored repository root.",
    )
    parser.add_argument(
        "--force-validation",
        action="store_true",
        help="Recompute validation tables instead of using cached derived_stats from the data lake.",
    )
    parser.add_argument("--bootstrap-reps", type=int, default=160, help="Bootstrap replicates used when recomputing validation.")
    parser.add_argument("--sample-size", type=int, default=25000, help="Bootstrap/null sample size used when recomputing validation.")
    return parser


def resolve_data_root(data_lake: Path) -> Path:
    path = data_lake.expanduser().resolve()
    candidates = [path, path / "files"]
    for candidate in candidates:
        if (candidate / "scratch" / "fire_vase_developmental_morphology").exists() and (
            candidate / "scratch" / "fire_vase_run_full" / "tables"
        ).exists():
            return candidate
    raise FileNotFoundError(
        "Could not find Fire VASE data-lake inputs. Expected either a package with files/scratch/... "
        f"or a restored root with scratch/... under {path}."
    )


def configure_paths(args: argparse.Namespace) -> Path:
    data_root = resolve_data_root(args.data_lake)
    os.environ["FIRE_VASE_DATA_ROOT"] = str(data_root)
    os.environ["FIRE_VASE_MAIN_FIGURE_DIR"] = str(SCRIPT_DIR)
    os.environ["FIRE_VASE_SUPPLEMENT_DIR"] = str(SCRIPT_DIR)
    os.environ["FIRE_VASE_DERIVED_STATS_DIR"] = str(SCRIPT_DIR / "derived_stats")
    if str(FIGURE_SOURCE_DIR) not in sys.path:
        sys.path.insert(0, str(FIGURE_SOURCE_DIR))
    if not args.force_validation:
        seed_cached_stats(data_root)
    return data_root


def seed_cached_stats(data_root: Path) -> None:
    destination = SCRIPT_DIR / "derived_stats"
    if destination.exists() and any(destination.iterdir()):
        return
    source = data_root / "repository" / "figures" / "main" / "derived_stats"
    if not source.exists():
        return
    destination.mkdir(parents=True, exist_ok=True)
    for path in source.iterdir():
        if path.is_file():
            shutil.copy2(path, destination / path.name)


def load_data_and_stats(args: argparse.Namespace):
    configure_paths(args)
    from morphospace import load_data
    from statistics import compute_validation_bundle

    data = load_data()
    stats = compute_validation_bundle(
        data,
        reps=args.bootstrap_reps,
        sample_size=args.sample_size,
        force=args.force_validation,
    )
    return data, stats


def render_main_figure(number: int, args: argparse.Namespace) -> dict[str, str]:
    data, stats = load_data_and_stats(args)
    module_name, output_name = MAIN_FIGURES[number]
    module = importlib.import_module(module_name)
    from style import save_figure

    fig = module.build(data, stats)
    try:
        return save_figure(fig, output_name)
    finally:
        plt.close(fig)


def render_supplementary(args: argparse.Namespace) -> dict[str, str]:
    data, stats = load_data_and_stats(args)
    module = importlib.import_module("make_supplementary_figures")
    fig = module.build(data, stats)
    try:
        return module.save_supplement(fig, "Supplementary_Figure_1_validation")
    finally:
        plt.close(fig)


def render_all(args: argparse.Namespace) -> dict[str, dict[str, str]]:
    data, stats = load_data_and_stats(args)
    from style import save_figure

    outputs: dict[str, dict[str, str]] = {}
    for number, (module_name, output_name) in MAIN_FIGURES.items():
        module = importlib.import_module(module_name)
        fig = module.build(data, stats)
        try:
            outputs[output_name] = save_figure(fig, output_name)
        finally:
            plt.close(fig)

    supplement = importlib.import_module("make_supplementary_figures")
    fig = supplement.build(data, stats)
    try:
        outputs["Supplementary_Figure_1_validation"] = supplement.save_supplement(fig, "Supplementary_Figure_1_validation")
    finally:
        plt.close(fig)
    return outputs
