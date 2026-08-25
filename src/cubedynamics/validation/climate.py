"""Validate GridMET dates and polygon-to-grid climate attribution choices."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import geopandas as gpd
import numpy as np
import pandas as pd
from pyproj import Transformer
from shapely.geometry import box
from shapely.ops import transform
import xarray as xr

from .core import QAResult, ValidationPaths, write_metrics_csv
from .data import (
    GRIDMET_VALUE_NAMES,
    event_bounds,
    event_centroid_wgs84,
    load_event,
    load_fired_daily,
    open_gridmet_subset,
    read_vase_slices,
)


def coordinate_edges(values: np.ndarray) -> np.ndarray:
    """Return cell edges for monotonic center coordinates, preserving order."""

    centers = np.asarray(values, dtype=float)
    if centers.ndim != 1 or centers.size == 0:
        raise ValueError("Grid coordinates must be a non-empty one-dimensional array")
    if centers.size == 1:
        return np.array([centers[0] - 0.5, centers[0] + 0.5])
    mid = (centers[:-1] + centers[1:]) / 2.0
    first = centers[0] - (mid[0] - centers[0])
    last = centers[-1] + (centers[-1] - mid[-1])
    return np.r_[first, mid, last]


def pixel_overlap_attribution(
    field: xr.DataArray,
    polygon_wgs84: Any,
    *,
    equal_area_epsg: int = 5070,
) -> dict[str, Any]:
    """Compute centroid, center-in-polygon, and fractional-overlap values."""

    if "time" in field.dims:
        if field.sizes["time"] != 1:
            raise ValueError("pixel_overlap_attribution expects one time slice")
        field = field.isel(time=0)
    if not {"lat", "lon"}.issubset(field.dims):
        raise ValueError("GridMET field must use lat/lon dimensions")

    lat = np.asarray(field.lat.values, dtype=float)
    lon = np.asarray(field.lon.values, dtype=float)
    lat_edges = coordinate_edges(lat)
    lon_edges = coordinate_edges(lon)
    values = np.asarray(field.values, dtype=float)
    transformer = Transformer.from_crs(4326, equal_area_epsg, always_xy=True)
    project = transformer.transform
    polygon_metric = transform(project, polygon_wgs84)
    centroid = polygon_wgs84.centroid

    centroid_y = int(np.argmin(np.abs(lat - centroid.y)))
    centroid_x = int(np.argmin(np.abs(lon - centroid.x)))
    centroid_value = float(values[centroid_y, centroid_x])

    records: list[dict[str, Any]] = []
    center_values: list[float] = []
    overlap_values: list[float] = []
    overlap_areas: list[float] = []
    for iy, lat_center in enumerate(lat):
        south, north = sorted((lat_edges[iy], lat_edges[iy + 1]))
        for ix, lon_center in enumerate(lon):
            west, east = sorted((lon_edges[ix], lon_edges[ix + 1]))
            cell_wgs84 = box(west, south, east, north)
            cell_metric = transform(project, cell_wgs84)
            intersection_area = float(cell_metric.intersection(polygon_metric).area)
            fraction = intersection_area / max(float(cell_metric.area), 1e-12)
            center_inside = bool(polygon_wgs84.covers(cell_wgs84.centroid))
            value = float(values[iy, ix])
            if center_inside and np.isfinite(value):
                center_values.append(value)
            if intersection_area > 0 and np.isfinite(value):
                overlap_values.append(value)
                overlap_areas.append(intersection_area)
            if intersection_area > 0 or (iy == centroid_y and ix == centroid_x):
                records.append(
                    {
                        "iy": iy,
                        "ix": ix,
                        "lat": float(lat_center),
                        "lon": float(lon_center),
                        "value": value,
                        "overlap_area_km2": intersection_area / 1e6,
                        "overlap_fraction": fraction,
                        "center_inside": center_inside,
                        "centroid_cell": bool(iy == centroid_y and ix == centroid_x),
                    }
                )

    area_weighted = (
        float(np.average(overlap_values, weights=overlap_areas))
        if overlap_areas
        else centroid_value
    )
    center_mean = float(np.mean(center_values)) if center_values else centroid_value
    return {
        "centroid_value": centroid_value,
        "cell_center_mean": center_mean,
        "area_weighted_mean": area_weighted,
        "overlap_cell_count": int(len(overlap_areas)),
        "center_inside_cell_count": int(len(center_values)),
        "overlap_area_km2": float(np.sum(overlap_areas) / 1e6),
        "records": records,
    }


def _convert_gridmet(variable: str, values: np.ndarray | float) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    return array - 273.15 if variable in {"tmmx", "tmmn"} else array


def validate_centroid_table_values(
    paths: ValidationPaths,
    *,
    fire_id: int,
    variable: str,
    cube: xr.DataArray,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Recompute lake-table values from NetCDF at the documented centroid."""

    table = read_vase_slices(paths, fire_id)
    value_column = GRIDMET_VALUE_NAMES[variable]
    lat, lon = event_centroid_wgs84(paths, fire_id)
    timestamps = pd.DatetimeIndex(table.timestamp)
    selected = cube.sel(
        time=xr.DataArray(timestamps.values, dims="points"),
        lat=xr.DataArray(np.full(len(timestamps), lat), dims="points"),
        lon=xr.DataArray(np.full(len(timestamps), lon), dims="points"),
        method="nearest",
    ).compute()
    recomputed = _convert_gridmet(variable, selected.values)
    audit = pd.DataFrame(
        {
            "fire_id": str(fire_id),
            "timestamp": timestamps,
            "table_value": table[value_column].to_numpy(float),
            "recomputed_centroid_value": recomputed,
        }
    )
    audit["residual"] = audit.recomputed_centroid_value - audit.table_value
    daily_dates = set(pd.to_datetime(load_fired_daily(paths, fire_id).date).dt.normalize())
    table_dates = set(timestamps.normalize())
    cube_dates = set(pd.to_datetime(cube.time.values).normalize())
    metrics = {
        "centroid_lat": lat,
        "centroid_lon": lon,
        "max_abs_table_residual": float(audit.residual.abs().max()),
        "table_dates_equal_fired_dates": table_dates == daily_dates,
        "table_dates_present_in_gridmet": table_dates.issubset(cube_dates),
        "table_rows": int(len(table)),
    }
    return audit, metrics


