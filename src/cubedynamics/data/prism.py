"""PRISM data access helpers with a streaming-first contract."""

from __future__ import annotations

from functools import lru_cache
from html import unescape
from io import BytesIO
import re
from threading import local
from typing import Hashable, Iterable, Mapping, Sequence
from urllib.parse import unquote
import warnings

import numpy as np
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import xarray as xr

from ..config import TIME_DIM, X_DIM, Y_DIM
from ..progress import progress_bar
from ..utils import set_cube_provenance


_POINT_BUFFER_DEGREES = 0.05
_PRISM_NCSS_ROOT = "https://thredds.climate.ncsu.edu/thredds/ncss/grid"
_PRISM_DODS_ROOT = "https://thredds.climate.ncsu.edu/thredds/dodsC"
_PRISM_CATALOG_ROOT = (
    "https://thredds.climate.ncsu.edu/thredds/catalog/prism/daily/combo"
)
_PRISM_DAILY_COMBO_VARIABLES = {"ppt", "tmean", "tmin", "tmax"}
_PRISM_STREAMING_CHUNKS: Mapping[str, int] = {
    TIME_DIM: 31,
    Y_DIM: 256,
    X_DIM: 256,
}
_PRISM_GRID_STEP_DEGREES = 1.0 / 24.0
_PRISM_HTTP_LOCAL = local()
_PRISM_VARIABLE_METADATA = {
    "ppt": {
        "units": "mm",
        "long_name": "Total precipitation",
    },
}


def _prism_http_session() -> requests.Session:
    session = getattr(_PRISM_HTTP_LOCAL, "session", None)
    if session is None:
        retry = Retry(
            total=4,
            connect=4,
            read=4,
            backoff_factor=0.5,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset({"GET"}),
            respect_retry_after_header=True,
        )
        session = requests.Session()
        session.headers.update({"User-Agent": "cubedynamics-prism-stream/1"})
        session.mount("https://", HTTPAdapter(max_retries=retry, pool_maxsize=4))
        _PRISM_HTTP_LOCAL.session = session
    return session


def _apply_prism_variable_metadata(
    ds: xr.Dataset, variables: Sequence[str]
) -> xr.Dataset:
    for name in variables:
        if name not in ds.data_vars:
            continue
        meta = _PRISM_VARIABLE_METADATA.get(name.lower())
        if not meta:
            continue
        da = ds[name]
        units = da.attrs.get("units")
        if not units or str(units).strip().lower() == "synthetic":
            da.attrs["units"] = meta["units"]
        for key, value in meta.items():
            if key == "units":
                continue
            da.attrs.setdefault(key, value)
    return ds


