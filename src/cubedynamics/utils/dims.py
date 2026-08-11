"""Utilities for inferring canonical cube dimensions."""

from __future__ import annotations

from typing import Optional, Tuple

import numpy as np
import xarray as xr

from cubedynamics.config import TIME_DIM


TimeYX = Tuple[Optional[str], str, str]


def _infer_time_y_x_dims(obj: xr.DataArray | xr.Dataset) -> TimeYX:
    """Infer time, y, and x dimension names from a cube-like object.

    The function prefers explicit time-like names (e.g., ``time`` or ``t``), then
    looks for datetime-like coordinates, and finally falls back to the longest
    dimension. Spatial dimensions are chosen from the remaining axes, ordered as
    the last two encountered.

    Parameters
    ----------
    obj : xr.DataArray or xr.Dataset
        Input data structure containing at least two dimensions.

    Returns
    -------
    tuple[str | None, str, str]
        A tuple of ``(time_dim, y_dim, x_dim)``. ``time_dim`` may be ``None``
        when the array is only 2D.
    """

    if isinstance(obj, xr.Dataset):
        if len(obj.data_vars) == 1:
            da = obj[list(obj.data_vars)[0]]
        else:
            raise ValueError(
                "Dataset must contain exactly one data variable or specify a variable name."
            )
    elif isinstance(obj, xr.DataArray):
        da = obj
    else:
        raise TypeError(
            "_infer_time_y_x_dims expects an xarray.DataArray or Dataset; "
            f"received {type(obj)!r}."
        )

    dims = list(da.dims)
    if len(dims) < 2:
        raise ValueError(
            f"Expected at least 2 dimensions to infer spatial axes, found dims={dims}."
        )

    # 1. Prefer explicit time-like names
    time_candidates = {TIME_DIM.lower(), "time", "t", "date", "datetime"}
    time_dim: str | None = None
    for dim in dims:
        if dim.lower() in time_candidates:
            time_dim = dim
            break

    # 2. Look for datetime-like coordinate values
    if time_dim is None:
        for dim in dims:
            if dim in da.coords:
                coord = da.coords[dim]
                if np.issubdtype(coord.dtype, np.datetime64):
                    time_dim = dim
                    break

    # 3. Fall back to the longest dimension for 3D+ arrays
    if time_dim is None and len(dims) >= 3:
        sizes = {dim: int(da.sizes.get(dim, 0)) for dim in dims}
        # Choose the dimension with the largest size (stable order via dims list)
        time_dim = max(dims, key=lambda d: sizes.get(d, 0))

    spatial_dims = [dim for dim in dims if dim != time_dim]
    if len(spatial_dims) < 2:
        raise ValueError(
            f"Could not infer spatial dimensions from dims={dims}; resolved time_dim={time_dim}."
        )

    y_dim, x_dim = spatial_dims[-2], spatial_dims[-1]
    return time_dim, y_dim, x_dim


__all__ = ["_infer_time_y_x_dims", "TimeYX"]
