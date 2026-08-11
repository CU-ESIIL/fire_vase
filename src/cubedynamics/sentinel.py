"""Legacy Sentinel-2 helpers preserved for backward compatibility.

This module now delegates to :mod:`cubedynamics.data.sentinel2` and emits
runtime deprecation warnings. Prefer calling the canonical loaders in
``cubedynamics.data`` or the semantic shortcuts in
:mod:`cubedynamics.variables`.
"""

from __future__ import annotations

from typing import Sequence

import xarray as xr

from .data import sentinel2 as _s2
from .data.sentinel2 import load_s2_cube, load_s2_ndvi_cube
from .deprecations import warn_deprecated
from .piping import pipe
from . import verbs as v

__all__ = [
    "cubo",
    "load_sentinel2_cube",
    "load_sentinel2_bands_cube",
    "load_sentinel2_ndvi_cube",
    "load_sentinel2_ndvi_zscore_cube",
]

# Expose cubo for backward compatibility and test injection. By default this
# mirrors the canonical cubo instance used by :mod:`cubedynamics.data.sentinel2`.
cubo = _s2.cubo


def load_sentinel2_cube(
    lat: float | None,
    lon: float | None,
    start: str,
    end: str,
    *,
    bbox: Sequence[float] | None = None,
    bands: Sequence[str] | None = None,
    edge_size: int = 512,
    resolution: int = 10,
    max_cloud: int = 40,
    show_progress: bool = True,
) -> xr.DataArray:
    """Deprecated. Use :func:`cubedynamics.data.sentinel2.load_s2_cube` instead.

    This wrapper exists for backward compatibility, preserving legacy
    arguments before delegating to the canonical loader. It also reorders the
    result to the historical ``(time, y, x, band)`` layout used by this module.
    """

    warn_deprecated(
        "cubedynamics.sentinel.load_sentinel2_cube",
        "cubedynamics.data.sentinel2.load_s2_cube",
        since="0.2.0",
        removal="0.3.0",
    )

    lat, lon, edge_size = _resolve_lat_lon_and_edge_size(
        lat, lon, bbox, edge_size, resolution
    )

    # Allow test and legacy callers to swap in a custom ``cubo`` implementation
    # by monkeypatching ``cubedynamics.sentinel.cubo``. If no override is
    # provided, fall back to the canonical loader.
    if cubo is not None and hasattr(cubo, "create") and cubo is not _s2.cubo:
        cube = cubo.create(
            lat=lat,
            lon=lon,
            start_date=start,
            end_date=end,
            edge_size=edge_size,
            resolution=resolution,
            collection="sentinel-2-l2a",
            bands=bands or ["B02", "B03", "B04", "B08"],
            query={"eo:cloud_cover": {"lt": max_cloud}},
        )
        data = _s2._to_dataarray(cube)
    else:
        data = load_s2_cube(
            lat=lat,
            lon=lon,
            start=start,
            end=end,
            edge_size=edge_size,
            resolution=resolution,
            cloud_lt=max_cloud,
            bands=bands,
        )

    desired_order = [dim for dim in ("time", "y", "x", "band") if dim in data.dims]
    return data.transpose(*desired_order)


def load_sentinel2_bands_cube(
    lat: float | None,
    lon: float | None,
    start: str,
    end: str,
    *,
    bbox: Sequence[float] | None = None,
    bands: Sequence[str],
    edge_size: int = 512,
    resolution: int = 10,
    max_cloud: int = 40,
    show_progress: bool = True,
) -> xr.DataArray:
    """Deprecated. Use :func:`cubedynamics.data.sentinel2.load_s2_cube` instead.

    This wrapper exists for callers that historically supplied an explicit
    band list; it forwards unchanged arguments to :func:`load_sentinel2_cube`.
    """

    warn_deprecated(
        "cubedynamics.sentinel.load_sentinel2_bands_cube",
        "cubedynamics.data.sentinel2.load_s2_cube",
        since="0.2.0",
        removal="0.3.0",
    )

    if not bands:
        raise ValueError(
            "load_sentinel2_bands_cube requires a non-empty 'bands' list."
        )

    return load_sentinel2_cube(
        lat=lat,
        lon=lon,
        start=start,
        end=end,
        bbox=bbox,
        bands=bands,
        edge_size=edge_size,
        resolution=resolution,
        max_cloud=max_cloud,
        show_progress=show_progress,
    )


