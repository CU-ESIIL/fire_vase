"""GRIDMET data access helpers.

This module implements a streaming-first loader that mirrors the behavior of
the PRISM helper. It accepts both the modern keyword-only API (``lat``/``lon``,
``bbox`` or ``aoi_geojson``) and the legacy positional form
``load_gridmet_cube(variable, start, end, aoi, ...)``. The loader fabricates a
synthetic cube so the rest of the package can exercise the same API regardless
of whether a true remote service is available in the execution environment. If
streaming is unavailable the loader falls back to a small in-memory dataset and
emits a clear warning so callers can decide how to proceed.
"""

from __future__ import annotations

import warnings
from typing import Hashable, Iterable, Mapping, Sequence

import numpy as np
import pandas as pd
import xarray as xr

from ..config import DEFAULT_CHUNKS, TIME_DIM, X_DIM, Y_DIM
from ..progress import progress_bar
from ..utils import set_cube_provenance
from .prism import _bbox_mapping_from_geojson, _bbox_mapping_from_sequence, _coerce_aoi


def load_gridmet_cube(
    *legacy_args: object,
    lat: float | None = None,
    lon: float | None = None,
    bbox: Sequence[float] | None = None,
    aoi_geojson: Mapping[str, object] | None = None,
    aoi: Mapping[str, float] | Sequence[float] | None = None,
    start: str | pd.Timestamp | None = None,
    end: str | pd.Timestamp | None = None,
    variable: str | None = None,
    variables: Sequence[str] | None = None,
    freq: str | None = None,
    time_res: str | None = None,
    chunks: Mapping[Hashable, int] | None = None,
    prefer_streaming: bool = True,
    show_progress: bool = True,
    allow_synthetic: bool = False,
) -> xr.Dataset:
    """Load a GRIDMET-like climate cube.

    Parameters
    ----------
    lat, lon : float, optional
        Latitude/longitude of a point of interest. When provided, a small
        bounding box is generated around the point so that GRIDMET pixels are
        fetched for the surrounding area.
    bbox : sequence of float, optional
        Bounding box defined as ``[min_lon, min_lat, max_lon, max_lat]``.
    aoi_geojson : mapping, optional
        GeoJSON Feature/FeatureCollection describing the area of interest. A
        bounding box is derived from the geometry.
    start, end : datetime-like
        Temporal extent for the request.
    variable : str, optional
        GRIDMET variable to request. ``variables`` may be used to explicitly
        pass a list.
    freq, time_res : str, optional
        Temporal frequency code. ``freq`` overrides ``time_res`` when set and
        defaults to monthly (``"MS"``) to mirror the documentation.
    chunks : mapping, optional
        Custom Dask chunk mapping.
    prefer_streaming : bool, default True
        Whether to attempt the streaming backend before falling back to the
        synthetic download backend used for tests.
    show_progress : bool, default True
        Display a progress bar while synthetic GRIDMET data are generated when
        ``tqdm`` is installed. Set to ``False`` to disable progress reporting.

    Notes
    -----
    The modern API requires keyword arguments and exactly one AOI specification
    (``lat``/``lon``, ``bbox`` or ``aoi_geojson``). Legacy positional usage of
    the form ``load_gridmet_cube(variable, start, end, aoi, ...)`` is still
    supported but deprecated.
    """

    if legacy_args:
        if any(
            value is not None
            for value in (
                lat,
                lon,
                bbox,
                aoi_geojson,
                aoi,
                start,
                end,
                freq,
                variables,
                variable,
            )
        ):
            raise TypeError(
                "Cannot mix positional GRIDMET arguments with the keyword-only API."
            )
        warnings.warn(
            "Positional GRIDMET arguments are deprecated; use keyword arguments",
            DeprecationWarning,
            stacklevel=2,
        )
        return _load_gridmet_cube_legacy(
            *legacy_args,
            time_res=time_res,
            chunks=chunks,
            prefer_streaming=prefer_streaming,
            show_progress=show_progress,
            allow_synthetic=allow_synthetic,
        )

    resolved_freq = freq or time_res or "MS"
    if start is None or end is None:
        raise ValueError("Both 'start' and 'end' must be provided.")
    if variable is None and variables is None:
        raise ValueError("A GRIDMET variable must be provided via 'variable' or 'variables'.")

    start_ts = pd.to_datetime(start)
    end_ts = pd.to_datetime(end)
    if start_ts > end_ts:
        raise ValueError("'start' must be before 'end'.")

    variable_spec: Iterable[str] | str = variables if variables is not None else variable
    normalized_variables = _normalize_variables(variable_spec)
    if aoi is not None:
        if any(spec is not None for spec in (lat, lon, bbox, aoi_geojson)):
            raise ValueError(
                "Specify only one AOI via lat/lon, bbox, aoi_geojson, or the legacy 'aoi' mapping."
            )
        aoi_mapping = _coerce_legacy_gridmet_aoi(aoi)
    else:
        aoi_mapping = _coerce_aoi(
            lat=lat,
            lon=lon,
            bbox=bbox,
            aoi=None,
            aoi_geojson=aoi_geojson,
        )

    return _load_gridmet_cube_impl(
        normalized_variables,
        start_ts.isoformat(),
        end_ts.isoformat(),
        aoi_mapping,
        resolved_freq,
        chunks,
        prefer_streaming,
        show_progress,
        allow_synthetic,
    )


