"""Anomaly and z-score utilities."""

from __future__ import annotations

import warnings
from typing import Hashable

import numpy as np
import xarray as xr

from ..config import STD_EPS, TIME_DIM
from ..verbs.stats import zscore as _zscore


def zscore_over_time(
    da: xr.DataArray,
    dim: Hashable = TIME_DIM,
    std_eps: float | None = None,
) -> xr.DataArray:
    """Deprecated helper that forwards to :func:`cubedynamics.ops.stats.zscore`."""

    warnings.warn(
        "`zscore_over_time` is deprecated; use `cubedynamics.ops.stats.zscore` or"
        " `cubedynamics.verbs.zscore` instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    eps = STD_EPS if std_eps is None else std_eps
    dim_str = str(dim)
    return _zscore(dim=dim_str, std_eps=eps)(da)


def temporal_anomaly(
    da: xr.DataArray,
    dim: Hashable = TIME_DIM,
    baseline_slice: slice | None = None,
) -> xr.DataArray:
    """Compute anomalies relative to a baseline mean over a time-like dimension."""

    da_baseline = da if baseline_slice is None else da.sel({dim: baseline_slice})
    baseline_mean = da_baseline.mean(dim=dim, skipna=True)
    anomalies = da - baseline_mean
    baseline_desc = "full" if baseline_slice is None else str(baseline_slice)
    anomalies.attrs = {
        **da.attrs,
        "long_name": f"{da.name or 'variable'} anomaly",
        "baseline_period": baseline_desc,
    }
    return anomalies


def temporal_difference(
    da: xr.DataArray,
    lag: int = 1,
    dim: Hashable = TIME_DIM,
) -> xr.DataArray:
    """Compute lagged differences along a time-like dimension."""

    lagged = da.shift({dim: lag})
    diff = da - lagged
    diff.attrs = {
        **da.attrs,
        "long_name": f"{da.name or 'variable'} difference (lag={lag})",
    }
    return diff


def rolling_mean(
    da: xr.DataArray,
    window: int,
    dim: Hashable = TIME_DIM,
    min_periods: int | None = None,
    center: bool = False,
) -> xr.DataArray:
    """Compute a simple rolling mean along a time-like dimension."""

    min_periods = window if min_periods is None else min_periods
    rolled = da.rolling({dim: window}, min_periods=min_periods, center=center).mean()
    rolled.attrs = {
        **da.attrs,
        "long_name": f"{da.name or 'variable'} rolling mean (window={window})",
    }
    return rolled
