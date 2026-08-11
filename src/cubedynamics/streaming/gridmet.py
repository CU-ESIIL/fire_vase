"""Streaming helpers for gridMET subsets.

This module participates in the CubeDynamics "grammar-of-cubes" by providing
stream-first data accessors that yield dask-friendly ``xarray`` cubes with
dims ``(time, y, x)``. The functions here are considered advanced utilities
that back the public :mod:`cubedynamics.data.gridmet` loaders.

Canonical API:
- :func:`stream_gridmet_to_cube`
"""

from __future__ import annotations

import io
from typing import Any, Dict, Optional, Sequence

import numpy as np
import requests
import xarray as xr
from xarray.backends.plugins import list_engines

from cubedynamics.progress import progress_bar

GRIDMET_BASE_URL = "https://www.northwestknowledge.net/metdata/data"
_ENGINE_PREFERENCE = ("h5netcdf", "netcdf4", "scipy")
_AVAILABLE_ENGINES = list_engines()


def _axis_slice(coord: Sequence[float], bound_a: float, bound_b: float) -> slice:
    """
    Return a slice that spans ``[bound_a, bound_b]`` regardless of axis order.

    gridMET tiles have a resolution of roughly 1/24th of a degree. When an AOI
    bounding box is smaller than that resolution, its numeric bounds can fall
    entirely between adjacent coordinate centers. To avoid empty selections we
    expand the slice bounds by half the native grid spacing before subsetting.
    """

    values = np.asarray(coord, dtype=float)
    if values.size == 0:
        val = float(min(bound_a, bound_b))
        return slice(val, val)

    lo = float(min(bound_a, bound_b))
    hi = float(max(bound_a, bound_b))

    if values.size > 1:
        diffs = np.diff(values)
        diffs = diffs[np.nonzero(diffs)]
        if diffs.size:
            spacing = float(np.min(np.abs(diffs)))
            span = hi - lo
            if spacing > 0 and span < spacing:
                padding = (spacing - span) / 2.0
                lo -= padding
                hi += padding

    descending = values[0] > values[-1]
    if descending:
        return slice(hi, lo)
    return slice(lo, hi)


def _lat_slice(lat_coord: Sequence[float], south: float, north: float) -> slice:
    """Return a latitude slice that works for ascending or descending axes."""

    return _axis_slice(lat_coord, south, north)


def _lon_slice(lon_coord: Sequence[float], west: float, east: float) -> slice:
    """Return a longitude slice that works for ascending or descending axes."""

    return _axis_slice(lon_coord, west, east)


def _select_stream_engine() -> Optional[str]:
    """Pick the best available xarray engine for streaming gridMET files."""

    for engine in _ENGINE_PREFERENCE:
        if engine in _AVAILABLE_ENGINES:
            return engine
    return None


_STREAM_ENGINE = _select_stream_engine()


def _prepare_stream_target(buf: io.BytesIO, engine: Optional[str]) -> Any:
    """Return an object suitable for xr.open_dataset for the chosen engine."""

    if engine == "netcdf4":
        # The netCDF4 backend cannot consume BytesIO objects directly, but it can
        # read from a ``bytes`` or ``memoryview`` buffer. ``getbuffer`` avoids an
        # extra copy while keeping the in-memory constraint intact.
        return memoryview(buf.getbuffer())

    if engine == "scipy":
        # SciPy prefers plain bytes. ``getvalue`` makes a copy, but we only fall
        # back here when h5netcdf/netCDF4 are unavailable.
        return buf.getvalue()

    # Default to BytesIO for h5netcdf (the validated path) and for any other
    # engines that support file-like objects.
    buf.seek(0)
    return buf


def _bbox_from_geojson(aoi_geojson: Dict) -> Dict[str, float]:
    """
    Compute a simple lat/lon bounding box from a GeoJSON polygon (EPSG:4326).
    Assumes geometry["type"] == "Polygon" and uses the outer ring.
    """
    geom = aoi_geojson.get("geometry", aoi_geojson)
    coords = geom["coordinates"][0]
    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    return {
        "south": float(min(lats)),
        "north": float(max(lats)),
        "west": float(min(lons)),
        "east": float(max(lons)),
    }


def _open_gridmet_year(
    variable: str,
    year: int,
    chunks: Optional[Dict[str, int]] = None,
) -> xr.Dataset:
    """
    Download a single gridMET year fully in memory and open it with the best
    available xarray backend (preferring the validated h5netcdf path).
    """
    url = f"{GRIDMET_BASE_URL}/{variable}_{year}.nc"

    resp = requests.get(url, stream=True, timeout=120)
    resp.raise_for_status()

    buf = io.BytesIO()
    for chunk in resp.iter_content(chunk_size=1024 * 1024):  # 1 MB chunks
        if not chunk:
            break
        buf.write(chunk)
    buf.seek(0)

    open_kwargs = {
        "decode_times": True,
        "chunks": chunks,
    }
    if _STREAM_ENGINE is None:
        raise RuntimeError(
            "No suitable xarray IO engine is available. Install 'h5netcdf' or "
            "'netCDF4' to stream gridMET data."
        )

    open_kwargs["engine"] = _STREAM_ENGINE

    stream_target = _prepare_stream_target(buf, _STREAM_ENGINE)
    ds = xr.open_dataset(stream_target, **open_kwargs)

    # gridMET uses "day" as the time dimension; normalize to "time"
    if "day" in ds.dims:
        ds = ds.rename({"day": "time"})
    if "day" in ds.coords:
        ds = ds.rename({"day": "time"})

    # Some of the lightweight test fixtures use CF-friendly variable names like
    # "precipitation_amount" even when the requested gridMET variable is
    # "pr".  When the dataset exposes exactly one data variable we can safely
    # alias it to the requested variable name so downstream logic can always
    # index ``ds[variable]`` regardless of the source naming convention.
    if variable not in ds.data_vars and len(ds.data_vars) == 1:
        (only_var,) = tuple(ds.data_vars)
        ds = ds.rename({only_var: variable})

    return ds


