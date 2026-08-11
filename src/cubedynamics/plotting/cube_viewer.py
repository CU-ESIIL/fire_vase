from __future__ import annotations

import base64
import io
import logging
import math
import uuid
import warnings
from pathlib import Path
from typing import Any, Dict, Optional, TYPE_CHECKING

import numpy as np
import pandas as pd
import xarray as xr
from matplotlib import colormaps, colors as mcolors
from PIL import Image

from cubedynamics.plotting.axis_rig import (
    AxisRigSpec,
    axis_rig_css,
    axis_rig_html,
    axis_rig_js,
    axis_rig_meta_script,
    build_axis_rig_meta,
    resolve_axis_rig_spec,
)
from cubedynamics.utils import _infer_time_y_x_dims
from cubedynamics.utils.drift_centering import drift_centering_script
from cubedynamics.plotting.progress import _CubeProgress
from cubedynamics.plotting.viewer import show_cube_viewer
from cubedynamics.vase import VasePanel

# Cube viewer pipeline:
# - :func:`cube_from_dataarray` prepares PNG faces and metadata.
# - :func:`_render_cube_html` owns the HTML/JS template for the 3D viewer.
# - :class:`cubedynamics.plotting.cube_plot.CubePlot` uses :func:`show_cube_viewer`
#   to stream the viewer into notebooks via an iframe to avoid script sanitization.

if TYPE_CHECKING:  # pragma: no cover - typing only
    from cubedynamics.plotting.cube_plot import CoordCube, CubeAnnotation


logger = logging.getLogger(__name__)


def _reduce_to_3d_time_y_x(da: xr.DataArray) -> xr.DataArray:
    """
    Ensure the DataArray has dims (time, y, x) for the cube viewer.

    - If a ``band`` dimension exists and has size 1, squeeze it away.
    - If ``band`` has multiple entries, default to the first band with a warning.
    - If there are more than 3 dims without ``band``, raise a clear error.
    """

    dims = tuple(da.dims)

    if "band" not in dims and len(dims) == 3:
        return da

    if "band" in dims:
        if da.sizes["band"] == 1:
            return da.squeeze("band", drop=True)

        band_coord = da.coords.get("band")
        if band_coord is not None:
            band_label = band_coord.values[0]
            warnings.warn(
                "cube_from_dataarray received a DataArray with a 'band' dimension; "
                f"defaulting to the first band: {band_label!r}",
                UserWarning,
            )
            return da.sel(band=band_label)

        warnings.warn(
            "cube_from_dataarray received a DataArray with a 'band' dimension but no "
            "'band' coordinate; defaulting to band index 0.",
            UserWarning,
        )
        return da.isel(band=0)

    if len(dims) > 3:
        raise ValueError(
            "cube_from_dataarray expects data with dims (time, y, x) or (time, band, y, x). "
            f"Got dims: {dims!r}. Please select or reduce your extra dimensions."
        )

    return da

def _apply_vase_tint(rgb_arr: np.ndarray, mask_2d: np.ndarray, color_rgb: tuple[int, int, int], alpha: float) -> np.ndarray:
    """
    Apply an overlay color to ``rgb_arr`` wherever ``mask_2d`` is True.

    This mutates a copy of the input and returns the tinted array.
    """

    overlay = np.zeros_like(rgb_arr, dtype=np.float32)
    overlay[..., 0] = color_rgb[0]
    overlay[..., 1] = color_rgb[1]
    overlay[..., 2] = color_rgb[2]

    mask_exp = np.broadcast_to(mask_2d[..., None], rgb_arr.shape)
    blended = rgb_arr.astype(np.float32)
    blended[mask_exp] = (1 - alpha) * blended[mask_exp] + alpha * overlay[mask_exp]
    return blended.astype(np.uint8)


def _colormap_to_rgba(arr: np.ndarray, *, cmap: str, fill_limits: tuple[float, float]) -> np.ndarray:
    arr = arr.astype("float32")
    mask = np.isfinite(arr)
    if mask.any():
        norm = mcolors.Normalize(vmin=fill_limits[0], vmax=fill_limits[1])
    else:
        norm = mcolors.Normalize(vmin=-1, vmax=1)
    cmap_obj = colormaps.get_cmap(cmap)
    rgba = cmap_obj(norm(arr))
    if not mask.all():
        rgba[~mask, 3] = 0.0
    return (rgba * 255).astype("uint8")


def _rgba_to_png_base64(rgba: np.ndarray) -> str:
    buf = io.BytesIO()
    Image.fromarray(rgba).save(buf, format="PNG", compress_level=1)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _array_to_png_base64(
    arr: np.ndarray, *, cmap: str, fill_limits: tuple[float, float]
) -> str:
    rgba = _colormap_to_rgba(arr, cmap=cmap, fill_limits=fill_limits)
    return _rgba_to_png_base64(rgba)


def _colorbar_labels(breaks, labels, *, viewer_id: str) -> str:
    if not breaks:
        return (
            f"<span id=\"cb-min-{viewer_id}\"></span><span id=\"cb-max-{viewer_id}\"></span>"
        )
    spans = []
    for idx, val in enumerate(breaks):
        label = labels[idx] if labels and idx < len(labels) else f"{val:.2f}"
        spans.append(f"<span class=\"cb-tick\" data-tick=\"{val:.2f}\">{label}</span>")
    return "".join(spans)


def _build_legend_html(
    *,
    legend_title: str | None,
    colorbar_b64: str | None,
    fill_breaks: list[float] | None,
    fill_labels: list[str] | None,
    viewer_id: str,
) -> str:
    if not legend_title or not colorbar_b64:
        return ""
    tick_block = _colorbar_labels(fill_breaks, fill_labels, viewer_id=viewer_id)
    return (
        "<div class=\"cube-legend-panel\">"
        "  <div class=\"cube-legend-card\">"
        f"    <div class=\"colorbar-title\">{legend_title}</div>"
        f"    <div class=\"colorbar-wrapper\"><img class=\"colorbar-img\" src=\"data:image/png;base64,{colorbar_b64}\" alt=\"colorbar\" /></div>"
        f"    <div class=\"colorbar-labels\">{tick_block}</div>"
        "  </div>"
        "</div>"
    )


