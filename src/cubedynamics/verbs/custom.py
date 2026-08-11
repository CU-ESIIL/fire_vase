"""Generic custom-function verbs."""

from __future__ import annotations

from collections.abc import Callable

import xarray as xr


def apply(
    func: Callable[[xr.DataArray | xr.Dataset], xr.DataArray | xr.Dataset],
    /,
    **kwargs,
):
    """Return a verb that applies ``func`` to the incoming cube.

    This is the generic "raster calculator" entry point: pass any callable that
    accepts an :class:`xarray.DataArray` or :class:`xarray.Dataset` and returns a
    compatible object. Shape changes are entirely controlled by ``func``; the
    verb simply forwards the cube and keyword arguments.
    """

    def _op(obj: xr.DataArray | xr.Dataset) -> xr.DataArray | xr.Dataset:
        return func(obj, **kwargs)

    return _op


__all__ = ["apply"]