def load_prism_cube(
    *legacy_args: object,
    lat: float | None = None,
    lon: float | None = None,
    bbox: Sequence[float] | None = None,
    aoi: Mapping[str, float] | None = None,
    aoi_geojson: Mapping[str, object] | None = None,
    start: str | pd.Timestamp | None = None,
    end: str | pd.Timestamp | None = None,
    variable: str | Sequence[str] = "ppt",
    variables: Sequence[str] | None = None,
    time_res: str = "ME",
    freq: str | None = None,
    chunks: Mapping[Hashable, int] | None = None,
    prefer_streaming: bool = True,
    show_progress: bool = True,
    allow_synthetic: bool = False,
) -> xr.Dataset | xr.DataArray:
    """Load a PRISM climate cube.

    Parameters
    ----------
    lat, lon : float, optional
        Latitude/longitude of a point of interest. When provided, a small
        bounding box is generated around the point so that PRISM pixels are
        fetched for the surrounding area.
    bbox : sequence of float, optional
        Bounding box defined as ``[min_lon, min_lat, max_lon, max_lat]``.
    aoi : mapping, optional
        Backward-compatible alias for ``bbox`` as a mapping containing
        ``min_lon``, ``min_lat``, ``max_lon``, and ``max_lat``.
    aoi_geojson : mapping, optional
        GeoJSON Feature/FeatureCollection describing the area of interest. A
        bounding box is derived from the geometry.
    start, end : datetime-like
        Temporal extent for the request.
    variable : str or sequence of str, default "ppt"
        PRISM variable(s) to request. ``variables`` may also be used for
        clarity when passing multiple entries. When a single variable is
        requested through ``variable``, the loader returns an ``xarray.DataArray``.
    time_res, freq : str, default "ME"
        Temporal frequency code. ``freq`` overrides ``time_res`` when set.
    chunks : mapping, optional
        Custom Dask chunk mapping.
    prefer_streaming : bool, default True
        Whether to use lazy, server-side AOI subsets from the PRISM THREDDS
        mirror. Daily slices are fetched only when Dask computes them.
    show_progress : bool, default True
        Display a progress bar while synthetic demo data are generated. Real
        streaming remains lazy and reports progress through the Dask scheduler.

    Notes
    -----
    The modern API requires keyword arguments and exactly one AOI specification
    (``lat``/``lon``, ``bbox`` or ``aoi_geojson``). Legacy positional usage of
    the form ``load_prism_cube(variables, start, end, aoi, ...)`` is still
    supported but deprecated.

    Real streaming currently supports daily ``ppt``, ``tmean``, ``tmin``, and
    ``tmax``. Synthetic fallback is disabled unless ``allow_synthetic=True``.
    """

    if legacy_args:
        if any(
            value is not None
            for value in (lat, lon, bbox, aoi, aoi_geojson, start, end, freq)
        ) or variables is not None:
            raise TypeError(
                "Cannot mix positional PRISM arguments with the keyword-only API."
            )
        warnings.warn(
            "Positional PRISM arguments are deprecated; use keyword arguments",
            DeprecationWarning,
            stacklevel=2,
        )
        return _load_prism_cube_legacy(
            *legacy_args,
            time_res=time_res,
            chunks=chunks,
            prefer_streaming=prefer_streaming,
            show_progress=show_progress,
            allow_synthetic=allow_synthetic,
        )

    freq_code = freq or time_res or "ME"
    if start is None or end is None:
        raise ValueError("Both 'start' and 'end' must be provided.")

    start_ts = pd.to_datetime(start)
    end_ts = pd.to_datetime(end)
    if start_ts > end_ts:
        raise ValueError("'start' must be before 'end'.")

    if variables is not None:
        if variable != "ppt":
            raise ValueError("Use either 'variable' or 'variables', not both.")
        variable_spec: Iterable[str] | str = variables
    else:
        variable_spec = variable
    normalized_variables = _normalize_variables(variable_spec)

    aoi_mapping = _coerce_aoi(
        lat=lat,
        lon=lon,
        bbox=bbox,
        aoi=aoi,
        aoi_geojson=aoi_geojson,
    )

    ds = _load_prism_cube_impl(
        normalized_variables,
        start_ts.isoformat(),
        end_ts.isoformat(),
        aoi_mapping,
        freq_code,
        chunks,
        prefer_streaming,
        show_progress,
        allow_synthetic,
    )
    if variables is None and len(normalized_variables) == 1:
        da = ds[normalized_variables[0]]
        da = da.copy()
        da.attrs.update(ds.attrs)
        return da
    return ds


