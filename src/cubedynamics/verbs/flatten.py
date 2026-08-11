"""Shape-changing verbs for flattening cubes."""

from __future__ import annotations

import xarray as xr


def flatten_space(
    time_dim: str = "time",
    y_dim: str = "y",
    x_dim: str = "x",
    new_dim: str = "pixel",
):
    """Flatten spatial dimensions (``y`` and ``x``) into a ``pixel`` dimension.

    This breaks the cube layout (time, y, x) -> (time, pixel) which is useful for
    time-series or ML preprocessing but incompatible with Lexcube visualizations.
    """

    def _op(obj: xr.Dataset | xr.DataArray) -> xr.Dataset | xr.DataArray:
        missing = [dim for dim in (y_dim, x_dim) if dim not in obj.dims]
        if missing:
            raise ValueError(
                f"flatten_space requires dims {y_dim!r} and {x_dim!r}; missing {missing}"
            )
        return obj.stack({new_dim: (y_dim, x_dim)})

    return _op


def flatten_cube(time_dim: str = "time", sample_dim: str = "sample"):
    """Flatten all non-time dimensions into a single ``sample`` dimension.

    This is an experimental modeling helper that reshapes the cube into (time,
    sample) so that each "sample" row can be consumed by ML tooling. It
    intentionally discards the cube layout and should not be passed to
    :func:`cubedynamics.verbs.show_cube_lexcube` afterwards.
    """

    def _op(obj: xr.Dataset | xr.DataArray) -> xr.Dataset | xr.DataArray:
        if time_dim not in obj.dims:
            raise ValueError(f"flatten_cube requires {time_dim!r} in dims {tuple(obj.dims)}")
        other_dims = tuple(dim for dim in obj.dims if dim != time_dim)
        if not other_dims:
            return obj.rename({time_dim: sample_dim})
        return obj.stack({sample_dim: other_dims})

    return _op


__all__ = ["flatten_space", "flatten_cube"]
