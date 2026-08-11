"""Lexcube visualization helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import xarray as xr

from ..config import TIME_DIM, X_DIM, Y_DIM

if TYPE_CHECKING:  # pragma: no cover - import-time dependency hint only
    import lexcube


def show_cube_lexcube(
    cube: xr.DataArray,
    title: str = "",
    cmap: str = "RdBu_r",
    vmin: float | None = None,
    vmax: float | None = None,
) -> "lexcube.Cube3DWidget":
    """Create a Lexcube Cube3DWidget from a 3D cube (time, y, x)."""

    cube = _prepare_lexcube_cube(cube)

    import lexcube

    widget = lexcube.Cube3DWidget(
        cube,
        title=title,
        cmap=cmap,
        vmin=vmin,
        vmax=vmax,
    )
    return widget


def _prepare_lexcube_cube(cube: xr.DataArray) -> xr.DataArray:
    """Validate and normalize a cube before handing it to Lexcube."""

    expected_dims = {TIME_DIM, Y_DIM, X_DIM}
    if cube.ndim != 3 or set(cube.dims) != expected_dims:
        raise ValueError(
            "Lexcube visualization requires dims exactly (time, y, x); "
            f"received dims {cube.dims}"
        )

    prepared = cube.transpose(TIME_DIM, Y_DIM, X_DIM).copy(deep=False)

    # Lexcube treats integer time values in [0, 365] as day-of-year data and
    # reads encoding["source"] while doing that detection. In-memory xarray
    # objects often do not have a source, so provide a harmless placeholder.
    if _has_integer_day_of_year_like_time(prepared) and "source" not in prepared.encoding:
        prepared.encoding["source"] = ""

    return prepared


def _has_integer_day_of_year_like_time(cube: xr.DataArray) -> bool:
    if TIME_DIM not in cube.coords:
        return False

    time = cube.coords[TIME_DIM]
    if not np.issubdtype(time.dtype, np.integer):
        return False
    if time.size == 0:
        return False

    return bool(time.min().item() >= 0 and time.max().item() <= 365)