def load_sentinel2_ndvi_cube(
    lat: float | None,
    lon: float | None,
    start: str,
    end: str,
    *,
    bbox: Sequence[float] | None = None,
    edge_size: int = 512,
    resolution: int = 10,
    max_cloud: int = 40,
    return_raw: bool = False,
    show_progress: bool = True,
) -> xr.DataArray | tuple[xr.DataArray, xr.DataArray]:
    """Deprecated. Use :func:`cubedynamics.variables.ndvi` instead.

    This wrapper exists for backward compatibility and forwards the loaded
    Sentinel-2 cube through the canonical NDVI verb pipeline.
    """

    warn_deprecated(
        "cubedynamics.sentinel.load_sentinel2_ndvi_cube",
        "cubedynamics.data.sentinel2.load_s2_ndvi_cube",
        since="0.2.0",
        removal="0.3.0",
    )

    lat, lon, edge_size = _resolve_lat_lon_and_edge_size(
        lat, lon, bbox, edge_size, resolution
    )

    ndvi = load_s2_ndvi_cube(
        lat=lat,
        lon=lon,
        start=start,
        end=end,
        edge_size=edge_size,
        resolution=resolution,
        cloud_lt=max_cloud,
    )

    if return_raw:
        s2 = load_s2_cube(
            lat=lat,
            lon=lon,
            start=start,
            end=end,
            edge_size=edge_size,
            resolution=resolution,
            cloud_lt=max_cloud,
            bands=["B04", "B08"],
        )
        s2 = s2.transpose(*[dim for dim in ("time", "y", "x", "band") if dim in s2.dims])
        return s2, ndvi

    return ndvi


def load_sentinel2_ndvi_zscore_cube(
    lat: float | None,
    lon: float | None,
    start: str,
    end: str,
    *,
    bbox: Sequence[float] | None = None,
    edge_size: int = 512,
    resolution: int = 10,
    max_cloud: int = 40,
    keep_dim: bool = True,
    show_progress: bool = True,
) -> xr.DataArray:
    """Deprecated. Use :func:`cubedynamics.variables.ndvi` and verbs.zscore instead.

    This wrapper exists for backward compatibility; it chains the canonical NDVI
    loader with the z-score verb to preserve historical behavior.
    """

    warn_deprecated(
        "cubedynamics.sentinel.load_sentinel2_ndvi_zscore_cube",
        "cubedynamics.variables.ndvi or cubedynamics.data.sentinel2.load_s2_ndvi_cube",
        since="0.2.0",
        removal="0.3.0",
    )

    ndvi = load_sentinel2_ndvi_cube(
        lat=lat,
        lon=lon,
        start=start,
        end=end,
        bbox=bbox,
        edge_size=edge_size,
        resolution=resolution,
        max_cloud=max_cloud,
        return_raw=False,
        show_progress=show_progress,
    )

    return (pipe(ndvi) | v.zscore(dim="time", keep_dim=keep_dim)).unwrap()


def _resolve_lat_lon_and_edge_size(
    lat: float | None,
    lon: float | None,
    bbox: Sequence[float] | None,
    edge_size: int,
    resolution: int,
) -> tuple[float, float, int]:
    """Convert legacy bbox inputs to center coordinate plus edge size."""

    if bbox is None:
        if lat is None or lon is None:
            raise ValueError(
                "load_sentinel2_cube requires either a bbox or both lat and lon."
            )
        return lat, lon, edge_size

    xmin, ymin, xmax, ymax = bbox
    center_lon = (xmin + xmax) / 2.0
    center_lat = (ymin + ymax) / 2.0

    span_x = abs(xmax - xmin)
    span_y = abs(ymax - ymin)
    span_deg = max(span_x, span_y)
    # Rough meters-per-degree scaling near equator; legacy behavior derived
    # from the previous implementation's UTM conversion.
    approx_m_per_deg = 111_000
    required_edge = int((span_deg * approx_m_per_deg) / resolution)
    adjusted_edge = max(edge_size, required_edge)

    return center_lat, center_lon, adjusted_edge