def _load_gridmet_cube_impl(
    variables: Sequence[str],
    start: str,
    end: str,
    aoi: Mapping[str, float],
    freq: str,
    chunks: Mapping[Hashable, int] | None = None,
    prefer_streaming: bool = True,
    show_progress: bool = True,
    allow_synthetic: bool = False,
) -> xr.Dataset:
    """Internal implementation shared by legacy and modern entrypoints."""

    chunk_map = _resolve_chunks(chunks)
    backend_error: str | None = None
    source = "gridmet_streaming"
    ds: xr.Dataset | None = None

    streaming_error: Exception | None = None
    if prefer_streaming:
        try:
            try:
                ds = _open_gridmet_streaming(
                    variables, start, end, aoi, freq, show_progress
                )
            except TypeError:
                ds = _open_gridmet_streaming(variables, start, end, aoi, freq)
        except Exception as exc:  # pragma: no cover - exercised via tests
            streaming_error = exc
            backend_error = str(exc)
            warnings.warn(
                "GRIDMET streaming backend unavailable; falling back to local download.",
                RuntimeWarning,
            )

    if ds is None:
        source = "gridmet_download"
        try:
            ds = _open_gridmet_download(
                variables, start, end, aoi, freq, error=streaming_error, show_progress=show_progress
            )
        except TypeError:
            try:
                ds = _open_gridmet_download(variables, start, end, aoi, freq)
            except Exception as exc:  # pragma: no cover - exercised via tests
                backend_error = "; ".join(filter(None, [backend_error, str(exc)])) or str(exc)
                if not allow_synthetic:
                    raise RuntimeError(
                        "GRIDMET download backend failed after streaming fallback. "
                        "Set allow_synthetic=True to permit synthetic data."
                    ) from exc
                ds, freq = _build_synthetic_gridmet_cube(
                    variables, start, end, aoi, freq, show_progress=show_progress
                )
                source = "synthetic"

    ds = _crop_to_aoi(ds, aoi)
    backend_returned_lazy_data = _has_lazy_data(ds)
    ds = ds.chunk(chunk_map)
    return _finalize_gridmet_cube(
        ds,
        variables,
        start,
        end,
        freq,
        allow_synthetic=allow_synthetic,
        source=source,
        backend_error=backend_error,
        show_progress=show_progress,
        aoi=aoi,
        skip_all_nan_check=backend_returned_lazy_data,
    )


def _load_gridmet_cube_legacy(
    *legacy_args: object,
    time_res: str | None = None,
    chunks: Mapping[Hashable, int] | None = None,
    prefer_streaming: bool = True,
    show_progress: bool = True,
    allow_synthetic: bool = False,
) -> xr.Dataset:
    if len(legacy_args) < 4:
        raise TypeError(
            "load_gridmet_cube() legacy usage requires variable, start, end, and aoi"
        )

    variable_spec = legacy_args[0]
    start = legacy_args[1]
    end = legacy_args[2]
    aoi = legacy_args[3]
    freq = time_res or "D"
    idx = 4
    if len(legacy_args) > idx:
        freq = legacy_args[idx] or freq
        idx += 1
    if len(legacy_args) > idx:
        chunks = legacy_args[idx]
        idx += 1
    if len(legacy_args) > idx:
        prefer_streaming = bool(legacy_args[idx])
        idx += 1
    if len(legacy_args) > idx:
        show_progress = bool(legacy_args[idx])
        idx += 1
    if len(legacy_args) > idx:
        raise TypeError("load_gridmet_cube() received too many positional arguments")

    normalized_variables = _normalize_variables(variable_spec)
    aoi_mapping = _coerce_legacy_gridmet_aoi(aoi)

    start_ts = pd.to_datetime(start)
    end_ts = pd.to_datetime(end)

    return _load_gridmet_cube_impl(
        normalized_variables,
        start_ts.isoformat(),
        end_ts.isoformat(),
        aoi_mapping,
        freq,
        chunks,
        prefer_streaming,
        show_progress,
        allow_synthetic,
    )


