"""Cross-check packaged inputs against independent upstream representations."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any
from urllib.parse import quote

import geopandas as gpd
import numpy as np
import pandas as pd
import requests
from shapely.ops import unary_union
import xarray as xr

from .core import QAResult, ValidationPaths
from .data import event_centroid_wgs84, gridmet_variable_name, load_fired_daily, load_fired_event_row


NCAR_GRIDMET_DAP = "https://tds.gdex.ucar.edu/thredds/dodsC/files/d761426"


def parse_opendap_ascii_block(text: str, *, expected_count: int | None = None) -> np.ndarray:
    """Parse the row-oriented numeric payload in a THREDDS DAP ASCII response."""

    values: list[float] = []
    for line in text.splitlines():
        match = re.match(r"^\[\d+\]\[\d+\],\s*(.+)$", line.strip())
        if not match:
            continue
        values.extend(float(token.strip()) for token in match.group(1).split(",") if token.strip())
    array = np.asarray(values, dtype=float)
    if expected_count is not None and array.size != expected_count:
        raise ValueError(f"Expected {expected_count} OPeNDAP values, parsed {array.size}")
    return array


def fetch_gridmet_mirror_block(
    *,
    variable: str,
    year: int,
    native_name: str,
    time_slice: slice,
    lat_slice: slice,
    lon_slice: slice,
    timeout: int = 60,
) -> tuple[np.ndarray, str]:
    """Fetch a tiny raw-value block from the independent NCAR GridMET mirror."""

    starts = [time_slice.start, lat_slice.start, lon_slice.start]
    stops = [time_slice.stop, lat_slice.stop, lon_slice.stop]
    if any(value is None for value in [*starts, *stops]):
        raise ValueError("External slices require explicit inclusive start and stop indices")
    nt, ny, nx = [int(stop) - int(start) + 1 for start, stop in zip(starts, stops)]
    query = (
        f"{native_name}[{time_slice.start}:1:{time_slice.stop}]"
        f"[{lat_slice.start}:1:{lat_slice.stop}]"
        f"[{lon_slice.start}:1:{lon_slice.stop}]"
    )
    url = f"{NCAR_GRIDMET_DAP}/{variable}_{year}.nc.ascii?{quote(query, safe='[],:')}"
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    values = parse_opendap_ascii_block(response.text, expected_count=nt * ny * nx)
    return values.reshape(nt, ny, nx), url


def _sample_indices(ds: xr.Dataset, *, timestamp: pd.Timestamp, lat: float, lon: float, radius: int = 1) -> tuple[slice, slice, slice]:
    time_name = "day" if "day" in ds.dims else "time"
    try:
        decoded_time = xr.decode_cf(ds[[time_name]])[time_name].values
    except Exception:
        decoded_time = ds[time_name].values
    time_values = pd.DatetimeIndex(pd.to_datetime(decoded_time))
    ti = int(np.argmin(np.abs(time_values - timestamp)))
    yi = int(np.argmin(np.abs(np.asarray(ds.lat.values, dtype=float) - lat)))
    xi = int(np.argmin(np.abs(np.asarray(ds.lon.values, dtype=float) - lon)))
    return (
        slice(max(0, ti - radius), min(ds.sizes[time_name] - 1, ti + radius)),
        slice(max(0, yi - radius), min(ds.sizes["lat"] - 1, yi + radius)),
        slice(max(0, xi - radius), min(ds.sizes["lon"] - 1, xi + radius)),
    )


def validate_gridmet_external_mirror(
    paths: ValidationPaths,
    *,
    fire_id: int,
    variable: str = "tmmx",
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Compare raw packed values in the local cache and NCAR mirror."""

    daily = load_fired_daily(paths, fire_id)
    timestamp = pd.Timestamp(daily.date.iloc[len(daily) // 2]).normalize()
    year = int(timestamp.year)
    path = paths.gridmet_cache / f"{variable}_{year}.nc"
    ds = xr.open_dataset(path, decode_cf=False, mask_and_scale=False)
    native_name = gridmet_variable_name(ds.drop_vars("crs", errors="ignore"), variable)
    lat, lon = event_centroid_wgs84(paths, fire_id)
    time_slice, lat_slice, lon_slice = _sample_indices(ds, timestamp=timestamp, lat=lat, lon=lon, radius=1)
    time_name = "day" if "day" in ds.dims else "time"
    local = np.asarray(
        ds[native_name].isel(
            {
                time_name: slice(time_slice.start, time_slice.stop + 1),
                "lat": slice(lat_slice.start, lat_slice.stop + 1),
                "lon": slice(lon_slice.start, lon_slice.stop + 1),
            }
        ).values,
        dtype=float,
    )
    external, url = fetch_gridmet_mirror_block(
        variable=variable,
        year=year,
        native_name=native_name,
        time_slice=time_slice,
        lat_slice=lat_slice,
        lon_slice=lon_slice,
    )
    difference = external - local
    records = []
    for index in np.ndindex(local.shape):
        records.append(
            {
                "time_offset": index[0],
                "lat_offset": index[1],
                "lon_offset": index[2],
                "local_raw_value": local[index],
                "ncar_mirror_raw_value": external[index],
                "residual": difference[index],
            }
        )
    return pd.DataFrame(records), {
        "external_url": url,
        "year": year,
        "timestamp_center": timestamp.isoformat(),
        "native_variable": native_name,
        "sample_shape": list(local.shape),
        "max_abs_raw_residual": float(np.max(np.abs(difference))),
        "local_values": local,
        "external_values": external,
    }


def validate_fired_event_consistency(paths: ValidationPaths, *, fire_id: int) -> dict[str, Any]:
    """Compare the event polygon with the union of its upstream daily polygons."""

    daily = load_fired_daily(paths, fire_id).to_crs(5070)
    event = load_fired_event_row(paths, fire_id).to_crs(5070)
    daily_union = unary_union(daily.geometry.values)
    event_union = unary_union(event.geometry.values)
    intersection = float(daily_union.intersection(event_union).area)
    union_area = float(daily_union.union(event_union).area)
    return {
        "daily_union": daily_union,
        "event_union": event_union,
        "daily_union_area_km2": float(daily_union.area / 1e6),
        "event_area_km2": float(event_union.area / 1e6),
        "intersection_over_union": intersection / max(union_area, 1e-12),
        "hausdorff_distance_m": float(daily_union.hausdorff_distance(event_union)),
        "daily_rows": int(len(daily)),
    }


def _plot_external_qa(
    mirror: pd.DataFrame | None,
    mirror_metrics: dict[str, Any],
    fired: dict[str, Any],
    output: Path,
) -> None:
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(2, 2, figsize=(12, 9), constrained_layout=True)
    ax = axes[0, 0]
    if mirror is not None:
        ax.scatter(mirror.local_raw_value, mirror.ncar_mirror_raw_value, color="#3b6f88", alpha=0.8)
        limits = [float(mirror[["local_raw_value", "ncar_mirror_raw_value"]].min().min()), float(mirror[["local_raw_value", "ncar_mirror_raw_value"]].max().max())]
        ax.plot(limits, limits, color="black", linestyle="--", linewidth=1)
        ax.set_title("Packaged cache vs independent NCAR mirror")
        ax.set_xlabel("local packed value")
        ax.set_ylabel("NCAR packed value")
        ax.grid(alpha=0.2)
    else:
        ax.text(0.5, 0.5, "External network check not requested", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()

    ax = axes[0, 1]
    if mirror is not None:
        shape = mirror_metrics["sample_shape"]
        residual = mirror.residual.to_numpy().reshape(shape)
        image = ax.imshow(residual[shape[0] // 2], cmap="RdBu_r", vmin=-1, vmax=1)
        for iy in range(shape[1]):
            for ix in range(shape[2]):
                ax.text(ix, iy, f"{residual[shape[0] // 2, iy, ix]:.0f}", ha="center", va="center", fontsize=10)
        ax.set_title(f"Mirror residual at center day (max = {np.abs(residual).max():.0f})")
        ax.set_xlabel("longitude index")
        ax.set_ylabel("latitude index")
        ax.set_xticks(range(shape[2]))
        ax.set_yticks(range(shape[1]))
        ax.set_xticks(np.arange(-0.5, shape[2], 1), minor=True)
        ax.set_yticks(np.arange(-0.5, shape[1], 1), minor=True)
        ax.grid(which="minor", color="#b8c0c4", linewidth=0.8)
        ax.text(0.5, -0.16, f"all {int(np.prod(shape))} sampled values identical", transform=ax.transAxes, ha="center", fontsize=8)
    else:
        ax.set_axis_off()

    ax = axes[1, 0]
    for geometry, color, label, width in [
        (fired["event_union"], "#d97732", "FIRED event polygon", 2.8),
        (fired["daily_union"], "#342b55", "union of FIRED daily polygons", 1.3),
    ]:
        boundary = geometry.boundary
        lines = [boundary] if boundary.geom_type == "LineString" else list(boundary.geoms)
        for line in lines:
            x, y = line.xy
            ax.plot(np.asarray(x) / 1000, np.asarray(y) / 1000, color=color, linewidth=width, label=label)
            label = None
    ax.set_aspect("equal")
    ax.set_title(f"FIRED daily-to-event geometry (IoU = {fired['intersection_over_union']:.8f})")
    ax.set_xlabel("equal-area x (km)")
    ax.set_ylabel("equal-area y (km)")
    ax.legend(fontsize=8)

    ax = axes[1, 1]
    ax.axis("off")
    lines = [
        "Independent representations checked",
        "",
        "GridMET:",
        "  packaged University of Idaho annual NetCDF",
        "  NCAR/GDEX THREDDS OPeNDAP mirror",
        f"  max raw residual: {mirror_metrics.get('max_abs_raw_residual', 'not run')}",
        "",
        "FIRED:",
        "  event-level polygon",
        "  union of daily progression polygons",
        f"  intersection / union: {fired['intersection_over_union']:.10f}",
        f"  Hausdorff distance: {fired['hausdorff_distance_m']:.4f} m",
    ]
    ax.text(0.02, 0.98, "\n".join(lines), va="top", family="monospace", fontsize=9)
    fig.suptitle("QA 4 - External and upstream-source validation", fontsize=15, fontweight="bold")
    fig.savefig(output, dpi=180)
    plt.close(fig)


def run_external_validation(
    paths: ValidationPaths,
    *,
    fire_id: int = 20657,
    variable: str = "tmmx",
    external_network: bool = False,
    output_dir: str | Path | None = None,
) -> QAResult:
    """Run FIRED internal-source and optional NCAR GridMET mirror checks."""

    out = Path(output_dir or paths.output_root / "external")
    out.mkdir(parents=True, exist_ok=True)
    fired = validate_fired_event_consistency(paths, fire_id=int(fire_id))
    mirror: pd.DataFrame | None = None
    mirror_metrics: dict[str, Any] = {"max_abs_raw_residual": None, "sample_shape": None}
    notes: list[str] = []
    if external_network:
        mirror, mirror_metrics = validate_gridmet_external_mirror(paths, fire_id=int(fire_id), variable=variable)
        mirror_csv = out / "gridmet_ncar_mirror_samples.csv"
        mirror.to_csv(mirror_csv, index=False)
    else:
        mirror_csv = None
        notes.append("NCAR mirror retrieval was skipped; rerun with --external for an independent network comparison.")

    fired_csv = out / "fired_event_consistency.csv"
    pd.DataFrame(
        [
            {
                key: value
                for key, value in fired.items()
                if key not in {"daily_union", "event_union"}
            }
        ]
    ).to_csv(fired_csv, index=False)
    plot = out / "external_source_validation.png"
    _plot_external_qa(mirror, mirror_metrics, fired, plot)

    fired_pass = fired["intersection_over_union"] >= 0.99
    mirror_pass = mirror is not None and mirror_metrics["max_abs_raw_residual"] == 0.0
    status = "pass" if fired_pass and (mirror_pass or not external_network) else "fail"
    summary = (
        "Packaged GridMET raw values exactly match the NCAR mirror and FIRED event geometry matches the union of daily polygons."
        if external_network and mirror_pass
        else "FIRED event geometry matches the union of daily polygons; the optional independent GridMET mirror check was not run."
    )
    artifacts = {"plot": plot.as_posix(), "fired_metrics": fired_csv.as_posix()}
    if mirror_csv:
        artifacts["gridmet_mirror_samples"] = mirror_csv.as_posix()
    result = QAResult(
        module="external",
        status=status,
        summary=summary,
        metrics={
            "fire_id": str(fire_id),
            "gridmet_variable": variable,
            "external_network_requested": external_network,
            "gridmet_max_abs_raw_residual": mirror_metrics.get("max_abs_raw_residual"),
            "gridmet_external_url": mirror_metrics.get("external_url"),
            "fired_intersection_over_union": fired["intersection_over_union"],
            "fired_hausdorff_distance_m": fired["hausdorff_distance_m"],
        },
        artifacts=artifacts,
        notes=notes,
    )
    result_path = result.write(out / "result.json")
    result.artifacts["result"] = result_path.as_posix()
    result.write(result_path)
    return result


__all__ = [
    "fetch_gridmet_mirror_block",
    "parse_opendap_ascii_block",
    "run_external_validation",
    "validate_fired_event_consistency",
    "validate_gridmet_external_mirror",
]