def compare_spatial_attribution(
    daily: gpd.GeoDataFrame,
    cube: xr.DataArray,
    *,
    variable: str,
) -> tuple[pd.DataFrame, dict[pd.Timestamp, dict[str, Any]]]:
    """Compare one centroid cell with cell-center and area-overlap summaries."""

    daily_wgs84 = daily.to_crs(4326)
    rows: list[dict[str, Any]] = []
    details: dict[pd.Timestamp, dict[str, Any]] = {}
    for record in daily_wgs84.itertuples(index=False):
        date = pd.Timestamp(record.date).normalize()
        if date not in pd.DatetimeIndex(cube.time.values).normalize():
            continue
        attribution = pixel_overlap_attribution(cube.sel(time=[date]), record.geometry)
        details[date] = attribution
        rows.append(
            {
                "timestamp": date,
                "centroid_value": float(_convert_gridmet(variable, attribution["centroid_value"])),
                "cell_center_mean": float(_convert_gridmet(variable, attribution["cell_center_mean"])),
                "area_weighted_mean": float(_convert_gridmet(variable, attribution["area_weighted_mean"])),
                "overlap_cell_count": attribution["overlap_cell_count"],
                "center_inside_cell_count": attribution["center_inside_cell_count"],
                "overlap_area_km2": attribution["overlap_area_km2"],
                "polygon_area_km2": float(gpd.GeoSeries([record.geometry], crs=4326).to_crs(5070).area.iloc[0] / 1e6),
            }
        )
    frame = pd.DataFrame(rows).sort_values("timestamp").reset_index(drop=True)
    return frame, details


