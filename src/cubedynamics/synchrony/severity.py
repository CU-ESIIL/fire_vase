"""Severity synchrony primitives."""

from __future__ import annotations

import numpy as np
import xarray as xr

from ..config import TIME_DIM
from ..stats.tails import _rank_1d
from .occurrence import _edge_to_output_map
from .spatial import (
    SpatialPairSet,
    build_spatial_pairs,
    pairwise_edge_dataset,
    regional_summary,
    stack_space,
    time_windows,
)


def severity_score(
    left_mag: np.ndarray,
    right_mag: np.ndarray,
    left_state: np.ndarray,
    right_state: np.ndarray,
    *,
    method: str = "spearman",
    min_joint_events: int = 10,
) -> tuple[float, float, float, float, float]:
    """Return severity synchrony and diagnostics for two locations."""

    joint = (
        np.asarray(left_state).astype(bool)
        & np.asarray(right_state).astype(bool)
        & np.isfinite(left_mag)
        & np.isfinite(right_mag)
    )
    n = int(np.count_nonzero(joint))
    if n < min_joint_events:
        return (np.nan, float(n), np.nan, np.nan, np.nan)
    left = np.asarray(left_mag, dtype=float)[joint]
    right = np.asarray(right_mag, dtype=float)[joint]
    if method == "spearman":
        left = _rank_1d(left)
        right = _rank_1d(right)
    elif method != "pearson":
        raise ValueError("method must be 'spearman' or 'pearson'")
    left_centered = left - left.mean()
    right_centered = right - right.mean()
    denom = np.sqrt(np.sum(left_centered**2) * np.sum(right_centered**2))
    score = float(np.sum(left_centered * right_centered) / denom) if denom > 0 else np.nan
    return (
        score,
        float(n),
        float(np.nanmean(np.asarray(left_mag, dtype=float)[joint])),
        float(np.nanmean(np.asarray(right_mag, dtype=float)[joint])),
        float(np.nanmean(np.abs(np.asarray(left_mag, dtype=float)[joint] - np.asarray(right_mag, dtype=float)[joint]))),
    )


def severity_synchrony(
    state_cube: xr.Dataset,
    *,
    state_var: str = "state",
    magnitude_var: str = "magnitude",
    condition: str = "joint",
    method: str = "spearman",
    spatial_mode: str = "neighbors",
    radius_km: float | None = None,
    k_neighbors: int | None = None,
    reference: str | tuple[int, int] | int | None = None,
    min_joint_events: int = 10,
    window: int | str | None = None,
    stride: int | str | None = None,
    time_dim: str = TIME_DIM,
) -> xr.Dataset:
    """Measure whether magnitudes co-vary when locations are jointly active."""

    if condition != "joint":
        raise NotImplementedError("severity_synchrony currently supports condition='joint'")
    if not isinstance(state_cube, xr.Dataset):
        raise TypeError("severity_synchrony requires a state Dataset")
    for name in (state_var, magnitude_var):
        if name not in state_cube.data_vars:
            raise ValueError(f"Required variable {name!r} not found in state Dataset")

    windows = time_windows(state_cube, window=window, stride=stride, time_dim=time_dim)
    window_results = []
    for t_end, sub in windows:
        pairs = build_spatial_pairs(
            sub[magnitude_var],
            mode="reference" if spatial_mode == "center" else spatial_mode,
            radius_km=radius_km,
            k_neighbors=k_neighbors,
            reference=reference or ("center" if spatial_mode in {"reference", "center"} else None),
        )
        edge = _severity_edges(
            sub[magnitude_var],
            sub[state_var],
            pairs=pairs,
            method=method,
            min_joint_events=min_joint_events,
            time_dim=time_dim,
            t_end=t_end,
        )
        if spatial_mode in {"all_pairs", "blocks"}:
            window_results.append(edge)
        elif spatial_mode == "regional":
            window_results.append(
                regional_summary(edge, metric_var="severity_synchrony", time_window_end=t_end)
            )
        else:
            window_results.append(
                _edge_to_output_map(
                    edge,
                    metric_var="severity_synchrony",
                    template=sub[magnitude_var],
                    pairs=pairs,
                    time_window_end=t_end,
                )
            )
    result = xr.concat(window_results, dim="time_window_end") if len(window_results) > 1 else window_results[0]
    result.attrs.update(
        {
            "analysis": "severity_synchrony",
            "spatial_mode": spatial_mode,
            "method": method,
            "condition": condition,
            "min_joint_events": min_joint_events,
            "window": str(window),
            "stride": str(stride),
        }
    )
    return result


def _severity_edges(
    magnitude: xr.DataArray,
    state: xr.DataArray,
    *,
    pairs: SpatialPairSet,
    method: str,
    min_joint_events: int,
    time_dim: str,
    t_end: object,
) -> xr.Dataset:
    mag_stacked = stack_space(magnitude)
    state_stacked = stack_space(state)
    values = []
    counts = []
    left_means = []
    right_means = []
    mean_abs_diffs = []
    for pair in pairs.pairs:
        left_mag = mag_stacked.isel(space=pair.source)
        right_mag = mag_stacked.isel(space=pair.target)
        left_state = state_stacked.isel(space=pair.source)
        right_state = state_stacked.isel(space=pair.target)
        score, n, left_mean, right_mean, mean_abs_diff = xr.apply_ufunc(
            severity_score,
            left_mag,
            right_mag,
            left_state,
            right_state,
            input_core_dims=[[time_dim], [time_dim], [time_dim], [time_dim]],
            output_core_dims=[[], [], [], [], []],
            vectorize=False,
            dask="parallelized",
            output_dtypes=[float, float, float, float, float],
            kwargs={"method": method, "min_joint_events": min_joint_events},
        )
        values.append(score)
        counts.append(n)
        left_means.append(left_mean)
        right_means.append(right_mean)
        mean_abs_diffs.append(mean_abs_diff)
    return pairwise_edge_dataset(
        values,
        var_name="severity_synchrony",
        pairs=pairs,
        time_window_end=t_end,
        extra_vars={
            "joint_observation_count": counts,
            "source_mean_magnitude": left_means,
            "target_mean_magnitude": right_means,
            "mean_absolute_magnitude_difference": mean_abs_diffs,
        },
    )
