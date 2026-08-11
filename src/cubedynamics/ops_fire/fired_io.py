"""Deprecated FIRED IO wrappers that forward to :mod:`cubedynamics.fire_time_hull`."""

from __future__ import annotations

from .. import fire_time_hull as _fth
from ..deprecations import warn_deprecated

TemporalSupport = _fth.TemporalSupport

__all__ = [
    "TemporalSupport",
    "load_fired_conus_ak",
    "pick_event_with_joint_support",
    "load_fired_event_by_joint_support",
]


def load_fired_conus_ak(*args, **kwargs):
    warn_deprecated(
        "cubedynamics.ops_fire.fired_io.load_fired_conus_ak",
        "cubedynamics.fire_time_hull.load_fired_conus_ak",
        since="0.2.0",
        removal="0.3.0",
    )
    return _fth.load_fired_conus_ak(*args, **kwargs)


def pick_event_with_joint_support(*args, **kwargs):
    warn_deprecated(
        "cubedynamics.ops_fire.fired_io.pick_event_with_joint_support",
        "cubedynamics.fire_time_hull.pick_event_with_joint_support",
        since="0.2.0",
        removal="0.3.0",
    )
    return _fth.pick_event_with_joint_support(*args, **kwargs)


def load_fired_event_by_joint_support(*args, **kwargs):
    warn_deprecated(
        "cubedynamics.ops_fire.fired_io.load_fired_event_by_joint_support",
        "cubedynamics.fire_time_hull.load_fired_event_by_joint_support",
        since="0.2.0",
        removal="0.3.0",
    )
    return _fth.load_fired_event_by_joint_support(*args, **kwargs)

