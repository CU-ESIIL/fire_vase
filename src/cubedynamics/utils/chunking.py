"""Chunking and subsampling utilities."""

from __future__ import annotations

import xarray as xr

from ..stats.spatial import spatial_coarsen_mean


def coarsen_and_stride(
    cube: xr.DataArray,
    coarsen_factor: int = 1,
    time_stride: int = 1,
    y_dim: str = "y",
    x_dim: str = "x",
    time_dim: str = "time",
) -> xr.DataArray:
    """Optionally coarsen spatially and subsample in time."""

    result = cube
    if coarsen_factor > 1:
        result = spatial_coarsen_mean(
            result,
            factor_y=coarsen_factor,
            factor_x=coarsen_factor,
            y_dim=y_dim,
            x_dim=x_dim,
        )
    if time_stride > 1:
        result = result.isel({time_dim: slice(0, None, time_stride)})
    return result
