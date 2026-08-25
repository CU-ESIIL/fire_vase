"""Validate CubeDynamics pipe grammar against direct lazy backend operations."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import xarray as xr
from dask import compute

from cubedynamics import pipe
from cubedynamics import verbs as v

from .core import QAResult, ValidationPaths, write_metrics_csv
from .data import event_bounds, load_event, open_gridmet_subset


def compare_pipe_and_direct(cube: xr.DataArray) -> dict[str, Any]:
    """Apply the same z-score verb directly and through ``pipe`` and compare."""

    direct = v.zscore(dim="time")(cube)
    piped = (pipe(cube) | v.zscore(dim="time")).unwrap()
    passthrough = pipe(cube).unwrap()
    direct_values, piped_values = compute(direct, piped)
    residual = direct_values - piped_values
    finite = np.asarray(residual.values, dtype=float)
    max_abs = float(np.nanmax(np.abs(finite))) if finite.size else float("nan")
    lazy_before = getattr(cube.data, "chunks", None) is not None
    lazy_after = getattr(piped.data, "chunks", None) is not None
    return {
        "direct": direct,
        "piped": piped,
        "direct_values": direct_values,
        "piped_values": piped_values,
        "residual": residual,
        "max_abs_residual": max_abs,
        "same_object_on_noop_unwrap": passthrough is cube,
        "lazy_before": lazy_before,
        "lazy_after": lazy_after,
        "chunks": str(getattr(cube.data, "chunks", None)),
    }


def _plot_pipeline_qa(cube: xr.DataArray, comparison: dict[str, Any], output: Path) -> None:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib.patches import Rectangle

    output.parent.mkdir(parents=True, exist_ok=True)
    direct = comparison["direct_values"]
    piped = comparison["piped_values"]
    residual = comparison["residual"]
    spatial = [dim for dim in cube.dims if dim != "time"]
    backend_mean = cube.mean(spatial).compute()
    direct_mean = direct.mean(spatial)
    piped_mean = piped.mean(spatial)

    fig, axes = plt.subplots(2, 2, figsize=(12, 8), constrained_layout=True)
    ax = axes[0, 0]
    ax.plot(backend_mean.time, backend_mean, color="#3b6f88", marker="o", label="lazy backend sample")
    ax.set_title("GridMET backend sample")
    ax.set_ylabel(f"{cube.name} ({cube.attrs.get('units', 'source units')})")
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8)
    ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=4, maxticks=7))
    ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(ax.xaxis.get_major_locator()))

    ax = axes[0, 1]
    ax.plot(direct_mean.time, direct_mean, color="#d97732", linewidth=3, label="direct v.zscore")
    ax.plot(piped_mean.time, piped_mean, color="#342b55", linestyle="--", linewidth=1.5, label="pipe(cube) | v.zscore")
    ax.set_title("Direct call and pipe grammar overlay")
    ax.set_ylabel("spatial mean z-score")
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8)
    ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=4, maxticks=7))
    ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(ax.xaxis.get_major_locator()))

    ax = axes[1, 0]
    residual_mean = residual.mean(spatial)
    ax.plot(residual_mean.time, residual_mean, color="#9e2f2f", marker="o")
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_title(f"Residual (max |difference| = {comparison['max_abs_residual']:.2e})")
    ax.set_ylabel("direct - pipe")
    ax.grid(alpha=0.25)
    ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=4, maxticks=7))
    ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(ax.xaxis.get_major_locator()))

    ax = axes[1, 1]
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 7)
    ax.axis("off")
    boxes = [
        (0.3, 4.8, 2.5, 1.2, "annual NetCDF\nchunked backend", "#d8e8ef"),
        (3.7, 4.8, 2.5, 1.2, "xarray.DataArray\n(time, lat, lon)", "#f4e2cf"),
        (7.1, 4.8, 2.5, 1.2, "pipe | verb\nlazy graph", "#e2dded"),
        (3.7, 1.5, 2.5, 1.2, "compute only\nsmall QA sample", "#e2eddc"),
    ]
    for x, y, width, height, label, color in boxes:
        ax.add_patch(Rectangle((x, y), width, height, facecolor=color, edgecolor="#334", linewidth=1.2))
        ax.text(x + width / 2, y + height / 2, label, ha="center", va="center", fontsize=9)
    for start, end in [((2.8, 5.4), (3.7, 5.4)), ((6.2, 5.4), (7.1, 5.4)), ((8.35, 4.8), (5.2, 2.7))]:
        ax.annotate("", xy=end, xytext=start, arrowprops={"arrowstyle": "->", "color": "#334", "lw": 1.4})
    ax.text(5, 6.65, "Execution contract", ha="center", fontsize=12, fontweight="bold")
    ax.text(5, 0.55, f"chunks preserved: {comparison['lazy_before']} -> {comparison['lazy_after']}", ha="center", fontsize=9)

    fig.suptitle("QA 1 - CubeDynamics grammar and GridMET streaming contract", fontsize=15, fontweight="bold")
    fig.savefig(output, dpi=180)
    plt.close(fig)


def run_pipeline_validation(
    paths: ValidationPaths,
    *,
    fire_id: int = 20657,
    variable: str = "tmmx",
    output_dir: str | Path | None = None,
    cube: xr.DataArray | None = None,
) -> QAResult:
    """Run and render the pipe/backend equivalence check."""

    out = Path(output_dir or paths.output_root / "pipeline")
    out.mkdir(parents=True, exist_ok=True)
    if cube is None:
        event = load_event(paths, fire_id)
        cube = open_gridmet_subset(
            paths,
            variable=variable,
            year=int(event.t0.year),
            start=event.t0,
            end=event.t1,
            bounds=event_bounds(event),
        )

    comparison = compare_pipe_and_direct(cube)
    png = _plot_path = out / "pipeline_grammar_equivalence.png"
    _plot_pipeline_qa(cube, comparison, png)
    metrics_path = write_metrics_csv(
        [
            {
                "variable": cube.name,
                "time_steps": int(cube.sizes.get("time", 0)),
                "lat_cells": int(cube.sizes.get("lat", cube.sizes.get("y", 0))),
                "lon_cells": int(cube.sizes.get("lon", cube.sizes.get("x", 0))),
                "lazy_before": comparison["lazy_before"],
                "lazy_after": comparison["lazy_after"],
                "max_abs_residual": comparison["max_abs_residual"],
                "same_object_on_noop_unwrap": comparison["same_object_on_noop_unwrap"],
            }
        ],
        out / "pipeline_grammar_metrics.csv",
    )
    passed = (
        comparison["max_abs_residual"] == 0.0
        and comparison["same_object_on_noop_unwrap"]
        and comparison["lazy_before"]
        and comparison["lazy_after"]
    )
    result = QAResult(
        module="pipeline",
        status="pass" if passed else "fail",
        summary="Pipe grammar and direct verb calls produce identical values while preserving lazy chunks.",
        metrics={
            "fire_id": str(fire_id),
            "variable": variable,
            "shape": {key: int(value) for key, value in cube.sizes.items()},
            "chunks": comparison["chunks"],
            "max_abs_residual": comparison["max_abs_residual"],
            "lazy_before": comparison["lazy_before"],
            "lazy_after": comparison["lazy_after"],
            "same_object_on_noop_unwrap": comparison["same_object_on_noop_unwrap"],
        },
        artifacts={"plot": _plot_path.as_posix(), "metrics": metrics_path.as_posix()},
    )
    result_path = result.write(out / "result.json")
    result.artifacts["result"] = result_path.as_posix()
    result.write(result_path)
    return result


__all__ = ["compare_pipe_and_direct", "run_pipeline_validation"]