def _interior_plane_transform(axis: str, index: int, meta: Dict[str, int], size_css: str) -> str:
    nt = max(meta.get("nt", 1) - 1, 1)
    ny = max(meta.get("ny", 1) - 1, 1)
    nx = max(meta.get("nx", 1) - 1, 1)
    if axis == "time":
        frac = index / nt
        z = f"calc(-0.5 * {size_css} + {frac:.6f} * {size_css})"
        return f"translate3d(0px, 0px, {z})"
    if axis == "x":
        frac = index / nx
        x_off = f"calc(-0.5 * {size_css} + {frac:.6f} * {size_css})"
        return f"rotateY(90deg) translateZ({x_off})"
    if axis == "y":
        frac = index / ny
        y_off = f"calc(-0.5 * {size_css} + {frac:.6f} * {size_css})"
        return f"rotateX(90deg) translateZ({y_off})"
    return ""


def _vase_panel_transform(panel: VasePanel, size_css: str) -> str:
    def _offset(norm: float) -> str:
        return f"calc(-0.5 * {size_css} + {float(norm):.6f} * {size_css})"

    x_off = _offset(panel.x)
    y_off = _offset(panel.y)
    z_off = _offset(panel.z)

    return (
        f"translate3d({x_off}, {y_off}, {z_off}) "
        f"rotateY({panel.yaw:.2f}deg) rotateX(90deg)"
    )


