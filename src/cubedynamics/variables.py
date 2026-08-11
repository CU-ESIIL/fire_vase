"""Semantic variable loaders for common climate and vegetation variables."""

from __future__ import annotations

from datetime import datetime, date
from typing import Any, Mapping, Optional, Sequence, Literal
import warnings

import pandas as pd
import xarray as xr

import cubedynamics as cd
from cubedynamics import pipe, verbs as v
from cubedynamics.data.gridmet import load_gridmet_cube
from cubedynamics.data.prism import load_prism_cube
from cubedynamics.streaming import (
    VirtualCube,
    make_spatial_tiler,
    make_time_tiler,
)
from cubedynamics.sentinel import (
    load_sentinel2_ndvi_cube,
    load_sentinel2_ndvi_zscore_cube,
)


TEMP_SOURCES: dict[str, dict[str, str]] = {
    "gridmet": {
        "mean": "tmmx",
        "min": "tmmn",
        "max": "tmmx",
    },
    "prism": {
        "mean": "tmean",
        "min": "tmin",
        "max": "tmax",
    },
}

STREAMING_SIZE_THRESHOLD = 2.5e6


def estimate_cube_size(
    lat: Optional[float],
    lon: Optional[float],
    bbox: Optional[Sequence[float]],
    aoi_geojson: Optional[Mapping[str, Any]],
    start: Any,
    end: Any,
    source: str,
) -> float:
    """Return a rough scalar size estimate for a requested cube.

    The heuristic multiplies the spatial footprint by the time span in days.
    It intentionally errs on the side of being simple and fast; the goal is to
    decide whether a request should stream rather than to predict byte counts
    exactly.
    """

    start_ts = pd.to_datetime(start) if start is not None else None
    end_ts = pd.to_datetime(end) if end is not None else None
    if start_ts is not None and end_ts is not None:
        days = max((end_ts - start_ts).days, 1)
    else:
        days = 1

    area = 1.0
    if bbox is not None:
        xmin, ymin, xmax, ymax = bbox
        area = max((xmax - xmin) * (ymax - ymin), 1.0)
    elif aoi_geojson is not None:
        # Without geometry computation fall back to a conservative factor.
        area = 2.0
    elif lat is not None and lon is not None:
        area = 1.0

    # A tiny boost for higher resolution sources.
    if source == "prism":
        area *= 1.25

    return float(area * days)


def _resolve_temp_variable(source: str, kind: str) -> str:
    if source not in TEMP_SOURCES:
        raise ValueError(f"Unsupported temperature source '{source}'. Expected one of {sorted(TEMP_SOURCES)}")
    mapping = TEMP_SOURCES[source]
    if kind not in mapping:
        raise ValueError(
            f"Unsupported temperature kind '{kind}' for source '{source}'. Expected one of {sorted(mapping)}"
        )
    return mapping[kind]


def _load_temperature(
    *,
    kind: str,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    bbox: Optional[Sequence[float]] = None,
    aoi_geojson: Optional[Mapping[str, Any]] = None,
    start: Any = None,
    end: Any = None,
    source: Literal["gridmet", "prism"] = "gridmet",
    **kwargs: Any,
) -> xr.DataArray:
    var_name = _resolve_temp_variable(source, kind)
    if source == "gridmet":
        ds = load_gridmet_cube(
            variable=var_name,
            lat=lat,
            lon=lon,
            bbox=bbox,
            aoi_geojson=aoi_geojson,
            start=start,
            end=end,
            **kwargs,
        )
    else:
        ds = load_prism_cube(
            variable=var_name,
            lat=lat,
            lon=lon,
            bbox=bbox,
            aoi_geojson=aoi_geojson,
            start=start,
            end=end,
            **kwargs,
        )

    if isinstance(ds, xr.DataArray):
        da = ds
    else:
        da = ds[var_name]
        da = da.copy()
    da.attrs.setdefault("variable", var_name)
    da.attrs.setdefault("source", source)
    return da