def _load_prism_cube_impl(
    variables: Sequence[str],
    start: str,
    end: str,
    aoi: Mapping[str, float],
    freq: str,
    chunks: Mapping[Hashable, int] | None,
    prefer_streaming: bool,
    show_progress: bool,
    allow_synthetic: bool,
) -> xr.Dataset:
    chunk_map = _resolve_chunks(chunks)
    backend_error: str | None = None
    source = "prism_streaming"
    ds: xr.Dataset | None = None

    streaming_error: Exception | None = None
    if prefer_streaming:
        try:
            try:
                ds = _open_prism_streaming(variables, start, end, aoi, freq, show_progress)
            except TypeError:
                ds = _open_prism_streaming(variables, start, end, aoi, freq)
        except Exception as exc:  # pragma: no cover - used in tests
            streaming_error = exc
            backend_error = str(exc)
            warnings.warn(
                "PRISM streaming backend unavailable; synthetic fallback requires "
                "allow_synthetic=True.",
                RuntimeWarning,
            )

    if ds is None:
        if not allow_synthetic:
            raise RuntimeError(
                "PRISM streaming backend failed and synthetic fallback is disabled. "
                "Set allow_synthetic=True only for demos."
            ) from streaming_error
        ds, freq = _build_synthetic_prism_cube(
            variables, start, end, aoi, freq, show_progress=show_progress
        )
        source = "synthetic"

    ds = _crop_to_aoi(ds, aoi)
    ds = _finalize_prism_cube(
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
    )
    return ds.chunk(chunk_map)


