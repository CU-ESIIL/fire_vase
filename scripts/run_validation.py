#!/usr/bin/env python3
"""Run modular Fire VASE validation checks and collate their QA artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

from cubedynamics.validation import ValidationPaths, run_validation_suite
from cubedynamics.validation.runner import MODULE_ORDER


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("config/validation.yml"))
    parser.add_argument("--data-root", type=Path, default=None)
    parser.add_argument("--output-root", type=Path, default=Path("output/validation"))
    parser.add_argument("--modules", nargs="+", choices=MODULE_ORDER, default=None)
    parser.add_argument("--fire-id", type=int, default=None)
    parser.add_argument("--variable", default=None)
    parser.add_argument("--external", action="store_true", help="Query the independent NCAR GridMET mirror.")
    parser.add_argument("--no-pdf", action="store_true")
    parser.add_argument("--publish-docs", action="store_true")
    args = parser.parse_args()

    config = yaml.safe_load(args.config.read_text(encoding="utf-8")) or {}
    paths = ValidationPaths.discover(data_root=args.data_root, output_root=args.output_root)
    results = run_validation_suite(
        paths,
        modules=args.modules or config.get("modules", MODULE_ORDER),
        fire_id=args.fire_id or int(config.get("sample", {}).get("fire_id", 20657)),
        variable=args.variable or config.get("sample", {}).get("gridmet_variable", "tmmx"),
        tolerances_m=config.get("geometry", {}).get("simplification_tolerances_m", [0, 125, 500, 1000]),
        operational_max_tolerance_m=float(config.get("geometry", {}).get("operational_max_tolerance_m", 125)),
        n_theta=int(config.get("geometry", {}).get("n_theta", 96)),
        external_network=args.external,
        build_pdf=not args.no_pdf,
        publish_docs=args.publish_docs,
    )
    print(json.dumps([result.as_dict() for result in results], indent=2, default=str))
    return 0 if all(result.passed for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
