"""Generic streaming adapter for global climate cubes."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np
import xarray as xr

from ..config import TIME_DIM, X_DIM, Y_DIM
from ..data.prism import _bbox_mapping_from_geojson, _bbox_mapping_from_sequence


_TIME_CANDIDATES = ("time", "day", "valid_time")
_Y_CANDIDATES = ("y", "lat", "latitude")
_X_CANDIDATES = ("x", "lon", "longitude")


def _as_dataset(obj: xr.Dataset | xr.DataArray) -> xr.Dataset:
    if isinstance(obj, xr.Dataset):
        return obj
    if isinstance(obj, xr.DataArray):
        return obj.to_dataset(name=obj.name or "value")
    raise TypeError("source must be an xarray Dataset or DataArray")


def _infer_dim(
    ds: xr.Dataset,
    explicit: str | None,
    candidates: Sequence[str],
    canonical: str,
) -> str:
    if explicit is not None:
        if explicit not in ds.dims:
            raise ValueError(f"{canonical!r} dimension {explicit!r} not found")
        return explicit
    found = [name for name in candidates if name in ds.dims]
    if len(found) == 1:
        return found[0]
    if not found:
        raise ValueError(
            f"Could not infer {canonical!r} dimension from dims {tuple(ds.dims)}"
        )
    if canonical in found:
        return canonical
    raise ValueError(
        f"Ambiguous {canonical!r} dimension candidates {found!r}; pass it explicitly"
    )


def _coerce_bbox(
    bbox: Sequence[float] | Mapping[str, float] | None,
    aoi_geojson: Mapping[str, object] | None,
) -> Mapping[str, float] | None:
    if bbox is not None and aoi_geojson is not None:
        raise ValueError("Specify only one of bbox or aoi_geojson")
    if bbox is None and aoi_geojson is None:
        return None
    if bbox is not None:
        if isinstance(bbox, Mapping):
            required = {"min_lon", "min_lat", "max_lon", "max_lat"}
            if not required.issubset(bbox):
                raise ValueError(f"bbox mapping must contain {sorted(required)!r}")
            return {key: float(bbox[key]) for key in required}
        return _bbox_mapping_from_sequence(bbox)
    return _bbox_mapping_from_geojson(aoi_geojson or {})


def _axis_slice(values: xr.DataArray, lower: float, upper: float) -> slice:
    coord = np.asarray(values.values, dtype="float64")
    if coord.size == 0:
        raise ValueError(f"Cannot slice empty coordinate {values.name!r}")
    lo = min(float(lower), float(upper))
    hi = max(float(lower), float(upper))
    if coord[0] > coord[-1]:
        return slice(hi, lo)
    return slice(lo, hi)


def _normalize_bbox_for_longitudes(
    bbox: Mapping[str, float],
    lon_values: xr.DataArray,
) -> Mapping[str, float]:
    coord = np.asarray(lon_values.values, dtype="float64")
    if coord.size == 0:
        return bbox
    min_coord = float(np.nanmin(coord))
    max_coord = float(np.nanmax(coord))
    if min_coord >= 0.0 and max_coord > 180.0:
        west = float(bbox["min_lon"])
        east = float(bbox["max_lon"])
        if west < 0.0:
            west = west % 360.0
        if east < 0.0:
            east = east % 360.0
        if west > east:
            raise NotImplementedError(
                "Global streaming adapter does not yet split dateline-crossing AOIs"
            )
        updated = dict(bbox)
        updated["min_lon"] = west
        updated["max_lon"] = east
        return updated
    return bbox


def stream_global_climate_cube(
    source: xr.Dataset | xr.DataArray,
    *,
    variables: Sequence[str] | None = None,
    bbox: Sequence[float] | Mapping[str, float] | None = None,
    aoi_geojson: Mapping[str, object] | None = None,
    time_dim: str | None = None,
    y_dim: str | None = None,
    x_dim: str | None = None,
    chunks: Mapping[str, int] | None = None,
    source_name: str = "global_xarray_stream",
) -> xr.Dataset:
    """Adapt a lazy global climate cube to CubeDynamics dimensions.

    This helper is for global alternatives such as ERA5, TerraClimate, CHIRPS,
    or cloud-opened Zarr/NetCDF datasets that are already represented as
    xarray objects. It does not download or cache data itself; it normalizes
    dimensions, applies an optional AOI slice, and preserves lazy backing.
    """

    ds = _as_dataset(source)
    if variables is not None:
        missing = [name for name in variables if name not in ds.data_vars]
        if missing:
            raise ValueError(f"Variables {missing!r} not found in source dataset")
        ds = ds[list(variables)]

    resolved_time = _infer_dim(ds, time_dim, _TIME_CANDIDATES, TIME_DIM)
    resolved_y = _infer_dim(ds, y_dim, _Y_CANDIDATES, Y_DIM)
    resolved_x = _infer_dim(ds, x_dim, _X_CANDIDATES, X_DIM)

    rename = {
        dim: canonical
        for dim, canonical in (
            (resolved_time, TIME_DIM),
            (resolved_y, Y_DIM),
            (resolved_x, X_DIM),
        )
        if dim != canonical
    }
    if rename:
        ds = ds.rename(rename)

    resolved_bbox = _coerce_bbox(bbox, aoi_geojson)
    if resolved_bbox is not None:
        resolved_bbox = _normalize_bbox_for_longitudes(resolved_bbox, ds[X_DIM])
        ds = ds.sel(
            {
                Y_DIM: _axis_slice(ds[Y_DIM], resolved_bbox["min_lat"], resolved_bbox["max_lat"]),
                X_DIM: _axis_slice(ds[X_DIM], resolved_bbox["min_lon"], resolved_bbox["max_lon"]),
            }
        )
        empty_dims = [dim for dim in (Y_DIM, X_DIM) if ds.sizes.get(dim, 0) == 0]
        if empty_dims:
            raise ValueError(f"Global climate subset is empty along {empty_dims!r}")

    if chunks is not None:
        ds = ds.chunk(chunks)

    ds.attrs.update(
        {
            "source": source_name,
            "source_provider": "user_supplied_global_xarray",
            "streaming_protocol": "xarray",
            "is_synthetic": False,
        }
    )
    return ds


__all__ = ["stream_global_climate_cube"]
