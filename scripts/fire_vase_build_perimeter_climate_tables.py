#!/usr/bin/env python3
"""Build perimeter-based fire VASE climate exposure tables from cached gridMET.

The existing VASE climate table samples one gridMET cell at each fire centroid.
This script creates a companion table with zone summaries over real FIRED daily
polygons: the active daily burn polygon, the cumulative burned area to date,
and configurable exterior perimeter-extension buffers.
"""

from __future__ import annotations

import argparse
import json
import math
import time
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely
import xarray as xr
import yaml
from shapely.geometry.base import BaseGeometry

try:
    from scripts.fire_vase_build_climate_tables import (
        GRIDMET_OUTPUTS,
        convert_gridmet,
        gridmet_var_name,
        gridmet_years,
    )
except ModuleNotFoundError:  # pragma: no cover - exercised when run as a file path
    from fire_vase_build_climate_tables import (
        GRIDMET_OUTPUTS,
        convert_gridmet,
        gridmet_var_name,
        gridmet_years,
    )


DEFAULT_GRIDMET_VARIABLES = ["tmmx", "tmmn", "vpd", "vs"]
ZONE_ACTIVE = "active_burned_area"
ZONE_CUMULATIVE = "cumulative_burned_area"
ZONE_EXTENSION = "perimeter_extension"


@dataclass(frozen=True)
class GridmetArray:
    variable: str
    year: int
    data: xr.DataArray
    lat: np.ndarray
    lon: np.ndarray
    time_index: pd.DatetimeIndex