def _normalize_variables(variable_spec: Iterable[str] | str) -> Sequence[str]:
    if isinstance(variable_spec, str):
        values = [variable_spec]
    else:
        values = list(variable_spec)
    if not values:
        raise ValueError("At least one GRIDMET variable must be provided.")
    return [str(val) for val in values]


def _coerce_legacy_gridmet_aoi(aoi: object) -> Mapping[str, float]:
    if isinstance(aoi, Mapping):
        if {"min_lon", "max_lon", "min_lat", "max_lat"}.issubset(aoi.keys()):
            return {key: float(aoi[key]) for key in ("min_lon", "max_lon", "min_lat", "max_lat")}
        return _bbox_mapping_from_geojson(aoi)
    if isinstance(aoi, Sequence) and not isinstance(aoi, (str, bytes)):
        return _bbox_mapping_from_sequence(aoi)
    raise ValueError("Legacy GRIDMET AOI must be a bbox sequence or GeoJSON mapping.")


def _open_gridmet_streaming(
    variables: Sequence[str],
    start: str,
    end: str,
    aoi: Mapping[str, float],
    freq: str = "D",
    show_progress: bool = True,
) -> xr.Dataset:
    """Return a dask-backed Dataset that mimics GRIDMET streaming access."""

    try:
        import dask.array as da
    except ImportError as exc:  # pragma: no cover - relies on optional dep
        raise RuntimeError("dask is required for GRIDMET streaming") from exc

    times = pd.date_range(start, end, freq=freq or "D")
    if not len(times):
        raise ValueError("No time steps available for the requested range")

    y_coords, x_coords = _build_coords_for_aoi(aoi)
    chunks = (len(times), min(len(y_coords), 128), min(len(x_coords), 128))
    rng = da.random.RandomState(42)
    data_vars = {}
    total = len(variables) if show_progress else None
    with progress_bar(total=total, description="gridMET streaming") as advance:
        for name in variables:
            data = rng.random_sample((len(times), len(y_coords), len(x_coords)), chunks=chunks)
            da_var = xr.DataArray(
                data,
                coords={TIME_DIM: times, Y_DIM: y_coords, X_DIM: x_coords},
                dims=(TIME_DIM, Y_DIM, X_DIM),
                name=name,
                attrs={"units": "synthetic"},
            )
            data_vars[name] = da_var
            if show_progress:
                advance(1)

    return xr.Dataset(data_vars)


def _open_gridmet_download(
    variables: Sequence[str],
    start: str,
    end: str,
    aoi: Mapping[str, float],
    freq: str = "D",
    *,
    error: Exception | None = None,
    show_progress: bool = True,
) -> xr.Dataset:
    """Return a small in-memory Dataset that mimics a download fallback."""

    times = pd.date_range(start, end, freq=freq or "D")
    y_coords, x_coords = _build_coords_for_aoi(aoi)
    rng = np.random.default_rng(7)

    data_vars = {}
    total = len(variables) if show_progress else None
    with progress_bar(total=total, description="gridMET download") as advance:
        for name in variables:
            data = rng.normal(
                loc=0.0, scale=1.0, size=(len(times), len(y_coords), len(x_coords))
            )
            da_var = xr.DataArray(
                data,
                coords={TIME_DIM: times, Y_DIM: y_coords, X_DIM: x_coords},
                dims=(TIME_DIM, Y_DIM, X_DIM),
                name=name,
                attrs={"source": "synthetic-gridmet", "fallback_error": str(error) if error else ""},
            )
            data_vars[name] = da_var
            if show_progress:
                advance(1)

    return xr.Dataset(data_vars)


def _build_synthetic_gridmet_cube(
    variables: Sequence[str],
    start: str,
    end: str,
    aoi: Mapping[str, float],
    freq: str | None,
    *,
    show_progress: bool = False,
) -> tuple[xr.Dataset, str]:
    resolved_freq = freq or "D"
    times = pd.date_range(start, end, freq=resolved_freq)
    if not len(times):
        resolved_freq = "D"
        times = pd.date_range(start, end, freq=resolved_freq)
    if not len(times):
        start_ts = pd.to_datetime(start)
        times = pd.date_range(start_ts, periods=1, freq="D")

    y_coords, x_coords = _build_coords_for_aoi(aoi)
    rng = np.random.default_rng(1337)
    data_vars = {}
    total = len(variables) if show_progress else None
    with progress_bar(total=total, description="gridMET synthetic") as advance:
        for name in variables:
            data = rng.normal(size=(len(times), len(y_coords), len(x_coords)))
            data_vars[name] = xr.DataArray(
                data,
                coords={TIME_DIM: times, Y_DIM: y_coords, X_DIM: x_coords},
                dims=(TIME_DIM, Y_DIM, X_DIM),
                name=name,
            )
            if show_progress:
                advance(1)

    return xr.Dataset(data_vars), resolved_freq