def _render_cube_html(
    *,
    front: str,
    back: str,
    left: str,
    right: str,
    top: str,
    bottom: str,
    interior_planes: list[tuple[str, int, str, Dict[str, int]]] | None,
    vase_panels: list[VasePanel] | None = None,
    theme: Dict[str, str],
    coord: "CoordCube" | None,
    legend_html: str,
    title_html: str,
    size_px: int | None,
    axis_meta: Dict[str, Dict[str, str]] | None,
    axis_rig_spec: AxisRigSpec | None,
    axis_rig_meta: Dict[str, Any] | None,
    color_limits: tuple[float, float],
    interior_meta: Dict[str, int],
    viewer_id: str,
) -> str:
    # NOTE: This function owns the inline HTML/JS template used both for
    # notebook embedding (written to disk and loaded via iframe) and standalone
    # file export. Keeping the template self contained ensures that v.plot()
    # renders the exact same viewer in both contexts.
    interior_html_parts = []
    size_css = "var(--cd-cube-size)"
    if interior_planes:
        for axis, idx, b64, meta in interior_planes:
            transform = _interior_plane_transform(axis, idx, meta or interior_meta, size_css)
            interior_html_parts.append(
                "<div class=\"interior-plane\" "
                f"style=\"transform: {transform}; background-image: url('data:image/png;base64,{b64}');\"></div>"
            )
    interior_html = "".join(interior_html_parts)

    vase_html_parts = []
    if vase_panels:
        for panel in vase_panels:
            width_px = f"max(2px, calc({float(panel.width):.6f} * {size_css}))"
            height_px = f"max(2px, calc({float(panel.height):.6f} * {size_css}))"
            transform = _vase_panel_transform(panel, size_css)
            vase_html_parts.append(
                "<div class=\"cd-vase-panel\" "
                f"style=\"width: {width_px}; height: {height_px}; transform: {transform};\"></div>"
            )
    vase_html = "".join(vase_html_parts)

    css_vars = " ".join(f"{k}: {v};" for k, v in theme.items())

    axis_meta = axis_meta or {}
    time_meta = axis_meta.get("time", {})
    x_meta = axis_meta.get("x", {})
    y_meta = axis_meta.get("y", {})
    figure_id = f"cube-figure-{viewer_id}"

    cube_faces_html = f"""
        <div class=\"cd-cube\" id=\"cube-{viewer_id}\">
          <div class=\"cd-face cd-front\" style=\"background-image: url('{front}');\"></div>
          <div class=\"cd-face cd-back\" style=\"background-image: url('{back}');\"></div>
          <div class=\"cd-face cd-left\" style=\"background-image: url('{left}');\"></div>
          <div class=\"cd-face cd-right\" style=\"background-image: url('{right}');\"></div>
          <div class=\"cd-face cd-top\" style=\"background-image: url('{top}');\"></div>
          <div class=\"cd-face cd-bottom\" style=\"background-image: url('{bottom}');\"></div>
        </div>
    """

    rot_x = getattr(coord, "elev", 30.0)
    rot_y = getattr(coord, "azim", 45.0)
    zoom = getattr(coord, "zoom", 1.0)

    rot_x_rad = math.radians(rot_x)
    rot_y_rad = math.radians(rot_y)

    axis_rig_css_block = axis_rig_css(axis_rig_spec) if axis_rig_spec else ""
    axis_rig_markup = axis_rig_html(viewer_id, axis_rig_spec) if axis_rig_spec else ""
    axis_rig_meta_block = (
        axis_rig_meta_script(viewer_id, axis_rig_meta) if axis_rig_spec and axis_rig_meta else ""
    )
    axis_rig_js_block = axis_rig_js(viewer_id) if axis_rig_spec else ""

    axis_rig_data_attr = " data-axis-rig=\"true\"" if axis_rig_spec else ""

    cube_size_css = (
        f"{size_px}px" if size_px is not None else "clamp(300px, min(58vh, 58vw), 640px)"
    )
    html = f"""
<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"UTF-8\" />
    <style>
    :root {{
      /* Viewer override hooks:
         --cd-cube-size
         --cd-axis-font
         --cd-axis-tick-l
         --cd-axis-stroke
      */
      /* Drift centering tuning (DYNAMIC DRIFT CENTERING V1):
         --cd-drift-max-px: maximum horizontal drift in pixels.
         --cd-drift-rot-range-deg: rotation range (deg) that maps to full drift.
         --cd-drift-scale-in: scale that cancels drift when zoomed in.
         --cd-drift-scale-out: scale that enables full drift when zoomed out.
         --cd-drift-smoothing: easing factor for motion smoothing.
      */
      --cd-cube-size: {cube_size_css};
      --cube-size: var(--cd-cube-size);
      --cd-axis-font: clamp(11px, calc(var(--cd-cube-size) * 0.045), 18px);
      --cd-axis-pill-px: clamp(4px, calc(var(--cd-cube-size) * 0.010), 8px);
      --cd-axis-stroke: clamp(2px, calc(var(--cd-cube-size) * 0.006), 4px);
      --cd-axis-tick-l: clamp(10px, calc(var(--cd-cube-size) * 0.035), 18px);
      --cd-drift-max-px: 220;
      --cd-drift-rot-range-deg: 55;
      --cd-drift-scale-in: 1.25;
      --cd-drift-scale-out: 0.85;
      --cd-drift-smoothing: 0.18;
      {css_vars}
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      padding: 28px 14px 32px 14px;
      width: 100%;
      height: 100%;
      background: var(--cube-bg-color);
      color: var(--cube-axis-color);
      font-family: var(--cube-font-family);
      display: flex;
      align-items: flex-start;
      justify-content: center;
      overflow: hidden;
      user-select: none;
    }}
    .cube-figure {{
      width: 100%;
      max-width: 1100px;
      margin: 0 auto;
      padding: 0 24px;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 12px;
    }}
    .cube-title {{
      font-size: var(--cube-title-font-size);
      letter-spacing: 0.04em;
      font-weight: 700;
      text-align: center;
      color: var(--cube-title-color);
      margin-bottom: 4px;
    }}
    .cube-main {{
      width: 100%;
      display: flex;
      justify-content: center;
    }}
    .cube-js-warning {{
      width: min(1180px, 100%);
      display: flex;
      align-items: center;
      gap: 10px;
      margin: 6px auto 0 auto;
      padding: 10px 12px;
      background: #fff4d4;
      color: #5c4300;
      border: 1px solid #f2d27c;
      border-radius: 10px;
      font-size: var(--cube-axis-font-size, 13px);
      box-shadow: 0 8px 24px rgba(0,0,0,0.06);
    }}
    .cube-js-warning.hidden {{
      display: none;
    }}
    .cube-js-warning .dot {{
      width: 10px;
      height: 10px;
      border-radius: 999px;
      background: #f59e0b;
      box-shadow: 0 0 0 4px rgba(245,158,11,0.2);
    }}
    .cube-inner {{
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 10px;
    }}
    .cube-container {{
      position: relative;
      width: var(--cube-size);
      height: var(--cube-size);
      margin: auto;
    }}

    .cube-wrapper {{
      position: relative;
      inset: 0;
      width: 100%;
      height: 100%;
      perspective: 950px;
      transform-style: preserve-3d;
      touch-action: none;
      z-index: 0;
      --rot-x: 0rad;
      --rot-y: 0rad;
      --zoom: 1;
    }}

    .cube-canvas {{
      position: absolute;
      inset: 0;
      width: 100%;
      height: 100%;
      display: block;
      pointer-events: none;
    }}

    .cube-rotation {{
      position: absolute;
      inset: 0;
      transform-style: preserve-3d;
      transform:
        rotateX(var(--rot-x, 0rad))
        rotateY(var(--rot-y, 0rad))
        scale(calc(1 / var(--zoom, 1)));
    }}

    .cube-drag-surface {{
      position: absolute;
      inset: 0;
      z-index: 999;
      cursor: grab;
      background: transparent;
      touch-action: none;
      pointer-events: auto;
    }}

    .cube-drag-surface.debug-show {{
      background: rgba(0, 255, 0, 0.1);
    }}

    .cube-scene {{
      position: relative;
      inset: 0;
      width: 100%;
      height: 100%;
      perspective: 950px;
      transform-style: preserve-3d;
    }}

    .cube-scene .cube-rotation {{
      transform:
        rotateX(var(--rot-x, 0rad))
        rotateY(var(--rot-y, 0rad))
        scale(calc(1 / var(--zoom, 1)));
    }}

    .scene-drag-surface {{
      position: absolute;
      inset: 0;
      z-index: 999;
      cursor: grab;
      background: transparent;
      touch-action: none;
      pointer-events: auto;
    }}

    .cd-drift-center-fallback {{
      --cd-drift-x: 0px;
      --cd-drift-base-transform: none;
      transform: translateX(var(--cd-drift-x, 0px)) var(--cd-drift-base-transform, none);
    }}

    .cd-cube {{
      position: absolute;
      inset: 0;
      transform-style: preserve-3d;
      width: 100%;
      height: 100%;
      transform: translateZ(calc(var(--cube-size) / -2));
      pointer-events: none;
    }}

    .cd-face {{
      position: absolute;
      width: 100%;
      height: 100%;
      background-size: cover;
      background-position: center;
      background-repeat: no-repeat;
      backface-visibility: hidden;
      border: 1px solid rgba(0,0,0,0.08);
      filter: drop-shadow(0 2px 6px rgba(0,0,0,0.25));
      pointer-events: none;
    }}

    .cd-front {{ transform: translateZ(calc(var(--cube-size) / 2)); }}
    .cd-back {{ transform: rotateY(180deg) translateZ(calc(var(--cube-size) / 2)); }}
    .cd-right {{ transform: rotateY(90deg) translateZ(calc(var(--cube-size) / 2)); }}
    .cd-left {{ transform: rotateY(-90deg) translateZ(calc(var(--cube-size) / 2)); }}
    .cd-top {{ transform: rotateX(90deg) translateZ(calc(var(--cube-size) / 2)); }}
    .cd-bottom {{ transform: rotateX(-90deg) translateZ(calc(var(--cube-size) / 2)); }}

    .interior-plane {{
      position: absolute;
      inset: 0;
      width: 100%;
      height: 100%;
      background-size: cover;
      background-position: center;
      opacity: 0.65;
      mix-blend-mode: normal;
      border: 1px solid rgba(255,255,255,0.08);
      pointer-events: none;
      transform-style: preserve-3d;
    }}

    .cd-vase-panel {{
      position: absolute;
      transform-style: preserve-3d;
      backface-visibility: hidden;
      border-radius: 999px;
      opacity: 0.9;
      background: rgba(200, 60, 60, 0.9);
      box-shadow: 0 0 8px rgba(0, 0, 0, var(--cube-shadow-strength, 0.25));
      pointer-events: none;
    }}

    .axis-label {{
      position: absolute;
      font-size: var(--cube-axis-font-size, 13px);
      color: var(--cube-axis-color);
      pointer-events: none;
    }}

    .cube-label {{
      position: absolute;
      font-size: var(--cube-axis-font-size, 13px);
      color: var(--cube-axis-color);
      pointer-events: none;
      letter-spacing: 0.04em;
    }}

    /* Tight to each cube face */
    .axis-x-min {{
      bottom: 5%;
      left: 15%;
    }}
    .axis-x-max {{
      bottom: 5%;
      right: 15%;
    }}
    .axis-x-name {{
      bottom: 0%;
      left: 50%;
      transform: translateX(-50%);
    }}

    .axis-y-min {{
      top: 15%;
      right: 5%;
      transform: rotate(90deg);
    }}
    .axis-y-max {{
      bottom: 15%;
      right: 5%;
      transform: rotate(90deg);
    }}
    .axis-y-name {{
      top: 50%;
      right: 0%;
      transform: translateY(-50%) rotate(90deg);
    }}

    .axis-t-min {{
      left: 5%;
      top: 75%;
      transform: rotate(-90deg);
    }}
    .axis-t-max {{
      left: 5%;
      top: 25%;
      transform: rotate(-90deg);
    }}
    .axis-t-name {{
      left: 0%;
      top: 50%;
      transform: translateY(-50%) rotate(-90deg);
    }}
    .cube-legend-panel {{
      width: 100%;
      display: flex;
      justify-content: center;
      margin-top: 6px;
    }}
    .cube-legend-card {{
      background: #ffffff;
      padding: 8px 12px;
      border-radius: 10px;
      box-shadow: 0 8px 24px rgba(0,0,0,0.08);
      min-width: min(420px, 90%);
    }}
    .colorbar-wrapper {{
      width: 100%;
    }}
    .colorbar-title {{
      font-size: var(--cube-legend-font-size);
      font-weight: 600;
      color: var(--cube-legend-color);
      text-align: center;
      margin-bottom: 6px;
      font-family: var(--cube-font-family);
    }}
    .colorbar-img {{
      width: 100%;
      height: 14px;
      border-radius: 4px;
      border: 1px solid rgba(0,0,0,0.2);
      display: block;
    }}
    .colorbar-labels {{
      width: 100%;
      display: flex;
      justify-content: space-between;
      font-size: var(--cube-legend-font-size);
      margin-top: 6px;
      align-self: center;
      color: var(--cube-legend-color);
      gap: 6px;
    }}
    .cb-tick {{
      flex: 1;
      text-align: center;
    }}
    {axis_rig_css_block}
  </style>
</head>
<body>\n\
  <div class=\"cube-figure\" id=\"{figure_id}\"{axis_rig_data_attr} data-cb-min=\"{color_limits[0]:.2f}\" data-cb-max=\"{color_limits[1]:.2f}\" data-rot-x=\"{rot_x:.1f}\" data-rot-y=\"{rot_y:.1f}\" data-zoom=\"{zoom}\">{title_html}
    <div class=\"cube-main\">
      <div class=\"cube-inner\">
        <div class=\"cube-container\">
          <div class=\"cube-scene\" id=\"cube-scene-{viewer_id}\">
            <div id=\"cube-wrapper-{viewer_id}\" class=\"cube-wrapper\" style=\"--rot-x: {rot_x_rad:.4f}rad; --rot-y: {rot_y_rad:.4f}rad; --zoom: {zoom};\">
              <canvas class=\"cube-canvas\" id=\"cube-canvas-{viewer_id}\"></canvas>
              <div class=\"cube-rotation\" id=\"cube-rotation-{viewer_id}\">
                {cube_faces_html}
                {interior_html}
                {vase_html}
                {axis_rig_markup}
              </div>
              <div class=\"cube-drag-surface\" id=\"cube-drag-{viewer_id}\"></div>
            </div>

            <div class=\"axis-label cube-label cube-label-x axis-x-min\">{x_meta.get('min','')}</div>
            <div class=\"axis-label cube-label cube-label-x axis-x-max\">{x_meta.get('max','')}</div>
            <div class=\"axis-label cube-label cube-label-y axis-y-min\">{y_meta.get('min','')}</div>
            <div class=\"axis-label cube-label cube-label-y axis-y-max\">{y_meta.get('max','')}</div>
            <div class=\"axis-label cube-label cube-label-time axis-t-min\">{time_meta.get('min','')}</div>
            <div class=\"axis-label cube-label cube-label-time axis-t-max\">{time_meta.get('max','')}</div>
            <div class=\"axis-label cube-label cube-label-x axis-x-name\">{x_meta.get('name','')}</div>
            <div class=\"axis-label cube-label cube-label-y axis-y-name\">{y_meta.get('name','')}</div>
            <div class=\"axis-label cube-label cube-label-time axis-t-name\">{time_meta.get('name','')}</div>
          </div>
        </div>
      </div>
    </div>
    <div class=\"cube-js-warning hidden\" id=\"cube-js-warning-{viewer_id}\" aria-live=\"polite\">
      <div class=\"dot\"></div>
      <div class=\"cube-warning-text\"><strong>Interactive controls need JavaScript.</strong> Trust this notebook/output and temporarily disable script blockers to rotate and zoom the cube.</div>
    </div>
    <noscript>
      <div class=\"cube-js-warning\" aria-live=\"polite\">
        <div class=\"dot\"></div>
        <div class=\"cube-warning-text\"><strong>Interactive controls need JavaScript.</strong> Trust this notebook/output and temporarily disable script blockers to rotate and zoom the cube.</div>
      </div>
    </noscript>
    {legend_html}
  </div>

  {axis_rig_meta_block}
  {drift_centering_script(viewer_id)}
  <script>
    (function() {{
      const viewerId = "{viewer_id}";
      const root = document.getElementById("cube-figure-" + viewerId);
      if (!root) {{
        console.warn("[CubeViewer] Root element not found for viewerId", viewerId);
        return;
      }}

      const canvas = document.getElementById("cube-canvas-" + viewerId);
      const cubeRotation = document.getElementById("cube-rotation-" + viewerId);
      const cubeWrapper = document.getElementById("cube-wrapper-" + viewerId);
      const scene = cubeWrapper ? cubeWrapper.closest(".cube-scene") : null;
      const sceneDragSurface = scene ? scene.querySelector(".scene-drag-surface") : null;
      const dragSurface =
        document.getElementById("cube-drag-" + viewerId)
        || sceneDragSurface
        || cubeWrapper;
      const rotationTarget = cubeWrapper || scene;
      const jsWarning = document.getElementById("cube-js-warning-" + viewerId);
      const jsWarningText = jsWarning ? jsWarning.querySelector(".cube-warning-text") : null;
      let updateAxisRigBillboard = null;

      const showWarning = (message) => {{
        if (!jsWarning) return;
        if (jsWarningText && message) {{
          jsWarningText.innerHTML = message;
        }}
        jsWarning.classList.remove("hidden");
      }};

      const data = root.dataset || {{}};
      let rotationX = (parseFloat(data.rotX) || 0) * Math.PI / 180;
      let rotationY = (parseFloat(data.rotY) || 0) * Math.PI / 180;
      let zoom = parseFloat(data.zoom) || 1;
      const zoomMin = 0.35;
      const zoomMax = 6.0;
      {axis_rig_js_block}

      try {{
        if (!canvas || !cubeRotation || !rotationTarget) {{
          showWarning("<strong>Interactive controls unavailable.</strong> Viewer elements failed to initialize.");
          return;
        }}

        const gl = canvas.getContext("webgl");

        // Maintain a universal reference frame via CSS variables so scenes with
        // multiple cubes can share rotation/zoom state.
        function applyCubeRotation() {{
          if (cubeWrapper) {{
            cubeWrapper.style.setProperty("--rot-x", rotationX + "rad");
            cubeWrapper.style.setProperty("--rot-y", rotationY + "rad");
            cubeWrapper.style.setProperty("--zoom", zoom);
          }}
          if (!cubeWrapper && rotationTarget) {{
            rotationTarget.style.setProperty("--rot-x", rotationX + "rad");
            rotationTarget.style.setProperty("--rot-y", rotationY + "rad");
            rotationTarget.style.setProperty("--zoom", zoom);
          }}
          if (updateAxisRigBillboard) {{
            updateAxisRigBillboard();
          }}
        }}

        applyCubeRotation();

        let dragging = false;
        let activePointerId = null;
        let startX = 0, startY = 0;
        let startRotX = rotationX, startRotY = rotationY;

        const handlePointerMove = (e) => {{
          if (!dragging || (activePointerId !== null && e.pointerId !== activePointerId)) {{
            return;
          }}
          const dx = e.clientX - startX;
          const dy = e.clientY - startY;
          rotationY = startRotY + dx * 0.01;
          rotationX = startRotX + dy * 0.01;
          applyCubeRotation();
        }};

        function stopDragging(e) {{
          if (!dragging) return;
          if (activePointerId !== null && e && e.pointerId !== activePointerId) return;
          dragging = false;
          window.removeEventListener("pointermove", handlePointerMove);
          if (dragSurface && activePointerId !== null && dragSurface.hasPointerCapture(activePointerId)) {{
            dragSurface.releasePointerCapture(activePointerId);
          }}
          if (dragSurface) {{
            dragSurface.style.cursor = "grab";
          }}
          activePointerId = null;
        }}

        if (dragSurface) {{
          dragSurface.style.cursor = "grab";
          dragSurface.style.touchAction = "none";

          dragSurface.addEventListener("pointerdown", e => {{
            e.preventDefault();
            e.stopPropagation();
            dragging = true;
            activePointerId = e.pointerId;
            startX = e.clientX;
            startY = e.clientY;
            startRotX = rotationX;
            startRotY = rotationY;
            dragSurface.setPointerCapture(e.pointerId);
            dragSurface.style.cursor = "grabbing";
            window.addEventListener("pointermove", handlePointerMove);
          }});

          dragSurface.addEventListener("pointerup", endEvent => {{
            stopDragging(endEvent);
          }});

          dragSurface.addEventListener("pointercancel", endEvent => {{
            stopDragging(endEvent);
          }});

          dragSurface.addEventListener("wheel", e => {{
            e.preventDefault();
            const delta = e.deltaY;
            const zoomFactor = Math.exp(delta * 0.0015);
            zoom = Math.min(zoomMax, Math.max(zoomMin, zoom * zoomFactor));
            applyCubeRotation();
          }}, {{ passive: false }});
        }} else {{
          showWarning("<strong>Interactive controls unavailable.</strong> Drag surface missing.");
        }}

        window.addEventListener("pointerup", endEvent => stopDragging(endEvent));
        window.addEventListener("pointercancel", endEvent => stopDragging(endEvent));

        if (!gl) {{
          console.warn("[CubeViewer] WebGL unavailable; rendering CSS cube only for viewerId", viewerId);
          showWarning('<strong>WebGL unavailable.</strong> Falling back to CSS-only cube rendering (rotation and zoom still work).');
        }}
      }} catch (err) {{
        console.error("[CubeViewer] Failed to initialize viewer", viewerId, err);
        showWarning("<strong>Interactive controls unavailable.</strong> Failed to initialize viewer script.");
      }}

      const cbMin = root.getAttribute("data-cb-min");
      const cbMax = root.getAttribute("data-cb-max");
      if (cbMin !== null) {{
        const minEl = document.getElementById("cb-min-" + viewerId);
        if (minEl) minEl.innerText = cbMin;
      }}
      if (cbMax !== null) {{
        const maxEl = document.getElementById("cb-max-" + viewerId);
        if (maxEl) maxEl.innerText = cbMax;
      }}
    }})();
  </script>
</body>
</html>
"""
    return html


