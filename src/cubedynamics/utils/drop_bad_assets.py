"""Utilities for handling intermittent remote asset failures.

The :func:`drop_bad_assets` helper is intended to work with streaming cubes
backed by remote assets (e.g., Sentinel-2 STAC items served through
``stackstac``). Occasionally, individual assets may return HTTP errors such as
403/404 during reads. Rather than failing the entire cube, we attempt to
identify and drop the problematic slices so downstream consumers can continue
operating on the remaining data.
"""

from __future__ import annotations

import logging
from typing import Iterable

import numpy as np
import xarray as xr

from .dims import _infer_time_y_x_dims


logger = logging.getLogger(__name__)


def drop_bad_assets(cube: xr.DataArray, *, sample_coords: Iterable[int] | None = None) -> xr.DataArray:
    """Return a copy of ``cube`` with slices that raise errors removed.

    Parameters
    ----------
    cube : xr.DataArray
        Input data cube to clean. Only :class:`xarray.DataArray` inputs are
        modified; other types are returned unchanged.
    sample_coords : iterable of int, optional
        Optional ``(y, x)`` coordinates to sample within each slice. Defaults to
        the first pixel if not provided. Providing an explicit coordinate allows
        callers to test a representative pixel when 0,0 falls outside the area
        of interest.

    Returns
    -------
    xr.DataArray
        The original cube when no failures are detected, or a subset with
        failing slices removed.
    """

    if not isinstance(cube, xr.DataArray):
        logger.debug(
            "drop_bad_assets: received non-DataArray input of type %s; returning unchanged",
            type(cube).__name__,
        )
        return cube

    try:
        time_dim, y_dim, x_dim = _infer_time_y_x_dims(cube)
    except Exception as exc:  # pragma: no cover - defensive guard
        logger.warning(
            "drop_bad_assets: unable to infer dimensions for %s due to %s: %r; returning input",
            cube.name or "<unnamed>",
            type(exc).__name__,
            exc,
        )
        return cube

    if time_dim is None or time_dim not in cube.dims:
        logger.debug(
            "drop_bad_assets: no time dimension detected for %s; returning unchanged",
            cube.name or "<unnamed>",
        )
        return cube

    sample_coords = tuple(sample_coords) if sample_coords is not None else (0, 0)
    if len(sample_coords) != 2:
        raise ValueError("sample_coords must be an iterable of two integers (y, x)")

    good_indices: list[int] = []
    bad_indices: list[int] = []

    time_size = int(cube.sizes.get(time_dim, 0))
    for idx in range(time_size):
        try:
            sample = cube.isel(
                {time_dim: idx, y_dim: sample_coords[0], x_dim: sample_coords[1]},
                drop=True,
            )
            np.asarray(sample)
            good_indices.append(idx)
        except Exception as exc:  # pragma: no cover - depends on external I/O
            bad_indices.append(idx)
            logger.warning(
                "drop_bad_assets: dropping %s index %s due to %s: %r",
                time_dim,
                idx,
                type(exc).__name__,
                exc,
            )

    if not bad_indices:
        return cube

    if not good_indices:
        raise RuntimeError("drop_bad_assets: all assets failed during sampling")

    cleaned = cube.isel({time_dim: good_indices})
    cleaned.attrs.update(cube.attrs)
    return cleaned


__all__ = ["drop_bad_assets"]