def _load_prism_cube_legacy(
    *legacy_args: object,
    time_res: str = "ME",
    chunks: Mapping[Hashable, int] | None = None,
    prefer_streaming: bool = True,
    show_progress: bool = True,
    allow_synthetic: bool = False,
) -> xr.Dataset:
    if len(legacy_args) < 4:
        raise TypeError(
            "load_prism_cube() legacy usage requires variables, start, end, and aoi"
        )

    variables = legacy_args[0]
    start = legacy_args[1]
    end = legacy_args[2]
    aoi = legacy_args[3]
    freq = time_res or "ME"
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
        raise TypeError("load_prism_cube() received too many positional arguments")

    normalized_variables = _normalize_variables(variables)
    aoi_mapping = _coerce_legacy_aoi(aoi)

    start_ts = pd.to_datetime(start)
    end_ts = pd.to_datetime(end)

    return _load_prism_cube_impl(
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
        raise ValueError("At least one PRISM variable must be provided.")
    return [str(val) for val in values]


def _coerce_aoi(
    *,
    lat: float | None,
    lon: float | None,
    bbox: Sequence[float] | None,
    aoi: Mapping[str, float] | None,
    aoi_geojson: Mapping[str, object] | None,
) -> Mapping[str, float]:
    specs = [
        lat is not None or lon is not None,
        bbox is not None,
        aoi is not None,
        aoi_geojson is not None,
    ]
    if sum(bool(spec) for spec in specs) != 1:
        raise ValueError(
            "Specify exactly one of (lat/lon), bbox, aoi, or aoi_geojson for PRISM requests."
        )

    if lat is not None or lon is not None:
        if lat is None or lon is None:
            raise ValueError("Both 'lat' and 'lon' must be provided together.")
        return _bbox_mapping_from_point(lat, lon)
    if bbox is not None:
        return _bbox_mapping_from_sequence(bbox)
    if aoi is not None:
        return _coerce_legacy_aoi(aoi)
    assert aoi_geojson is not None  # for mypy/static
    return _bbox_mapping_from_geojson(aoi_geojson)


def _bbox_mapping_from_point(lat: float, lon: float) -> Mapping[str, float]:
    buffer = _POINT_BUFFER_DEGREES
    return {
        "min_lat": float(lat) - buffer,
        "max_lat": float(lat) + buffer,
        "min_lon": float(lon) - buffer,
        "max_lon": float(lon) + buffer,
    }


def _bbox_mapping_from_sequence(values: Sequence[float]) -> Mapping[str, float]:
    if len(values) != 4:
        raise ValueError("'bbox' must contain four values: [min_lon, min_lat, max_lon, max_lat].")
    min_lon, min_lat, max_lon, max_lat = map(float, values)
    if min_lon >= max_lon or min_lat >= max_lat:
        raise ValueError("'bbox' must have min values less than max values.")
    return {
        "min_lon": min_lon,
        "min_lat": min_lat,
        "max_lon": max_lon,
        "max_lat": max_lat,
    }


def _bbox_mapping_from_geojson(aoi_geojson: Mapping[str, object]) -> Mapping[str, float]:
    if not isinstance(aoi_geojson, Mapping):
        raise ValueError("GeoJSON AOI must be a mapping with a 'type' field.")
    geometries = _extract_geojson_geometries(aoi_geojson)
    coords = []
    for geometry in geometries:
        coords.extend(_flatten_geojson_coords(geometry.get("coordinates")))
    if not coords:
        raise ValueError("GeoJSON AOI does not contain any coordinates.")
    lons = [float(coord[0]) for coord in coords]
    lats = [float(coord[1]) for coord in coords]
    return {
        "min_lon": min(lons),
        "max_lon": max(lons),
        "min_lat": min(lats),
        "max_lat": max(lats),
    }


def _extract_geojson_geometries(obj: Mapping[str, object]) -> Sequence[Mapping[str, object]]:
    geo_type = obj.get("type")
    if geo_type == "FeatureCollection":
        features = obj.get("features", [])
        if not isinstance(features, Sequence) or isinstance(features, (str, bytes)):
            raise ValueError("GeoJSON FeatureCollection must include a 'features' array.")
        geometries = [feat.get("geometry") for feat in features if isinstance(feat, Mapping)]
        return [geom for geom in geometries if isinstance(geom, Mapping)]
    if geo_type == "Feature":
        geometry = obj.get("geometry")
        if not isinstance(geometry, Mapping):
            raise ValueError("GeoJSON Feature missing a valid geometry.")
        return [geometry]
    if geo_type in {"Polygon", "MultiPolygon", "Point", "LineString", "MultiLineString", "MultiPoint"}:
        return [obj]
    raise ValueError("Unsupported GeoJSON type for AOI: {0}".format(geo_type))


def _flatten_geojson_coords(coords: object) -> list[tuple[float, float]]:
    if coords is None:
        return []
    if isinstance(coords, (float, int)):
        raise ValueError("Invalid GeoJSON coordinate structure.")
    if isinstance(coords, Sequence) and not isinstance(coords, (str, bytes)):
        if coords and isinstance(coords[0], (float, int)):
            if len(coords) < 2:
                raise ValueError("GeoJSON coordinates must include lon/lat pairs.")
            return [(float(coords[0]), float(coords[1]))]
        flat: list[tuple[float, float]] = []
        for sub in coords:
            flat.extend(_flatten_geojson_coords(sub))
        return flat
    return []


def _coerce_legacy_aoi(aoi: object) -> Mapping[str, float]:
    if not isinstance(aoi, Mapping):
        raise ValueError("Legacy PRISM AOI must be a mapping with bounding box keys.")
    required_keys = {"min_lon", "max_lon", "min_lat", "max_lat"}
    if not required_keys.issubset(aoi.keys()):
        raise ValueError(
            "Legacy AOI missing bounding box keys: {0}".format(
                ", ".join(sorted(required_keys - set(aoi.keys())))
            )
        )
    return {key: float(aoi[key]) for key in required_keys}


def _open_prism_streaming(
    variables: Sequence[str],
    start: str,
    end: str,
    aoi: Mapping[str, float],
    freq: str = "ME",
    show_progress: bool = True,
) -> xr.Dataset:
    """Build a lazy daily PRISM cube from server-side AOI subsets."""

    if str(freq or "D").upper() != "D":
        raise NotImplementedError(
            "Real PRISM streaming currently supports freq='D'; "
            "monthly streaming will be added separately."
        )

    unsupported = sorted(set(variables) - _PRISM_DAILY_COMBO_VARIABLES)
    if unsupported:
        raise ValueError(
            f"Daily PRISM streaming does not provide variables {unsupported!r}; "
            f"available variables are {sorted(_PRISM_DAILY_COMBO_VARIABLES)!r}"
        )

    try:
        import dask.array as da
        from dask import delayed
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("dask is required for PRISM streaming") from exc

    times = pd.date_range(start, end, freq="D")
    if not len(times):
        raise ValueError("No time steps available for the requested range")

    dataset_paths = _discover_prism_daily_paths(times)
    first = _request_prism_ncss_subset(dataset_paths[0], variables, aoi)
    y_coords = _normalize_prism_coords(first[Y_DIM].values)
    x_coords = _normalize_prism_coords(first[X_DIM].values)
    first = first.assign_coords({Y_DIM: y_coords, X_DIM: x_coords})
    first_stack = np.stack(
        [first[name].values.astype("float32") for name in variables]
    )
    shape = first_stack.shape
    daily_stacks = [da.from_array(first_stack, chunks=shape)]

    for dataset_path in dataset_paths[1:]:
        task = delayed(_request_prism_ncss_array)(
            dataset_path,
            tuple(variables),
            dict(aoi),
            shape,
            tuple(float(value) for value in y_coords),
            tuple(float(value) for value in x_coords),
        )
        daily_stacks.append(da.from_delayed(task, shape=shape, dtype=np.float32))

    stacked = da.stack(daily_stacks, axis=0)
    data_vars = {}
    for index, name in enumerate(variables):
        attrs = dict(first[name].attrs)
        attrs.update(
            {
                "source": "PRISM via NCSCO THREDDS NcSS",
                "is_synthetic": False,
            }
        )
        data_vars[name] = xr.DataArray(
            stacked[:, index, :, :],
            coords={TIME_DIM: times, Y_DIM: y_coords, X_DIM: x_coords},
            dims=(TIME_DIM, Y_DIM, X_DIM),
            name=name,
            attrs=attrs,
        )

    return xr.Dataset(
        data_vars,
        attrs={
            "source": "prism_streaming",
            "source_provider": "PRISM Climate Group",
            "streaming_service": "NCSCO THREDDS NetCDF Subset Service",
            "streaming_protocol": "NcSS",
            "is_synthetic": False,
        },
    )


@lru_cache(maxsize=64)
def _prism_daily_catalog(year: int) -> dict[str, str]:
    response = _prism_http_session().get(
        f"{_PRISM_CATALOG_ROOT}/{year}/catalog.html", timeout=60
    )
    response.raise_for_status()
    paths: dict[str, str] = {}
    for encoded_path in re.findall(r"dataset=([^\"&]+\.nc)", response.text):
        dataset_path = unquote(unescape(encoded_path))
        match = re.search(r"(\d{8})\.nc$", dataset_path)
        if match:
            paths.setdefault(match.group(1), dataset_path)
    if not paths:
        raise RuntimeError(f"No daily PRISM datasets found in the {year} catalog")
    return paths


def _discover_prism_daily_paths(times: pd.DatetimeIndex) -> list[str]:
    paths = []
    for timestamp in times:
        stamp = timestamp.strftime("%Y%m%d")
        try:
            paths.append(_prism_daily_catalog(timestamp.year)[stamp])
        except KeyError as exc:
            raise RuntimeError(f"PRISM daily dataset is unavailable for {stamp}") from exc
    return paths


def _request_prism_ncss_subset(
    dataset_path: str,
    variables: Sequence[str],
    aoi: Mapping[str, float],
) -> xr.Dataset:
    params = [("var", name) for name in variables]
    params.extend(
        [
            ("north", str(aoi["max_lat"])),
            ("south", str(aoi["min_lat"])),
            ("west", str(aoi["min_lon"])),
            ("east", str(aoi["max_lon"])),
            ("accept", "netcdf"),
        ]
    )
    response = _prism_http_session().get(
        f"{_PRISM_NCSS_ROOT}/{dataset_path}",
        params=params,
        timeout=120,
    )
    if not response.ok and "unknown DataType == long" in response.text:
        return _request_prism_dods_ascii_subset(dataset_path, variables, aoi)
    response.raise_for_status()
    with xr.open_dataset(BytesIO(response.content), engine="scipy") as remote:
        loaded = remote.load()
    aliases = {
        TIME_DIM: ("t", "time"),
        Y_DIM: ("latitude", "lat", "y"),
        X_DIM: ("longitude", "lon", "x"),
    }
    rename = {}
    for canonical, candidates in aliases.items():
        source = next((name for name in candidates if name in loaded.dims), None)
        if source is None:
            raise RuntimeError(
                f"PRISM NcSS response has no {canonical!r} dimension; "
                f"received {tuple(loaded.dims)!r}"
            )
        if source != canonical:
            rename[source] = canonical
    loaded = loaded.rename(rename)
    return loaded.isel({TIME_DIM: 0}, drop=True)


@lru_cache(maxsize=64)
def _request_prism_dods_coords(dataset_path: str) -> tuple[np.ndarray, np.ndarray]:
    response = _prism_http_session().get(
        f"{_PRISM_DODS_ROOT}/{dataset_path}.ascii?latitude,longitude",
        timeout=120,
    )
    response.raise_for_status()
    sections = _parse_dods_ascii_sections(response.text)
    return (
        _parse_dods_vector(sections, "latitude"),
        _parse_dods_vector(sections, "longitude"),
    )


def _request_prism_dods_ascii_subset(
    dataset_path: str,
    variables: Sequence[str],
    aoi: Mapping[str, float],
) -> xr.Dataset:
    lat, lon = _request_prism_dods_coords(dataset_path)
    lat_indices = np.flatnonzero((lat >= aoi["min_lat"]) & (lat <= aoi["max_lat"]))
    lon_indices = np.flatnonzero((lon >= aoi["min_lon"]) & (lon <= aoi["max_lon"]))
    if not len(lat_indices) or not len(lon_indices):
        raise RuntimeError("PRISM OPeNDAP fallback found no cells inside the AOI")

    y_start, y_stop = int(lat_indices[0]), int(lat_indices[-1])
    x_start, x_stop = int(lon_indices[0]), int(lon_indices[-1])
    constraints = [
        f"{name}[0:1:0][{y_start}:1:{y_stop}][{x_start}:1:{x_stop}]"
        for name in variables
    ]
    constraints.extend(
        [
            f"latitude[{y_start}:1:{y_stop}]",
            f"longitude[{x_start}:1:{x_stop}]",
        ]
    )
    response = _prism_http_session().get(
        f"{_PRISM_DODS_ROOT}/{dataset_path}.ascii?{','.join(constraints)}",
        timeout=120,
    )
    response.raise_for_status()
    sections = _parse_dods_ascii_sections(response.text)
    y_coords = _parse_dods_vector(sections, "latitude").astype("float64")
    x_coords = _parse_dods_vector(sections, "longitude").astype("float64")
    coords = {Y_DIM: y_coords, X_DIM: x_coords}
    data_vars = {}
    for name in variables:
        values = _parse_dods_grid(sections, name).astype("float32")
        values = np.where(values <= -9990.0, np.nan, values)
        data_vars[name] = xr.DataArray(
            values,
            dims=(Y_DIM, X_DIM),
            coords=coords,
            attrs={
                "source": "PRISM via NCSCO THREDDS OPeNDAP ASCII fallback",
                "is_synthetic": False,
            },
        )
    return xr.Dataset(data_vars)


def _parse_dods_ascii_sections(text: str) -> dict[str, list[str]]:
    if "---------------------------------------------" not in text:
        raise RuntimeError("Unexpected OPeNDAP ASCII response")
    _, data = text.split("---------------------------------------------", 1)
    sections: dict[str, list[str]] = {}
    header: str | None = None
    rows: list[str] = []
    for line in data.splitlines():
        stripped = line.strip()
        if not stripped:
            if header is not None:
                sections[header] = rows
                header = None
                rows = []
            continue
        if header is None:
            header = stripped
            rows = []
        else:
            rows.append(stripped)
    if header is not None:
        sections[header] = rows
    return sections


def _parse_dods_vector(sections: Mapping[str, list[str]], name: str) -> np.ndarray:
    prefix = f"{name}["
    rows = next((rows for header, rows in sections.items() if header.startswith(prefix)), None)
    if rows is None:
        raise RuntimeError(f"OPeNDAP ASCII response is missing {name!r}")
    values: list[float] = []
    for row in rows:
        values.extend(float(part.strip()) for part in row.split(",") if part.strip())
    return np.asarray(values, dtype="float64")


def _parse_dods_grid(sections: Mapping[str, list[str]], name: str) -> np.ndarray:
    prefix = f"{name}.{name}["
    rows = next((rows for header, rows in sections.items() if header.startswith(prefix)), None)
    if rows is None:
        raise RuntimeError(f"OPeNDAP ASCII response is missing {name!r}")
    parsed_rows = []
    for row in rows:
        if "," not in row:
            continue
        _, values = row.split(",", 1)
        parsed_rows.append(
            [float(part.strip()) for part in values.split(",") if part.strip()]
        )
    return np.asarray(parsed_rows, dtype="float64")


def _request_prism_ncss_array(
    dataset_path: str,
    variables: tuple[str, ...],
    aoi: dict[str, float],
    expected_shape: tuple[int, ...],
    expected_y: tuple[float, ...],
    expected_x: tuple[float, ...],
) -> np.ndarray:
    subset = _request_prism_ncss_subset(dataset_path, variables, aoi)
    subset = _align_prism_subset_to_grid(subset, expected_y, expected_x)
    result = np.stack([subset[name].values.astype("float32") for name in variables])
    if result.shape != expected_shape:
        raise RuntimeError(
            f"PRISM subset shape changed for {dataset_path}: "
            f"expected {expected_shape}, got {result.shape}"
        )
    return result


def _normalize_prism_coords(values: Sequence[float]) -> np.ndarray:
    values_array = np.asarray(values, dtype="float64")
    snapped = np.round(values_array / _PRISM_GRID_STEP_DEGREES)
    return np.round(snapped * _PRISM_GRID_STEP_DEGREES, 6)


def _align_prism_subset_to_grid(
    subset: xr.Dataset,
    expected_y: Sequence[float],
    expected_x: Sequence[float],
) -> xr.Dataset:
    y_coords = _normalize_prism_coords(subset[Y_DIM].values)
    x_coords = _normalize_prism_coords(subset[X_DIM].values)
    return subset.assign_coords({Y_DIM: y_coords, X_DIM: x_coords}).reindex(
        {Y_DIM: np.asarray(expected_y), X_DIM: np.asarray(expected_x)}
    )


def _open_prism_download(
    variables: Sequence[str],
    start: str,
    end: str,
    aoi: Mapping[str, float],
    freq: str = "ME",
    *,
    error: Exception | None = None,
    show_progress: bool = True,
) -> xr.Dataset:
    """Return legacy synthetic data for compatibility with older imports."""

    resolved_freq = freq or "ME"
    times = pd.date_range(start, end, freq=resolved_freq)
    y_coords, x_coords = _build_coords_for_aoi(aoi)
    rng = np.random.default_rng(19)

    data_vars = {}
    total = len(variables) if show_progress else None
    with progress_bar(total=total, description="PRISM download") as advance:
        for name in variables:
            data = rng.uniform(low=0.0, high=5.0, size=(len(times), len(y_coords), len(x_coords)))
            da_var = xr.DataArray(
                data,
                coords={TIME_DIM: times, Y_DIM: y_coords, X_DIM: x_coords},
                dims=(TIME_DIM, Y_DIM, X_DIM),
                name=name,
                attrs={"source": "synthetic-prism", "fallback_error": str(error) if error else ""},
            )
            data_vars[name] = da_var
            if show_progress:
                advance(1)

    return xr.Dataset(data_vars)


def _build_synthetic_prism_cube(
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
        times = pd.date_range(pd.to_datetime(start), periods=1, freq="D")

    y_coords, x_coords = _build_coords_for_aoi(aoi)
    rng = np.random.default_rng(2024)
    data_vars = {}
    total = len(variables) if show_progress else None
    with progress_bar(total=total, description="PRISM synthetic") as advance:
        for name in variables:
            data = rng.uniform(low=0.0, high=5.0, size=(len(times), len(y_coords), len(x_coords)))
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
    min_lat, max_lat = float(aoi["min_lat"]), float(aoi["max_lat"])
    min_lon, max_lon = float(aoi["min_lon"]), float(aoi["max_lon"])
    n_y = max(2, int(round((max_lat - min_lat) / 0.1)))
    n_x = max(2, int(round((max_lon - min_lon) / 0.1)))
    y_coords = np.linspace(min_lat, max_lat, n_y)
    x_coords = np.linspace(min_lon, max_lon, n_x)
    return y_coords, x_coords


def _crop_to_aoi(ds: xr.Dataset, aoi: Mapping[str, float]) -> xr.Dataset:
    y_vals = ds.coords[Y_DIM]
    x_vals = ds.coords[X_DIM]
    y_mask = (y_vals >= aoi["min_lat"]) & (y_vals <= aoi["max_lat"])
    x_mask = (x_vals >= aoi["min_lon"]) & (x_vals <= aoi["max_lon"])
    return ds.sel({Y_DIM: y_vals[y_mask], X_DIM: x_vals[x_mask]})


def _resolve_chunks(chunks: Mapping[Hashable, int] | None) -> Mapping[Hashable, int]:
    if chunks is None:
        return _PRISM_STREAMING_CHUNKS
    return chunks


def _finalize_prism_cube(
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
) -> xr.Dataset:
    time_len = int(ds.sizes.get(TIME_DIM, 0)) if TIME_DIM in ds.sizes else 0
    all_nan = False
    is_lazy = any(var.chunks is not None for var in ds.data_vars.values())
    if ds.data_vars and not is_lazy:
        flags = []
        for var in ds.data_vars.values():
            flags.append(bool(var.isnull().all()))
        all_nan = all(flags)

    if time_len == 0:
        message = (
            "PRISM returned empty time axis. Month-end ('ME') requests can yield no timestamps "
            "for short ranges. Use freq='D' for daily analysis or extend the date window."
        )
        if not allow_synthetic:
            raise RuntimeError(message)
        backend_error = message if backend_error is None else f"{message} {backend_error}"
        ds, freq = _build_synthetic_prism_cube(
            variables, start, end, aoi, "D", show_progress=show_progress
        )
        source = "synthetic"
        time_len = int(ds.sizes.get(TIME_DIM, 0))
        all_nan = False

    if all_nan:
        nan_message = (
            "PRISM returned all-NaN data; ensure the requested region and dates are valid or "
            "enable allow_synthetic=True for demo data."
        )
        if not allow_synthetic:
            raise RuntimeError(nan_message)
        backend_error = nan_message if backend_error is None else f"{nan_message} {backend_error}"
        ds, freq = _build_synthetic_prism_cube(
            variables, start, end, aoi, "D", show_progress=show_progress
        )
        source = "synthetic"

    ds = _apply_prism_variable_metadata(ds, variables)

    provenance_error = backend_error if source != "prism_streaming" else None
    return set_cube_provenance(
        ds,
        source=source,
        is_synthetic=source == "synthetic",
        freq=freq,
        requested_start=start,
        requested_end=end,
        backend_error=provenance_error,
    )


__all__ = ["load_prism_cube"]