def _plot_climate_qa(
    cube: xr.DataArray,
    daily: gpd.GeoDataFrame,
    centroid_audit: pd.DataFrame,
    spatial: pd.DataFrame,
    details: dict[pd.Timestamp, dict[str, Any]],
    output: Path,
    *,
    variable: str,
) -> None:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib.patches import Rectangle

    fig, axes = plt.subplots(2, 2, figsize=(13, 10), constrained_layout=True)
    daily_wgs84 = daily.to_crs(4326).copy()
    daily_wgs84["area"] = daily.to_crs(5070).area.values
    selected_row = daily_wgs84.loc[daily_wgs84["area"].idxmax()]
    selected_date = pd.Timestamp(selected_row.date).normalize()
    field = _convert_gridmet(variable, cube.sel(time=selected_date).compute().values)
    lat = np.asarray(cube.lat.values)
    lon = np.asarray(cube.lon.values)

    ax = axes[0, 0]
    image = ax.pcolormesh(lon, lat, field, shading="nearest", cmap="magma")
    x, y = selected_row.geometry.exterior.xy if selected_row.geometry.geom_type == "Polygon" else selected_row.geometry.convex_hull.exterior.xy
    ax.plot(x, y, color="cyan", linewidth=2.0, label="FIRED daily polygon")
    detail = pd.DataFrame(details[selected_date]["records"])
    overlap = detail[detail.overlap_fraction > 0]
    ax.scatter(
        overlap.lon,
        overlap.lat,
        s=35 + 160 * overlap.overlap_fraction,
        facecolors="none",
        edgecolors="white",
        linewidths=1.2,
        label="overlap-weighted cells",
    )
    centroid_cell = detail[detail.centroid_cell]
    ax.scatter(centroid_cell.lon, centroid_cell.lat, marker="x", s=90, color="#29f2ff", linewidths=2.2, label="polygon centroid cell")
    ax.set_title(f"Grid alignment on {selected_date.date()}")
    ax.set_xlabel("longitude")
    ax.set_ylabel("latitude")
    ax.legend(fontsize=7, loc="best")
    fig.colorbar(image, ax=ax, shrink=0.8, label=f"{variable} (C)" if variable.startswith("tmm") else variable)

    ax = axes[0, 1]
    ax.plot(centroid_audit.timestamp, centroid_audit.table_value, color="#342b55", linewidth=3, label="lake table")
    ax.plot(
        centroid_audit.timestamp,
        centroid_audit.recomputed_centroid_value,
        color="#d97732",
        linestyle="--",
        marker="o",
        label="NetCDF centroid recomputation",
    )
    ax.set_title("Centroid table value audit")
    ax.set_ylabel("maximum temperature (C)" if variable == "tmmx" else variable)
    ax.grid(alpha=0.2)
    ax.legend(fontsize=8)
    ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=4, maxticks=7))
    ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(ax.xaxis.get_major_locator()))

    ax = axes[1, 0]
    ax.plot(spatial.timestamp, spatial.centroid_value, marker="o", label="daily polygon centroid")
    ax.plot(spatial.timestamp, spatial.cell_center_mean, marker="s", label="centers inside polygon")
    ax.plot(spatial.timestamp, spatial.area_weighted_mean, marker="^", label="fractional pixel overlap")
    ax.set_title("Attribution method sensitivity")
    ax.set_ylabel("maximum temperature (C)" if variable == "tmmx" else variable)
    ax.grid(alpha=0.2)
    ax.legend(fontsize=8)
    ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=4, maxticks=7))
    ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(ax.xaxis.get_major_locator()))

    ax = axes[1, 1]
    differences = spatial.area_weighted_mean - spatial.centroid_value
    ax.bar(spatial.timestamp, differences, color=np.where(differences >= 0, "#b35b27", "#3b6f88"), width=0.8)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_title("Fractional-overlap minus centroid attribution")
    ax.set_ylabel("difference")
    ax.grid(axis="y", alpha=0.2)
    ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=4, maxticks=7))
    ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(ax.xaxis.get_major_locator()))
    note = (
        f"table max |residual|: {centroid_audit.residual.abs().max():.2e}\n"
        f"overlap cells: {int(spatial.overlap_cell_count.min())}-{int(spatial.overlap_cell_count.max())}"
    )
    ax.add_patch(Rectangle((0.02, 0.78), 0.45, 0.18, transform=ax.transAxes, facecolor="white", edgecolor="#aaa", alpha=0.9))
    ax.text(0.04, 0.87, note, transform=ax.transAxes, va="center", fontsize=8)

    fig.suptitle("QA 3 - GridMET time and polygon attribution", fontsize=15, fontweight="bold")
    fig.savefig(output, dpi=180)
    plt.close(fig)


