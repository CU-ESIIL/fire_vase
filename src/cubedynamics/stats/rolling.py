"""Rolling-window computation utilities."""

from __future__ import annotations

from collections.abc import Callable

import xarray as xr
import numpy as np

StatFunc = Callable[[np.ndarray, np.ndarray], float]


def _empty_result(cube: xr.DataArray, time_dim: str, end_dim: str) -> xr.DataArray:
    template = cube.isel({time_dim: slice(0, 0)}).rename({time_dim: end_dim})
    return xr.full_like(template, np.nan, dtype="float32")


def rolling_pairwise_stat_cube(
    cube: xr.DataArray,
    ref: xr.DataArray,
    stat_func: StatFunc,
    window_days: int,
    min_t: int = 5,
    time_dim: str = "time",
) -> xr.DataArray:
    """Compute a rolling-window pairwise statistic vs a reference time series."""

    time_coord = cube[time_dim]
    end_dim = f"{time_dim}_window_end"
    results: list[xr.DataArray] = []
    end_times: list[np.datetime64] = []

    for t_end in time_coord.values:
        t_start = t_end - np.timedelta64(window_days, "D")
        cube_sub = cube.sel({time_dim: slice(t_start, t_end)})
        ref_sub = ref.sel({time_dim: slice(t_start, t_end)})
        if cube_sub.sizes.get(time_dim, 0) < min_t or ref_sub.sizes.get(time_dim, 0) < min_t:
            continue

        stat = xr.apply_ufunc(
            stat_func,
            cube_sub,
            ref_sub,
            input_core_dims=[[time_dim], [time_dim]],
            output_core_dims=[[]],
            vectorize=True,
            dask="parallelized",
            output_dtypes=["float32"],
        )
        stat = stat.rename(cube.name or "stat")
        results.append(stat.expand_dims({end_dim: [t_end]}))
        end_times.append(t_end)

    if not results:
        return _empty_result(cube, time_dim=time_dim, end_dim=end_dim)

    cube_out = xr.concat(results, dim=end_dim)
    cube_out = cube_out.assign_coords({end_dim: np.array(end_times)})
    cube_out.attrs.update(
        {
            "window_days": window_days,
            "min_time_points": min_t,
        }
    )
    return cube_out
