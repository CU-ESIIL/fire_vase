"""Backend utilities for tube detection and analysis."""

from __future__ import annotations

import numpy as np
import pandas as pd
import xarray as xr
from scipy.ndimage import generate_binary_structure, label
from shapely.geometry import MultiPoint, Polygon

from .vase import VaseDefinition, VaseSection


__all__ = [
    "compute_suitability_from_ndvi",
    "label_tubes",
    "compute_tube_metrics",
    "tube_to_vase_definition",
]


def compute_suitability_from_ndvi(
    da: xr.DataArray,
    lo: float = 0.3,
    hi: float = 0.8,
    time_dim: str = "time",
    y_dim: str = "y",
    x_dim: str = "x",
) -> xr.DataArray:
    """
    Return a boolean mask marking suitability based on NDVI thresholds.
    Suitable if lo <= NDVI <= hi.

    - Must preserve dims and coords.
    - Return dtype=bool DataArray.
    - Name it "ndvi_suitability".
    """

    for dim in (time_dim, y_dim, x_dim):
        if dim not in da.dims:
            raise ValueError(f"Dimension {dim!r} not found in input dims: {da.dims}")

    suitability = (da >= lo) & (da <= hi)
    suitability = suitability.astype(bool)
    suitability.name = "ndvi_suitability"
    return suitability


def _connectivity_structure(connectivity: int) -> np.ndarray:
    if connectivity == 6:
        return generate_binary_structure(rank=3, connectivity=1)
    if connectivity == 26:
        return generate_binary_structure(rank=3, connectivity=3)
    raise ValueError("connectivity must be either 6 or 26")


def label_tubes(
    mask_da: xr.DataArray,
    connectivity: int = 6,
    time_dim: str = "time",
    y_dim: str = "y",
    x_dim: str = "x",
) -> xr.DataArray:
    """
    Label 3D connected components (tubes) in a boolean mask.

    - Reorder to (time, y, x) internally.
    - Apply scipy.ndimage.label with connectivity=6 or 26.
    - Reconstruct a DataArray with original dims & coords.
    - Store in attrs:
        "tube_count" : number of labeled components
        "connectivity" : connectivity used
    - Name it "tube_id".
    """

    for dim in (time_dim, y_dim, x_dim):
        if dim not in mask_da.dims:
            raise ValueError(f"Dimension {dim!r} not found in mask dims: {mask_da.dims}")

    original_dims = mask_da.dims
    mask = mask_da.transpose(time_dim, y_dim, x_dim)
    structure = _connectivity_structure(connectivity)

    labeled_np, num_features = label(mask.astype(bool).values, structure=structure)

    labeled_da = xr.DataArray(
        labeled_np,
        coords={
            time_dim: mask.coords[time_dim],
            y_dim: mask.coords[y_dim],
            x_dim: mask.coords[x_dim],
        },
        dims=(time_dim, y_dim, x_dim),
        name="tube_id",
    ).transpose(*original_dims)

    labeled_da.attrs["tube_count"] = int(num_features)
    labeled_da.attrs["connectivity"] = int(connectivity)
    return labeled_da


