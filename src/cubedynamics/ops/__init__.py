"""Pipeable cube operations."""

from .transforms import anomaly, month_filter
from .stats import correlation_cube, variance, zscore
from .io import to_netcdf
from .ndvi import ndvi_from_s2
from .viz import plot

__all__ = [
    "anomaly",
    "month_filter",
    "variance",
    "correlation_cube",
    "to_netcdf",
    "zscore",
    "ndvi_from_s2",
    "plot",
]