def read_config(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def variable_codes(config: dict[str, Any], *, include_optional: bool, variables: list[str] | None) -> list[str]:
    if variables:
        codes = variables
    else:
        climate_cfg = config.get("climate", {})
        configured = list(climate_cfg.get("variables", {}).values()) or DEFAULT_GRIDMET_VARIABLES
        optional = list(climate_cfg.get("optional_variables", {}).values()) if include_optional else []
        codes = [*configured, *optional]
    seen: set[str] = set()
    normalized: list[str] = []
    for code in codes:
        if code not in GRIDMET_OUTPUTS:
            raise ValueError(f"Unsupported gridMET variable {code!r}. Known variables: {sorted(GRIDMET_OUTPUTS)}")
        if code not in seen:
            normalized.append(code)
            seen.add(code)
    return normalized


def read_daily_geometry(daily_gpkg: Path, *, max_fires: int | None = None) -> gpd.GeoDataFrame:
    columns = ["id", "date", "event_day", "event_dur", "dy_ar_km2", "tot_ar_km2", "geometry"]
    daily = gpd.read_file(daily_gpkg, columns=columns)
    daily["date"] = pd.to_datetime(daily["date"]).dt.normalize()
    daily["fire_id"] = daily["id"].astype(str)
    daily = daily.sort_values(["fire_id", "date", "event_day"]).reset_index(drop=True)
    if max_fires is not None:
        keep = daily[["fire_id"]].drop_duplicates().head(max_fires)["fire_id"]
        daily = daily[daily["fire_id"].isin(keep)].copy()
    if daily.crs is None:
        raise ValueError(f"{daily_gpkg} has no CRS; cannot build metric perimeter buffers.")
    return daily


def clean_geometry(geometry: BaseGeometry | None) -> BaseGeometry | None:
    if geometry is None or geometry.is_empty:
        return None
    if not geometry.is_valid:
        geometry = shapely.make_valid(geometry)
    if geometry.is_empty:
        return None
    return geometry


def km2(geometry: BaseGeometry | None) -> float:
    if geometry is None or geometry.is_empty:
        return 0.0
    return float(geometry.area) / 1_000_000.0


def exposure_geometries(
    daily: gpd.GeoDataFrame,
    *,
    extension_distances_m: list[float],
) -> Iterator[dict[str, Any]]:
    """Yield active, cumulative, and exterior extension geometries per fire-day."""

    for fire_id, group in daily.groupby("fire_id", sort=True):
        cumulative: BaseGeometry | None = None
        for slice_index, (_, row) in enumerate(group.iterrows()):
            active = clean_geometry(row.geometry)
            if active is not None:
                cumulative = active if cumulative is None else clean_geometry(shapely.union_all([cumulative, active]))
            timestamp = pd.to_datetime(row["date"]).normalize()
            common = {
                "fire_id": str(fire_id),
                "slice_index": int(slice_index),
                "timestamp": timestamp,
                "year": int(timestamp.year),
                "event_day": int(row["event_day"]),
                "event_duration_days": int(row["event_dur"]),
                "ring_area_km2": float(row["dy_ar_km2"]) if pd.notna(row["dy_ar_km2"]) else math.nan,
                "cumulative_area_km2": float(row["tot_ar_km2"]) if pd.notna(row["tot_ar_km2"]) else math.nan,
            }
            if active is not None:
                yield {
                    **common,
                    "exposure_zone": ZONE_ACTIVE,
                    "extension_distance_m": 0.0,
                    "exposure_area_km2": km2(active),
                    "geometry": active,
                }
            if cumulative is not None:
                yield {
                    **common,
                    "exposure_zone": ZONE_CUMULATIVE,
                    "extension_distance_m": 0.0,
                    "exposure_area_km2": km2(cumulative),
                    "geometry": cumulative,
                }
                for distance_m in extension_distances_m:
                    extension = clean_geometry(cumulative.buffer(float(distance_m)).difference(cumulative))
                    if extension is not None:
                        yield {
                            **common,
                            "exposure_zone": ZONE_EXTENSION,
                            "extension_distance_m": float(distance_m),
                            "exposure_area_km2": km2(extension),
                            "geometry": extension,
                        }


def open_gridmet_array(gridmet_cache: Path, variable: str, year: int) -> GridmetArray | None:
    path = gridmet_cache / f"{variable}_{year}.nc"
    if not path.exists():
        return None
    ds = xr.open_dataset(path, chunks={})
    if "day" in ds.dims:
        ds = ds.rename({"day": "time"})
    data = ds[gridmet_var_name(ds, variable)].sortby("time")
    return GridmetArray(
        variable=variable,
        year=year,
        data=data,
        lat=data["lat"].to_numpy().astype(float),
        lon=data["lon"].to_numpy().astype(float),
        time_index=pd.DatetimeIndex(pd.to_datetime(data["time"].to_numpy()).normalize()),
    )


def grid_spacing(values: np.ndarray) -> float:
    if len(values) < 2:
        return 0.0
    diffs = np.diff(np.sort(values.astype(float)))
    diffs = diffs[np.isfinite(diffs) & (diffs > 0)]
    return float(np.median(diffs)) if len(diffs) else 0.0


def cell_mask_for_geometry(
    geometry_4326: BaseGeometry,
    *,
    lat: np.ndarray,
    lon: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, str]:
    lon_pad = grid_spacing(lon)
    lat_pad = grid_spacing(lat)
    min_lon, min_lat, max_lon, max_lat = geometry_4326.bounds
    lon_idx = np.flatnonzero((lon >= min_lon - lon_pad) & (lon <= max_lon + lon_pad))
    lat_idx = np.flatnonzero((lat >= min_lat - lat_pad) & (lat <= max_lat + lat_pad))
    if len(lon_idx) == 0 or len(lat_idx) == 0:
        return lat_idx, lon_idx, np.zeros((0, 0), dtype=bool), "outside_grid"

    lon_grid, lat_grid = np.meshgrid(lon[lon_idx], lat[lat_idx])
    mask = shapely.contains_xy(geometry_4326, lon_grid, lat_grid)
    if np.any(mask):
        return lat_idx, lon_idx, mask, "grid_cells_inside_zone"

    representative = geometry_4326.representative_point()
    nearest_lat = int(np.abs(lat - representative.y).argmin())
    nearest_lon = int(np.abs(lon - representative.x).argmin())
    return (
        np.array([nearest_lat], dtype=int),
        np.array([nearest_lon], dtype=int),
        np.ones((1, 1), dtype=bool),
        "fallback_nearest_cell_to_zone",
    )


def summarize_values(values: np.ndarray) -> dict[str, float]:
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    if values.size == 0:
        return {"mean": math.nan, "minimum": math.nan, "maximum": math.nan, "std": math.nan}
    return {
        "mean": float(np.nanmean(values)),
        "minimum": float(np.nanmin(values)),
        "maximum": float(np.nanmax(values)),
        "std": float(np.nanstd(values)),
    }


def extract_zone_variable(
    gridmet: GridmetArray,
    geometry_4326: BaseGeometry,
    timestamp: pd.Timestamp,
) -> tuple[dict[str, float], int, str]:
    if timestamp not in gridmet.time_index:
        return summarize_values(np.array([], dtype=float)), 0, "date_not_in_gridmet_file"
    time_index = int(gridmet.time_index.get_loc(timestamp))
    lat_idx, lon_idx, mask, sample_method = cell_mask_for_geometry(
        geometry_4326,
        lat=gridmet.lat,
        lon=gridmet.lon,
    )
    if mask.size == 0 or len(lat_idx) == 0 or len(lon_idx) == 0:
        return summarize_values(np.array([], dtype=float)), 0, sample_method
    subset = gridmet.data.isel(time=time_index, lat=lat_idx, lon=lon_idx).compute().to_numpy()
    values = convert_gridmet(gridmet.variable, np.asarray(subset)[mask])
    return summarize_values(values), int(np.isfinite(values).sum()), sample_method


def build_perimeter_exposure_table(
    daily: gpd.GeoDataFrame,
    *,
    gridmet_cache: Path,
    variables: list[str],
    extension_distances_m: list[float],
    wind_present_threshold_m_s: float,
    climate_version: str,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    geometries_native = list(exposure_geometries(daily, extension_distances_m=extension_distances_m))
    geometry_4326 = gpd.GeoSeries(
        [row["geometry"] for row in geometries_native],
        crs=daily.crs,
    ).to_crs("EPSG:4326")
    arrays: dict[tuple[str, int], GridmetArray | None] = {}
    records: list[dict[str, Any]] = []
    missing_files: set[str] = set()
    cached_years = gridmet_years(gridmet_cache)

    for native, projected_geometry in zip(geometries_native, geometry_4326, strict=True):
        timestamp = pd.to_datetime(native["timestamp"]).normalize()
        base = {
            key: value
            for key, value in native.items()
            if key != "geometry"
        }
        base["timestamp"] = timestamp.strftime("%Y-%m-%d")
        base["climate_source"] = "gridmet"
        base["climate_temporal_resolution"] = "daily"
        base["climate_extraction_method"] = "gridmet_gridcell_zone_summary"
        base["climate_version"] = climate_version
        base["climate_variables"] = ",".join(variables)
        base["sample_cell_count"] = 0
        sample_methods: set[str] = set()
        available = True
        for variable in variables:
            output = GRIDMET_OUTPUTS[variable]
            array_key = (variable, int(native["year"]))
            if array_key not in arrays:
                arrays[array_key] = open_gridmet_array(gridmet_cache, variable, int(native["year"]))
            gridmet = arrays[array_key]
            if gridmet is None:
                missing_files.add(f"{variable}_{int(native['year'])}.nc")
                stats = summarize_values(np.array([], dtype=float))
                cells = 0
                sample_method = "gridmet_file_missing"
            else:
                stats, cells, sample_method = extract_zone_variable(
                    gridmet,
                    projected_geometry,
                    timestamp,
                )
            base["sample_cell_count"] = max(int(base["sample_cell_count"]), cells)
            sample_methods.add(sample_method)
            for stat_name, value in stats.items():
                base[f"{output}_{stat_name}"] = value
            available = available and np.isfinite(stats["mean"])
        wind_mean = base.get("wind_speed_m_s_mean", math.nan)
        base["wind_present"] = bool(np.isfinite(wind_mean) and wind_mean > wind_present_threshold_m_s)
        base["climate_available"] = bool(available)
        base["climate_sample_method"] = ",".join(sorted(sample_methods))
        if available:
            base["climate_failure_reason"] = None
        elif any(method == "gridmet_file_missing" for method in sample_methods):
            base["climate_failure_reason"] = "gridmet_file_missing"
        else:
            base["climate_failure_reason"] = "outside_gridmet_coverage_or_missing_value"
        records.append(base)

    report = {
        "cached_gridmet_years": cached_years,
        "missing_gridmet_files": sorted(missing_files),
        "requested_variables": variables,
        "extension_distances_m": extension_distances_m,
    }
    return pd.DataFrame(records), report


def run(args: argparse.Namespace) -> dict[str, Any]:
    started = time.perf_counter()
    config = read_config(args.config)
    climate_cfg = config.get("climate", {})
    perimeter_cfg = climate_cfg.get("perimeter_exposure", {})
    variables = variable_codes(config, include_optional=args.include_optional_variables, variables=args.variables)
    extension_distances_m = [
        float(value)
        for value in (args.extension_distances_m or perimeter_cfg.get("extension_distances_m", [5000, 10000, 25000]))
    ]
    wind_threshold = float(climate_cfg.get("wind_present_threshold_m_s", 0.1))
    climate_version = config.get("versions", {}).get("perimeter_climate", "gridmet-daily-perimeter-v0")
    daily = read_daily_geometry(args.daily_gpkg, max_fires=args.max_fires)
    table, extraction_report = build_perimeter_exposure_table(
        daily,
        gridmet_cache=args.gridmet_cache,
        variables=variables,
        extension_distances_m=extension_distances_m,
        wind_present_threshold_m_s=wind_threshold,
        climate_version=climate_version,
    )
    args.table_root.mkdir(parents=True, exist_ok=True)
    output_path = args.table_root / "vase_climate_exposures.parquet"
    table.to_parquet(output_path, index=False)
    report = {
        "run_id": f"perimeter-climate-{datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(':', '')}",
        "daily_gpkg": args.daily_gpkg.as_posix(),
        "gridmet_cache": args.gridmet_cache.as_posix(),
        "output": output_path.as_posix(),
        "max_fires": args.max_fires,
        "fire_count": int(table["fire_id"].nunique()) if not table.empty else 0,
        "exposure_rows": int(len(table)),
        "climate_available_rows": int(table["climate_available"].sum()) if not table.empty else 0,
        "fallback_nearest_cell_rows": int(
            table["climate_sample_method"].str.contains("fallback_nearest_cell_to_zone", na=False).sum()
        ) if not table.empty else 0,
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        **extraction_report,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("config/fire_vase_pipeline.yml"))
    parser.add_argument("--daily-gpkg", type=Path, default=Path("artifacts/fire-vase-gridmet-real/fired-cache/fired_conus-ak_daily_nov2001-march2021.gpkg"))
    parser.add_argument("--gridmet-cache", type=Path, default=Path("artifacts/fire-vase-gridmet-real/gridmet-cache"))
    parser.add_argument("--table-root", type=Path, default=Path("scratch/fire_vase_run_full/tables"))
    parser.add_argument("--report", type=Path, default=Path("scratch/fire_vase_run_full/perimeter_climate_build_report.json"))
    parser.add_argument("--variables", nargs="+", default=None)
    parser.add_argument("--include-optional-variables", action="store_true")
    parser.add_argument("--extension-distances-m", nargs="+", type=float, default=None)
    parser.add_argument("--max-fires", type=int, default=None)
    args = parser.parse_args()
    run(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
