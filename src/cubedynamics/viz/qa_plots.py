"""Quality-assurance plotting helpers."""

from __future__ import annotations

import matplotlib.pyplot as plt
import xarray as xr


def _spatial_dims(cube: xr.DataArray, dims: list[str] | None = None) -> list[str]:
    """Return dimensions that should be collapsed for a time-series QA plot."""

    if dims is not None:
        missing = [dim for dim in dims if dim not in cube.dims]
        if missing:
            raise ValueError(f"Dimensions {missing!r} not found in cube dims: {cube.dims!r}")
        return dims

    if not cube.dims:
        raise ValueError("Cube must have at least one dimension")

    spatial = [dim for dim in cube.dims if dim not in (cube.dims[0],)]
    if not spatial:
        raise ValueError("Cube must have spatial dimensions to aggregate over")
    return spatial


def plot_median_over_space(
    cube: xr.DataArray,
    ax: plt.Axes | None = None,
    dims: list[str] | None = None,
    ylabel: str = "",
    title: str = "",
    ylim: tuple[float, float] | None = None,
) -> plt.Axes:
    """Plot the median over space of a 3D cube as a time series."""

    dims = _spatial_dims(cube, dims)
    ts = cube.median(dim=dims, skipna=True)
    if ax is None:
        _, ax = plt.subplots(figsize=(8, 3))
    ts.to_series().plot(ax=ax)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.grid(True, alpha=0.3)
    if ylim is not None:
        ax.set_ylim(*ylim)
    if "long_name" in cube.attrs:
        ax.set_xlabel(cube.dims[0])
    return ax


def plot_tail_dependence_over_time(
    bottom_tail: xr.DataArray,
    top_tail: xr.DataArray | None = None,
    diff_tail: xr.DataArray | None = None,
    ax: plt.Axes | None = None,
    dims: list[str] | None = None,
    title: str = "Median tail-dependence synchrony through time",
    ylabel: str = "Median tail dependence",
    ylim: tuple[float, float] | None = None,
    labels: tuple[str, str, str] = ("bottom half", "top half", "bottom - top"),
) -> plt.Axes:
    """Plot spatial median tail-dependence synchrony traces through time.

    The first dimension is treated as the rolling-window time axis and all
    remaining dimensions are aggregated with a spatial median by default.
    """

    spatial_dims = _spatial_dims(bottom_tail, dims)
    if len(labels) != 3:
        raise ValueError("labels must contain bottom, top, and difference labels")
    if ax is None:
        _, ax = plt.subplots(figsize=(8, 3))

    series = [
        (bottom_tail, labels[0]),
        (top_tail, labels[1]),
        (diff_tail, labels[2]),
    ]
    for cube, label in series:
        if cube is None:
            continue
        if cube.dims != bottom_tail.dims:
            raise ValueError(
                f"{label!r} cube dims {cube.dims!r} do not match bottom_tail dims "
                f"{bottom_tail.dims!r}"
            )
        cube.median(dim=spatial_dims, skipna=True).to_series().plot(ax=ax, label=label)

    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.set_xlabel(bottom_tail.dims[0])
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best")
    if ylim is not None:
        ax.set_ylim(*ylim)
    return ax
