"""Pipe-friendly biological cube verbs."""

from __future__ import annotations

from ..biology.align import align_cube as _align_cube
from ..biology.rasterize import rasterize_observations as _rasterize_observations


def rasterize_observations(
    observations,
    *,
    template,
    time_col: str = "date",
    y_col: str = "y",
    x_col: str = "x",
    value_col: str = "value",
    reducer: str = "sum",
    name: str | None = None,
):
    """Rasterize observation rows into a biological cube."""

    return _rasterize_observations(
        observations,
        template=template,
        time_col=time_col,
        y_col=y_col,
        x_col=x_col,
        value_col=value_col,
        reducer=reducer,
        name=name,
    )


def align_cube(
    *,
    like,
    spatial_method: str = "nearest",
    temporal_method: str = "nearest",
    tolerance: str | None = None,
):
    """Align a cube to another cube's grid."""

    def _op(obj):
        return _align_cube(
            obj,
            like=like,
            spatial_method=spatial_method,
            temporal_method=temporal_method,
            tolerance=tolerance,
        )

    return _op


__all__ = ["align_cube", "rasterize_observations"]
