"""Grammar-of-graphics + streaming core for cube plotting.

This module powers the "CubePlot" narrative used throughout the docs:
`pipe(ndvi) | v.plot()` for the simple case, and `CubePlot(...).geom_cube()`
when you want fully controlled layers, scales, captions, and facets. Every
component is designed to stay **streaming-first**: the viewer iterates over
time slices and avoids materializing whole cubes, keeping NEON/Sentinel/PRISM
requests responsive in notebooks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import logging
import html
import math
import os
import string

import xarray as xr

import numpy as np
import pandas as pd

from cubedynamics.plotting.axis_rig import AxisRigSpec
from cubedynamics.plotting.cube_viewer import cube_from_dataarray
from cubedynamics.vase import VaseDefinition
from cubedynamics.utils import _infer_time_y_x_dims
from cubedynamics.plotting.viewer import show_cube_viewer
from ..utils import drop_bad_assets as _drop_bad_assets


logger = logging.getLogger(__name__)


class _CubePlotMeta(type):
    def __instancecheck__(cls, instance: object) -> bool:  # pragma: no cover - lightweight helper
        if type.__instancecheck__(cls, instance):
            return True
        viewer = getattr(instance, "_cd_last_viewer", None)
        if viewer is None:
            viewer = getattr(getattr(instance, "attrs", {}), "_cd_last_viewer", None)
        return viewer is not None and type.__instancecheck__(cls, viewer)


@dataclass
class CubeTheme:
    """Theme configuration for cube plots.

    CSS variables and font sizes flow through to the generated HTML so captions,
    titles, axes, and legends match report-ready styling. Themes are intentionally
    lightweight: adjust only what is needed while leaving streaming behavior
    untouched.
    """

    bg_color: str = "#ffffff"
    panel_color: str = "#ffffff"
    shadow_strength: float = 0.15
    lighting_style: str = "studio"

    title_font_family: str = (
        "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
    )
    title_font_size: int = 20
    axis_scale: float = 0.6
    legend_scale: float = 0.6

    title_color: str = "cornflowerblue"
    axis_color: str = "rgba(25, 25, 25, 0.9)"
    legend_color: str = "limegreen"

    caption_font_scale: float = 0.8

    panel_padding: int = 10


def theme_cube_studio(tight_axes: bool | None = False, **kwargs: Any) -> CubeTheme:
    """Return the default "studio" theme."""

    return CubeTheme()


@dataclass
class CubeAes:
    """Aesthetic mapping for cube plots.

    Mirrors ggplot's ``aes`` by mapping data variables to visuals. Only the
    fields relevant to the cube viewer are exposed (fill, alpha, and slice
    selection), keeping the API small while matching the grammar-of-graphics
    vocabulary documented on the website.
    """

    fill: Optional[str] = None
    alpha: Optional[str] = None
    slice: Optional[str] = None
    facet: Optional[str] = None


@dataclass
class CubeFacet:
    row: Optional[str] = None
    col: Optional[str] = None
    wrap: Optional[int] = None
    by: Optional[str] = None


def _infer_aes_from_data(data: Any) -> CubeAes:
    """Infer a simple aesthetic mapping from a DataArray."""

    if isinstance(data, xr.DataArray):
        return CubeAes(fill=data.name)
    return CubeAes()


@dataclass
class CubeLayer:
    """A plotting layer pairing a geom with data and stat.

    ``CubePlot`` currently supports a single primary layer but the object model
    mirrors ggplot so additional geoms can be added in the future without
    breaking the streaming renderer.
    """

    geom: str
    data: Any = None
    aes: Optional[CubeAes] = None
    stat: Optional[str] = "identity"
    params: Dict[str, Any] = field(default_factory=dict)


def geom_cube(**params: Any) -> CubeLayer:
    return CubeLayer(geom="cube", stat="identity", params=params)


def geom_slice(**params: Any) -> CubeLayer:
    return CubeLayer(geom="slice", stat="identity", params=params)


def geom_outline(**params: Any) -> CubeLayer:
    return CubeLayer(geom="outline", stat="identity", params=params)


def geom_path3d(**params: Any) -> CubeLayer:
    return CubeLayer(geom="path3d", stat="identity", params=params)


@dataclass
class ScaleFillContinuous:
    """Continuous color scale used by the cube viewer.

    Supports palette selection, centered/diverging ramps, and legend metadata.
    ``CubePlot`` infers limits lazily from the streamed slices.
    """
    cmap: str = "cividis"
    palette: str = "sequential"
    limits: Optional[tuple[float, float]] = None
    breaks: Optional[list[float]] = None
    labels: Optional[list[str]] = None
    center: Optional[float] = None
    transform: Optional[str] = None
    name: Optional[str] = None
    units: Optional[str] = None

    def _default_cmap(self) -> str:
        if self.cmap:
            return self.cmap
        if self.palette == "diverging":
            return "coolwarm"
        return "cividis"

    def resolved_cmap(self) -> str:
        return self._default_cmap()

    def infer_limits(self, data: xr.DataArray) -> tuple[float, float]:
        """
        Infer limits for continuous fill scales.

        If `self.limits` is set, return that directly. Otherwise, attempt to
        convert the input DataArray/DataArray-like object to a NumPy array.

        When working with remote-backed dask arrays (e.g., Sentinel-2 STAC
        cubes via stackstac), individual assets may intermittently raise
        I/O errors (403, 404, etc.) when accessed. In that case, we
        defensively attempt to clean the data with `drop_bad_assets`
        before giving up.

        This makes CubePlot more robust for both "normal" and vase views
        without requiring users to explicitly pre-clean cubes.
        """
        if self.limits is not None:
            return self.limits

        try:
            arr = np.asarray(data)
        except Exception as exc:  # pragma: no cover - depends on remote I/O
            logger.warning(
                "ScaleFillContinuous.infer_limits: initial np.asarray() "
                "failed with %s: %r; attempting to drop bad assets and retry",
                type(exc).__name__,
                exc,
            )
            try:
                cleaned = _drop_bad_assets(data)
                arr = np.asarray(cleaned)
            except Exception as fallback_exc:  # pragma: no cover
                logger.error(
                    "ScaleFillContinuous.infer_limits: fallback after "
                    "drop_bad_assets() also failed with %s: %r; re-raising",
                    type(fallback_exc).__name__,
                    fallback_exc,
                )
                raise exc

        finite = np.isfinite(arr)
        if finite.any():
            vmin = float(arr[finite].min())
            vmax = float(arr[finite].max())
            if self.center is not None:
                spread = max(abs(vmin - self.center), abs(vmax - self.center))
                vmin = self.center - spread
                vmax = self.center + spread
            if vmin == vmax:
                return (vmin, vmax or vmin + 1.0)
            return (vmin, vmax)

        logger.warning(
            "ScaleFillContinuous.infer_limits: no finite values found; "
            "falling back to (0.0, 1.0)"
        )
        return (0.0, 1.0)

    def infer_breaks(self, limits: tuple[float, float]) -> list[float]:
        if self.breaks is not None:
            return self.breaks
        lo, hi = limits
        step = (hi - lo) / 4.0 if hi != lo else 1.0
        return [round(lo + step * i, 2) for i in range(5)]


@dataclass
class ScaleAlphaContinuous:
    limits: Optional[tuple[float, float]] = None
    range: tuple[float, float] = (0.1, 1.0)
    name: Optional[str] = None


@dataclass
class CoordCube:
    """Camera/coordinate configuration for cube plots."""
    view: str = "iso"
    elev: float = 30.0
    azim: float = 45.0
    zoom: float = 1.0
    aspect: tuple[float, float, float] = (1.0, 1.0, 1.0)
    time_ticks: int = 4
    space_ticks: int = 3
    time_format: str = "%Y-%m-%d"


DEFAULT_CAMERA: Dict[str, Dict[str, float]] = {
    "eye": {"x": 3.0, "y": -2.5, "z": -0.7},
    "up": {"x": 0.0, "y": 0.0, "z": 1.0},
    "center": {"x": 0.0, "y": 0.0, "z": 0.0},
}
_PLOTLY_DEFAULT_EYE = {"x": 1.25, "y": 1.25, "z": 1.25}


def resolve_camera(camera: Optional[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
    merged = {
        "eye": dict(DEFAULT_CAMERA["eye"]),
        "up": dict(DEFAULT_CAMERA["up"]),
        "center": dict(DEFAULT_CAMERA["center"]),
    }
    if not camera:
        return merged
    for key in ("eye", "up", "center"):
        values = camera.get(key)
        if isinstance(values, dict):
            for axis in ("x", "y", "z"):
                if axis in values:
                    merged[key][axis] = float(values[axis])
    return merged


def plotly_camera_to_coord(camera: Optional[Dict[str, Any]]) -> CoordCube:
    resolved = resolve_camera(camera)
    eye = resolved["eye"]
    x = float(eye.get("x", 0.0))
    y = float(eye.get("y", 0.0))
    z = float(eye.get("z", 0.0))

    azim = math.degrees(math.atan2(y, x)) if (x or y) else 0.0
    horiz = math.hypot(x, y)
    elev = math.degrees(math.atan2(z, horiz)) if (horiz or z) else 0.0

    ref = math.sqrt(
        _PLOTLY_DEFAULT_EYE["x"] ** 2
        + _PLOTLY_DEFAULT_EYE["y"] ** 2
        + _PLOTLY_DEFAULT_EYE["z"] ** 2
    )
    mag = math.sqrt(x**2 + y**2 + z**2) or ref
    zoom = mag / ref if ref else 1.0

    return CoordCube(elev=elev, azim=azim, zoom=zoom)


@dataclass
class CubeAnnotation:
    """Simple annotation container for planes/text anchored to cube axes."""
    kind: str
    axis: Optional[str] = None
    value: Optional[float] = None
    text: Optional[str] = None
    coord: Optional[tuple] = None


def stat_identity(data: xr.DataArray, aes: CubeAes, params: Dict[str, Any]) -> xr.DataArray:
    return data


def stat_time_mean(data: xr.DataArray, aes: CubeAes, params: Dict[str, Any]) -> xr.DataArray:
    time_dim = params.get("time_dim") or aes.slice or "time"
    if time_dim not in data.dims:
        return data
    return data.mean(time_dim)


def stat_time_anomaly(
    data: xr.DataArray, aes: CubeAes, params: Dict[str, Any]
) -> xr.DataArray:
    time_dim = params.get("time_dim") or aes.slice or "time"
    if time_dim not in data.dims:
        return data
    mean = data.mean(time_dim)
    std = data.std(time_dim)
    return (data - mean) / std


def stat_space_mean(data: xr.DataArray, aes: CubeAes, params: Dict[str, Any]) -> xr.DataArray:
    space_dims = params.get("space_dims") or params.get("dims") or ("y", "x")
    dims_to_use = [d for d in space_dims if d in data.dims]
    if not dims_to_use:
        return data
    return data.mean(dim=dims_to_use)


_STAT_REGISTRY = {
    "identity": stat_identity,
    "time_mean": stat_time_mean,
    "time_anomaly": stat_time_anomaly,
    "space_mean": stat_space_mean,
}


def _derive_legend_title(da: xr.DataArray, legend_title: str | None) -> str | None:
    if legend_title is not None:
        return legend_title
    if da.name:
        return str(da.name)
    for attr in ("long_name", "standard_name"):
        if attr in da.attrs:
            return str(da.attrs[attr])
    return None


def _build_caption(caption: Optional[Dict[str, Any]]) -> str:
    if not caption:
        return ""

    fig_id = caption.get("id")
    fig_title = caption.get("title")
    fig_text = caption.get("text")

    parts = ["<div class=\"cube-caption\">"]
    if fig_id is not None:
        parts.append(f"<div class='cube-caption-label'>Figure {html.escape(str(fig_id))}.</div>")
    if fig_title:
        parts.append(f"<div class='cube-caption-title'><strong>{html.escape(str(fig_title))}</strong></div>")
    if fig_text:
        text_html = html.escape(str(fig_text)).replace("\n", "<br />")
        parts.append(f"<div class='cube-caption-text'>{text_html}</div>")
    parts.append("</div>")
    return "".join(parts)


def _format_time_label(value: Any) -> str:
    try:
        ts = pd.to_datetime(value)
        return ts.strftime("%d.%m.%Y")
    except Exception:
        return str(value)


def _format_lat(value: Any) -> str:
    try:
        val = float(value)
    except Exception:
        return str(value)
    hemi = "N" if val >= 0 else "S"
    return f"{abs(val):.0f}°{hemi}"


def _format_lon(value: Any) -> str:
    try:
        val = float(value)
    except Exception:
        return str(value)
    hemi = "E" if val >= 0 else "W"
    return f"{abs(val):.0f}°{hemi}"


def _format_numeric(value: Any) -> str:
    try:
        return f"{float(value):.2f}"
    except Exception:
        return str(value)


def _looks_like_lat(values: np.ndarray, units: str, dim_name: str) -> bool:
    name_lower = dim_name.lower()
    units_lower = units.lower()
    if "lat" in name_lower or "latitude" in name_lower:
        return True
    if name_lower == "y":
        try:
            numeric = values.astype(float)
            finite = np.isfinite(numeric)
            if finite.any():
                within_range = np.nanmin(numeric[finite]) >= -90.5 and np.nanmax(numeric[finite]) <= 90.5
                has_fraction = np.any(np.mod(numeric[finite], 1) != 0)
                if within_range and has_fraction:
                    return True
        except Exception:
            pass
    if any(k in units_lower for k in ["lat", "north", "degrees_north", "deg"]):
        try:
            numeric = values.astype(float)
            finite = np.isfinite(numeric)
            if finite.any():
                return np.nanmin(numeric[finite]) >= -90.5 and np.nanmax(numeric[finite]) <= 90.5
        except Exception:
            return False
    return False


def _looks_like_lon(values: np.ndarray, units: str, dim_name: str) -> bool:
    name_lower = dim_name.lower()
    units_lower = units.lower()
    if "lon" in name_lower or "longitude" in name_lower:
        return True
    if name_lower == "x":
        try:
            numeric = values.astype(float)
            finite = np.isfinite(numeric)
            if finite.any():
                within_range = np.nanmin(numeric[finite]) >= -360.5 and np.nanmax(numeric[finite]) <= 360.5
                has_fraction = np.any(np.mod(numeric[finite], 1) != 0)
                if within_range and has_fraction:
                    return True
        except Exception:
            pass
    if any(k in units_lower for k in ["lon", "east", "west", "degrees_east", "deg"]):
        try:
            numeric = values.astype(float)
            finite = np.isfinite(numeric)
            if finite.any():
                return np.nanmin(numeric[finite]) >= -360.5 and np.nanmax(numeric[finite]) <= 360.5
        except Exception:
            return False
    return False


@dataclass
class CubePlot(metaclass=_CubePlotMeta):
    """Internal object model for cube visualizations.

    The class glues the grammar-of-graphics pieces together while keeping the
    streaming pipeline intact. It powers both pipe-style usage (``v.plot``) and
    advanced layering/faceting examples used throughout the docs.
    """

    data: Any
    aes: Optional[CubeAes] = None
    layers: List[CubeLayer] = field(default_factory=list)
    title: Optional[str] = None
    fig_title: Optional[str] = None
    legend_title: Optional[str] = None
    theme: CubeTheme = field(default_factory=theme_cube_studio)
    caption: Optional[Dict[str, Any]] = None
    size_px: int | None = None
    cmap: str = "cividis"
    fill_scale: Optional[ScaleFillContinuous] = None
    alpha_scale: Optional[ScaleAlphaContinuous] = None
    thin_time_factor: int = 4
    time_label: Optional[str] = None
    x_label: Optional[str] = None
    y_label: Optional[str] = None
    time_dim: Optional[str] = None
    show_progress: bool = True
    progress_style: str = "bar"
    coord: CoordCube = field(default_factory=CoordCube)
    camera: Optional[Dict[str, Any]] = None
    annotations: List[CubeAnnotation] = field(default_factory=list)
    out_html: str = "cube_da.html"
    facet: Optional[CubeFacet] = None
    fill_mode: str = "shell"
    volume_density: Dict[str, int] = field(
        default_factory=lambda: {"time": 6, "x": 2, "y": 2}
    )
    volume_downsample: Dict[str, int] = field(
        default_factory=lambda: {"time": 4, "space": 4}
    )
    vase_mask: Optional[xr.DataArray] = None
    vase_outline: Any = None
    axis_rig: bool | AxisRigSpec = True
    axis_meta: Dict[str, Dict[str, str]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.aes is None:
            self.aes = _infer_aes_from_data(self.data)
        if not self.layers:
            self.layers.append(geom_cube())
        if self.fill_scale is None:
            palette = "diverging" if (self.fill_scale and self.fill_scale.center is not None) else "sequential"
            self.fill_scale = ScaleFillContinuous(
                cmap=self.cmap,
                palette=palette,
                name=self.legend_title,
            )
        elif self.fill_scale.center is not None and self.fill_scale.palette == "sequential":
            # Promote palette to diverging when a center is provided.
            self.fill_scale.palette = "diverging"
        if self.alpha_scale is None:
            self.alpha_scale = ScaleAlphaContinuous()
        if self.caption is None and self.fig_title is not None:
            self.caption = {"title": self.fig_title}
        if self.camera is not None:
            self.camera = resolve_camera(self.camera)
            self.coord = plotly_camera_to_coord(self.camera)
        if isinstance(self.data, xr.DataArray):
            self.axis_meta = self.axis_meta or self._build_axis_meta(self.data)

    def _resolve_dims(self, data: xr.DataArray) -> tuple[str | None, str | None, str | None]:
        if self.time_dim:
            t_dim = self.time_dim
            remaining = [d for d in data.dims if d != t_dim]
            y_dim, x_dim = (remaining + [None, None])[-2:]
            return t_dim, y_dim, x_dim
        return _infer_time_y_x_dims(data)

    def _build_axis_meta(self, data: xr.DataArray) -> Dict[str, Dict[str, str]]:
        def _entry(dim: str | None, kind_hint: str, label_override: Optional[str]) -> tuple[str, Dict[str, str]] | None:
            if dim is None:
                return None
            coord = data.coords.get(dim)
            dim_name = str(dim)
            if coord is not None and coord.size > 0:
                values = np.asarray(coord.values)
                units = str(coord.attrs.get("units", ""))
            else:
                values = np.arange(data.sizes.get(dim, 0))
                units = ""

            kind = kind_hint
            if kind_hint == "y":
                if _looks_like_lat(values, units, dim_name):
                    kind = "lat"
                elif _looks_like_lon(values, units, dim_name):
                    kind = "lon"
                else:
                    kind = "generic"
            elif kind_hint == "x":
                if _looks_like_lon(values, units, dim_name):
                    kind = "lon"
                elif _looks_like_lat(values, units, dim_name):
                    kind = "lat"
                else:
                    kind = "generic"
            elif kind_hint == "time":
                kind = "time"

            name_lookup = {"time": "Time", "lat": "Latitude", "lon": "Longitude"}
            base_name = label_override or name_lookup.get(kind) or str(dim).title()

            if values.size == 0:
                min_label = max_label = ""
            else:
                min_val = values.min()
                max_val = values.max()
                if kind == "time":
                    min_label = _format_time_label(min_val)
                    max_label = _format_time_label(max_val)
                elif kind == "lat":
                    min_label = _format_lat(min_val)
                    max_label = _format_lat(max_val)
                elif kind == "lon":
                    min_label = _format_lon(min_val)
                    max_label = _format_lon(max_val)
                else:
                    min_label = _format_numeric(min_val)
                    max_label = _format_numeric(max_val)

            return str(kind_hint), {"name": base_name, "min": min_label, "max": max_label}

        t_dim, y_dim, x_dim = self._resolve_dims(data)
        meta: Dict[str, Dict[str, str]] = {}
        for dim, kind, label in (
            (t_dim, "time", self.time_label),
            (y_dim, "y", self.y_label),
            (x_dim, "x", self.x_label),
        ):
            entry = _entry(dim, kind, label)
            if entry:
                key, value = entry
                meta[key] = value
        return meta

    def scale_fill_continuous(self, **kwargs: Any) -> "CubePlot":
        self.fill_scale = ScaleFillContinuous(**kwargs)
        return self

    def scale_alpha_continuous(self, **kwargs: Any) -> "CubePlot":
        self.alpha_scale = ScaleAlphaContinuous(**kwargs)
        return self

    def coord_cube(self, **kwargs: Any) -> "CubePlot":
        for key, val in kwargs.items():
            if hasattr(self.coord, key) and val is not None:
                setattr(self.coord, key, val)
        return self

    def facet_wrap(self, by: str, ncol: Optional[int] = None) -> "CubePlot":
        self.facet = CubeFacet(col=by, wrap=ncol or None, by=by)
        return self

    def facet_grid(self, row: Optional[str] = None, col: Optional[str] = None) -> "CubePlot":
        self.facet = CubeFacet(row=row, col=col)
        return self

    def theme_cube_studio(self, tight_axes: bool | None = False, **kwargs: Any) -> "CubePlot":
        self.theme = theme_cube_studio(tight_axes=tight_axes, **kwargs)
        return self

    def annot_plane(self, axis: str, value: float, text: Optional[str] = None) -> "CubePlot":
        self.annotations.append(CubeAnnotation(kind="plane", axis=axis, value=value, text=text))
        return self

    def annot_text(self, coord: tuple, text: str) -> "CubePlot":
        self.annotations.append(CubeAnnotation(kind="text", coord=coord, text=text))
        return self

    def add_layer(self, layer: CubeLayer) -> "CubePlot":
        self.layers.append(layer)
        return self

    def geom_cube(self, **params: Any) -> "CubePlot":
        """Explicitly add a cube geometry layer."""

        return self.add_layer(geom_cube(**params))

    def stat_vase(
        self,
        vase: VaseDefinition,
        time_dim: str = "time",
        y_dim: str = "y",
        x_dim: str = "x",
    ) -> "CubePlot":
        """Attach a vase mask and masked cube to this plot via ``StatVase``.

        ``stat_vase`` computes a streaming-safe mask with
        :func:`cubedynamics.vase.build_vase_mask`, replaces ``self.data`` with
        ``cube.where(mask)``, and stores the mask on ``self.vase_mask`` for
        downstream geoms (notably ``geom_vase_outline``) or viewer overlays.
        """

        from .stats import StatVase

        stat = StatVase(
            vase=vase,
            time_dim=time_dim,
            y_dim=y_dim,
            x_dim=x_dim,
        )

        if vase is None:
            logger.debug("stat_vase called with no vase; skipping overlay")
            return self
        if not isinstance(vase, VaseDefinition):
            logger.warning(
                "stat_vase expects a VaseDefinition; got %s. Skipping vase overlay.",
                type(vase).__name__,
            )
            self.vase_mask = None
            return self

        try:
            masked_cube, mask = stat.compute(self.data)
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.warning("stat_vase failed; skipping vase overlay: %s", exc)
            self.vase_mask = None
            return self

        self.data = masked_cube
        self.vase_mask = mask
        return self

    def geom_vase_outline(self, color: str = "limegreen", alpha: float = 0.6) -> "CubePlot":
        from .geom import GeomVaseOutline

        self.vase_outline = GeomVaseOutline(color=color, alpha=alpha)
        return self

    def to_html(self) -> str:
        da = self.data
        if not isinstance(da, xr.DataArray):
            raise TypeError("CubePlot expects an xarray.DataArray")

        if self.camera is not None:
            self.camera = resolve_camera(self.camera)
            self.coord = plotly_camera_to_coord(self.camera)

        def _apply_stat(data_obj: xr.DataArray) -> xr.DataArray:
            primary_layer = self.layers[0] if self.layers else geom_cube()
            layer_data = primary_layer.data if primary_layer.data is not None else data_obj
            layer_aes = primary_layer.aes if primary_layer.aes is not None else self.aes
            stat_fn = _STAT_REGISTRY.get(primary_layer.stat or "identity", stat_identity)
            return stat_fn(layer_data, layer_aes or CubeAes(), primary_layer.params)

        def _annot_block() -> str:
            if not self.annotations:
                return ""
            annot_html_parts = ["<div class=\"cube-annotations\">"]
            for annot in self.annotations:
                if annot.kind == "plane":
                    annot_html_parts.append(
                        f"<div class='cube-annot'>Plane {html.escape(str(annot.axis))}={html.escape(str(annot.value))}"
                        + (f" — {html.escape(str(annot.text))}" if annot.text else "")
                        + "</div>"
                    )
                elif annot.kind == "text":
                    annot_html_parts.append(
                        f"<div class='cube-annot'>Text @ {html.escape(str(annot.coord))}: {html.escape(str(annot.text or ''))}</div>"
                    )
            annot_html_parts.append("</div>")
            return "".join(annot_html_parts)

        def _panel_label(idx: int, extra: str | None = None) -> str:
            label = string.ascii_lowercase[idx % len(string.ascii_lowercase)]
            suffix = f" {extra}" if extra else ""
            return f"<div class='cube-facet-label'>({label}){suffix}</div>"

        def _render_viewer(
            stat_data: xr.DataArray,
            fill_scale: ScaleFillContinuous,
            legend_title: Optional[str],
            *,
            facet_idx: int = 0,
            show_legend: bool = True,
            axis_meta: Optional[Dict[str, Dict[str, str]]] = None,
        ) -> str:
            panel_path = None
            if self.out_html != "cube_da.html":
                base, ext = os.path.splitext(self.out_html)
                panel_path = f"{base}_facet{facet_idx}{ext or '.html'}" if self.facet else self.out_html
            viewer_obj = cube_from_dataarray(
                stat_data,
                out_html=panel_path,
                cmap=fill_scale.resolved_cmap(),
                size_px=self.size_px,
                thin_time_factor=self.thin_time_factor,
                title=self.title,
                time_label=self.time_label,
                x_label=self.x_label,
                y_label=self.y_label,
                legend_title=legend_title,
                theme=self.theme,
                show_progress=self.show_progress,
                progress_style=self.progress_style,
                time_dim=self.time_dim,
                fill_limits=fill_limits,
                fill_breaks=fill_scale.infer_breaks(fill_limits),
                fill_labels=fill_scale.labels,
                coord=self.coord,
                annotations=self.annotations,
                return_html=True,
                show_legend=show_legend,
                fill_mode=self.fill_mode,
                volume_density=self.volume_density,
                volume_downsample=self.volume_downsample,
                vase_mask=self.vase_mask,
                vase_outline=self.vase_outline,
                axis_meta=axis_meta,
                axis_rig=self.axis_rig,
            )
            return viewer_obj

        fill_scale = self.fill_scale or ScaleFillContinuous(cmap=self.cmap)

        caption_html = _build_caption(self.caption)
        caption_html += _annot_block()

        theme_vars = {
            "--cube-title-font-size": f"{self.theme.title_font_size}px",
            "--cube-title-color": self.theme.title_color,
            "--cube-axis-color": self.theme.axis_color,
            "--cube-legend-color": self.theme.legend_color,
            "--cube-axis-font-size": f"{max(self.theme.title_font_size * self.theme.axis_scale, 11):.1f}px",
            "--cube-legend-font-size": f"{max(self.theme.title_font_size * self.theme.legend_scale, 11):.1f}px",
            "--cube-bg-color": self.theme.bg_color,
            "--cube-panel-color": self.theme.panel_color,
            "--cube-shadow-strength": str(self.theme.shadow_strength),
            "--cube-caption-font-size": f"{self.theme.title_font_size * self.theme.axis_scale * self.theme.caption_font_scale}px",
            "--cube-font-family": self.theme.title_font_family,
        }

        figure_style = " ".join(f"{k}: {v};" for k, v in theme_vars.items())

        if not self.facet:
            stat_data = _apply_stat(da)
            fill_limits = fill_scale.infer_limits(stat_data)
            if fill_scale.units is None:
                units_attr = getattr(stat_data, "attrs", {}).get("units")
                if isinstance(units_attr, str) and units_attr.strip():
                    fill_scale.units = units_attr.strip()

            base_legend_title = fill_scale.name or _derive_legend_title(stat_data, self.legend_title)
            legend_title = (
                f"{base_legend_title} ({fill_scale.units})"
                if base_legend_title and fill_scale.units
                else base_legend_title
            )
            axis_meta = self.axis_meta or self._build_axis_meta(stat_data)
            viewer_html = _render_viewer(
                stat_data, fill_scale, legend_title, axis_meta=axis_meta
            )
            return (
                "<div class='cube-figure' style="
                f"font-family:{self.theme.title_font_family}; background:{self.theme.bg_color}; padding:16px; border-radius:12px; box-shadow:0 16px 40px rgba(0,0,0,{self.theme.shadow_strength});"
                f" color:{self.theme.axis_color};" + "'>"
                "<style>"
                " .cube-figure{margin:8px auto; max-width: 1200px;}"
                " .cube-viewer{padding:" + str(self.theme.panel_padding) + "px; background:" + self.theme.panel_color + "; border-radius: 14px;}"
                " .cube-legend-title{font-size: var(--cube-axis-font-size,12px); color: var(--cube-legend-color, #222); margin-bottom:6px;}"
                " .cube-caption{margin-top:12px; color: var(--cube-axis-color,#222); font-size: var(--cube-caption-font-size,12px); line-height:1.4;}"
                " .cube-caption-label{display:inline-block; margin-right:6px; color: var(--cube-axis-color,#222);}"
                " .cube-caption-title{display:inline-block; margin-right:8px; color: var(--cube-title-color,#222);}"
                " .cube-caption-text{margin-top:4px; color: var(--cube-axis-color,#222);}"
                " .cube-annotations{margin-top:8px; font-size: var(--cube-caption-font-size,12px); color: var(--cube-axis-color,#222);}"
                " .cube-annot{margin-top:2px;}"
                "</style>"
                f"<div class='cube-viewer' style='{figure_style}'>{viewer_html}</div>"
                f"{caption_html}"
                "</div>"
            )

        # Faceted rendering
        facet_panels: List[Tuple[str, xr.DataArray]] = []
        facet_spec = self.facet
        assert facet_spec is not None

        def _unique_values(coord: xr.DataArray) -> Iterable[Any]:
            seen = []
            for v in coord.values.tolist():
                if v not in seen:
                    seen.append(v)
            return seen

        if facet_spec.by:
            by = facet_spec.by
            if by not in da.coords and by not in da.dims:
                raise ValueError(f"Facet variable '{by}' not found in coordinates or dimensions")
            values = list(_unique_values(da[by]))
            for v in values:
                facet_panels.append((f"{by} = {v}", da.sel({by: v})))
            ncol = facet_spec.wrap or len(values)
        else:
            row_vals = list(_unique_values(da[facet_spec.row])) if facet_spec.row else [None]
            col_vals = list(_unique_values(da[facet_spec.col])) if facet_spec.col else [None]
            for r in row_vals:
                for c in col_vals:
                    sel_dict = {}
                    label_parts = []
                    if facet_spec.row:
                        sel_dict[facet_spec.row] = r
                        label_parts.append(f"{facet_spec.row} = {r}")
                    if facet_spec.col:
                        sel_dict[facet_spec.col] = c
                        label_parts.append(f"{facet_spec.col} = {c}")
                    subset = da.sel(sel_dict) if sel_dict else da
                    facet_panels.append((", ".join(label_parts), subset))
            ncol = len(col_vals)

        stat_arrays = [
            _apply_stat(subset) for _, subset in facet_panels
        ]
        combined = xr.concat(stat_arrays, dim="__facet__") if len(stat_arrays) > 1 else stat_arrays[0]
        fill_limits = fill_scale.infer_limits(combined)
        if fill_scale.units is None:
            units_attr = getattr(combined, "attrs", {}).get("units")
            if isinstance(units_attr, str) and units_attr.strip():
                fill_scale.units = units_attr.strip()

        base_legend_title = fill_scale.name or _derive_legend_title(combined, self.legend_title)
        legend_title = (
            f"{base_legend_title} ({fill_scale.units})"
            if base_legend_title and fill_scale.units
            else base_legend_title
        )

        panel_html = []
        for idx, (label_meta, stat_data) in enumerate(zip(facet_panels, stat_arrays)):
            title_text, _ = label_meta
            axis_meta = self.axis_meta or self._build_axis_meta(stat_data)
            viewer_html = _render_viewer(
                stat_data,
                fill_scale,
                legend_title,
                facet_idx=idx,
                show_legend=idx == 0,
                axis_meta=axis_meta,
            )
            panel_html.append(
                "<div class='cube-facet-panel'>" + _panel_label(idx, title_text) + viewer_html + "</div>"
            )

        grid_style = f"grid-template-columns: repeat({ncol}, minmax(320px, 1fr)); gap: 18px;"

        return (
            "<div class='cube-figure' style="
            f"font-family:{self.theme.title_font_family}; background:{self.theme.bg_color}; padding:18px; border-radius:14px; box-shadow:0 16px 40px rgba(0,0,0,{self.theme.shadow_strength});"  # noqa: E501
            f" color:{self.theme.axis_color};" + "'>"
            "<style>"
            " .cube-figure{margin:10px auto; max-width: 1400px;}"
            " .cube-viewer{padding:" + str(self.theme.panel_padding) + "px; background:" + self.theme.panel_color + "; border-radius: 14px;}"
            " .cube-facets{display:grid;" + grid_style + " align-items:start;}"
            " .cube-facet-panel{position:relative; padding-top:6px;}"
            " .cube-facet-label{position:absolute; top:8px; left:12px; z-index:10; background:rgba(255,255,255,0.8); color:" + self.theme.axis_color + "; font-size: 12px; font-weight:600; padding:2px 6px; border-radius:6px; box-shadow:0 2px 6px rgba(0,0,0,0.08);}"
            " .cube-legend-title{font-size: var(--cube-axis-font-size,12px); color: var(--cube-legend-color, #222); margin-bottom:6px;}"
            " .cube-caption{margin-top:14px; color: var(--cube-axis-color,#222); font-size: var(--cube-caption-font-size,12px);}"
            " .cube-caption-label{display:inline-block; margin-right:6px; color: var(--cube-axis-color,#222);}"
            " .cube-caption-title{display:inline-block; margin-right:8px; color: var(--cube-title-color,#222);}"
            " .cube-caption-text{margin-top:4px; color: var(--cube-axis-color,#222);}"
            " .cube-annotations{margin-top:8px; font-size: var(--cube-caption-font-size,12px); color: var(--cube-axis-color,#222);}"
            " .cube-annot{margin-top:2px;}"
            "</style>"
            f"<div class='cube-facets' style='{figure_style}'>{''.join(panel_html)}</div>"
            f"{caption_html}"
            "</div>"
        )

    def save(self, path: str, format: Optional[str] = None, dpi: int = 150) -> None:
        """Save the cube figure to disk.

        Currently supports HTML output natively. PNG export can be added in
        environments with a headless browser; for now a clear error is raised
        guiding users to HTML snapshots.
        """

        fmt = format or os.path.splitext(path)[1].lstrip(".").lower()
        if fmt == "":
            fmt = "html"

        html_out = self.to_html()

        if fmt == "html":
            with open(path, "w", encoding="utf-8") as f:
                f.write(html_out)
            return
        if fmt == "png":
            raise NotImplementedError(
                "PNG export requires a rasterizer. Export HTML and snapshot it with a headless browser."
            )
        raise NotImplementedError(f"Unsupported export format '{fmt}'. Supported: html, png (stub)")

    def _repr_html_(self) -> str:  # pragma: no cover - exercised in notebooks
        logger.info("CubePlot._repr_html_ called for %s", getattr(self.data, "name", None))
        html_out = self.to_html()
        prefix = Path(self.out_html).stem or "cube_viewer"
        frame_base = self.size_px if self.size_px is not None else 760
        iframe = show_cube_viewer(
            html_out,
            width=max(850, frame_base + 300),
            height=max(850, frame_base + 300),
            prefix=prefix,
        )
        self._last_iframe = iframe  # used in tests/notebooks to locate the file
        return iframe._repr_html_()


__all__ = [
    "CubePlot",
    "CubeTheme",
    "theme_cube_studio",
    "CubeAes",
    "CubeLayer",
    "CubeAnnotation",
    "CubeFacet",
    "ScaleFillContinuous",
    "ScaleAlphaContinuous",
    "CoordCube",
    "geom_cube",
    "geom_slice",
    "geom_outline",
    "geom_path3d",
]
