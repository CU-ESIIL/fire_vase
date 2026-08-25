"""Orchestrate modular validation runs without coupling module internals."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
from typing import Iterable

from .climate import run_climate_validation
from .core import QAResult, ValidationPaths
from .cube import run_cube_validation
from .external import run_external_validation
from .geometry import run_geometry_validation
from .hull3d import run_hull3d_validation
from .pipeline import run_pipeline_validation
from .report import build_validation_pdf


MODULE_ORDER = ("pipeline", "cube", "geometry", "hull3d", "climate", "external")


def publish_validation_plots(
    results: Iterable[QAResult],
    docs_asset_dir: str | Path,
    *,
    report_pdf: str | Path | None = None,
) -> list[Path]:
    """Copy stable QA plots and the optional report into the website tree."""

    destination = Path(docs_asset_dir)
    destination.mkdir(parents=True, exist_ok=True)
    copied: list[Path] = []
    for result in results:
        source = Path(result.artifacts["plot"])
        target = destination / f"{result.module}.png"
        shutil.copy2(source, target)
        copied.append(target)
        interactive_source = result.artifacts.get("interactive_html")
        if interactive_source and Path(interactive_source).exists():
            interactive_target = destination / f"{result.module}.html"
            shutil.copy2(interactive_source, interactive_target)
            copied.append(interactive_target)
    if report_pdf is not None and Path(report_pdf).exists():
        target = destination / "fire_vase_validation_report.pdf"
        shutil.copy2(Path(report_pdf), target)
        copied.append(target)
    return copied


def run_validation_suite(
    paths: ValidationPaths,
    *,
    modules: Iterable[str] = MODULE_ORDER,
    fire_id: int = 20657,
    variable: str = "tmmx",
    tolerances_m: Iterable[float] = (0, 125, 500, 1000),
    operational_max_tolerance_m: float = 125,
    n_theta: int = 96,
    averaging_windows: Iterable[int] = (1, 3, 7),
    external_network: bool = False,
    build_pdf: bool = True,
    publish_docs: bool = False,
) -> list[QAResult]:
    """Run selected modules and optionally collate/publish their artifacts."""

    requested = list(dict.fromkeys(modules))
    unknown = set(requested).difference(MODULE_ORDER)
    if unknown:
        raise ValueError(f"Unknown validation modules: {sorted(unknown)}")
    paths.output_root.mkdir(parents=True, exist_ok=True)
    results: list[QAResult] = []
    for module in MODULE_ORDER:
        if module not in requested:
            continue
        if module == "pipeline":
            result = run_pipeline_validation(paths, fire_id=fire_id, variable=variable)
        elif module == "cube":
            result = run_cube_validation(paths, fire_id=fire_id, variable=variable)
        elif module == "geometry":
            result = run_geometry_validation(
                paths,
                fire_id=fire_id,
                tolerances_m=tuple(tolerances_m),
                operational_max_tolerance_m=operational_max_tolerance_m,
                n_theta=n_theta,
            )
        elif module == "hull3d":
            result = run_hull3d_validation(
                paths,
                fire_id=fire_id,
                n_theta=n_theta,
                averaging_windows=tuple(averaging_windows),
            )
        elif module == "climate":
            result = run_climate_validation(paths, fire_id=fire_id, variable=variable)
        else:
            result = run_external_validation(
                paths,
                fire_id=fire_id,
                variable=variable,
                external_network=external_network,
            )
        results.append(result)

    manifest = {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "fire_id": str(fire_id),
        "variable": variable,
        "modules": [result.as_dict() for result in results],
        "all_passed": all(result.passed for result in results),
    }
    (paths.output_root / "validation_manifest.json").write_text(
        json.dumps(manifest, indent=2, default=str), encoding="utf-8"
    )
    report_pdf = paths.repo_root / "output" / "pdf" / "fire_vase_validation_report.pdf"
    if build_pdf and results:
        build_validation_pdf(results, report_pdf)
    if publish_docs:
        publish_validation_plots(
            results,
            paths.repo_root / "docs" / "assets" / "validation",
            report_pdf=report_pdf if build_pdf else None,
        )
    return results


__all__ = ["MODULE_ORDER", "publish_validation_plots", "run_validation_suite"]
