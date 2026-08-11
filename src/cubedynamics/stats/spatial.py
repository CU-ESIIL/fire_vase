"""Spatial cube math primitives."""

from __future__ import annotations

from typing import Hashable, Literal

import xarray as xr

from ..config import X_DIM, Y_DIM


def spatial_coarsen_mean(
    da: xr.DataArray,
    factor_y: int = 1,
    factor_x: int = 1,
    y_dim: Hashable = Y_DIM,
    x_dim: Hashable = X_DIM,
) -> xr.DataArray:
    """Coarsen a DataArray by averaging blocks in the spatial dimensions."""

    if factor_y <= 0 or factor_x <= 0:
        raise ValueError("Coarsening factors must be positive integers")
    if factor_y == 1 and factor_x == 1:
        return da
    return da.coarsen({y_dim: factor_y, x_dim: factor_x}, boundary="trim").mean()


def spatial_smooth_mean(
    da: xr.DataArray,
    kernel_size: int = 3,
    y_dim: Hashable = Y_DIM,
    x_dim: Hashable = X_DIM,
) -> xr.DataArray:
    """Apply a boxcar spatial mean filter over the y/x dimensions."""

    if kernel_size < 1:
        raise ValueError("kernel_size must be >= 1")
    if kernel_size % 2 == 0:
        raise ValueError("kernel_size must be an odd integer")
    return da.rolling(
        {y_dim: kernel_size, x_dim: kernel_size}, center=True
    ).mean()


def mask_by_threshold(
    da: xr.DataArray,
    threshold: float,
    direction: Literal[">", ">=", "<", "<="] = ">",
) -> xr.DataArray:
    """Create a boolean mask for values that satisfy a threshold condition."""

    if direction == ">":
        mask = da > threshold
    elif direction == ">=":
        mask = da >= threshold
    elif direction == "<":
        mask = da < threshold
    elif direction == "<=":
        mask = da <= threshold
    else:
        raise ValueError("direction must be one of '>', '>=', '<', '<='")

    mask.attrs = {
        **da.attrs,
        "long_name": f"mask ({da.name or 'variable'} {direction} {threshold})",
    }
    return mask
