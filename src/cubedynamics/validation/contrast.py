"""Expected-failure controls for demonstrating that validators reject bad inputs."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import xarray as xr

from .core import QAResult, ValidationPaths, write_metrics_csv
from .cube import _rgba, audit_cube_html, run_cube_validation
from .data import event_bounds, load_event, open_gridmet_subset
from .geometry import run_geometry_validation


def corrupted_cube_variants(cube: xr.DataArray) -> dict[str, xr.DataArray]:
    """Return deterministic axis, time-order, and missing-date negative controls."""

    canonical = cube.transpose("time", "lat", "lon").compute()
    values = np.asarray(canonical.values).copy()

    latitude_values = np.flip(values, axis=1)
    latitude_scramble = canonical.copy(data=latitude_values)
    latitude_scramble.attrs = {**canonical.attrs, "negative_control": "latitude values reversed while coordinates remain unchanged"}

    time_values = values.copy()
    first_swap = min(5, len(time_values) - 2)
    second_swap = max(first_swap + 1, len(time_values) - 6)
    time_values[[first_swap, second_swap]] = time_values[[second_swap, first_swap]]
    time_scramble = canonical.copy(data=time_values)
    time_scramble.attrs = {
        **canonical.attrs,
        "negative_control": f"values at time indices {first_swap} and {second_swap} swapped while timestamps remain unchanged",
    }

    drop_index = len(canonical.time) // 2
    keep = np.delete(np.arange(len(canonical.time)), drop_index)
    dropped_day = canonical.isel(time=keep)
    dropped_day.attrs = {**canonical.attrs, "negative_control": f"time index {drop_index} removed"}

    return {
        "latitude_values_reversed": latitude_scramble,
        "time_values_scrambled": time_scramble,
        "middle_day_dropped": dropped_day,
    }


def _daily_contiguous(cube: xr.DataArray) -> bool:
    dates = np.asarray(cube.time.values).astype("datetime64[D]").astype(int)
    gaps = np.diff(dates)
    return bool(len(gaps) == 0 or np.all(gaps == 1))


def _audit_record(name: str, cube: xr.DataArray, audit: dict[str, Any]) -> dict[str, Any]:
    comparisons = audit["records"]
    failing = [record for record in comparisons if not record["exact_pixel_match"]]
    max_residual = max(record["max_rgba_channel_difference"] for record in comparisons)
    contiguous = _daily_contiguous(cube)
    rejected = not (
        audit["all_planes_present"]
        and audit["all_pixels_exact"]
        and audit["all_time_slices_serialized_once"]
        and contiguous
    )
    return {
        "variant": name,
        "expected_status": "fail" if name != "uncorrupted_baseline" else "pass",
        "observed_status": "fail" if rejected else "pass",
        "detected_as_expected": bool((name == "uncorrupted_baseline" and not rejected) or (name != "uncorrupted_baseline" and rejected)),
        "time_steps": int(cube.sizes["time"]),
        "daily_dates_contiguous": contiguous,
        "all_planes_present": bool(audit["all_planes_present"]),
        "all_time_slices_serialized_once": bool(audit["all_time_slices_serialized_once"]),
        "all_pixels_exact": bool(audit["all_pixels_exact"]),
        "failing_raster_comparisons": int(len(failing)),
        "total_raster_comparisons": int(len(comparisons)),
        "maximum_rgba_channel_residual": int(max_residual),
        "negative_control": cube.attrs.get("negative_control", "none"),
    }


def _plot_cube_negative_controls(
    baseline: xr.DataArray,
    baseline_audit: dict[str, Any],
    variants: dict[str, xr.DataArray],
    records: list[dict[str, Any]],
    *,
    limits: tuple[float, float],
    output: Path,
) -> None:
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt

    baseline_values = np.asarray(baseline.values)
    latitude_bad = np.asarray(variants["latitude_values_reversed"].values)
    time_bad = np.asarray(variants["time_values_scrambled"].values)
    html_front = baseline_audit["faces"]["front"]
    bad_front = _rgba(latitude_bad[-1], cmap="viridis", limits=limits)
    residual = np.max(np.abs(bad_front.astype("int16") - html_front.astype("int16")), axis=2)

    fig, axes = plt.subplots(2, 3, figsize=(15, 9), constrained_layout=True)
    axes[0, 0].imshow(baseline_values[-1], cmap="viridis", aspect="auto")
    axes[0, 0].set_title("PASS control: final source plane")
    axes[0, 0].set_xlabel("longitude index")
    axes[0, 0].set_ylabel("latitude index")

    axes[0, 1].imshow(latitude_bad[-1], cmap="viridis", aspect="auto")
    axes[0, 1].set_title("FAIL control: latitude values reversed")
    axes[0, 1].annotate("north/south values swapped", xy=(0.5, 0.04), xycoords="axes fraction", color="white", ha="center", fontsize=9)
    axes[0, 1].set_xlabel("longitude index")
    axes[0, 1].set_ylabel("unchanged latitude index")

    image = axes[0, 2].imshow(residual, cmap="magma", vmin=0, aspect="auto")
    axes[0, 2].set_title("Decoded HTML residual exposes the reversal")
    axes[0, 2].set_xlabel("HTML pixel column")
    axes[0, 2].set_ylabel("HTML pixel row")
    fig.colorbar(image, ax=axes[0, 2], shrink=0.75, label="max RGBA residual")

    baseline_mean = np.nanmean(baseline_values, axis=(1, 2))
    scrambled_mean = np.nanmean(time_bad, axis=(1, 2))
    axes[1, 0].plot(pd.to_datetime(baseline.time.values), baseline_mean, color="#3b6f88", marker="o", markersize=3, label="baseline")
    axes[1, 0].plot(pd.to_datetime(baseline.time.values), scrambled_mean, color="#b23a48", linestyle="--", marker="x", label="scrambled values")
    date_locator = mdates.AutoDateLocator(minticks=4, maxticks=7)
    axes[1, 0].xaxis.set_major_locator(date_locator)
    axes[1, 0].xaxis.set_major_formatter(mdates.ConciseDateFormatter(date_locator))
    axes[1, 0].set_title("FAIL control: values assigned to wrong dates")
    axes[1, 0].set_ylabel("spatial mean")
    axes[1, 0].legend(fontsize=8)
    axes[1, 0].grid(alpha=0.2)

    dropped = variants["middle_day_dropped"]
    gaps = np.diff(np.asarray(dropped.time.values).astype("datetime64[D]").astype(int))
    axes[1, 1].bar(np.arange(len(gaps)), gaps, color=np.where(gaps == 1, "#669bbc", "#c1121f"))
    axes[1, 1].axhline(1, color="black", linewidth=0.8)
    axes[1, 1].set_title("FAIL control: missing date creates a 2-day gap")
    axes[1, 1].set_xlabel("adjacent timestamp pair")
    axes[1, 1].set_ylabel("gap (days)")

    frame = pd.DataFrame(records)
    negatives = frame[frame.variant != "uncorrupted_baseline"]
    axes[1, 2].barh(negatives.variant, negatives.failing_raster_comparisons, color="#c1121f")
    axes[1, 2].set_title("All three corrupted variants are rejected")
    axes[1, 2].set_xlabel("failed source-to-HTML raster comparisons")
    axes[1, 2].grid(axis="x", alpha=0.2)

    fig.suptitle("Expected FAIL controls - axis reversal, time scrambling, and a dropped date", fontsize=15, fontweight="bold")
    fig.savefig(output, dpi=190)
    plt.close(fig)


def run_cube_negative_controls(
    paths: ValidationPaths,
    *,
    fire_id: int = 20657,
    variable: str = "tmmx",
    output_dir: str | Path,
) -> QAResult:
    """Run corruptions against a freshly rendered passing real-cube baseline."""

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    baseline_result = run_cube_validation(
        paths,
        fire_id=fire_id,
        variable=variable,
        output_dir=out / "baseline",
    )
    event = load_event(paths, fire_id)
    cube = open_gridmet_subset(
        paths,
        variable=variable,
        year=int(event.t0.year),
        start=event.t0,
        end=event.t1,
        bounds=event_bounds(event),
    ).transpose("time", "lat", "lon").compute()
    values = np.asarray(cube.values, dtype=float)
    finite = values[np.isfinite(values)]
    limits = (float(finite.min()), float(finite.max()))
    html = Path(baseline_result.artifacts["interactive_html"]).read_text(encoding="utf-8")

    baseline_audit = audit_cube_html(cube, html, cmap="viridis", limits=limits)
    records = [_audit_record("uncorrupted_baseline", cube, baseline_audit)]
    variants = corrupted_cube_variants(cube)
    for name, variant in variants.items():
        audit = audit_cube_html(variant, html, cmap="viridis", limits=limits)
        records.append(_audit_record(name, variant, audit))

    metrics_path = write_metrics_csv(records, out / "cube_negative_control_metrics.csv")
    plot = out / "cube_negative_controls.png"
    _plot_cube_negative_controls(cube, baseline_audit, variants, records, limits=limits, output=plot)
    frame = pd.DataFrame(records)
    baseline_passed = bool(frame.loc[frame.variant == "uncorrupted_baseline", "observed_status"].iloc[0] == "pass")
    negative_frame = frame[frame.variant != "uncorrupted_baseline"]
    detected = int(negative_frame.detected_as_expected.sum())
    expected_failure_worked = baseline_passed and detected == len(negative_frame)

    result = QAResult(
        module="cube_negative_controls",
        status="fail",
        summary="Expected FAIL: the baseline passes, while latitude reversal, time-value scrambling, and a dropped date are all rejected by the cube/HTML audit.",
        metrics={
            "fire_id": str(fire_id),
            "variable": variable,
            "uncorrupted_baseline_passed": baseline_passed,
            "corrupted_variants": int(len(negative_frame)),
            "corruptions_detected": detected,
            "all_negative_controls_detected": expected_failure_worked,
            "latitude_reversal_failed_comparisons": int(negative_frame.loc[negative_frame.variant == "latitude_values_reversed", "failing_raster_comparisons"].iloc[0]),
            "time_scramble_failed_comparisons": int(negative_frame.loc[negative_frame.variant == "time_values_scrambled", "failing_raster_comparisons"].iloc[0]),
            "dropped_day_daily_contiguity": bool(negative_frame.loc[negative_frame.variant == "middle_day_dropped", "daily_dates_contiguous"].iloc[0]),
        },
        artifacts={
            "plot": plot.as_posix(),
            "metrics": metrics_path.as_posix(),
            "baseline_html": baseline_result.artifacts["interactive_html"],
        },
        notes=[
            "FAIL is the intended result in this contrast module. The run command succeeds only when the clean baseline passes and every corruption is detected.",
            "The latitude and time corruptions keep coordinate labels unchanged, demonstrating that value-to-index checks are required in addition to monotonic-coordinate checks.",
        ],
    )
    result_path = result.write(out / "result.json")
    result.artifacts["result"] = result_path.as_posix()
    result.write(result_path)
    return result


def run_contrast_suite(
    paths: ValidationPaths,
    *,
    cube_fire_id: int = 20657,
    geometry_fire_id: int = 72016,
    variable: str = "tmmx",
    output_root: str | Path,
) -> tuple[list[QAResult], Path]:
    """Run the deterministic cube controls and real geometry failure."""

    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    cube_result = run_cube_negative_controls(
        paths,
        fire_id=cube_fire_id,
        variable=variable,
        output_dir=root / "cube",
    )
    geometry_result = run_geometry_validation(
        paths,
        fire_id=geometry_fire_id,
        tolerances_m=(0, 125, 500, 1000),
        operational_max_tolerance_m=125,
        n_theta=96,
        output_dir=root / "geometry",
    )
    operational_change = float(
        geometry_result.metrics["operational_max_absolute_area_change_pct"]
    )
    geometry_result.summary = (
        f"Expected FAIL: real FIRED event {geometry_fire_id} changes cumulative "
        f"area by {operational_change:.2f}% at the operational 125 m "
        "simplification, exceeding the 10% threshold."
    )
    geometry_result.notes.insert(
        0,
        "This deliberately selected real-world counterexample demonstrates a "
        "sensitivity limit; it does not indicate that the production validation "
        "run failed.",
    )
    geometry_result.write(root / "geometry" / "result.json")
    results = [cube_result, geometry_result]
    expected = bool(
        cube_result.metrics["all_negative_controls_detected"]
        and geometry_result.status == "fail"
        and float(geometry_result.metrics["operational_max_absolute_area_change_pct"]) > 10.0
    )
    manifest = {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "purpose": "expected-failure negative controls",
        "expected_failures_detected": expected,
        "modules": [result.as_dict() for result in results],
    }
    manifest_path = root / "contrast_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, default=str), encoding="utf-8")
    return results, manifest_path


__all__ = [
    "corrupted_cube_variants",
    "run_contrast_suite",
    "run_cube_negative_controls",
]