def cube_from_dataarray(
    da: xr.DataArray,
    out_html: str | None = None,
    cmap: str = "viridis",
    size_px: int | None = None,
    thin_time_factor: int = 4,
    title: str | None = None,
    time_label: str | None = None,
    x_label: str | None = None,
    y_label: str | None = None,
    *,
    legend_title: str | None = None,
    theme: Any | None = None,
    show_progress: bool = True,
    progress_style: str = "bar",
    time_dim: str | None = None,
    fill_limits: tuple[float, float] | None = None,
    fill_breaks: list[float] | None = None,
    fill_labels: list[str] | None = None,
    coord: "CoordCube" | None = None,
    annotations: list["CubeAnnotation"] | None = None,
    return_html: bool = False,
    show_legend: bool = True,
    fill_mode: str = "shell",
    volume_density: Dict[str, int] | None = None,
    volume_downsample: Dict[str, int] | None = None,
    vase_mask: xr.DataArray | None = None,
    vase_outline: Any | None = None,
    axis_meta: Dict[str, Dict[str, str]] | None = None,
    axis_rig: bool | AxisRigSpec = True,
):
    if out_html is None and not return_html:
        out_html = "cube_da.html"

    volume_density = volume_density or {"time": 6, "x": 2, "y": 2}
    volume_downsample = volume_downsample or {"time": 4, "space": 4}

    viewer_id = uuid.uuid4().hex

    da = _reduce_to_3d_time_y_x(da)

    vase_panels = da.attrs.get("vase_panels")

    if time_dim:
        if time_dim not in da.dims:
            raise ValueError(f"Specified time_dim '{time_dim}' not found in DataArray dims {da.dims}")
        remaining_dims = [d for d in da.dims if d != time_dim]
        if len(remaining_dims) < 2:
            raise ValueError("Need at least two spatial dimensions when providing time_dim")
        t_dim = time_dim
        y_dim, x_dim = remaining_dims[-2], remaining_dims[-1]
    else:
        t_dim, y_dim, x_dim = _infer_time_y_x_dims(da)
    if t_dim is None:
        raise ValueError("cube_from_dataarray expects a time dimension for 3D cubes.")
    da = da.transpose(t_dim, y_dim, x_dim)

    nt, ny, nx = da.sizes[t_dim], da.sizes[y_dim], da.sizes[x_dim]

    time_tick_count = getattr(coord, "time_ticks", 4) if coord is not None else 4
    space_tick_count = getattr(coord, "space_ticks", 3) if coord is not None else 3
    time_format = getattr(coord, "time_format", "%Y-%m-%d") if coord is not None else "%Y-%m-%d"

    time_ticks = _infer_axis_ticks(da, t_dim, n_ticks=time_tick_count, time_format=time_format)
    x_ticks = _infer_axis_ticks(da, x_dim, n_ticks=space_tick_count)
    y_ticks = _infer_axis_ticks(da, y_dim, n_ticks=space_tick_count)

    axis_meta = axis_meta or {
        "time": {
            "name": (time_label or _guess_axis_name(da, t_dim)).title(),
            "min": time_ticks[0][1] if time_ticks else "",
            "max": time_ticks[-1][1] if time_ticks else "",
        },
        "x": {
            "name": (x_label or _guess_axis_name(da, x_dim)).title(),
            "min": x_ticks[0][1] if x_ticks else "",
            "max": x_ticks[-1][1] if x_ticks else "",
        },
        "y": {
            "name": (y_label or _guess_axis_name(da, y_dim)).title(),
            "min": y_ticks[0][1] if y_ticks else "",
            "max": y_ticks[-1][1] if y_ticks else "",
        },
    }

    axis_rig_spec = resolve_axis_rig_spec(axis_rig)
    axis_rig_meta = (
        build_axis_rig_meta(da, t_dim, y_dim, x_dim, axis_meta, axis_rig_spec)
        if axis_rig_spec
        else None
    )

    t_indices = list(range(0, nt, max(1, thin_time_factor)))
    if nt > 1 and len(t_indices) == 1:
        # Avoid rendering a degenerate "flat" cube when thinning skips all but one time slice.
        t_indices = [0, nt - 1]

    nt_eff = len(t_indices)

    progress = _CubeProgress(total=nt_eff, enabled=show_progress, style=progress_style)

    front_spatial: Optional[np.ndarray] = None
    back_spatial: Optional[np.ndarray] = None
    left_time_y = np.full((ny, nt_eff), np.nan, dtype="float32")
    right_time_y = np.full((ny, nt_eff), np.nan, dtype="float32")
    top_time_x = np.full((nx, nt_eff), np.nan, dtype="float32")
    bottom_time_x = np.full((nx, nt_eff), np.nan, dtype="float32")

    for idx, t_idx in enumerate(t_indices):
        frame = da.isel({t_dim: t_idx}).transpose(y_dim, x_dim)
        arr = frame.values

        if idx == 0:
            back_spatial = np.flip(arr, axis=1)
        front_spatial = arr

        left_time_y[:, idx] = arr[:, 0]
        right_time_y[:, idx] = arr[:, -1]
        top_time_x[:, idx] = arr[-1, :]
        bottom_time_x[:, idx] = arr[0, :]

        progress.step()

    progress.done()

    assert front_spatial is not None and back_spatial is not None

    all_vals = np.concatenate(
        [
            front_spatial.astype("float32").ravel(),
            back_spatial.astype("float32").ravel(),
            left_time_y.astype("float32").ravel(),
            right_time_y.astype("float32").ravel(),
            top_time_x.astype("float32").ravel(),
            bottom_time_x.astype("float32").ravel(),
        ]
    )

    if fill_limits is not None:
        vmin, vmax = fill_limits
    else:
        mask = np.isfinite(all_vals)
        if mask.any():
            vmin = float(np.nanpercentile(all_vals[mask], 2))
            vmax = float(np.nanpercentile(all_vals[mask], 98))
        else:
            vmin, vmax = -1.0, 1.0

        if vmin == vmax:
            vmin -= 1.0
            vmax += 1.0

    apply_vase_overlay = vase_mask is not None and vase_outline is not None
    mask_slices: Dict[str, np.ndarray] = {}
    vase_color_rgb: tuple[int, int, int] | None = None
    if apply_vase_overlay:
        try:
            if not isinstance(vase_mask, xr.DataArray):
                raise TypeError("vase_mask must be an xarray.DataArray")

            if not all(dim in vase_mask.dims for dim in (t_dim, y_dim, x_dim)):
                raise ValueError(
                    "vase_mask must include the cube dimensions for time, y, and x"
                )

            for dim, size in ((t_dim, nt), (y_dim, ny), (x_dim, nx)):
                if vase_mask.sizes.get(dim) != size:
                    raise ValueError(
                        f"vase_mask dimension {dim!r} mismatch: expected {size}, got {vase_mask.sizes.get(dim)}"
                    )

            from matplotlib.colors import to_rgb

            vase_color_rgb = tuple(int(255 * c) for c in to_rgb(vase_outline.color))
            # Extract per-face mask slices so each PNG face can be tinted before encoding.
            # Faces follow the viewer convention: front/back in space, left/right through time,
            # and top/bottom over the two spatial axes.
            mask_slices["front"] = np.asarray(
                vase_mask.isel({t_dim: t_indices[-1]}).transpose(y_dim, x_dim).values,
                dtype=bool,
            )
            mask_slices["back"] = np.flip(
                np.asarray(
                    vase_mask.isel({t_dim: t_indices[0]}).transpose(y_dim, x_dim).values,
                    dtype=bool,
                ),
                axis=1,
            )
            mask_slices["left"] = np.asarray(
                vase_mask.isel({x_dim: 0, t_dim: t_indices}).transpose(y_dim, t_dim).values,
                dtype=bool,
            )
            mask_slices["right"] = np.asarray(
                vase_mask.isel({x_dim: -1, t_dim: t_indices}).transpose(y_dim, t_dim).values,
                dtype=bool,
            )
            mask_slices["top"] = np.asarray(
                vase_mask.isel({y_dim: -1, t_dim: t_indices}).transpose(x_dim, t_dim).values,
                dtype=bool,
            )
            mask_slices["bottom"] = np.asarray(
                vase_mask.isel({y_dim: 0, t_dim: t_indices}).transpose(x_dim, t_dim).values,
                dtype=bool,
            )
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.warning("Skipping vase overlay due to incompatible mask: %s", exc)
            apply_vase_overlay = False

    face_kwargs = {"cmap": cmap, "fill_limits": (vmin, vmax)}

    def _face_to_png(arr: np.ndarray, mask_key: str | None) -> str:
        rgba = _colormap_to_rgba(arr, **face_kwargs)
        if apply_vase_overlay and vase_color_rgb is not None and mask_key:
            mask_slice = mask_slices.get(mask_key)
            if mask_slice is not None:
                # Apply tint on the RGB channels before turning the face into a base64 PNG.
                tinted_rgb = _apply_vase_tint(
                    rgba[..., :3],
                    mask_slice.astype(bool),
                    vase_color_rgb,
                    vase_outline.alpha,
                )
                rgba = np.concatenate([tinted_rgb, rgba[..., 3:4]], axis=2)
        return _rgba_to_png_base64(rgba)

    front_b64 = _face_to_png(front_spatial, "front")
    back_b64 = _face_to_png(back_spatial, "back")
    left_b64 = _face_to_png(left_time_y, "left")
    right_b64 = _face_to_png(right_time_y, "right")
    top_b64 = _face_to_png(top_time_x, "top")
    bottom_b64 = _face_to_png(bottom_time_x, "bottom")

    faces = {
        "front": f"data:image/png;base64,{front_b64}",
        "back": f"data:image/png;base64,{back_b64}",
        "left": f"data:image/png;base64,{left_b64}",
        "right": f"data:image/png;base64,{right_b64}",
        "top": f"data:image/png;base64,{top_b64}",
        "bottom": f"data:image/png;base64,{bottom_b64}",
    }

    logger.debug(
        "Cube faces generated (base64 lengths): %s",
        {k: len(v) for k, v in faces.items()},
    )

    gradient = np.linspace(0, 1, 256).reshape(1, -1)
    grad_rgba = colormaps.get_cmap(cmap)(gradient)
    grad_img = (grad_rgba * 255).astype("uint8")
    colorbar_b64 = None
    if show_legend:
        buf_cb = io.BytesIO()
        Image.fromarray(grad_img).save(buf_cb, format="PNG")
        colorbar_b64 = base64.b64encode(buf_cb.getvalue()).decode("ascii")

    derived_title = title or da.name or f"{t_dim} × {y_dim} × {x_dim} cube"
    legend_title = legend_title or derived_title
    if not show_legend:
        legend_title = None

    css_vars: Dict[str, str] = {
        "--cube-bg-color": getattr(theme, "bg_color", "#000"),
        "--cube-panel-color": getattr(theme, "panel_color", "#000"),
        "--cube-shadow-strength": str(getattr(theme, "shadow_strength", 0.2)),
        "--cube-title-color": getattr(theme, "title_color", "#f7f7f7"),
        "--cube-axis-color": getattr(theme, "axis_color", "rgba(25, 25, 25, 0.9)"),
        "--cube-legend-color": getattr(theme, "legend_color", "#f7f7f7"),
        "--cube-title-font-size": f"{getattr(theme, 'title_font_size', 18)}px",
        "--cube-axis-font-size": f"{getattr(theme, 'title_font_size', 18) * getattr(theme, 'axis_scale', 0.6)}px",
        "--cube-legend-font-size": f"{getattr(theme, 'title_font_size', 18) * getattr(theme, 'legend_scale', 0.55)}px",
        "--cube-font-family": getattr(
            theme,
            "title_font_family",
            "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
        ),
    }

    legend_html = _build_legend_html(
        legend_title=legend_title,
        colorbar_b64=colorbar_b64,
        fill_breaks=fill_breaks,
        fill_labels=fill_labels,
        viewer_id=viewer_id,
    )
    title_html = f"<div class=\"cube-title\">{derived_title}</div>"

    interior_meta = {"nt": nt, "ny": ny, "nx": nx}
    if fill_mode == "shell":
        logger.debug("Rendering shell cube viewer (no interior planes)")
        full_html = _render_cube_html(
            front=faces["front"],
            back=faces["back"],
            left=faces["left"],
            right=faces["right"],
            top=faces["top"],
            bottom=faces["bottom"],
            interior_planes=None,
            theme=css_vars,
            coord=coord,
            legend_html=legend_html,
            title_html=title_html,
            size_px=size_px,
            axis_meta=axis_meta,
            axis_rig_spec=axis_rig_spec,
            axis_rig_meta=axis_rig_meta,
            color_limits=(vmin, vmax),
            interior_meta=interior_meta,
            viewer_id=viewer_id,
        )
        if return_html:
            if out_html is not None:
                with open(out_html, "w", encoding="utf-8") as f:
                    f.write(full_html)
            return full_html
        if out_html is None:
            raise ValueError("out_html must be provided when return_html=False")
        with open(out_html, "w", encoding="utf-8") as f:
            f.write(full_html)
        frame_base = size_px if size_px is not None else 760
        prefix = Path(out_html).stem or "cube_viewer"
        return show_cube_viewer(
            full_html,
            width=max(850, frame_base + 300),
            height=max(850, frame_base + 300),
            prefix=prefix,
        )

    ts = volume_density.get("time", 6)
    xs = volume_density.get("x", 2)
    ys = volume_density.get("y", 2)

    t_factor = volume_downsample.get("time", 4)
    s_factor = volume_downsample.get("space", 4)

    d_da = da.coarsen({t_dim: t_factor, y_dim: s_factor, x_dim: s_factor}, boundary="trim").mean()

    nt_down = d_da.sizes[t_dim]
    time_indices = np.linspace(1, nt_down - 2, ts, dtype=int) if ts > 0 and nt_down > 2 else []

    ny_down = d_da.sizes[y_dim]
    nx_down = d_da.sizes[x_dim]
    x_indices = np.linspace(1, nx_down - 2, xs, dtype=int) if xs > 0 and nx_down > 2 else []
    y_indices = np.linspace(1, ny_down - 2, ys, dtype=int) if ys > 0 and ny_down > 2 else []

    total_planes = len(time_indices) + len(x_indices) + len(y_indices)
    progress2 = _CubeProgress(total_planes, enabled=show_progress)

    interior_planes = []

    for i in time_indices:
        frame = d_da.isel({t_dim: i})
        arr = frame.values
        b64 = _array_to_png_base64(arr, **face_kwargs)
        interior_planes.append(("time", int(i), b64, {"nt": nt_down, "nx": nx_down, "ny": ny_down}))
        progress2.step()

    for i in x_indices:
        frame = d_da.isel({x_dim: i})
        arr = frame.values
        b64 = _array_to_png_base64(arr, **face_kwargs)
        interior_planes.append(("x", int(i), b64, {"nt": nt_down, "nx": nx_down, "ny": ny_down}))
        progress2.step()

    for i in y_indices:
        frame = d_da.isel({y_dim: i})
        arr = frame.values
        b64 = _array_to_png_base64(arr, **face_kwargs)
        interior_planes.append(("y", int(i), b64, {"nt": nt_down, "nx": nx_down, "ny": ny_down}))
        progress2.step()

    progress2.done()

    interior_meta = {"nt": nt_down, "ny": ny_down, "nx": nx_down}
    logger.debug("Rendering volume cube viewer with %d interior planes", len(interior_planes))
    full_html = _render_cube_html(
        front=faces["front"],
        back=faces["back"],
        left=faces["left"],
        right=faces["right"],
        top=faces["top"],
        bottom=faces["bottom"],
        interior_planes=interior_planes,
        vase_panels=vase_panels,
        theme=css_vars,
        coord=coord,
        legend_html=legend_html,
        title_html=title_html,
        size_px=size_px,
        axis_meta=axis_meta,
        axis_rig_spec=axis_rig_spec,
        axis_rig_meta=axis_rig_meta,
        color_limits=(vmin, vmax),
        interior_meta=interior_meta,
        viewer_id=viewer_id,
    )

    if return_html:
        if out_html is not None:
            with open(out_html, "w", encoding="utf-8") as f:
                f.write(full_html)
        return full_html
    if out_html is None:
        raise ValueError("out_html must be provided when return_html=False")
    with open(out_html, "w", encoding="utf-8") as f:
        f.write(full_html)
    frame_base = size_px if size_px is not None else 760
    prefix = Path(out_html).stem or "cube_viewer"
    return show_cube_viewer(
        full_html,
        width=max(850, frame_base + 300),
        height=max(850, frame_base + 300),
        prefix=prefix,
    )


