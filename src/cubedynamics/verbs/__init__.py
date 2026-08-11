# STANDARD DOCSTRING TEMPLATE (for future verbs):
# Summary
# Grammar contract
# Parameters
# Returns
# Notes
# Examples
# See Also

"""Namespace exposing pipe-friendly cube verbs.

This module is part of the CubeDynamics "grammar-of-cubes":
- Data loaders produce xarray objects (often dask-backed) with dims ``(time, y, x)``.
- Verbs are pipe-friendly transformations: cube → cube (or cube → scalar/plot side-effect).
- Plotting follows a grammar-of-graphics model (aes, geoms, stats, scales, themes).

Canonical API:
- Statistical verbs: :func:`mean`, :func:`variance`, :func:`anomaly`, :func:`zscore`
- Plotting verbs: :func:`plot`, :func:`plot_mean`, :func:`diagnostic_panel`, :func:`show_cube_lexcube`
- Fire/vase verbs: :func:`extract`, :func:`vase`, :func:`fire_plot`, :func:`fire_panel`, :func:`fire_vase_panel`
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
from IPython.display import display

from ..config import TIME_DIM, X_DIM, Y_DIM
from ..ops_fire.time_hull import (
    FireEventDaily,
    TimeHull,
    Vase,
    compute_time_hull_geometry,
    time_hull_to_vase,
)
from ..ops_fire.climate_hull_extract import (
    HullClimateSummary,
    build_inside_outside_climate_samples,
)
from ..ops.io import to_netcdf
from ..ops.ndvi import ndvi_from_s2
from ..ops.stats import correlation_cube
from ..ops.transforms import month_filter
from ..piping import Verb
from ..streaming import VirtualCube
from ..vase import VaseDefinition
from .custom import apply
from .diagnostics import diagnostic_panel
from .flatten import flatten_cube, flatten_space
from .models import fit_model
from .plot import plot
from .plot_mean import plot_mean
from .tubes import tubes
from .vase import vase as _vase_base, vase_demo, vase_extract, vase_mask
from .stats import (
    anomaly,
    aoi_signature,
    block_signature,
    collect_blocks,
    compare_blocks,
    compare_aoi_signature,
    mean,
    rolling_median_split_synchrony,
    rolling_tail_dep_vs_center,
    variance,
    zscore,
)
from .biology import align_cube, rasterize_observations
from .events import detect_events
from .states import (
    binary_state,
    change_state,
    exceedance,
    quantile_state,
    threshold_state,
)
from .synchrony import (
    duration_synchrony,
    occurrence_synchrony,
    severity_synchrony,
    sync_with,
    timing_synchrony,
)


def _import_xarray():
    """Import xarray lazily to avoid import-time hard dependency failures."""

    import xarray as xr

    return xr


def _unwrap_dataarray(
    obj,
):
    """
    Normalize a verb input to an (xarray.DataArray, original_obj) pair.

    - If obj is a VirtualCube, materialize its underlying DataArray while
      returning the original VirtualCube so downstream callers can keep
      working with the same type.
    - If obj is a DataArray, return it as both (base_da, original_obj).
    - If obj is None, raise a clear error.
    """

    if obj is None:
        raise ValueError("extract() requires an input cube/DataArray; got None.")

    xr = _import_xarray()

    if isinstance(obj, VirtualCube):
        base_da = obj.materialize()
        if not isinstance(base_da, xr.DataArray):
            raise TypeError("VirtualCube underlying data is not a DataArray.")
        return base_da, obj

    if isinstance(obj, xr.DataArray):
        return obj, obj

    raise TypeError(f"Unsupported type for extract(): {type(obj)!r}")


def landsat8_mpc(*args, **kwargs):
    """Lazy import wrapper for the Landsat MPC helper.

    Avoids importing optional heavy dependencies (e.g., rioxarray) unless the
    verb is actually invoked.
    """

    from .landsat_mpc import landsat8_mpc as _landsat8_mpc

    return _landsat8_mpc(*args, **kwargs)


def landsat_vis_ndvi(*args, **kwargs):
    """Lazy import wrapper for a visualization-friendly Landsat NDVI cube."""

    from .landsat_mpc import landsat_vis_ndvi as _landsat_vis_ndvi

    return _landsat_vis_ndvi(*args, **kwargs)


def landsat_ndvi_plot(*args, **kwargs):
    """Lazy import wrapper for Landsat NDVI plotting."""

    from .landsat_mpc import landsat_ndvi_plot as _landsat_ndvi_plot

    return _landsat_ndvi_plot(*args, **kwargs)


def show_cube_lexcube(**kwargs):
    """Render a Lexcube widget as a side-effect and return the original cube.

    Grammar contract
    ----------------
    Side-effect verb (cube → cube, produces output). Returns a pipe-ready
    callable that displays an interactive Lexcube view while keeping the cube
    unchanged in the pipe.

    Parameters
    ----------
    **kwargs : Any
        Forwarded directly to :func:`cubedynamics.viz.show_cube_lexcube`.

    Returns
    -------
    Verb
        Pipe-ready verb when used without immediate ``da``; otherwise the
        original cube after rendering.

    Notes
    -----
    The incoming object must represent a 3D cube with dims ``(time, y, x)``.
    Reducers such as :func:`mean`, :func:`variance`, :func:`anomaly`, and
    :func:`zscore` keep the cube Lexcube-ready when ``keep_dim=True``. Dask
    backing is preserved and only a light viewer object is created.

    Examples
    --------
    >>> from cubedynamics import pipe, verbs as v
    >>> cube = ...  # xarray.DataArray with dims (time, y, x)
    >>> _ = pipe(cube) | v.show_cube_lexcube()
    >>> cube  # still available

    See Also
    --------
    cubedynamics.verbs.plot.plot
    cubedynamics.plotting.viewers
    """

    def _op(obj):
        xr = _import_xarray()

        # normalize to DataArray if needed (Dataset with 1 var)
        if isinstance(obj, xr.Dataset):
            if len(obj.data_vars) != 1:
                raise ValueError(
                    "show_cube_lexcube verb expects a Dataset with exactly one data variable."
                )
            var = next(iter(obj.data_vars))
            da = obj[var]
        else:
            da = obj

        required_dims = {TIME_DIM, Y_DIM, X_DIM}
        if da.ndim != 3 or set(da.dims) != required_dims:
            raise ValueError(
                "show_cube_lexcube expects a 3D cube with dims (time, y, x); "
                f"received dims {da.dims}"
            )

        da = da.transpose(TIME_DIM, Y_DIM, X_DIM)
        import cubedynamics.viz as viz

        widget = viz.show_cube_lexcube(da, **kwargs)
        display(widget)

        # return original object so the pipe chain can continue
        return obj

    return _op


def extract(
    da: xr.DataArray | VirtualCube | None = None,
    *,
    fired_event: FireEventDaily,
    date_col: str = "date",
    n_ring_samples: int = 100,
    n_theta: int = 96,
    verbose: bool = False,
):
    """Attach fire time-hull and climate summaries to a cube.

    Grammar contract
    ----------------
    Annotating verb (cube → cube with attrs attached). When called without
    ``da`` it returns a pipe-ready verb. When called directly it returns the
    original cube (DataArray or VirtualCube) with fire metadata stored in
    attributes.

    Parameters
    ----------
    da : xarray.DataArray or VirtualCube, optional
        Input climate cube with dims ``(time, y, x)``. If ``None``, a verb is
        returned for use in a pipe chain.
    fired_event : FireEventDaily
        Fire event describing daily perimeters.
    date_col : str, default "date"
        Column name for date stamps in the FIRED GeoDataFrame.
    n_ring_samples : int, default 100
        Perimeter sampling density for hull reconstruction.
    n_theta : int, default 96
        Angular resolution of the hull.
    verbose : bool, default False
        If True, print hull metrics and climate sampling summaries.

    Returns
    -------
    xarray.DataArray or VirtualCube or Verb
        The same type provided on input with additional attrs, or a pipe-ready
        verb when ``da`` is omitted.

    Notes
    -----
    The verb stores:
    ``attrs["fire_time_hull"]`` → :class:`~cubedynamics.ops_fire.time_hull.TimeHull`
    ``attrs["fire_climate_summary"]`` → :class:`~cubedynamics.ops_fire.climate_hull_extract.HullClimateSummary`
    ``attrs["vase"]`` → :class:`~cubedynamics.ops_fire.time_hull.Vase`

    Streaming/laziness: VirtualCube inputs are materialized only to build the
    summaries; the original VirtualCube is returned to keep downstream streaming
    intact.

    Examples
    --------
    Direct call:
    >>> import cubedynamics as cd
    >>> from cubedynamics import verbs as v
    >>> clim = cd.load_gridmet_cube(lat=43.11, lon=-122.74, start="2002-07-01", end="2002-09-15", variable="tmmx")
    >>> fired_evt = cd.fired_event(event_id=21281)
    >>> annotated = v.extract(clim, fired_event=fired_evt)

    Pipe style:
    >>> from cubedynamics import pipe
    >>> annotated = pipe(clim) | v.extract(fired_event=fired_evt)

    See Also
    --------
    cubedynamics.verbs.vase
    cubedynamics.verbs.fire_plot
    cubedynamics.verbs.fire_panel
    """

    def _op(value: xr.DataArray | VirtualCube):
        base_da, original_obj = _unwrap_dataarray(value)

        hull: TimeHull = compute_time_hull_geometry(
            fired_event,
            n_ring_samples=n_ring_samples,
            n_theta=n_theta,
            verbose=verbose,
        )

        summary: HullClimateSummary = build_inside_outside_climate_samples(
            fired_event,
            base_da,
            date_col=date_col,
            verbose=verbose,
        )

        vase_obj = time_hull_to_vase(hull)

        base_da.attrs["fire_time_hull"] = hull
        base_da.attrs["fire_climate_summary"] = summary
        base_da.attrs["vase"] = vase_obj

        return original_obj

    if da is None:
        return Verb(_op)
    return _op(da)


def _plot_time_hull_vase(
    vase_obj: Vase,
    da: xr.DataArray,
    summary: HullClimateSummary | None,
    **plot_kwargs,
):
    """Render a TimeHull-derived vase using matplotlib."""

    verts = np.asarray(vase_obj.verts_km)
    tris = np.asarray(vase_obj.tris)
    meta = getattr(vase_obj, "metadata", {}) or {}
    t_days_vert = np.asarray(meta.get("t_days_vert", []), dtype=float)
    metrics = meta.get("metrics", {}) or {}

    intensities = None
    if isinstance(summary, HullClimateSummary):
        day_vals = np.asarray(summary.per_day_mean.sort_index().values, dtype=float)
        M = int(metrics.get("days", day_vals.size if day_vals.size else 0) or 0)
        if M <= 0 and t_days_vert.size:
            M = int(np.nanmax(t_days_vert)) if np.isfinite(t_days_vert).any() else day_vals.size
        if M > 0 and day_vals.size:
            if len(day_vals) < M:
                day_vals = np.pad(day_vals, (0, M - len(day_vals)), mode="edge")
            elif len(day_vals) > M:
                day_vals = day_vals[:M]
            if t_days_vert.size:
                layer_indices = np.clip((t_days_vert - 1).astype(int), 0, M - 1)
                intensities = day_vals[layer_indices]

    from matplotlib import cm

    fig = plt.figure(figsize=plot_kwargs.get("figsize", (6, 4)))
    ax = fig.add_subplot(111, projection="3d")

    faces = [verts[idx] for idx in tris]

    if intensities is not None and intensities.size:
        norm = plt.Normalize(vmin=float(np.nanmin(intensities)), vmax=float(np.nanmax(intensities)))
        face_colors = []
        for tri in tris:
            vals = intensities[tri]
            mean_val = np.nanmean(vals)
            face_colors.append(cm.viridis(norm(mean_val)))
    else:
        face_colors = "steelblue"

    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    poly = Poly3DCollection(faces, facecolors=face_colors, linewidths=0.4, alpha=0.7)
    edge_color = plot_kwargs.get("edgecolor", "#2c3e50")
    poly.set_edgecolor(edge_color)
    ax.add_collection3d(poly)

    ax.set_xlabel("x (km)")
    ax.set_ylabel("y (km)")
    ax.set_zlabel("days")

    if isinstance(summary, HullClimateSummary) and intensities is not None and intensities.size:
        mappable = cm.ScalarMappable(cmap="viridis", norm=plt.Normalize(vmin=float(np.nanmin(intensities)), vmax=float(np.nanmax(intensities))))
        mappable.set_array([])
        fig.colorbar(mappable, ax=ax, label=da.name or "value")

    ax.view_init(
        elev=plot_kwargs.get("elev", 26),
        azim=plot_kwargs.get("azim", -58),
    )
    ax.set_title(plot_kwargs.get("title", "Fire time-hull vase"))
    plt.tight_layout()
    plt.show()

    return fig


def vase(
    da: xr.DataArray | VirtualCube | None = None,
    *,
    vase=None,
    outline: bool = True,
    verbose: bool = False,
    **plot_kwargs,
):
    """Plot a vase representation of a fire time-hull or custom vase definition.

    Grammar contract
    ----------------
    Side-effect verb (cube → cube, produces output). When called without ``da``
    it returns a pipe-ready verb. When called directly it produces a Matplotlib
    or Plotly figure (depending on vase type) and returns the original cube
    unchanged so pipe chains continue.

    Parameters
    ----------
    da : xarray.DataArray or VirtualCube, optional
        Input cube that carries ``attrs['vase']`` from :func:`extract` or a
        custom :class:`~cubedynamics.vase.VaseDefinition`. If ``None`` a verb is
        returned.
    vase : VaseDefinition or Vase or any, optional
        Override the vase object; otherwise read from ``da.attrs['vase']``.
    outline : bool, default True
        Whether to overlay the vase outline.
    verbose : bool, default False
        Print which vase source is being used.
    **plot_kwargs : Any
        Passed through to the plotting backend.

    Returns
    -------
    xarray.DataArray or VirtualCube or Verb
        Original cube (or VirtualCube) so additional verbs can follow, or a
        pipe-ready verb when ``da`` is omitted.

    Notes
    -----
    If ``attrs['vase']`` contains a :class:`~cubedynamics.ops_fire.time_hull.Vase`
    object, the verb will render a 3D hull colored by climate summaries when
    present. VirtualCube inputs are materialized only for plotting while the
    returned object preserves streaming behavior.

    Examples
    --------
    >>> from cubedynamics import pipe, verbs as v
    >>> annotated = ...  # result of v.extract(...)
    >>> _ = pipe(annotated) | v.vase(verbose=True)

    See Also
    --------
    cubedynamics.verbs.extract
    cubedynamics.verbs.fire_plot
    cubedynamics.vase.vase
    """

    def _inner(value: xr.DataArray | VirtualCube):
        base_da, _ = _unwrap_dataarray(value)

        vase_obj = vase if vase is not None else base_da.attrs.get("vase", None)

        if vase_obj is None:
            raise ValueError(
                "v.vase() requires a vase definition via `vase=` or attrs['vase']."
            )

        if verbose and vase is None:
            print("Using vase from attrs['vase']")

        if isinstance(vase_obj, VaseDefinition):
            return _vase_base(vase=vase_obj, outline=outline, **plot_kwargs)(base_da)

        if isinstance(vase_obj, Vase):
            summary = base_da.attrs.get("fire_climate_summary")
            if summary is None:
                raise ValueError(
                    "Time-hull vase plotting requires attrs['fire_climate_summary']; run v.extract first."
                )
            return _plot_time_hull_vase(vase_obj, base_da, summary, **plot_kwargs)

        return _vase_base(vase=vase_obj, outline=outline, **plot_kwargs)(base_da)

    if da is None:
        return Verb(_inner)
    return _inner(da)


def climate_hist(
    da: xr.DataArray | VirtualCube | None = None,
    *,
    bins: int = 40,
    var_label: str | None = None,
):
    """Plot histogram of climate inside vs outside fire perimeters.

    Grammar contract
    ----------------
    Side-effect verb (cube → cube, produces output). When called without ``da``
    returns a pipe-ready verb; when called directly it renders a Matplotlib
    histogram and returns the original cube unchanged.

    Parameters
    ----------
    da : xarray.DataArray or VirtualCube or None
        Input cube with ``attrs['fire_climate_summary']`` produced by
        :func:`extract`. If ``None``, a verb is returned.
    bins : int, default 40
        Number of histogram bins.
    var_label : str, optional
        Label for the x-axis. Defaults to the DataArray name.

    Returns
    -------
    xarray.DataArray or VirtualCube
        The original cube so the pipe chain can continue.

    Notes
    -----
    This verb requires ``attrs['fire_climate_summary']`` to be a
    :class:`~cubedynamics.ops_fire.climate_hull_extract.HullClimateSummary`.
    VirtualCube inputs are materialized only to access histogram data; the
    returned object preserves streaming behavior.

    Examples
    --------
    >>> from cubedynamics import pipe, verbs as v
    >>> annotated = pipe(cube) | v.extract(fired_event=fired_evt)
    >>> _ = annotated | v.climate_hist(bins=30)

    See Also
    --------
    cubedynamics.verbs.extract
    cubedynamics.verbs.fire_plot
    """

    base_da, _ = _unwrap_dataarray(da)

    summary = base_da.attrs.get("fire_climate_summary")
    if not isinstance(summary, HullClimateSummary):
        raise ValueError(
            "climate_hist() requires attrs['fire_climate_summary'] to be a "
            "HullClimateSummary, typically added by v.extract()."
        )

    inside = np.asarray(summary.values_inside)
    outside = np.asarray(summary.values_outside)

    inside = inside[np.isfinite(inside)]
    outside = outside[np.isfinite(outside)]

    if var_label is None:
        var_label = base_da.name or "value"

    plt.figure(figsize=(5, 3))
    if inside.size:
        plt.hist(
            inside,
            bins=bins,
            alpha=0.6,
            density=True,
            label="inside",
            histtype="stepfilled",
        )
    if outside.size:
        plt.hist(
            outside,
            bins=bins,
            alpha=0.6,
            density=True,
            label="outside",
            histtype="step",
        )

    plt.xlabel(var_label)
    plt.ylabel("Density")
    plt.title(f"{var_label}: inside vs outside fire perimeters")
    plt.legend()
    plt.tight_layout()
    plt.show()

    return base_da


def fire_plot(
    da: xr.DataArray | VirtualCube | None = None,
    *,
    fired_event: FireEventDaily,
    date_col: str = "date",
    n_ring_samples: int = 100,
    n_theta: int = 96,
    bins: int = 40,
    var_label: str | None = None,
    show_hist: bool = False,
    show_vase: bool = True,
    verbose: bool = False,
):
    """
    High-level convenience verb: fire time-hull × climate visualization.

    This combines:
      - v.extract(...)    → attach fire/time-hull + climate summary + vase attrs
      - v.vase(...)       → 3D climate-filled hull
      - v.climate_hist(...) → inside vs outside climate histogram

    Typical usage
    -------------
    >>> import cubedynamics as cd
    >>> from cubedynamics import pipe, verbs as v
    >>>
    >>> fired_evt = cd.fired_event(event_id=21281)
    >>> clim = cd.gridmet(
    ...     lat=fired_evt.centroid_lat,
    ...     lon=fired_evt.centroid_lon,
    ...     start=str(fired_evt.t0 - pd.Timedelta(days=14)),
    ...     end=str(fired_evt.t1 + pd.Timedelta(days=14)),
    ...     variable="tmmx",
    ... )
    >>>
    >>> pipe(clim) | v.fire_plot(fired_event=fired_evt)

    The default call is quiet (no histogram, minimal console chatter) and shows
    only the interactive 3D hull. To request diagnostics and the histogram,
    opt in explicitly:

    >>> pipe(clim) | v.fire_plot(
    ...     fired_event=fired_evt,
    ...     show_hist=True,
    ...     verbose=True,
    ... )

    Parameters
    ----------
    da : DataArray or VirtualCube or None
        Input climate cube (e.g., from cd.gridmet). If None, follow the
        same conventions as other verbs for pulling from context.
    fired_event : FireEventDaily
        Fire event describing daily perimeters.
    date_col : str
        Date column name for the FIRED GeoDataFrame.
    n_ring_samples : int
        Perimeter sampling density for hull reconstruction.
    n_theta : int
        Angular resolution of the hull.
    bins : int
        Histogram bins passed to climate_hist.
    var_label : str, optional
        Label for climate variable; defaults to DataArray name.
    show_hist : bool, default False
        If True, show the histogram via v.climate_hist.
    show_vase : bool, default True
        If True, show the 3D time-hull via v.vase.
    verbose : bool, default False
        If True, print diagnostics during extraction/plotting.

    Returns
    -------
    Same type as input (DataArray or VirtualCube)
        The cube with fire/time-hull attrs attached.
    """

    def _inner(value: xr.DataArray | VirtualCube):
        out = extract(
            value,
            fired_event=fired_event,
            date_col=date_col,
            n_ring_samples=n_ring_samples,
            n_theta=n_theta,
            verbose=verbose,
        )

        if show_vase:
            vase(out, verbose=verbose)

        if show_hist:
            climate_hist(out, bins=bins, var_label=var_label)

        return out

    if da is None:
        return Verb(_inner)
    return _inner(da)


def fire_panel(
    da: xr.DataArray | VirtualCube | None = None,
    *,
    fired_event: FireEventDaily,
    date_col: str = "date",
    n_ring_samples: int = 100,
    n_theta: int = 96,
    bins: int = 40,
    var_label: str | None = None,
):
    """
    Convenience helper: fire time-hull + climate distribution "panel".

    This is similar to fire_plot(), but returns the figure objects where
    possible so advanced users can embed them in their own layouts.

    Parameters
    ----------
    da : DataArray or VirtualCube or None
        Input climate cube.
    fired_event : FireEventDaily
        Fire event describing daily perimeters.
    date_col, n_ring_samples, n_theta, bins, var_label :
        As in fire_plot().

    Returns
    -------
    out, fig_vase, fig_hist :
        out      : same cube type as input (DataArray or VirtualCube).
        fig_vase : Plotly Figure for the 3D time-hull (or None).
        fig_hist : Matplotlib Figure for the histogram (or None).
    """

    def _inner(value: xr.DataArray | VirtualCube):
        out = extract(
            value,
            fired_event=fired_event,
            date_col=date_col,
            n_ring_samples=n_ring_samples,
            n_theta=n_theta,
        )

        fig_vase = None
        maybe_fig = vase(out)
        import plotly.graph_objects as go

        if isinstance(maybe_fig, go.Figure):
            fig_vase = maybe_fig

        climate_hist(out, bins=bins, var_label=var_label)
        fig_hist = plt.gcf()

        return out, fig_vase, fig_hist

    if da is None:
        return Verb(_inner)
    return _inner(da)


# Canonical fire/VASE adapters live in verbs.fire. The local implementations
# above remain as compatibility-era helpers, but public names are bound to the
# canonical module here so fire-specific behavior is defined in one place.
from .fire import (  # noqa: E402
    climate_hist,
    extract,
    fire_derivative,
    fire_panel,
    fire_plot,
    fire_vase_panel,
    vase,
)


__all__ = [
    "anomaly",
    "aoi_signature",
    "apply",
    "block_signature",
    "collect_blocks",
    "compare_blocks",
    "compare_aoi_signature",
    "mean",
    "month_filter",
    "flatten_space",
    "flatten_cube",
    "rolling_median_split_synchrony",
    "rolling_tail_dep_vs_center",
    "variance",
    "correlation_cube",
    "diagnostic_panel",
    "to_netcdf",
    "zscore",
    "ndvi_from_s2",
    "landsat8_mpc",
    "landsat_vis_ndvi",
    "landsat_ndvi_plot",
    "show_cube_lexcube",
    "fit_model",
    "plot",
    "plot_mean",
    "extract",
    "climate_hist",
    "fire_plot",
    "fire_derivative",
    "fire_panel",
    "fire_vase_panel",
    "tubes",
    "vase",
    "vase_demo",
    "vase_extract",
    "vase_mask",
]
