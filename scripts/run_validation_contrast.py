#!/usr/bin/env python3
"""Run expected-failure controls and build a separate contrast report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil

import yaml

from cubedynamics.validation import ValidationPaths
from cubedynamics.validation.contrast import run_contrast_suite
from cubedynamics.validation.report import build_validation_pdf


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("config/validation.yml"))
    parser.add_argument("--data-root", type=Path, default=None)
    parser.add_argument("--output-root", type=Path, default=Path("output/validation/contrast"))
    parser.add_argument("--report", type=Path, default=Path("output/pdf/fire_vase_validation_contrast_report.pdf"))
    parser.add_argument("--publish-docs", action="store_true")
    args = parser.parse_args()

    config = yaml.safe_load(args.config.read_text(encoding="utf-8")) or {}
    contrast = config.get("contrast", {})
    paths = ValidationPaths.discover(data_root=args.data_root)
    results, manifest_path = run_contrast_suite(
        paths,
        cube_fire_id=int(contrast.get("cube_fire_id", 20657)),
        geometry_fire_id=int(contrast.get("geometry_fire_id", 72016)),
        variable=str(contrast.get("gridmet_variable", "tmmx")),
        output_root=args.output_root,
    )
    build_validation_pdf(
        results,
        args.report,
        title="Fire VASE Validation Contrast Report",
        lead=(
            "Expected-failure controls showing that the validators reject corrupted cube views "
            "and a real FIRED event that violates the declared geometry simplification threshold. "
            "Red FAIL labels are the intended outcome here; they do not describe the production sample."
        ),
        footer_label="Fire VASE expected-failure contrast report",
    )

    if args.publish_docs:
        destination = paths.repo_root / "docs" / "assets" / "validation"
        destination.mkdir(parents=True, exist_ok=True)
        shutil.copy2(results[0].artifacts["plot"], destination / "contrast_cube.png")
        shutil.copy2(results[1].artifacts["plot"], destination / "contrast_geometry.png")
        shutil.copy2(args.report, destination / "fire_vase_validation_contrast_report.pdf")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    print(json.dumps(manifest, indent=2, default=str))
    return 0 if manifest["expected_failures_detected"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