def run_climate_validation(
    paths: ValidationPaths,
    *,
    fire_id: int = 20657,
    variable: str = "tmmx",
    output_dir: str | Path | None = None,
) -> QAResult:
    """Run date, centroid-table, and polygon-overlap climate QA."""

    if variable not in GRIDMET_VALUE_NAMES:
        raise ValueError(f"Climate validation currently supports {sorted(GRIDMET_VALUE_NAMES)}")
    out = Path(output_dir or paths.output_root / "climate")
    out.mkdir(parents=True, exist_ok=True)
    event = load_event(paths, fire_id)
    daily = load_fired_daily(paths, fire_id)
    cube = open_gridmet_subset(
        paths,
        variable=variable,
        year=int(event.t0.year),
        start=event.t0,
        end=event.t1,
        bounds=event_bounds(event, pad_degrees=0.16),
    )
    centroid_audit, time_metrics = validate_centroid_table_values(
        paths,
        fire_id=int(fire_id),
        variable=variable,
        cube=cube,
    )
    spatial, details = compare_spatial_attribution(daily, cube, variable=variable)
    centroid_csv = out / "centroid_table_audit.csv"
    centroid_audit.to_csv(centroid_csv, index=False)
    spatial_csv = out / "polygon_attribution_comparison.csv"
    spatial.to_csv(spatial_csv, index=False)
    plot = out / "gridmet_time_space_attribution.png"
    _plot_climate_qa(cube, daily, centroid_audit, spatial, details, plot, variable=variable)

    max_method_difference = float((spatial.area_weighted_mean - spatial.centroid_value).abs().max())
    passed = (
        time_metrics["max_abs_table_residual"] <= 1e-8
        and time_metrics["table_dates_equal_fired_dates"]
        and time_metrics["table_dates_present_in_gridmet"]
        and spatial.overlap_cell_count.min() >= 1
    )
    result = QAResult(
        module="climate",
        status="pass" if passed else "fail",
        summary="Lake-table dates and centroid values match FIRED/GridMET inputs; fractional overlap attribution is computed and exposed as a deliberate alternative.",
        metrics={
            "fire_id": str(fire_id),
            "variable": variable,
            **time_metrics,
            "daily_polygon_rows_compared": int(len(spatial)),
            "min_overlap_cells": int(spatial.overlap_cell_count.min()),
            "max_overlap_cells": int(spatial.overlap_cell_count.max()),
            "max_abs_area_weighted_minus_centroid": max_method_difference,
        },
        artifacts={
            "plot": plot.as_posix(),
            "centroid_audit": centroid_csv.as_posix(),
            "attribution_comparison": spatial_csv.as_posix(),
        },
        notes=[
            "Centroid attribution reproduces the current vase_slices table contract.",
            "Fractional overlap weights each GridMET cell by intersected equal-area square meters; it is a sensitivity analysis, not a silent replacement of the table baseline.",
        ],
    )
    result_path = result.write(out / "result.json")
    result.artifacts["result"] = result_path.as_posix()
    result.write(result_path)
    return result


__all__ = [
    "compare_spatial_attribution",
    "coordinate_edges",
    "pixel_overlap_attribution",
    "run_climate_validation",
    "validate_centroid_table_values",
]
