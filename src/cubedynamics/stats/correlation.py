"""Correlation helpers."""

from __future__ import annotations

import numpy as np
import xarray as xr

from ..utils.reference import center_pixel_indices, center_pixel_series
from .rolling import rolling_pairwise_stat_cube


def pearson_corr_stat(x: np.ndarray, y: np.ndarray) -> float:
    """Compute Pearson correlation between two 1D arrays."""

    mask = ~(np.isnan(x) | np.isnan(y))
    x_valid = x[mask]
    y_valid = y[mask]
    if x_valid.size < 2 or y_valid.size < 2:
        return float("nan")
    x_d = x_valid - x_valid.mean()
    y_d = y_valid - y_valid.mean()
    denom = np.sqrt(np.sum(x_d**2) * np.sum(y_d**2))
    if denom == 0.0:
        return float("nan")
    return float(np.sum(x_d * y_d) / denom)


def rolling_corr_vs_center(
    zcube: xr.DataArray,
    window_days: int = 90,
    min_t: int = 5,
    time_dim: str = "time",
) -> xr.DataArray:
    """Build a rolling-window correlation cube vs the center pixel."""

    ref = center_pixel_series(zcube, time_dim=time_dim)
    corr_cube = rolling_pairwise_stat_cube(
        cube=zcube,
        ref=ref,
        stat_func=pearson_corr_stat,
        window_days=window_days,
        min_t=min_t,
        time_dim=time_dim,
    )
    y_idx, x_idx = center_pixel_indices(zcube)
    corr_cube.attrs.update(
        {
            "long_name": "Rolling Pearson correlation vs center pixel",
            "reference_pixel_y": y_idx,
            "reference_pixel_x": x_idx,
        }
    )
    return corr_cube