def temperature(
    *,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    bbox: Optional[Sequence[float]] = None,
    aoi_geojson: Optional[Mapping[str, Any]] = None,
    start: Any = None,
    end: Any = None,
    source: Literal["gridmet", "prism"] = "gridmet",
    streaming_strategy: str | None = None,
    time_chunk: str = "AS",
    spatial_tile: float | None = None,
    streaming_threshold: float | None = None,
    **kwargs: Any,
) -> xr.DataArray | VirtualCube:
    """
    Load a mean temperature cube from the chosen climate provider.

    This is a semantic wrapper around ``load_gridmet_cube`` or ``load_prism_cube``.
    It forwards AOI, time, and additional keyword arguments directly to the
    underlying loader.
    """

    strategy = streaming_strategy or "auto"
    size_estimate = estimate_cube_size(lat, lon, bbox, aoi_geojson, start, end, source)
    threshold = streaming_threshold if streaming_threshold is not None else STREAMING_SIZE_THRESHOLD

    def base_loader(**loader_kwargs: Any) -> xr.DataArray:
        return _load_temperature(kind="mean", **loader_kwargs)

    loader_kwargs: dict[str, Any] = {
        "lat": lat,
        "lon": lon,
        "bbox": bbox,
        "aoi_geojson": aoi_geojson,
        "start": start,
        "end": end,
        "source": source,
        **kwargs,
    }

    if strategy == "materialize" or (strategy == "auto" and size_estimate <= threshold):
        return base_loader(**loader_kwargs)

    time_tiler = make_time_tiler(start, end, freq=time_chunk)
    if spatial_tile is None or bbox is None:
        spatial_tiler = lambda kw: ({} for _ in [None])  # type: ignore[misc]
    else:
        spatial_tiler = make_spatial_tiler(bbox, dlon=spatial_tile, dlat=spatial_tile)

    return VirtualCube(
        dims=("time", "y", "x"),
        coords_metadata={
            "start": start,
            "end": end,
            "aoi": {
                "lat": lat,
                "lon": lon,
                "bbox": bbox,
                "aoi_geojson": aoi_geojson,
            },
            "source": source,
        },
        loader=base_loader,
        loader_kwargs=loader_kwargs,
        time_tiler=time_tiler,
        spatial_tiler=spatial_tiler,
    )


def temperature_min(
    *,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    bbox: Optional[Sequence[float]] = None,
    aoi_geojson: Optional[Mapping[str, Any]] = None,
    start: Any = None,
    end: Any = None,
    source: Literal["gridmet", "prism"] = "gridmet",
    **kwargs: Any,
) -> xr.DataArray:
    """Load a minimum daily temperature cube from the selected source."""

    return _load_temperature(
        kind="min",
        lat=lat,
        lon=lon,
        bbox=bbox,
        aoi_geojson=aoi_geojson,
        start=start,
        end=end,
        source=source,
        **kwargs,
    )


def temperature_max(
    *,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    bbox: Optional[Sequence[float]] = None,
    aoi_geojson: Optional[Mapping[str, Any]] = None,
    start: Any = None,
    end: Any = None,
    source: Literal["gridmet", "prism"] = "gridmet",
    **kwargs: Any,
) -> xr.DataArray:
    """Load a maximum daily temperature cube from the selected source."""

    return _load_temperature(
        kind="max",
        lat=lat,
        lon=lon,
        bbox=bbox,
        aoi_geojson=aoi_geojson,
        start=start,
        end=end,
        source=source,
        **kwargs,
    )


def temperature_anomaly(
    *,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    bbox: Optional[Sequence[float]] = None,
    aoi_geojson: Optional[Mapping[str, Any]] = None,
    start: Any = None,
    end: Any = None,
    source: Literal["gridmet", "prism"] = "gridmet",
    kind: Literal["mean", "min", "max"] = "mean",
    baseline: Optional[xr.DataArray] = None,
    baseline_start: Any = None,
    baseline_end: Any = None,
    **kwargs: Any,
) -> xr.DataArray:
    """
    Compute a temperature anomaly cube along the time dimension.

    Uses the semantic temperature loaders and ``verbs.anomaly``.
    """

    if kind == "mean":
        temp_cube = temperature(
            lat=lat,
            lon=lon,
            bbox=bbox,
            aoi_geojson=aoi_geojson,
            start=start,
            end=end,
            source=source,
            **kwargs,
        )
    elif kind == "min":
        temp_cube = temperature_min(
            lat=lat,
            lon=lon,
            bbox=bbox,
            aoi_geojson=aoi_geojson,
            start=start,
            end=end,
            source=source,
            **kwargs,
        )
    elif kind == "max":
        temp_cube = temperature_max(
            lat=lat,
            lon=lon,
            bbox=bbox,
            aoi_geojson=aoi_geojson,
            start=start,
            end=end,
            source=source,
            **kwargs,
        )
    else:
        raise ValueError("Unsupported temperature anomaly kind: {0}".format(kind))

    if baseline is None and baseline_start is None and baseline_end is None:
        return (pipe(temp_cube) | v.anomaly(dim="time")).unwrap()

    baseline_data: xr.DataArray = baseline if baseline is not None else temp_cube
    if baseline_start is not None or baseline_end is not None:
        baseline_data = baseline_data.sel(time=slice(baseline_start, baseline_end))

    baseline_mean = baseline_data.mean(dim="time", skipna=True, keep_attrs=True)
    baseline_mean = baseline_mean.broadcast_like(temp_cube)
    return temp_cube - baseline_mean