def compute_tube_metrics(
    tube_da: xr.DataArray,
    time_dim: str = "time",
    y_dim: str = "y",
    x_dim: str = "x",
) -> pd.DataFrame:
    """
    Compute per-tube metrics:

    - duration (number of unique timesteps)
    - start & end times
    - spatial extents (min/max y, min/max x)
    - n_voxels
    - mean & max cells per timestep

    Return a pandas.DataFrame sorted by:
        duration_steps DESC, n_voxels DESC
    """

    for dim in (time_dim, y_dim, x_dim):
        if dim not in tube_da.dims:
            raise ValueError(f"Dimension {dim!r} not found in tube dims: {tube_da.dims}")

    tube_aligned = tube_da.transpose(time_dim, y_dim, x_dim)
    values = tube_aligned.values
    mask = values > 0

    if not np.any(mask):
        columns = [
            "tube_id",
            "duration_steps",
            "n_voxels",
            "time_start",
            "time_end",
            "y_min",
            "y_max",
            "x_min",
            "x_max",
            "cells_per_timestep_mean",
            "cells_per_timestep_max",
        ]
        return pd.DataFrame(columns=columns)

    t_idx, y_idx, x_idx = np.nonzero(mask)
    tube_ids = values[mask]

    time_coords = tube_aligned.coords[time_dim].values
    y_coords = tube_aligned.coords[y_dim].values
    x_coords = tube_aligned.coords[x_dim].values

    df = pd.DataFrame(
        {
            "tube_id": tube_ids,
            "time": time_coords[t_idx],
            "y": y_coords[y_idx],
            "x": x_coords[x_idx],
        }
    )

    grouped = df.groupby("tube_id")

    duration_steps = grouped["time"].nunique()
    n_voxels = grouped.size()
    time_start = grouped["time"].min()
    time_end = grouped["time"].max()
    y_min = grouped["y"].min()
    y_max = grouped["y"].max()
    x_min = grouped["x"].min()
    x_max = grouped["x"].max()

    cells_per_timestep = df.groupby(["tube_id", "time"]).size()
    cells_per_timestep_mean = cells_per_timestep.groupby(level=0).mean()
    cells_per_timestep_max = cells_per_timestep.groupby(level=0).max()

    metrics = pd.DataFrame(
        {
            "tube_id": duration_steps.index,
            "duration_steps": duration_steps.values,
            "n_voxels": n_voxels.values,
            "time_start": time_start.values,
            "time_end": time_end.values,
            "y_min": y_min.values,
            "y_max": y_max.values,
            "x_min": x_min.values,
            "x_max": x_max.values,
            "cells_per_timestep_mean": cells_per_timestep_mean.reindex(duration_steps.index).values,
            "cells_per_timestep_max": cells_per_timestep_max.reindex(duration_steps.index).values,
        }
    )

    metrics = metrics.sort_values(
        by=["duration_steps", "n_voxels"], ascending=[False, False]
    ).reset_index(drop=True)

    return metrics


def _hull_to_polygon(hull: Polygon) -> Polygon | None:
    if hull.is_empty:
        return None
    if isinstance(hull, Polygon):
        return hull

    buffered = hull.buffer(0)
    if isinstance(buffered, Polygon) and buffered.is_valid:
        return buffered

    buffered_small = hull.buffer(1e-9)
    if isinstance(buffered_small, Polygon) and buffered_small.is_valid:
        return buffered_small

    return None


def tube_to_vase_definition(
    cube: xr.DataArray,
    tube_da: xr.DataArray,
    tube_id: int,
    time_dim: str = "time",
    y_dim: str = "y",
    x_dim: str = "x",
    hull_method: str = "convex",
    interp: str = "nearest",
) -> VaseDefinition:
    """
    Convert a single tube (tube_id) into a VaseDefinition.

    For each time slice where tube_da == tube_id:
        - Extract (x, y) coords of voxels inside the tube
        - Build a polygon hull (convex hull via shapely.MultiPoint)
        - Create VaseSection(time=t, polygon=poly)

    Return a VaseDefinition(sections, interp=interp).
    Polygons must be valid; skip empty slices gracefully.
    """

    if hull_method != "convex":
        raise ValueError("Only 'convex' hull_method is supported")

    for dim in (time_dim, y_dim, x_dim):
        if dim not in tube_da.dims:
            raise ValueError(f"Dimension {dim!r} not found in tube dims: {tube_da.dims}")

    tube_aligned = tube_da.transpose(time_dim, y_dim, x_dim)
    time_coords = tube_aligned.coords[time_dim].values
    y_coords = tube_aligned.coords[y_dim].values
    x_coords = tube_aligned.coords[x_dim].values

    sections: list[VaseSection] = []

    for idx, t in enumerate(time_coords):
        slice_da = tube_aligned.isel({time_dim: idx})
        mask = slice_da == tube_id

        if not bool(mask.any()):
            continue

        ys, xs = np.nonzero(mask.values)
        points = [(x_coords[x], y_coords[y]) for y, x in zip(ys, xs)]

        if not points:
            continue

        multipoint = MultiPoint(points)
        hull = multipoint.convex_hull
        polygon = _hull_to_polygon(hull)

        if polygon is None or not polygon.is_valid:
            continue

        sections.append(VaseSection(time=t, polygon=polygon))

    if not sections:
        raise ValueError(f"Tube id {tube_id} produced no sections")

    return VaseDefinition(sections=sections, interp=interp)
