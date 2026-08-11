"""Plotting verb for displaying cubes via :class:`CubePlot`.

This module is part of the CubeDynamics "grammar-of-cubes":
- Data loaders produce xarray objects (often dask-backed) with dims ``(time, y, x)``.
- Verbs are pipe-friendly transformations: cube → cube (or cube → scalar/plot side-effect).
- Plotting follows a grammar-of-graphics model (aes, geoms, stats, scales, themes).

Canonical API:
- :func:`cubedynamics.verbs.plot.plot` (side-effect verb returning the viewer)
- :class:`cubedynamics.plotting.cube_plot.CubePlot`
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import overload

import logging

import xarray as xr

from cubedynamics.plotting.axis_rig import AxisRigSpec
from cubedynamics.plotting.cube_plot import (
    CubePlot,
    ScaleFillContinuous,
    plotly_camera_to_coord,
    resolve_camera,
)
from cubedynamics.streaming import VirtualCube
from cubedynamics.utils import _infer_time_y_x_dims
from ..piping import Verb
from ..vase import VaseDefinition, extract_vase_from_attrs

__all__ = ["plot"]


logger = logging.getLogger(__name__)


@dataclass
class PlotOptions:
    title: str | None = None
    cmap: str = "viridis"
    size_px: int | None = None
    thin_time_factor: int = 4
    time_dim: str | None = None
    clim: tuple[float, float] | None = None
    camera: dict | None = None
    axis_rig: bool | AxisRigSpec = True
    fig_id: int | None = None
    fig_title: str | None = None
    fig_text: str | None = None


@overload
def plot(
    da: xr.DataArray | VirtualCube,
    *,
    title: str | None = None,
    cmap: str = "viridis",
    size_px: int | None = None,
    thin_time_factor: int = 4,
    time_dim: str | None = None,
    clim: tuple[float, float] | None = None,
    camera: dict | None = None,
    axis_rig: bool | AxisRigSpec = True,
    fig_id: int | None = None,
    fig_title: str | None = None,
    fig_text: str | None = None,
) -> xr.DataArray | VirtualCube:
    ...


@overload
def plot(
    *,
    title: str | None = None,
    cmap: str = "viridis",
    size_px: int | None = None,
    thin_time_factor: int = 4,
    time_dim: str | None = None,
    clim: tuple[float, float] | None = None,
    camera: dict | None = None,
    axis_rig: bool | AxisRigSpec = True,
    fig_id: int | None = None,
    fig_title: str | None = None,
    fig_text: str | None = None,
) -> Verb:
    ...


def plot(
    da: xr.DataArray | VirtualCube | None = None,
    *,
    title: str | None = None,
    cmap: str = "viridis",
    size_px: int | None = None,
    thin_time_factor: int = 4,
    time_dim: str | None = None,
    clim: tuple[float, float] | None = None,
    camera: dict | None = None,
    axis_rig: bool | AxisRigSpec = True,
    fig_id: int | None = None,
    fig_title: str | None = None,
    fig_text: str | None = None,
):
    """Plot a cube using the CubePlot grammar and keep the cube flowing.

    Grammar contract
    ----------------
    Side-effect verb (cube → cube, produces output). When called with ``da`` it
    immediately builds a :class:`~cubedynamics.plotting.cube_plot.CubePlot` and
    returns it while leaving the cube unchanged. When called without ``da`` it
    returns a pipe-ready :class:`~cubedynamics.piping.Verb` so you can write
    ``pipe(cube) | v.plot(...)``.

    Parameters
    ----------
    da : xarray.DataArray or VirtualCube, optional
        Input cube with dims ``(time, y, x)``. If ``None``, a verb is returned.
    title : str, optional
        Override the viewer title. Defaults to ``<name> time × y × x cube``.
    cmap : str, default "viridis"
        Colormap used for the fill scale.
    size_px : int, optional
        Pixel size for each facet tile. If omitted, the viewer uses responsive sizing.
    thin_time_factor : int, default 4
        Decimation factor for time frames to keep the viewer responsive.
    time_dim : str, optional
        Name of the temporal dimension. Inferred when not provided.
    clim : tuple of float, optional
        Color limits for the continuous scale.
    camera : dict, optional
        Plotly-style camera configuration used to set the initial cube view.
        When omitted, a front-right, zoomed-out default is applied.
    fig_id, fig_title, fig_text : optional
        Caption metadata used by the viewer export helpers.

    Returns
    -------
    CubePlot or Verb
        Viewer ready for notebook display, or a pipe-ready verb when ``da`` is
        omitted.

    Notes
    -----
    The viewer preserves dask-backed arrays and only samples minimal data for
    thumbnails, keeping streaming behavior intact. If a vase is attached in
    ``da.attrs['vase']`` a thin outline overlay is attempted. The original cube
    is returned unchanged so pipe chains continue.

    Examples
    --------
    Direct call:
    >>> import cubedynamics as cd
    >>> cube = cd.load_gridmet_cube(lat=40.0, lon=-105.0, start="2005-01-01", end="2005-01-05", variable="tmmx")
    >>> viewer = cd.verbs.plot.plot(cube, cmap="magma")

    Pipe style:
    >>> from cubedynamics import pipe, verbs as v
    >>> viewer = (pipe(cube) | v.plot(cmap="magma")).unwrap()
    >>> cube  # cube still available

    See Also
    --------
    cubedynamics.plotting.cube_plot.CubePlot
    cubedynamics.verbs.plot_mean.plot_mean
    cubedynamics.piping.pipe
    """

    opts = PlotOptions(
        title=title,
        cmap=cmap,
        size_px=size_px,
        thin_time_factor=thin_time_factor,
        time_dim=time_dim,
        clim=clim,
        camera=camera,
        axis_rig=axis_rig,
        fig_id=fig_id,
        fig_title=fig_title,
        fig_text=fig_text,
    )

    def _plot(value: xr.DataArray | VirtualCube):
        da_value = value.materialize() if isinstance(value, VirtualCube) else value
        if not isinstance(da_value, xr.DataArray):
            raise TypeError(
                "v.plot expects an xarray.DataArray or VirtualCube. "
                f"Got type {type(da_value)!r}."
            )

        logger.info(
            "v.plot() called with da name=%s dims=%s", getattr(da_value, "name", None), da_value.dims
        )

        t_dim, y_dim, x_dim = _infer_time_y_x_dims(da_value)
        resolved_time = opts.time_dim or t_dim
        default_title = da_value.name or f"{resolved_time} × {y_dim} × {x_dim} cube"

        caption_payload = None
        if opts.fig_id is not None or opts.fig_title is not None or opts.fig_text is not None:
            caption_payload = {"id": opts.fig_id, "title": opts.fig_title, "text": opts.fig_text}

        camera_to_use = resolve_camera(opts.camera)
        coord = plotly_camera_to_coord(camera_to_use)

        # 1. Build CubePlot for this cube
        cube = CubePlot(
            da_value,
            title=opts.title or default_title,
            caption=caption_payload,
            size_px=opts.size_px,
            cmap=opts.cmap,
            thin_time_factor=opts.thin_time_factor,
            time_dim=resolved_time,
            fill_scale=ScaleFillContinuous(cmap=opts.cmap, limits=opts.clim),
            fig_title=opts.fig_title,
            coord=coord,
            camera=camera_to_use,
            axis_rig=opts.axis_rig,
        )

        # 2. Draw cube
        cube = cube.geom_cube(cmap=opts.cmap)

        # 3. If a vase is present, overlay outline
        vase = extract_vase_from_attrs(da_value)
        if vase is not None:
            if not isinstance(vase, VaseDefinition):
                logger.warning(
                    "Ignoring attrs['vase'] with unexpected type %s; skipping vase overlay",
                    type(vase).__name__,
                )
            else:
                try:
                    cube = cube.stat_vase(vase).geom_vase_outline(
                        color="limegreen",
                        alpha=0.6,
                    )
                except Exception as exc:  # pragma: no cover - defensive guard
                    logger.warning("Vase overlay failed; continuing without vase: %s", exc)

        # 4. Apply studio theme with tight axes (implementation in CubePlot)
        cube = cube.theme_cube_studio(tight_axes=True)

        return cube

    verb = Verb(_plot)
    if da is None:
        return verb
    return verb(da)
