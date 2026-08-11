"""Cube alignment helpers for biological and climate cubes."""

from __future__ import annotations

import xarray as xr

from ..config import TIME_DIM, X_DIM, Y_DIM


def align_cube(
    cube: xr.DataArray | xr.Dataset,
    *,
    like: xr.DataArray | xr.Dataset,
    spatial_method: str = "nearest",
    temporal_method: str = "nearest",
    tolerance: str | None = None,
) -> xr.DataArray | xr.Dataset:
    """Align a cube to another cube's time/y/x grid."""

    if spatial_method not in {"nearest", "linear"}:
        raise ValueError("spatial_method must be 'nearest' or 'linear'")
    if temporal_method not in {"nearest", "pad", "backfill"}:
        raise ValueError("temporal_method must be 'nearest', 'pad', or 'backfill'")
    indexers = {}
    for dim in (Y_DIM, X_DIM):
        if dim in cube.dims and dim in like.coords:
            indexers[dim] = like[dim]
    if TIME_DIM in cube.dims and TIME_DIM in like.coords:
        indexers[TIME_DIM] = like[TIME_DIM]
    aligned = cube.interp(
        {dim: coord for dim, coord in indexers.items() if dim in (Y_DIM, X_DIM)},
        method=spatial_method,
    )
    if TIME_DIM in indexers:
        aligned = aligned.reindex(
            {TIME_DIM: indexers[TIME_DIM]},
            method=temporal_method,
            tolerance=tolerance,
        )
    aligned.attrs.update(getattr(cube, "attrs", {}))
    aligned.attrs.update(
        {
            "analysis": "align_cube",
            "spatial_method": spatial_method,
            "temporal_method": temporal_method,
            "tolerance": str(tolerance),
            "aligned_like": getattr(like, "name", None) or "cube",
        }
    )
    return aligned
