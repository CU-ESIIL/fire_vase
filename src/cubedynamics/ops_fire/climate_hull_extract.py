"""Deprecated climate extraction wrappers that forward to :mod:`cubedynamics.fire_time_hull`."""

from __future__ import annotations

from .. import fire_time_hull as _fth
from ..deprecations import warn_deprecated

HullClimateSummary = _fth.HullClimateSummary

__all__ = [
    "HullClimateSummary",
    "_infer_spatial_dims",
    "_infer_cube_epsg",
    "build_inside_outside_climate_samples",
]


def _infer_spatial_dims(*args, **kwargs):
    warn_deprecated(
        "cubedynamics.ops_fire.climate_hull_extract._infer_spatial_dims",
        "cubedynamics.fire_time_hull._infer_spatial_dims",
        since="0.2.0",
        removal="0.3.0",
    )
    return _fth._infer_spatial_dims(*args, **kwargs)


def _infer_cube_epsg(*args, **kwargs):
    warn_deprecated(
        "cubedynamics.ops_fire.climate_hull_extract._infer_cube_epsg",
        "cubedynamics.fire_time_hull._infer_cube_epsg",
        since="0.2.0",
        removal="0.3.0",
    )
    return _fth._infer_cube_epsg(*args, **kwargs)


def build_inside_outside_climate_samples(*args, **kwargs):
    """Deprecated. Use :func:`cubedynamics.fire_time_hull.build_inside_outside_climate_samples` instead.

    This shim exists for callers still importing from ``cubedynamics.ops_fire``;
    it issues a :class:`DeprecationWarning` and delegates all parameters to the
    canonical backend in :mod:`cubedynamics.fire_time_hull`.
    """
    warn_deprecated(
        "cubedynamics.ops_fire.climate_hull_extract.build_inside_outside_climate_samples",
        "cubedynamics.fire_time_hull.build_inside_outside_climate_samples",
        since="0.2.0",
        removal="0.3.0",
    )
    return _fth.build_inside_outside_climate_samples(*args, **kwargs)