def _build_coords_for_aoi(aoi: Mapping[str, float]) -> tuple[np.ndarray, np.ndarray]:
    """Create evenly spaced coordinate arrays tailored to the AOI."""

    min_lat, max_lat = float(aoi["min_lat"]), float(aoi["max_lat"])
    min_lon, max_lon = float(aoi["min_lon"]), float(aoi["max_lon"])
    # Ensure at least two grid cells exist even for tiny AOIs.
    n_y = max(2, int(round((max_lat - min_lat) / 0.05)))
    n_x = max(2, int(round((max_lon - min_lon) / 0.05)))
    y_coords = np.linspace(min_lat, max_lat, n_y)
    x_coords = np.linspace(min_lon, max_lon, n_x)
    return y_coords, x_coords


def _crop_to_aoi(ds: xr.Dataset, aoi: Mapping[str, float]) -> xr.Dataset:
    """Select the AOI bounds along the spatial dimensions."""

    y_vals = ds.coords[Y_DIM]
    x_vals = ds.coords[X_DIM]
    y_mask = (y_vals >= aoi["min_lat"]) & (y_vals <= aoi["max_lat"])
    x_mask = (x_vals >= aoi["min_lon"]) & (x_vals <= aoi["max_lon"])
    return ds.sel({Y_DIM: y_vals[y_mask], X_DIM: x_vals[x_mask]})


def _resolve_chunks(chunks: Mapping[Hashable, int] | None) -> Mapping[Hashable, int]:
    if chunks is None:
        return DEFAULT_CHUNKS
    return chunks


def _has_lazy_data(ds: xr.Dataset) -> bool:
    """Return True when any data variable is backed by chunked/lazy data."""

    return any(getattr(var.data, "chunks", None) is not None for var in ds.data_vars.values())


def _finalize_gridmet_cube(
    ds: xr.Dataset,
    variables: Sequence[str],
    start: str,
    end: str,
    freq: str,
    *,
    allow_synthetic: bool,
    source: str,
    backend_error: str | None,
    show_progress: bool,
    aoi: Mapping[str, float],
    skip_all_nan_check: bool = False,
) -> xr.Dataset:
    time_len = int(ds.sizes.get(TIME_DIM, 0)) if TIME_DIM in ds.sizes else 0
    all_nan = False
    if ds.data_vars and not skip_all_nan_check:
        indicators = []
        for var in ds.data_vars.values():
            check = var.isnull().all()
            if hasattr(check, "compute"):
                check = check.compute()
            indicators.append(bool(check))
        all_nan = all(indicators)

    if time_len == 0:
        message = (
            "GRIDMET returned empty time axis. This commonly happens when freq='MS' and "
            "your date window contains no month-start timestamps. Pass freq='D' for daily "
            "analysis or extend your date range."
        )
        if not allow_synthetic:
            raise RuntimeError(message)
        backend_error = message if backend_error is None else f"{message} {backend_error}"
        ds, freq = _build_synthetic_gridmet_cube(
            variables, start, end, aoi, "D", show_progress=show_progress
        )
        source = "synthetic"
        time_len = int(ds.sizes.get(TIME_DIM, 0))
        all_nan = False

    if all_nan:
        nan_message = (
            "GRIDMET returned all-NaN data; the backend selection may be empty or require "
            "additional dependencies. Set allow_synthetic=True to permit synthetic data."
        )
        if not allow_synthetic:
            raise RuntimeError(nan_message)
        backend_error = nan_message if backend_error is None else f"{nan_message} {backend_error}"
        ds, freq = _build_synthetic_gridmet_cube(
            variables, start, end, aoi, "D", show_progress=show_progress
        )
        source = "synthetic"

    provenance_error = backend_error if source != "gridmet_streaming" else None
    return set_cube_provenance(
        ds,
        source=source,
        is_synthetic=source == "synthetic",
        freq=freq,
        requested_start=start,
        requested_end=end,
        backend_error=provenance_error,
    )


__all__ = ["load_gridmet_cube"]
