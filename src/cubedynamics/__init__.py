"""Cubedynamics public surface and convenience helpers.

This module is part of the CubeDynamics "grammar-of-cubes":
- Data loaders produce xarray objects (often dask-backed) with dims ``(time, y, x)``.
- Verbs are pipe-friendly transformations: cube → cube (or cube → scalar/plot side-effect).
- Plotting follows a grammar-of-graphics model (aes, geoms, stats, scales, themes).

Canonical API:
- :func:`cubedynamics.piping.pipe` and :class:`cubedynamics.piping.Pipe`
- Verb namespace at :mod:`cubedynamics.verbs`
- Data loaders: :mod:`cubedynamics.data.gridmet`, :mod:`cubedynamics.data.prism`,
  :mod:`cubedynamics.data.sentinel2`
- Semantic variable shortcuts: :mod:`cubedynamics.variables`

Documentation inventory:
- Stable, user-facing surface: :mod:`cubedynamics` (this module),
  :mod:`cubedynamics.verbs` (importable as ``v``), :func:`cubedynamics.piping.pipe`,
  :mod:`cubedynamics.variables`, and :mod:`cubedynamics.data.*` loaders.
- Legacy/deprecated shims: :mod:`cubedynamics.sentinel`, :mod:`cubedynamics.ops.*`,
  :mod:`cubedynamics.viewers.*`; these remain importable but emit runtime warnings
  and delegate to the canonical verbs/loaders.
- Advanced/internal utilities: :mod:`cubedynamics.streaming.*`,
  :mod:`cubedynamics.plotting.*`, :mod:`cubedynamics.ops_fire.*`. These are
  documented for contributors but may change more frequently.
"""

from __future__ import annotations

from .version import __version__
from .piping import Pipe, pipe
from . import verbs
from . import tubes
from .demo_vase import demo
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import xarray as xr

# Legacy, fully implemented APIs -------------------------------------------------
from .data.gridmet import load_gridmet_cube
from .data.prism import load_prism_cube
from .data.sentinel2 import load_s2_cube, load_s2_ndvi_cube
from .verbs.plot import plot as _plot_verb
from .variables import (
    temperature,
    temperature_anomaly,
    temperature_max,
    temperature_min,
    ndvi_chunked,
    ndvi,
)
from .sentinel import (
    load_sentinel2_bands_cube,
    load_sentinel2_cube,
    load_sentinel2_ndvi_cube,
    load_sentinel2_ndvi_zscore_cube,
)

# Streaming-first stubs for the new architecture ---------------------------------
from .streaming.global_climate import stream_global_climate_cube
from .streaming.gridmet import stream_gridmet_to_cube
from .prism_streaming import stream_prism_to_cube
from .correlation_cubes import correlation_cube as streaming_correlation_cube

# Legacy helpers retained for backward compatibility. Prefer the verb-first API.
from .indices.vegetation import compute_ndvi_from_s2
from .stats.anomalies import (
    rolling_mean,
    temporal_anomaly,
    temporal_difference,
    zscore_over_time,
)
from .stats.correlation import rolling_corr_vs_center
from .stats.spatial import mask_by_threshold, spatial_coarsen_mean, spatial_smooth_mean
from .stats.tails import rolling_tail_dep_vs_center
from .utils.chunking import coarsen_and_stride
from .ops import (
    anomaly,
    month_filter,
    variance,
    correlation_cube,
    to_netcdf,
    zscore,
    ndvi_from_s2,
)

__all__ = [
    "__version__",
    "Pipe",
    "pipe",
    "verbs",
    "plot",
    "load_gridmet_cube",
    "load_prism_cube",
    "load_s2_cube",
    "load_s2_ndvi_cube",
    "stream_global_climate_cube",
    "stream_gridmet_to_cube",
    "stream_prism_to_cube",
    "streaming_correlation_cube",
    "temperature",
    "temperature_min",
    "temperature_max",
    "temperature_anomaly",
    "ndvi_chunked",
    "ndvi",
]


def plot(
    cube: xr.DataArray,
    time_dim: str | None = "time",
    cmap: str = "viridis",
    clim: tuple[float, float] | None = None,
    camera: dict | None = None,
    **kwargs,
):
    """Plot a cube without explicitly building a pipe chain.

    Parameters
    ----------
    cube : xarray.DataArray
        Input cube with dims ``(time, y, x)``. Dask-backed arrays are supported
        and stay lazy; the viewer itself is small metadata/HTML.
    time_dim : str, optional
        Name of the temporal dimension. Defaults to ``"time"``.
    cmap : str, optional
        Matplotlib colormap name to use for the fill scale.
    clim : tuple of float, optional
        Value limits passed through to the plotting verb for consistent color
        scaling.
    camera : dict, optional
        Plotly-style camera configuration for the initial cube view.
    **kwargs : Any
        Forwarded to :func:`cubedynamics.verbs.plot.plot` for advanced layout
        control.

    Returns
    -------
    CubePlot or xarray.DataArray
        The underlying plot verb returns a :class:`~cubedynamics.plotting.cube_plot.CubePlot`
        viewer while leaving the original cube intact so it can continue through
        downstream computations.

    Notes
    -----
    This is a thin wrapper around :func:`cubedynamics.verbs.plot.plot` for
    users who prefer a single function call instead of the pipe syntax. It does
    not trigger computation for dask-backed data beyond what the viewer needs
    to summarize.

    Examples
    --------
    >>> import cubedynamics as cd
    >>> cube = cd.load_gridmet_cube(lat=40.0, lon=-105.0, start="2005-01-01", end="2005-01-10", variable="tmmx")
    >>> viewer = cd.plot(cube)
    >>> cube  # cube is unchanged and can be reused

    See Also
    --------
    cubedynamics.piping.pipe
    cubedynamics.verbs.plot.plot
    """

    return _plot_verb(
        cube,
        time_dim=time_dim,
        cmap=cmap,
        clim=clim,
        camera=camera,
        **kwargs,
    )


from .ops_io.gridmet_api import gridmet
from .ops_fire.fired_api import fired_event
from .fire_time_hull import FireEventDaily, FireHull, TimeHull

__all__ += ["gridmet", "fired_event", "FireEventDaily", "FireHull", "TimeHull"]


def show_cube_lexcube(*args, **kwargs):
    """Lazy wrapper to avoid importing visualization stack at package import time."""

    from .viz.lexcube_viz import show_cube_lexcube as _show_cube_lexcube

    return _show_cube_lexcube(*args, **kwargs)


def plot_median_over_space(*args, **kwargs):
    """Lazy wrapper to avoid importing visualization stack at package import time."""

    from .viz.qa_plots import plot_median_over_space as _plot_median_over_space

    return _plot_median_over_space(*args, **kwargs)
