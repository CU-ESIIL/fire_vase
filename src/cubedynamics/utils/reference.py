"""Reference pixel helpers."""

from __future__ import annotations

import xarray as xr


def center_pixel_indices(
    cube: xr.DataArray,
    y_dim: str = "y",
    x_dim: str = "x",
) -> tuple[int, int]:
    """Return the (y_idx, x_idx) of the center pixel in a cube."""

    y_idx = cube.sizes[y_dim] // 2
    x_idx = cube.sizes[x_dim] // 2
    return y_idx, x_idx


def center_pixel_series(
    cube: xr.DataArray,
    y_dim: str = "y",
    x_dim: str = "x",
    time_dim: str = "time",
) -> xr.DataArray:
    """Extract the time series at the center pixel of a 3D cube."""

    y_idx, x_idx = center_pixel_indices(cube, y_dim=y_dim, x_dim=x_dim)
    return cube.isel({y_dim: y_idx, x_dim: x_idx})
