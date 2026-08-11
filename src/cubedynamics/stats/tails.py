"""Tail dependence utilities."""

from __future__ import annotations

from typing import Sequence, Tuple

import numpy as np
import xarray as xr

from ..utils.reference import center_pixel_indices, center_pixel_series


def _rank_1d(a: np.ndarray) -> np.ndarray:
    """Return 1-based ranks, assigning the average rank to tied values."""

    order = np.argsort(a, kind="mergesort")
    sorted_values = a[order]
    ranks = np.empty(a.size, dtype=float)

    start = 0
    while start < a.size:
        stop = start + 1
        while stop < a.size and sorted_values[stop] == sorted_values[start]:
            stop += 1
        average_rank = (start + 1 + stop) / 2.0
        ranks[order[start:stop]] = average_rank
        start = stop
    return ranks


def partial_tail_spearman(
    x: np.ndarray,
    y: np.ndarray,
    b: float = 0.5,
    min_t: int = 5,
) -> Tuple[float, float, float]:
    """Spearman synchrony below and above per-series quantile thresholds.

    With the default ``b=0.5``, the lower set contains observations where both
    series are at or below their own median. The upper set contains observations
    where both series are above their own median. Correlations are calculated
    independently within those two sets.
    """

    if not 0.0 < b <= 0.5:
        raise ValueError("b must be greater than 0 and no greater than 0.5")

    mask = ~(np.isnan(x) | np.isnan(y))
    x_valid = x[mask]
    y_valid = y[mask]
    n = x_valid.size
    if n < min_t:
        return (np.nan, np.nan, np.nan)

    lower_x = np.quantile(x_valid, b)
    lower_y = np.quantile(y_valid, b)
    upper_x = np.quantile(x_valid, 1.0 - b)
    upper_y = np.quantile(y_valid, 1.0 - b)
    lower_mask = (x_valid <= lower_x) & (y_valid <= lower_y)
    upper_mask = (x_valid > upper_x) & (y_valid > upper_y)

    def _tail_corr(mask: np.ndarray) -> float:
        if np.count_nonzero(mask) < min_t:
            return float("nan")
        u = _rank_1d(x_valid[mask])
        v = _rank_1d(y_valid[mask])
        u_centered = u - u.mean()
        v_centered = v - v.mean()
        denom = np.sqrt(np.sum(u_centered**2) * np.sum(v_centered**2))
        if denom <= 0 or np.isnan(denom):
            return float("nan")
        return float(np.sum(u_centered * v_centered) / denom)

    bottom = _tail_corr(lower_mask)
    top = _tail_corr(upper_mask)
    diff = bottom - top if not np.isnan(bottom) and not np.isnan(top) else np.nan
    return (bottom, top, diff)


def rolling_tail_dep_vs_center(
    zcube: xr.DataArray,
    window_days: int = 90,
    min_t: int = 5,
    b: float = 0.5,
    time_dim: str = "time",
    output_stride: int = 1,
    output_times: Sequence[object] | None = None,
) -> tuple[xr.DataArray, xr.DataArray, xr.DataArray]:
    """Build rolling median-split synchrony cubes vs the center pixel.

    ``b=0.5`` partitions each pixel/reference pair using their respective
    rolling-window medians. Bottom synchrony is calculated where both values
    are at or below their medians; top synchrony is calculated where both are
    above their medians.

    ``output_stride`` evaluates every Nth input timestamp. ``output_times`` can
    provide an explicit set of rolling window end timestamps, which is useful
    when a long record is processed in bounded batches.
    """

    if output_stride < 1:
        raise ValueError("output_stride must be at least 1")

    ref = center_pixel_series(zcube, time_dim=time_dim)
    end_dim = f"{time_dim}_window_end"
    bottoms: list[xr.DataArray] = []
    tops: list[xr.DataArray] = []
    diffs: list[xr.DataArray] = []
    end_times: list[np.datetime64] = []

    if output_times is None:
        target_times = zcube[time_dim].values[::output_stride]
    else:
        target_times = np.asarray(list(output_times), dtype="datetime64[ns]")

    for t_end in target_times:
        t_start = t_end - np.timedelta64(window_days, "D")
        cube_sub = zcube.sel({time_dim: slice(t_start, t_end)})
        ref_sub = ref.sel({time_dim: slice(t_start, t_end)})
        if cube_sub.sizes.get(time_dim, 0) < min_t:
            continue
        if cube_sub.chunks is not None:
            cube_sub = cube_sub.chunk({time_dim: -1})
            ref_sub = ref_sub.chunk({time_dim: -1})
        bottom, top, diff = xr.apply_ufunc(
            partial_tail_spearman,
            cube_sub,
            ref_sub,
            input_core_dims=[[time_dim], [time_dim]],
            output_core_dims=[[], [], []],
            vectorize=True,
            dask="parallelized",
            output_dtypes=[np.float32, np.float32, np.float32],
            kwargs={"b": b, "min_t": min_t},
        )
        bottoms.append(bottom.expand_dims({end_dim: [t_end]}))
        tops.append(top.expand_dims({end_dim: [t_end]}))
        diffs.append(diff.expand_dims({end_dim: [t_end]}))
        end_times.append(t_end)

    if not end_times:
        template = zcube.isel({time_dim: slice(0, 0)}).rename({time_dim: end_dim})
        empty = xr.full_like(template, np.nan, dtype="float32")
        return empty, empty.copy(), empty.copy()

    bottom_cube = xr.concat(bottoms, dim=end_dim)
    top_cube = xr.concat(tops, dim=end_dim)
    diff_cube = xr.concat(diffs, dim=end_dim)
    coords = {end_dim: np.array(end_times)}
    bottom_cube = bottom_cube.assign_coords(coords)
    top_cube = top_cube.assign_coords(coords)
    diff_cube = diff_cube.assign_coords(coords)

    y_idx, x_idx = center_pixel_indices(zcube)
    for da in (bottom_cube, top_cube, diff_cube):
        da.attrs.update(
            {
                "reference_pixel_y": y_idx,
                "reference_pixel_x": x_idx,
                "window_days": window_days,
                "min_time_points": min_t,
                "tail_b": b,
                "split_quantile": b,
                "split_method": "per_series_quantile",
                "output_stride": output_stride,
            }
        )

    bottom_cube.attrs["long_name"] = "Below-median Spearman synchrony vs center"
    top_cube.attrs["long_name"] = "Above-median Spearman synchrony vs center"
    diff_cube.attrs["long_name"] = "Below minus above median Spearman synchrony"
    return bottom_cube, top_cube, diff_cube
