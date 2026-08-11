"""Diagnostic panel verb for cube and fire/VASE outputs."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

import numpy as np
import xarray as xr

from ..piping import Verb
from ..plotting import CubePlot
from ..utils import _infer_time_y_x_dims


def diagnostic_panel(
    obj: Any | None = None,
    *,
    output_path: str | Path | None = None,
    kind: str = "auto",
    variable: str | None = None,
    title: str | None = None,
    cmap: str = "RdBu_r",
    dpi: int = 180,
):
    """Create a static PNG-ready diagnostic panel for a cube or fire result.

    The verb accepts a :class:`CubePlot`, an xarray cube, a synchrony Dataset,
    or the dictionary returned by ``v.fire_plot``. When ``output_path`` is
    supplied the figure is saved as a PNG and the Matplotlib figure is returned.
    """

    def _op(value: Any):
        resolved_kind = _resolve_kind(value, kind)
        if resolved_kind == "fire":
            fig = _fire_diagnostic_panel(value, title=title)
        else:
            fig = _cube_diagnostic_panel(value, variable=variable, title=title, cmap=cmap)
        if output_path is not None:
            path = Path(output_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            fig.savefig(path, dpi=dpi, bbox_inches="tight")
        return fig

    verb = Verb(_op)
    if obj is None:
        return verb
    return verb(obj)


def _resolve_kind(value: Any, kind: str) -> str:
    if kind not in {"auto", "cube", "fire"}:
        raise ValueError("kind must be one of 'auto', 'cube', or 'fire'")
    if kind != "auto":
        return kind
    if isinstance(value, dict) and {"hull", "summary"}.intersection(value):
        return "fire"
    return "cube"


def _cube_diagnostic_panel(
    value: Any,
    *,
    variable: str | None,
    title: str | None,
    cmap: str,
):
    import matplotlib.pyplot as plt

    source = value.data if isinstance(value, CubePlot) else value
    cube = _as_cube_dataarray(value, variable=variable)
    t_dim, y_dim, x_dim = _infer_time_y_x_dims(cube)
    cube = cube.transpose(t_dim, y_dim, x_dim)
    display = _finite_clip(cube)
    mid_t = max(display.sizes[t_dim] // 2, 0)
    mid_y = max(display.sizes[y_dim] // 2, 0)
    mid_x = max(display.sizes[x_dim] // 2, 0)
    spatial_dims = [y_dim, x_dim]

    fig = plt.figure(figsize=(14, 9), constrained_layout=True)
    gs = fig.add_gridspec(2, 3)
    fig.suptitle(title or _cube_title(cube), fontsize=16, fontweight="bold")

    ax_top = fig.add_subplot(gs[0, 0])
    im = ax_top.imshow(_values2d(display.isel({t_dim: mid_t})), origin="lower", cmap=cmap, aspect="auto")
    ax_top.set_title(f"map face at {t_dim}[{mid_t}]")
    ax_top.set_xlabel(x_dim)
    ax_top.set_ylabel(y_dim)
    fig.colorbar(im, ax=ax_top, shrink=0.8)

    ax_y_time = fig.add_subplot(gs[0, 1])
    im = ax_y_time.imshow(
        _values2d(display.isel({x_dim: mid_x}).transpose(t_dim, y_dim)),
        origin="lower",
        cmap=cmap,
        aspect="auto",
    )
    ax_y_time.set_title(f"{t_dim} x {y_dim} face")
    ax_y_time.set_xlabel(y_dim)
    ax_y_time.set_ylabel(t_dim)
    fig.colorbar(im, ax=ax_y_time, shrink=0.8)

    ax_x_time = fig.add_subplot(gs[0, 2])
    im = ax_x_time.imshow(
        _values2d(display.isel({y_dim: mid_y}).transpose(t_dim, x_dim)),
        origin="lower",
        cmap=cmap,
        aspect="auto",
    )
    ax_x_time.set_title(f"{t_dim} x {x_dim} face")
    ax_x_time.set_xlabel(x_dim)
    ax_x_time.set_ylabel(t_dim)
    fig.colorbar(im, ax=ax_x_time, shrink=0.8)

    ax_ts = fig.add_subplot(gs[1, 0])
    _plot_cube_time_series(source, cube, ax_ts, t_dim=t_dim, spatial_dims=spatial_dims)

    ax_var = fig.add_subplot(gs[1, 1])
    variance = cube.var(dim=t_dim, skipna=True)
    im = ax_var.imshow(_values2d(_finite_clip(variance)), origin="lower", cmap="magma", aspect="auto")
    ax_var.set_title("variance map")
    ax_var.set_xlabel(x_dim)
    ax_var.set_ylabel(y_dim)
    fig.colorbar(im, ax=ax_var, shrink=0.8)

    ax_hist = fig.add_subplot(gs[1, 2])
    vals = _finite_values(cube)
    ax_hist.hist(vals, bins=32, color="#4c78a8", alpha=0.85)
    ax_hist.set_title("value distribution")
    ax_hist.set_xlabel(cube.name or "value")
    ax_hist.set_ylabel("count")
    ax_hist.grid(True, alpha=0.25)
    return fig


def _as_cube_dataarray(value: Any, *, variable: str | None) -> xr.DataArray:
    if isinstance(value, CubePlot):
        value = value.data
    if isinstance(value, xr.DataArray):
        return value
    if isinstance(value, xr.Dataset):
        if variable is not None:
            if variable not in value:
                raise ValueError(f"variable {variable!r} not found in Dataset")
            return value[variable]
        for candidate in ("bottom_minus_top", "difference", "diff"):
            if candidate in value:
                return value[candidate]
        if len(value.data_vars) == 1:
            return value[next(iter(value.data_vars))]
        raise ValueError(
            "Dataset diagnostic panels need variable=... unless the Dataset has "
            "a bottom_minus_top variable or exactly one data variable"
        )
    raise TypeError(
        "diagnostic_panel(kind='cube') expects a CubePlot, DataArray, or Dataset; "
        f"got {type(value)!r}"
    )


def _plot_cube_time_series(
    source: Any,
    cube: xr.DataArray,
    ax: Any,
    *,
    t_dim: str,
    spatial_dims: list[str],
) -> None:
    traces = _synchrony_traces(source)
    if traces:
        for name, da in traces:
            trace_t_dim, trace_y_dim, trace_x_dim = _infer_time_y_x_dims(da)
            trace_spatial = [trace_y_dim, trace_x_dim]
            x = _coord_values(da, trace_t_dim)
            median = da.median(dim=trace_spatial, skipna=True)
            ax.plot(x, _values1d(median), label=name)
    else:
        x = _coord_values(cube, t_dim)
        median = cube.median(dim=spatial_dims, skipna=True)
        q10 = cube.quantile(0.10, dim=spatial_dims, skipna=True)
        q90 = cube.quantile(0.90, dim=spatial_dims, skipna=True)
        ax.plot(x, _values1d(median), label="spatial median", color="#1f77b4")
        ax.fill_between(x, _values1d(q10), _values1d(q90), color="#1f77b4", alpha=0.18, label="10-90%")
    ax.axhline(0.0, color="black", linewidth=0.8, alpha=0.4)
    ax.set_title("spatial summary through time")
    ax.set_xlabel(t_dim)
    ax.set_ylabel(cube.name or "value")
    ax.grid(True, alpha=0.25)
    ax.legend(loc="best", fontsize=8)


def _synchrony_traces(source: Any) -> list[tuple[str, xr.DataArray]]:
    if not isinstance(source, xr.Dataset):
        return []
    candidates = [
        ("cold synchrony", "bottom_synchrony"),
        ("hot synchrony", "top_synchrony"),
        ("cold - hot", "bottom_minus_top"),
    ]
    return [(label, source[name]) for label, name in candidates if name in source]


def _fire_diagnostic_panel(value: dict[str, Any], *, title: str | None):
    import matplotlib.pyplot as plt

    hull = value.get("hull")
    summary = value.get("summary")
    cube = _fire_cube(value)
    if hull is None:
        raise ValueError("fire diagnostic panel requires a result with a 'hull'")

    verts = np.asarray(getattr(hull, "verts_km", np.empty((0, 3))), dtype=float)
    tris = np.asarray(getattr(hull, "tris", np.empty((0, 3))), dtype=int)
    metrics = dict(getattr(hull, "metrics", {}) or {})

    fig = plt.figure(figsize=(15, 10), constrained_layout=True)
    gs = fig.add_gridspec(2, 3)
    event_id = getattr(value.get("event"), "event_id", "unknown")
    fig.suptitle(title or f"Fire VASE diagnostic panel: event {event_id}", fontsize=16, fontweight="bold")

    ax_3d = fig.add_subplot(gs[0, 0], projection="3d")
    _draw_hull_3d(ax_3d, verts, tris)

    ax_xy = fig.add_subplot(gs[0, 1])
    _draw_projection(ax_xy, verts, x_idx=0, y_idx=1, title="footprint projection", xlabel="x (km)", ylabel="y (km)")

    ax_xt = fig.add_subplot(gs[0, 2])
    _draw_projection(ax_xt, verts, x_idx=0, y_idx=2, title="x-time projection", xlabel="x (km)", ylabel="time (days)")

    ax_ts = fig.add_subplot(gs[1, 0])
    _plot_fire_climate_time_series(ax_ts, cube, summary)

    ax_hist = fig.add_subplot(gs[1, 1])
    _plot_inside_outside_hist(ax_hist, summary)

    ax_metrics = fig.add_subplot(gs[1, 2])
    _plot_fire_metrics(ax_metrics, metrics)
    return fig


def _fire_cube(value: dict[str, Any]) -> xr.DataArray | xr.Dataset | None:
    cube = value.get("diagnostic_cube", value.get("cube"))
    if cube is None:
        return None
    if hasattr(cube, "da"):
        cube = cube.da
    return cube


def _draw_hull_3d(ax: Any, verts: np.ndarray, tris: np.ndarray) -> None:
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    if verts.size and tris.size:
        faces = verts[tris]
        poly = Poly3DCollection(faces, facecolors="#4c78a8", edgecolors="none", alpha=0.65)
        ax.add_collection3d(poly)
        ax.auto_scale_xyz(verts[:, 0], verts[:, 1], verts[:, 2])
    ax.set_title("3D VASE hull")
    ax.set_xlabel("x (km)")
    ax.set_ylabel("y (km)")
    ax.set_zlabel("time (days)")
    ax.view_init(elev=24, azim=-55)


def _draw_projection(
    ax: Any,
    verts: np.ndarray,
    *,
    x_idx: int,
    y_idx: int,
    title: str,
    xlabel: str,
    ylabel: str,
) -> None:
    if verts.size:
        color = verts[:, 2] if verts.shape[1] > 2 else np.arange(verts.shape[0])
        scatter = ax.scatter(verts[:, x_idx], verts[:, y_idx], c=color, s=8, cmap="viridis", alpha=0.75)
        ax.figure.colorbar(scatter, ax=ax, shrink=0.75, label="time (days)")
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.25)


def _plot_fire_climate_time_series(ax: Any, cube: xr.DataArray | xr.Dataset | None, summary: Any) -> None:
    plotted = False
    if isinstance(cube, xr.Dataset):
        for name in _preferred_fire_vars(cube.data_vars):
            da = cube[name]
            t_dim = _first_dim_like(da, ("time", "day", "date"))
            if t_dim is None:
                continue
            spatial = [dim for dim in da.dims if dim != t_dim]
            da.mean(dim=spatial, skipna=True).to_series().plot(ax=ax, label=name)
            plotted = True
    elif isinstance(cube, xr.DataArray):
        t_dim = _first_dim_like(cube, ("time", "day", "date"))
        if t_dim is not None:
            spatial = [dim for dim in cube.dims if dim != t_dim]
            cube.mean(dim=spatial, skipna=True).to_series().plot(ax=ax, label=cube.name or "climate")
            plotted = True

    per_day = getattr(summary, "per_day_mean", None)
    if per_day is not None:
        per_day.plot(ax=ax, label="inside footprint mean", linestyle="--", color="black")
        plotted = True

    ax.set_title("climate through time")
    ax.set_ylabel("value")
    ax.grid(True, alpha=0.25)
    if plotted:
        ax.legend(loc="best", fontsize=8)
    else:
        ax.text(0.5, 0.5, "No climate time series available", ha="center", va="center", transform=ax.transAxes)


def _preferred_fire_vars(names: Iterable[str]) -> list[str]:
    names = list(names)
    preferred = [name for name in ("tmmx", "tmax", "tmmn", "tmin", "vpd") if name in names]
    return preferred or names[:4]


def _plot_inside_outside_hist(ax: Any, summary: Any) -> None:
    inside = _array_from_attr(summary, "values_inside")
    outside = _array_from_attr(summary, "values_outside")
    if inside.size:
        ax.hist(inside, bins=24, alpha=0.65, label="inside", color="#e45756")
    if outside.size:
        ax.hist(outside, bins=24, alpha=0.45, label="outside", color="#4c78a8")
    if inside.size or outside.size:
        ax.legend(loc="best", fontsize=8)
    else:
        ax.text(0.5, 0.5, "No inside/outside samples", ha="center", va="center", transform=ax.transAxes)
    ax.set_title("inside vs outside samples")
    ax.set_xlabel("climate value")
    ax.set_ylabel("count")
    ax.grid(True, alpha=0.25)


def _plot_fire_metrics(ax: Any, metrics: dict[str, Any]) -> None:
    keys = ["duration_days", "scale_km", "footprint_area_peak_km2", "hull_volume_km2_days"]
    labels = []
    values = []
    for key in keys:
        if key in metrics and np.isfinite(float(metrics[key])):
            labels.append(key.replace("_", "\n"))
            values.append(float(metrics[key]))
    if values:
        ax.bar(labels, values, color="#72b7b2")
        ax.tick_params(axis="x", labelrotation=0, labelsize=8)
    else:
        ax.text(0.5, 0.5, "No hull metrics available", ha="center", va="center", transform=ax.transAxes)
    ax.set_title("hull metrics")
    ax.set_ylabel("value")
    ax.grid(True, axis="y", alpha=0.25)


def _cube_title(cube: xr.DataArray) -> str:
    name = cube.name or "cube"
    return f"{name} diagnostic panel"


def _finite_clip(cube: xr.DataArray) -> xr.DataArray:
    vals = _finite_values(cube)
    if vals.size == 0:
        return cube
    lo, hi = np.nanpercentile(vals, [2, 98])
    if np.isfinite(lo) and np.isfinite(hi) and hi > lo:
        return cube.clip(float(lo), float(hi))
    return cube


def _finite_values(cube: xr.DataArray) -> np.ndarray:
    vals = np.asarray(cube).ravel()
    return vals[np.isfinite(vals)]


def _values2d(cube: xr.DataArray) -> np.ndarray:
    return np.asarray(cube, dtype=float)


def _values1d(cube: xr.DataArray) -> np.ndarray:
    return np.asarray(cube, dtype=float).ravel()


def _coord_values(cube: xr.DataArray, dim: str) -> np.ndarray:
    coord = cube.coords.get(dim)
    if coord is None:
        return np.arange(cube.sizes[dim])
    return np.asarray(coord.values)


def _first_dim_like(cube: xr.DataArray, names: tuple[str, ...]) -> str | None:
    for name in names:
        if name in cube.dims:
            return name
    return cube.dims[0] if cube.dims else None


def _array_from_attr(obj: Any, attr: str) -> np.ndarray:
    if obj is None or not hasattr(obj, attr):
        return np.array([])
    arr = np.asarray(getattr(obj, attr), dtype=float).ravel()
    return arr[np.isfinite(arr)]


__all__ = ["diagnostic_panel"]