def _guess_axis_name(da: xr.DataArray, dim: str) -> str:
    name = str(dim).lower()
    if "lat" in name:
        return "latitude"
    if "lon" in name or "lng" in name:
        return "longitude"
    return dim


def _infer_axis_ticks(
    da: xr.DataArray, dim: str, n_ticks: int = 3, time_format: str = "%Y-%m-%d"
):
    if dim not in da.dims:
        return []
    coords = da.coords[dim].values
    if coords.size == 0:
        return []

    idxs = np.linspace(0, coords.size - 1, num=min(n_ticks, coords.size), dtype=int)
    values = coords[idxs]

    if np.issubdtype(values.dtype, np.datetime64):
        times = pd.to_datetime(values)
        labels = [t.strftime(time_format) for t in times]
    else:
        units = da.coords[dim].attrs.get("units", "") if dim in da.coords else ""
        units_str = f" {units}" if units else ""
        labels = [f"{float(v):.2f}{units_str}" for v in values]

    return list(zip(values, labels))


def _axis_range_from_ticks(ticks):
    if not ticks:
        return ""
    if len(ticks) == 1:
        return ticks[0][1]
    return f"{ticks[0][1]} \u2192 {ticks[-1][1]}"


__all__ = [
    "cube_from_dataarray",
    "_guess_axis_name",
    "_infer_axis_ticks",
    "_axis_range_from_ticks",
]
