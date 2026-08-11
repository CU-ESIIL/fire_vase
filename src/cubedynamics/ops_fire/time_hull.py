"""Deprecated fire time-hull wrappers.

This module now delegates to :mod:`cubedynamics.fire_time_hull` so there is a
single backend. All public functions emit :class:`DeprecationWarning` on use but
preserve existing signatures.
"""

from __future__ import annotations

from typing import Any

from .. import fire_time_hull as _fth
from ..deprecations import warn_deprecated

FireEventDaily = _fth.FireEventDaily
TimeHull = _fth.TimeHull
Vase = _fth.Vase

__all__ = [
    "FireEventDaily",
    "TimeHull",
    "Vase",
    "clean_event_daily_rows",
    "_largest_polygon",
    "_sample_ring_equal_steps",
    "_tri_area",
    "build_fire_event",
    "compute_time_hull_geometry",
    "time_hull_to_vase",
]


def clean_event_daily_rows(*args, **kwargs):
    warn_deprecated(
        "cubedynamics.ops_fire.time_hull.clean_event_daily_rows",
        "cubedynamics.fire_time_hull.clean_event_daily_rows",
        since="0.2.0",
        removal="0.3.0",
    )
    return _fth.clean_event_daily_rows(*args, **kwargs)


def _largest_polygon(geom: Any):
    warn_deprecated(
        "cubedynamics.ops_fire.time_hull._largest_polygon",
        "cubedynamics.fire_time_hull._largest_polygon",
        since="0.2.0",
        removal="0.3.0",
    )
    return _fth._largest_polygon(geom)


def _sample_ring_equal_steps(*args, **kwargs):
    warn_deprecated(
        "cubedynamics.ops_fire.time_hull._sample_ring_equal_steps",
        "cubedynamics.fire_time_hull._sample_ring_equal_steps",
        since="0.2.0",
        removal="0.3.0",
    )
    return _fth._sample_ring_equal_steps(*args, **kwargs)


def _tri_area(*args, **kwargs):
    warn_deprecated(
        "cubedynamics.ops_fire.time_hull._tri_area",
        "cubedynamics.fire_time_hull._tri_area",
        since="0.2.0",
        removal="0.3.0",
    )
    return _fth._tri_area(*args, **kwargs)


def build_fire_event(*args, **kwargs):
    warn_deprecated(
        "cubedynamics.ops_fire.time_hull.build_fire_event",
        "cubedynamics.fire_time_hull.build_fire_event",
        since="0.2.0",
        removal="0.3.0",
    )
    return _fth.build_fire_event(*args, **kwargs)


def compute_time_hull_geometry(*args, **kwargs):
    """Deprecated. Use :func:`cubedynamics.fire_time_hull.compute_time_hull_geometry` instead.

    This wrapper emits a :class:`DeprecationWarning` and simply forwards all
    arguments to the canonical implementation in :mod:`cubedynamics.fire_time_hull`.
    It exists to preserve older import paths while users migrate.
    """
    warn_deprecated(
        "cubedynamics.ops_fire.time_hull.compute_time_hull_geometry",
        "cubedynamics.fire_time_hull.compute_time_hull_geometry",
        since="0.2.0",
        removal="0.3.0",
    )
    return _fth.compute_time_hull_geometry(*args, **kwargs)


def time_hull_to_vase(*args, **kwargs):
    """Deprecated. Use :func:`cubedynamics.fire_time_hull.time_hull_to_vase` instead.

    The shim keeps backward compatibility for callers importing from
    ``cubedynamics.ops_fire.time_hull`` and relays all parameters unchanged to the
    canonical function. A :class:`DeprecationWarning` is raised on use.
    """
    warn_deprecated(
        "cubedynamics.ops_fire.time_hull.time_hull_to_vase",
        "cubedynamics.fire_time_hull.time_hull_to_vase",
        since="0.2.0",
        removal="0.3.0",
    )
    return _fth.time_hull_to_vase(*args, **kwargs)

