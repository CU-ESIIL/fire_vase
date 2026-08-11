#!/usr/bin/env python3
"""Populate fire VASE slice tables with cached real gridMET climate.

This builds a durable lakehouse table instead of sampling climate ad hoc inside
reports. It uses the currently cached daily gridMET NetCDF files, so only years
present in the gridMET cache are marked climate-complete.
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import geopandas as gpd
import numpy as np
import pandas as pd
import xarray as xr
import yaml

from cubedynamics.fire_vase_lakehouse.cache import climate_key, vase_key


GRIDMET_OUTPUTS = {
    "tmmx": "maximum_temperature_c",
    "tmmn": "minimum_temperature_c",
    "vpd": "vpd_kpa",
    "vs": "wind_speed_m_s",
    "pr": "precipitation_mm",
    "rmax": "maximum_relative_humidity_pct",
    "rmin": "minimum_relative_humidity_pct",
    "sph": "specific_humidity_kg_kg",
    "fm100": "fuel_moisture_100hr_pct",
    "fm1000": "fuel_moisture_1000hr_pct",
    "erc": "energy_release_component",
    "bi": "burning_index",
    "etr": "reference_evapotranspiration_mm",
    "pet": "potential_evapotranspiration_mm",
    "srad": "solar_radiation_w_m2",
}


def read_config(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def variable_codes(config: dict[str, Any], *, include_optional: bool, variables: list[str] | None) -> list[str]:
    if variables:
        codes = variables
    else:
        climate_cfg = config.get("climate", {})
        configured = list(climate_cfg.get("variables", {}).values()) or list(GRIDMET_OUTPUTS)
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


def gridmet_years(gridmet_cache: Path) -> list[int]:
    years = {
        int(path.stem.split("_")[-1])
        for path in gridmet_cache.glob("*.nc")
        if path.stem.split("_")[-1].isdigit()
    }
    return sorted(years)


def read_events(events_gpkg: Path) -> pd.DataFrame:
    events = gpd.read_file(events_gpkg)
    projected = events.to_crs("EPSG:5070").geometry.centroid
    centroids = projected.to_crs("EPSG:4326")
    events = pd.DataFrame(events.drop(columns="geometry"))
    events["centroid_lon"] = centroids.x
    events["centroid_lat"] = centroids.y
    for col in ("ig_date", "last_date"):
        events[col] = pd.to_datetime(events[col])
    return events


def read_daily(daily_gpkg: Path) -> pd.DataFrame:
    columns = ["id", "date", "event_day", "event_dur", "dy_ar_km2", "tot_ar_km2"]
    daily = gpd.read_file(daily_gpkg, columns=columns, ignore_geometry=True)
    daily = pd.DataFrame(daily)
    daily["date"] = pd.to_datetime(daily["date"]).dt.normalize()
    return daily.sort_values(["id", "date", "event_day"]).reset_index(drop=True)


def normalize_daily(events: pd.DataFrame, daily: pd.DataFrame, cached_years: list[int]) -> tuple[pd.DataFrame, pd.DataFrame]:
    event_cols = ["id", "ig_date", "last_date", "centroid_lon", "centroid_lat"]
    merged = daily.merge(events[event_cols], on="id", how="inner")
    merged["year"] = merged["date"].dt.year.astype(int)
    merged["fire_id"] = merged["id"].astype(str)
    merged["slice_index"] = merged.groupby("fire_id").cumcount().astype(int)
    merged["ring_area_km2"] = merged["dy_ar_km2"].fillna(0).clip(lower=0)
    merged["cumulative_area_km2"] = merged.groupby("fire_id")["ring_area_km2"].cumsum()
    final = merged.groupby("fire_id")["cumulative_area_km2"].transform("max").replace(0, np.nan)
    merged["normalized_vase_width"] = np.sqrt(merged["cumulative_area_km2"] / final).fillna(0.0)
    supported = merged[merged["year"].isin(cached_years)].copy()
    unsupported = merged[~merged["year"].isin(cached_years)].copy()
    return supported, unsupported


def gridmet_var_name(ds: xr.Dataset, variable: str) -> str:
    if variable in ds.data_vars:
        return variable
    if len(ds.data_vars) == 1:
        return next(iter(ds.data_vars))
    candidates = {
        "tmmx": ("air_temperature", "maximum_temperature"),
        "tmmn": ("air_temperature", "minimum_temperature"),
        "vpd": ("mean_vapor_pressure_deficit", "vapor_pressure_deficit"),
        "vs": ("wind_speed",),
        "pr": ("precipitation",),
        "rmax": ("maximum_relative_humidity", "relative_humidity"),
        "rmin": ("minimum_relative_humidity", "relative_humidity"),
        "sph": ("specific_humidity",),
        "fm100": ("100-hour_dead_fuel_moisture", "fuel_moisture"),
        "fm1000": ("1000-hour_dead_fuel_moisture", "fuel_moisture"),
        "erc": ("energy_release_component",),
        "bi": ("burning_index",),
        "etr": ("reference_evapotranspiration",),
        "pet": ("potential_evapotranspiration",),
        "srad": ("surface_downwelling_shortwave_flux", "solar_radiation"),
    }
    wanted = candidates.get(variable, ())
    for name, da in ds.data_vars.items():
        haystack = " ".join([name, *(str(v) for v in da.attrs.values())]).lower()
        if any(token in haystack for token in wanted):
            return name
    raise KeyError(f"Could not identify {variable!r} in {list(ds.data_vars)}")


def convert_gridmet(variable: str, values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    if variable in {"tmmx", "tmmn"}:
        return values - 273.15
    return values


def extract_variable_for_year(frame: pd.DataFrame, gridmet_cache: Path, variable: str, year: int) -> np.ndarray:
    path = gridmet_cache / f"{variable}_{year}.nc"
    if not path.exists():
        return np.full(len(frame), np.nan, dtype=float)
    ds = xr.open_dataset(path, chunks={})
    if "day" in ds.dims:
        ds = ds.rename({"day": "time"})
    da = ds[gridmet_var_name(ds, variable)].sortby("time")
    times = xr.DataArray(pd.DatetimeIndex(frame["date"]).to_numpy(), dims="points")
    lats = xr.DataArray(frame["centroid_lat"].to_numpy(float), dims="points")
    lons = xr.DataArray(frame["centroid_lon"].to_numpy(float), dims="points")
    values = da.sel(time=times, lat=lats, lon=lons, method="nearest").compute().values
    return convert_gridmet(variable, values)


def attach_climate(frame: pd.DataFrame, gridmet_cache: Path, variables: list[str]) -> pd.DataFrame:
    out = frame.copy()
    for output in GRIDMET_OUTPUTS.values():
        out[output] = np.nan
    for year, year_frame in out.groupby("year", sort=True):
        idx = year_frame.index
        for variable in variables:
            output_name = GRIDMET_OUTPUTS[variable]
            out.loc[idx, output_name] = extract_variable_for_year(year_frame, gridmet_cache, variable, int(year))
    out["wind_present"] = out["wind_speed_m_s"] > 0.1
    climate_cols = [GRIDMET_OUTPUTS[variable] for variable in variables]
    out["climate_available"] = out[climate_cols].notna().all(axis=1)
    out["climate_failure_reason"] = np.where(
        out["climate_available"],
        None,
        "outside_gridmet_coverage_or_missing_value",
    )
    return out


def add_keys(frame: pd.DataFrame, catalog: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    out = frame.copy()
    catalog = catalog.copy()
    catalog["fire_id"] = catalog["fire_id"].astype(str)
    key_cols = ["fire_id", "geometry_cache_key", "climate_cache_key", "vase_cache_key"]
    out = out.merge(catalog[key_cols], on="fire_id", how="left")
    versions = config.get("versions", {})
    climate_cfg = config.get("climate", {})
    missing = out["climate_cache_key"].isna()
    if missing.any():
        out.loc[missing, "climate_cache_key"] = [
            climate_key(
                fire_id,
                geometry_cache_key=geometry or f"geometry:unknown-{fire_id}",
                climate_source=climate_cfg.get("source", "gridmet"),
                variables=list(climate_cfg.get("variables", {}).values()) or list(GRIDMET_OUTPUTS),
                temporal_resolution=climate_cfg.get("temporal_resolution", "daily"),
                climate_version=versions.get("climate", "gridmet-daily-centroid-v0"),
            )
            for fire_id, geometry in zip(out.loc[missing, "fire_id"], out.loc[missing, "geometry_cache_key"])
        ]
    missing_vase = out["vase_cache_key"].isna()
    if missing_vase.any():
        out.loc[missing_vase, "vase_cache_key"] = [
            vase_key(
                fire_id,
                geometry_cache_key=geometry or f"geometry:unknown-{fire_id}",
                climate_cache_key=clim,
                vase_version=versions.get("vase", "vase-ring-v0"),
                parameters={"temporal_resolution": climate_cfg.get("temporal_resolution", "daily")},
            )
            for fire_id, geometry, clim in zip(
                out.loc[missing_vase, "fire_id"],
                out.loc[missing_vase, "geometry_cache_key"],
                out.loc[missing_vase, "climate_cache_key"],
            )
        ]
    out["vase_version"] = versions.get("vase", "vase-ring-v0")
    out["climate_source"] = climate_cfg.get("source", "gridmet")
    out["climate_temporal_resolution"] = climate_cfg.get("temporal_resolution", "daily")
    out["climate_extraction_method"] = climate_cfg.get("extraction_method", "event_centroid_nearest_grid_cell")
    return out


def build_manifest_tables(
    manifest: pd.DataFrame,
    complete_fire_ids: set[str],
    unsupported_fire_ids: set[str],
    incomplete_cached_fire_ids: set[str],
    run_id: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    manifest = manifest.copy()
    manifest["fire_id"] = manifest["fire_id"].astype(str)
    processed = manifest[manifest["fire_id"].isin(complete_fire_ids)].copy()
    processed["status"] = "climate_complete"
    processed["run_id"] = run_id
    processed["updated_at"] = now
    failure_rows = [
        {
            "run_id": run_id,
            "fire_id": fire_id,
            "failed_at": now,
            "stage": "climate",
            "message": "No cached gridMET daily file for one or more fire slice years.",
            "retryable": True,
            "context": {"missing_reason": "climate_year_not_cached"},
        }
        for fire_id in sorted(unsupported_fire_ids)
    ]
    failure_rows.extend(
        {
            "run_id": run_id,
            "fire_id": fire_id,
            "failed_at": now,
            "stage": "climate",
            "message": "Cached gridMET extraction returned missing values for one or more fire slices.",
            "retryable": True,
            "context": {"missing_reason": "outside_gridmet_coverage_or_missing_value"},
        }
        for fire_id in sorted(incomplete_cached_fire_ids)
    )
    failures = pd.DataFrame(failure_rows)
    return processed, failures


def write_outputs(
    slices: pd.DataFrame,
    manifest: pd.DataFrame,
    failures: pd.DataFrame,
    table_root: Path,
) -> dict[str, str]:
    table_root.mkdir(parents=True, exist_ok=True)
    slices_path = table_root / "vase_slices.parquet"
    manifest_path = table_root / "processing_manifest_climate.parquet"
    failures_path = table_root / "processing_failures_climate.parquet"
    slices.to_parquet(slices_path, index=False)
    manifest.to_parquet(manifest_path, index=False)
    failures.to_parquet(failures_path, index=False)
    return {
        "vase_slices": slices_path.as_posix(),
        "processing_manifest_climate": manifest_path.as_posix(),
        "processing_failures_climate": failures_path.as_posix(),
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    started = time.perf_counter()
    config = read_config(args.config)
    cached_years = gridmet_years(args.gridmet_cache)
    variables = variable_codes(config, include_optional=args.include_optional_variables, variables=args.variables)
    run_id = f"climate-{datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(':', '')}"

    events = read_events(args.events_gpkg)
    daily = read_daily(args.daily_gpkg)
    supported, unsupported = normalize_daily(events, daily, cached_years)
    if args.max_slices is not None:
        keep_fire_ids = supported[["fire_id"]].drop_duplicates().head(args.max_slices)["fire_id"].tolist()
        supported = supported[supported["fire_id"].isin(keep_fire_ids)].copy()
    supported = attach_climate(supported, args.gridmet_cache, variables)

    catalog = pd.read_parquet(args.table_root / "fire_catalog.parquet")
    manifest = pd.read_parquet(args.table_root / "processing_manifest.parquet")
    supported = add_keys(supported, catalog, config)
    climate_value_cols = [GRIDMET_OUTPUTS[variable] for variable in variables]
    selected_cols = [
        "fire_id",
        "slice_index",
        "date",
        "year",
        "vase_version",
        "vase_cache_key",
        "geometry_cache_key",
        "climate_cache_key",
        "climate_source",
        "climate_temporal_resolution",
        "climate_extraction_method",
        "ring_area_km2",
        "cumulative_area_km2",
        "normalized_vase_width",
        *climate_value_cols,
        "wind_present",
        "climate_available",
        "climate_failure_reason",
    ]
    slices = supported[selected_cols].rename(columns={"date": "timestamp"})
    slices["timestamp"] = pd.to_datetime(slices["timestamp"]).dt.strftime("%Y-%m-%d")
    availability = slices.groupby("fire_id")["climate_available"].all()
    complete_fire_ids = set(availability[availability].index.astype(str))
    incomplete_cached_fire_ids = set(availability[~availability].index.astype(str))
    unsupported_fire_ids = set(unsupported["fire_id"].astype(str)).difference(complete_fire_ids).difference(incomplete_cached_fire_ids)
    climate_manifest, failures = build_manifest_tables(
        manifest,
        complete_fire_ids,
        unsupported_fire_ids,
        incomplete_cached_fire_ids,
        run_id,
    )
    outputs = write_outputs(slices, climate_manifest, failures, args.table_root)
    report = {
        "run_id": run_id,
        "cached_gridmet_years": cached_years,
        "climate_variables": variables,
        "vase_slice_rows": int(len(slices)),
        "climate_complete_fires": int(len(complete_fire_ids)),
        "climate_incomplete_cached_fires": int(len(incomplete_cached_fire_ids)),
        "climate_not_cached_fires": int(len(unsupported_fire_ids)),
        "outputs": outputs,
        "elapsed_seconds": round(time.perf_counter() - started, 3),
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("config/fire_vase_pipeline.yml"))
    parser.add_argument("--daily-gpkg", type=Path, default=Path("artifacts/fire-vase-gridmet-real/fired-cache/fired_conus-ak_daily_nov2001-march2021.gpkg"))
    parser.add_argument("--events-gpkg", type=Path, default=Path("artifacts/fire-vase-gridmet-real/fired-cache/fired_conus-ak_events_nov2001-march2021.gpkg"))
    parser.add_argument("--gridmet-cache", type=Path, default=Path("artifacts/fire-vase-gridmet-real/gridmet-cache"))
    parser.add_argument("--table-root", type=Path, default=Path("scratch/fire_vase_run_full/tables"))
    parser.add_argument("--report", type=Path, default=Path("scratch/fire_vase_run_full/climate_build_report.json"))
    parser.add_argument("--max-slices", type=int, default=None)
    parser.add_argument("--variables", nargs="+", default=None)
    parser.add_argument("--include-optional-variables", action="store_true")
    args = parser.parse_args()
    report = run(args)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
