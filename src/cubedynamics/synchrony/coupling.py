"""Cross-cube synchrony and coupling."""

from __future__ import annotations

import numpy as np
import xarray as xr

from ..config import TIME_DIM
from .occurrence import occurrence_score


def sync_with(
    left: xr.Dataset | xr.DataArray,
    right: xr.Dataset | xr.DataArray,
    *,
    synchrony: str = "occurrence",
    spatial_relation: str = "same_pixel",
    lags: list[str | int] | tuple[str | int, ...] = ("0D",),
    state_var: str = "state",
    time_dim: str = TIME_DIM,
) -> xr.Dataset:
    """Compare two aligned state cubes with optional lag search."""

    if synchrony != "occurrence":
        raise NotImplementedError("sync_with currently supports synchrony='occurrence'")
    if spatial_relation != "same_pixel":
        raise NotImplementedError("sync_with currently supports spatial_relation='same_pixel'")
    left_state = _state_array(left, state_var)
    right_state = _state_array(right, state_var)
    left_state, right_state = xr.align(left_state, right_state, join="inner")
    scores = []
    joint_counts = []
    valid_counts = []
    lag_labels = []
    for lag in lags:
        periods = _lag_to_periods(lag, right_state[time_dim])
        shifted = right_state.shift({time_dim: -periods})
        score, joint, _, valid = xr.apply_ufunc(
            occurrence_score,
            left_state,
            shifted,
            input_core_dims=[[time_dim], [time_dim]],
            output_core_dims=[[], [], [], []],
            vectorize=True,
            dask="parallelized",
            output_dtypes=[float, float, float, float],
            kwargs={"method": "jaccard"},
        )
        scores.append(score)
        joint_counts.append(joint)
        valid_counts.append(valid)
        lag_labels.append(str(lag))
    score_da = xr.concat(scores, dim="lag").assign_coords(lag=lag_labels).rename("coupling_score")
    joint_da = xr.concat(joint_counts, dim="lag").assign_coords(lag=lag_labels).rename("joint_event_count")
    valid_da = xr.concat(valid_counts, dim="lag").assign_coords(lag=lag_labels).rename("valid_sample_count")
    best_lag = score_da.idxmax(dim="lag").rename("best_lag")
    ds = xr.Dataset(
        {
            "coupling_score": score_da,
            "joint_event_count": joint_da,
            "valid_sample_count": valid_da,
            "best_lag": best_lag,
        },
        attrs={
            "analysis": "sync_with",
            "synchrony": synchrony,
            "spatial_relation": spatial_relation,
            "state_var": state_var,
            "null_diagnostics": "not_implemented",
        },
    )
    return ds


def _state_array(obj: xr.Dataset | xr.DataArray, state_var: str) -> xr.DataArray:
    if isinstance(obj, xr.DataArray):
        return obj
    if state_var not in obj:
        raise ValueError(f"State variable {state_var!r} not found")
    return obj[state_var]


def _lag_to_periods(lag: str | int, time: xr.DataArray) -> int:
    if isinstance(lag, int):
        return lag
    text = lag.strip().upper()
    if text.endswith("D"):
        days = int(text[:-1])
    elif text.endswith("Y"):
        days = int(text[:-1]) * 365
    else:
        raise ValueError("lags must use 'D' or 'Y', e.g. '90D'")
    if days == 0:
        return 0
    diffs = np.diff(time.values.astype("datetime64[ns]"))
    if diffs.size == 0:
        return 0
    step_days = float(np.median(diffs) / np.timedelta64(1, "D"))
    return int(round(days / step_days))
