"""I/O helpers for pipe chains."""

from __future__ import annotations

import xarray as xr


def to_netcdf(path: str, **to_netcdf_kwargs):
    """Factory for a pipeable ``.to_netcdf`` side-effect operation."""

    def _inner(da: xr.DataArray | xr.Dataset):
        da.to_netcdf(path, **to_netcdf_kwargs)
        return da

    return _inner


__all__ = ["to_netcdf"]