def _year_chunks(start: str, end: str, years_per_chunk: int = 1):
    """
    Yield (start_str, end_str) for consecutive chunks of up to years_per_chunk.
    Both start and end are 'YYYY-MM-DD' strings.

    The last chunk is clamped so it never extends beyond the requested `end`.
    """
    start_dt = datetime.fromisoformat(start).date()
    end_dt = datetime.fromisoformat(end).date()

    # Start at the beginning of the start year, but clamp to requested start.
    current = date(start_dt.year, 1, 1)
    if start_dt > current:
        current = start_dt

    while current <= end_dt:
        chunk_end_year = current.year + years_per_chunk - 1
        chunk_end = date(chunk_end_year, 12, 31)
        if chunk_end > end_dt:
            chunk_end = end_dt
        chunk_start = max(current, start_dt)
        yield chunk_start.isoformat(), chunk_end.isoformat()
        # Next chunk starts at Jan 1 of the year after this chunk_end
        current = date(chunk_end.year + 1, 1, 1)


def ndvi_chunked(
    lat: float,
    lon: float,
    start: str,
    end: str,
    years_per_chunk: int = 1,
    drop_bad: bool = True,
    **ndvi_kwargs,
) -> xr.DataArray:
    """
    Load a Sentinel-2 NDVI cube in time chunks and concatenate along 'time'.

    This wraps the existing `cd.ndvi` function and is designed for long
    date ranges that may cause STAC API timeouts if requested in a single
    call. The time interval [start, end] is split into chunks of up to
    `years_per_chunk` calendar years, `cd.ndvi` is called for each chunk,
    and the results are concatenated along the `time` dimension.

    Parameters
    ----------
    lat, lon : float
        Center of the Sentinel-2 query (same semantics as cd.ndvi).
    start, end : str
        Date strings 'YYYY-MM-DD' specifying the full period of interest.
    years_per_chunk : int, default 1
        Maximum number of years per STAC query. Smaller values are safer
        and more robust against remote API timeouts.
    drop_bad : bool, default True
        If True, applies `v.drop_bad_assets()` to each chunk to remove any
        time slices whose assets fail to load (e.g., 403 errors).
    **ndvi_kwargs :
        Additional keyword arguments forwarded to `cd.ndvi` (e.g., edge_size,
        max_cloud, etc.).

    Returns
    -------
    xr.DataArray
        NDVI DataArray concatenated across all chunks, sorted by time.

    Raises
    ------
    RuntimeError
        If no chunks could be loaded (e.g. due to bad dates).
    """
    all_cubes: list[xr.DataArray] = []

    for s_chunk, e_chunk in _year_chunks(start, end, years_per_chunk=years_per_chunk):
        print(f"Loading NDVI chunk: {s_chunk} \u2192 {e_chunk}")
        cube = cd.ndvi(
            lat=lat,
            lon=lon,
            start=s_chunk,
            end=e_chunk,
            **ndvi_kwargs,
        )
        if drop_bad:
            # Use the existing pipe/verbs API; unwrap back to DataArray.
            cube = (pipe(cube) | v.drop_bad_assets()).unwrap()
        all_cubes.append(cube)

    if not all_cubes:
        raise RuntimeError("ndvi_chunked: no chunks loaded – check dates and query area.")

    if len(all_cubes) == 1:
        ndvi = all_cubes[0]
    else:
        ndvi = xr.concat(all_cubes, dim="time").sortby("time")

    return ndvi


def ndvi(
    *,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    bbox: Optional[Sequence[float]] = None,
    aoi_geojson: Optional[Mapping[str, Any]] = None,
    start: Any = None,
    end: Any = None,
    source: Literal["sentinel2"] = "sentinel2",
    as_zscore: bool = False,
    show_progress: bool = True,
    **kwargs: Any,
) -> xr.DataArray:
    """
    Load a Sentinel-2 NDVI cube.

    For now, only Sentinel-2 is supported. The loader returns **raw** NDVI in
    its physical units. Apply :func:`cubedynamics.verbs.zscore` in a downstream
    pipe to standardize the time dimension. ``as_zscore`` is deprecated and
    will be removed in a future release.

    Parameters
    ----------
    show_progress : bool, default True
        Whether to display a progress bar for time-stepped NDVI building when
        available. Progress reporting is a no-op when ``tqdm`` is not
        installed.
    """

    if source != "sentinel2":
        raise ValueError("Only the 'sentinel2' source is supported for NDVI.")

    if as_zscore:
        warnings.warn(
            "`as_zscore` is deprecated. Call v.zscore(dim='time') on the raw NDVI cube instead.",
            DeprecationWarning,
            stacklevel=2,
        )

    ndvi = load_sentinel2_ndvi_cube(
        lat=lat,
        lon=lon,
        start=start,
        end=end,
        bbox=bbox,
        show_progress=show_progress,
        **kwargs,
    )

    if as_zscore:
        ndvi = (pipe(ndvi) | v.zscore(dim="time", keep_dim=True)).unwrap()

    return ndvi


__all__ = [
    "temperature",
    "temperature_min",
    "temperature_max",
    "temperature_anomaly",
    "ndvi_chunked",
    "ndvi",
]