def stream_gridmet_to_cube(
    aoi_geojson: Dict,
    variable: str,
    start: str,
    end: str,
    freq: str = "D",
    chunks: Optional[Dict[str, int]] = None,
    show_progress: bool = True,
) -> xr.DataArray:
    """Stream a gridMET subset as an ``xarray.DataArray`` cube for a given AOI.

    Parameters
    ----------
    aoi_geojson : dict
        GeoJSON Feature or geometry in EPSG:4326 describing the spatial extent.
    variable : str
        gridMET variable name, e.g. ``"pr"``, ``"tmmx"``, ``"tmmn"``, ``"vs"``,
        ``"erc"``.
    start, end : str
        Inclusive time range in ISO format, e.g. ``"2000-01-01"``.
    freq : str, default "D"
        Output time frequency; passed to ``xarray.resample``.
    chunks : dict, optional
        Dask-style chunk mapping (for example ``{"time": 365}``) applied when
        opening the streamed dataset.
    show_progress : bool, default True
        Whether to render a small progress bar while downloading yearly tiles.

    Returns
    -------
    xarray.DataArray
        Cube with dims ``(time, lat, lon)`` cropped to the AOI and resampled to
        the requested frequency. Coordinates remain in EPSG:4326.

    Notes
    -----
    - Data are streamed year-by-year from the gridMET endpoint without writing
      to disk; chunking is preserved when a suitable backend (h5netcdf/netCDF4)
      is available.
    - The function keeps outputs lazy when ``chunks`` is provided and will only
      materialize small index computations such as resampling.
    - AOIs smaller than the native grid resolution are padded slightly to avoid
      empty selections.

    Examples
    --------
    >>> from cubedynamics.streaming.gridmet import stream_gridmet_to_cube
    >>> cube = stream_gridmet_to_cube(
    ...     aoi_geojson={"type": "Polygon", "coordinates": [[(-105.1, 40.0), (-105.0, 40.0), (-105.0, 40.1), (-105.1, 40.1), (-105.1, 40.0)]]},
    ...     variable="tmmx",
    ...     start="2001-01-01",
    ...     end="2001-01-10",
    ...     chunks={"time": 5},
    ... )
    >>> cube.dims
    ('time', 'lat', 'lon')
    """
    # Parse years from the date strings
    start_year = int(start[:4])
    end_year = int(end[:4])

    # 1) Load all needed years into a list of Datasets
    year_chunks = chunks or {"time": 366}
    ds_list = []
    total_years = end_year - start_year + 1
    with progress_bar(total=total_years if show_progress else None, description="gridMET years") as advance:
        for year in range(start_year, end_year + 1):
            ds_y = _open_gridmet_year(variable, year, chunks=year_chunks)
            ds_list.append(ds_y)
            if show_progress:
                advance(1)

    # 2) Concatenate along the normalized time axis and clip to [start, end]
    ds = xr.concat(ds_list, dim="time")
    ds = ds.sel(time=slice(start, end))

    # 3) Spatial subset using the AOI bbox
    bbox = _bbox_from_geojson(aoi_geojson)
    lat_coord = ds.coords.get("lat")
    if lat_coord is None:
        raise KeyError("gridMET dataset is missing the 'lat' coordinate")
    lon_coord = ds.coords.get("lon")
    if lon_coord is None:
        raise KeyError("gridMET dataset is missing the 'lon' coordinate")

    lat_slice = _lat_slice(lat_coord, bbox["south"], bbox["north"])
    lon_slice = _lon_slice(lon_coord, bbox["west"], bbox["east"])
    da = ds[variable].sel(lat=lat_slice, lon=lon_slice)

    empty_dims = [dim for dim in ("lat", "lon") if da.sizes.get(dim, 0) == 0]
    if empty_dims:
        raise ValueError(
            "gridMET subset is empty along "
            + ", ".join(f"'{dim}'" for dim in empty_dims)
            + ". "
            f"Requested south={bbox['south']}, north={bbox['north']}, "
            f"west={bbox['west']}, east={bbox['east']}"
        )

    # 4) Optional resampling in time (e.g., to monthly)
    if freq != "D":
        da = da.resample(time=freq).mean()

    da.name = variable
    return da


__all__ = ["stream_gridmet_to_cube"]
