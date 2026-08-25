"""Read small, real FIRED and GridMET samples from the packaged data lake."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import geopandas as gpd
import numpy as np
import pandas as pd
import xarray as xr

from cubedynamics.fire_time_hull import FireEventDaily

from .core import ValidationPaths


GRIDMET_VALUE_NAMES = {
    "tmmx": "maximum_temperature_c",
    "tmmn": "minimum_temperature_c",
    "vpd": "vpd_kpa",
    "vs": "wind_speed_m_s",
}


def _read_where(path: Path, fire_id: int | str) -> gpd.GeoDataFrame:
    """Read one event through the GeoPackage SQL filter when supported."""

    where = f'"id" = {int(fire_id)}'
    try:
        return gpd.read_file(path, where=where)
    except Exception:
        frame = gpd.read_file(path)
        return frame[frame["id"].astype(str) == str(fire_id)].copy()


def load_fired_daily(paths: ValidationPaths, fire_id: int | str) -> gpd.GeoDataFrame:
    frame = _read_where(paths.fired_daily, fire_id)
    if frame.empty:
        raise ValueError(f"FIRED daily data do not contain fire_id={fire_id!r}")
    frame["date"] = pd.to_datetime(frame["date"]).dt.normalize()
    return frame.sort_values(["date", "event_day"]).reset_index(drop=True)


def load_fired_event_row(paths: ValidationPaths, fire_id: int | str) -> gpd.GeoDataFrame:
    frame = _read_where(paths.fired_events, fire_id)
    if frame.empty:
        raise ValueError(f"FIRED events data do not contain fire_id={fire_id!r}")
    return frame.reset_index(drop=True)


def load_event(paths: ValidationPaths, fire_id: int | str) -> FireEventDaily:
    return FireEventDaily.from_fired(load_fired_daily(paths, fire_id), int(fire_id), date_col="date")


def gridmet_variable_name(ds: xr.Dataset, variable: str) -> str:
    """Resolve a GridMET short code to the NetCDF data variable."""

    if variable in ds.data_vars:
        return variable
    if len(ds.data_vars) == 1:
        return next(iter(ds.data_vars))
    for name, da in ds.data_vars.items():
        attrs = " ".join(str(value) for value in da.attrs.values()).lower()
        if variable.lower() in f"{name.lower()} {attrs}":
            return name
    raise KeyError(f"Could not identify GridMET variable {variable!r} in {list(ds.data_vars)}")


def axis_slice(coord: Iterable[float], low: float, high: float) -> slice:
    values = np.asarray(coord, dtype=float)
    lo, hi = sorted((float(low), float(high)))
    return slice(hi, lo) if values[0] > values[-1] else slice(lo, hi)


def open_gridmet_subset(
    paths: ValidationPaths,
    *,
    variable: str,
    year: int,
    start: str | pd.Timestamp,
    end: str | pd.Timestamp,
    bounds: tuple[float, float, float, float],
    chunks: dict[str, int] | None = None,
) -> xr.DataArray:
    """Open a lazy subset of one cached annual GridMET file."""

    path = paths.gridmet_cache / f"{variable}_{year}.nc"
    if not path.exists():
        raise FileNotFoundError(path)
    ds = xr.open_dataset(path, chunks=chunks if chunks is not None else {})
    time_name = "day" if "day" in ds.dims else "time"
    if time_name == "day":
        ds = ds.rename({"day": "time"})
    name = gridmet_variable_name(ds, variable)
    min_lon, min_lat, max_lon, max_lat = bounds
    da = ds[name].sel(
        time=slice(pd.Timestamp(start), pd.Timestamp(end)),
        lat=axis_slice(ds["lat"].values, min_lat, max_lat),
        lon=axis_slice(ds["lon"].values, min_lon, max_lon),
    )
    da = da.rename(variable).assign_attrs(
        {
            **da.attrs,
            "epsg": 4326,
            "source": "gridmet_cached_annual_netcdf",
            "source_path": path.as_posix(),
        }
    )
    return da


def event_bounds(event: FireEventDaily, *, pad_degrees: float = 0.12) -> tuple[float, float, float, float]:
    gdf = event.gdf.to_crs(4326)
    minx, miny, maxx, maxy = gdf.total_bounds
    return (
        float(minx - pad_degrees),
        float(miny - pad_degrees),
        float(maxx + pad_degrees),
        float(maxy + pad_degrees),
    )


def event_centroid_wgs84(paths: ValidationPaths, fire_id: int | str) -> tuple[float, float]:
    """Reproduce the lake builder's equal-area event-centroid calculation."""

    event = load_fired_event_row(paths, fire_id)
    centroid = event.to_crs(5070).geometry.centroid
    point = gpd.GeoSeries(centroid, crs=5070).to_crs(4326).iloc[0]
    return float(point.y), float(point.x)


def read_vase_slices(paths: ValidationPaths, fire_id: int | str) -> pd.DataFrame:
    path = paths.table_root / "vase_slices.parquet"
    frame = pd.read_parquet(path, filters=[("fire_id", "==", str(fire_id))])
    if frame.empty:
        raise ValueError(f"vase_slices.parquet does not contain fire_id={fire_id!r}")
    frame["timestamp"] = pd.to_datetime(frame["timestamp"]).dt.normalize()
    return frame.sort_values("timestamp").reset_index(drop=True)
