"""Synchrony primitives for state and event cubes."""

from .coupling import sync_with
from .occurrence import occurrence_synchrony
from .severity import severity_synchrony
from .spatial import build_spatial_pairs
from .states import binary_state, change_state, quantile_state, threshold_state
from .timing import duration_synchrony, timing_synchrony

__all__ = [
    "binary_state",
    "build_spatial_pairs",
    "change_state",
    "duration_synchrony",
    "occurrence_synchrony",
    "quantile_state",
    "severity_synchrony",
    "sync_with",
    "threshold_state",
    "timing_synchrony",
]
