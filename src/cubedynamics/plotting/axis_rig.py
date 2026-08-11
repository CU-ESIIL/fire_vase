from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any

import numpy as np
import pandas as pd
import xarray as xr


@dataclass(frozen=True)
class AxisRigSpec:
    enabled: bool = True
    show_axis_names: bool = True
    show_end_labels: bool = True
    show_ticks: bool = True
    time_tick: str | int = "monthly"
    time_label_max: int = 10
    end_nudge_px: int = 6
    out_y_px: int = 8
    out_z_px: int = 6
    out_x_px: int = 6
    axis_line_w_px: int = 2
    tick_w_px: int = 1
    tick_l_px: int = 8
    debug: bool = False


def resolve_axis_rig_spec(axis_rig: bool | AxisRigSpec | None) -> AxisRigSpec | None:
    if axis_rig is None or axis_rig is False:
        return None
    if isinstance(axis_rig, AxisRigSpec):
        return axis_rig if axis_rig.enabled else None
    if axis_rig is True:
        return AxisRigSpec()
    raise TypeError("axis_rig must be a bool or AxisRigSpec")


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


def _coord_values(da: xr.DataArray, dim: str) -> np.ndarray:
    coord = da.coords.get(dim)
    if coord is None or coord.size == 0:
        return np.arange(da.sizes.get(dim, 0))
    return np.asarray(coord.values)


def _axis_formatter(values: np.ndarray, units: str, dim_name: str) -> tuple[str, Any]:
    if _looks_like_lat(values, units, dim_name):
        return "Latitude", _format_lat
    if _looks_like_lon(values, units, dim_name):
        return "Longitude", _format_lon
    return dim_name.title(), _format_numeric


def _time_tick_sequence(times: pd.DatetimeIndex, spec: AxisRigSpec) -> pd.DatetimeIndex:
    time_tick = spec.time_tick
    if isinstance(time_tick, str):
        freq_map = {"monthly": "MS", "quarterly": "QS", "yearly": "AS"}
        freq = freq_map.get(time_tick.lower())
        if freq:
            ticks = pd.date_range(start=times.min(), end=times.max(), freq=freq)
            if ticks.size == 0:
                ticks = pd.DatetimeIndex([times.min(), times.max()])
            else:
                if ticks[0] != times.min():
                    ticks = ticks.insert(0, times.min())
                if ticks[-1] != times.max():
                    ticks = ticks.append(pd.DatetimeIndex([times.max()]))
            return ticks
    if isinstance(time_tick, int):
        count = max(2, time_tick)
        ticks_ns = np.linspace(times.min().value, times.max().value, count)
        return pd.to_datetime(ticks_ns)
    return times


def _subsample_tick_labels(
    ticks: list[dict[str, Any]], label_max: int
) -> list[dict[str, Any]]:
    if label_max <= 0 or len(ticks) <= 2 or len(ticks) <= label_max:
        return ticks
    max_labels = max(2, label_max)
    indices = np.linspace(0, len(ticks) - 1, num=max_labels, dtype=int)
    keep = {int(idx) for idx in indices}
    keep.update({0, len(ticks) - 1})
    for idx, tick in enumerate(ticks):
        if idx not in keep:
            tick["label"] = ""
    return ticks


def _ticks_from_values(values: np.ndarray, count: int = 5) -> list[tuple[float, Any]]:
    if values.size == 0:
        return []
    if values.size == 1:
        return [(0.0, values[0])]
    idxs = np.linspace(0, values.size - 1, num=min(count, values.size), dtype=int)
    selected = values[idxs]
    min_val = values.min()
    max_val = values.max()
    denom = max_val - min_val
    if denom == 0:
        return [(0.0, selected[0])]
    ticks = []
    for val in selected:
        frac = float((val - min_val) / denom)
        ticks.append((frac, val))
    return ticks


def build_axis_rig_meta(
    da: xr.DataArray,
    t_dim: str,
    y_dim: str,
    x_dim: str,
    axis_meta: dict[str, dict[str, str]] | None,
    spec: AxisRigSpec,
) -> dict[str, Any]:
    axis_meta = axis_meta or {}

    def _axis_payload(dim: str, axis_key: str, fallback_name: str) -> dict[str, Any]:
        values = _coord_values(da, dim)
        units = str(getattr(da.coords.get(dim), "attrs", {}).get("units", ""))
        fallback_axis_name, formatter = _axis_formatter(values, units, dim)
        axis_name = axis_meta.get(axis_key, {}).get("name") or fallback_name or fallback_axis_name
        if values.size == 0:
            min_label = max_label = ""
        else:
            min_label = formatter(values.min())
            max_label = formatter(values.max())
        ticks = _ticks_from_values(values)
        tick_payload = [
            {"frac": float(frac), "label": ""} for frac, _ in ticks
        ]
        return {
            "name": axis_name,
            "min_label": min_label,
            "max_label": max_label,
            "ticks": tick_payload,
        }

    def _time_payload() -> dict[str, Any]:
        values = _coord_values(da, t_dim)
        axis_name = axis_meta.get("time", {}).get("name") or "Time"
        if values.size <= 1:
            min_label = "t0"
            max_label = "tN"
            tick_count = 4 if isinstance(spec.time_tick, str) else max(2, int(spec.time_tick))
            ticks = [
                {"frac": float(idx) / (tick_count - 1), "label": ""}
                for idx in range(tick_count)
            ]
            return {
                "name": axis_name,
                "min_label": min_label,
                "max_label": max_label,
                "ticks": ticks,
            }

        if np.issubdtype(values.dtype, np.datetime64):
            times = pd.to_datetime(values)
            ticks = _time_tick_sequence(times, spec)
            t0 = times.min()
            tN = times.max()
            denom = (tN - t0).total_seconds() or 1.0
            tick_payload = []
            for tick in ticks:
                frac = (tick - t0).total_seconds() / denom
                tick_payload.append({"frac": float(frac), "label": _format_time_label(tick)})
            tick_payload = _subsample_tick_labels(tick_payload, spec.time_label_max)
            return {
                "name": axis_name,
                "min_label": _format_time_label(t0),
                "max_label": _format_time_label(tN),
                "ticks": tick_payload,
            }

        numeric = values.astype(float)
        min_val = np.nanmin(numeric)
        max_val = np.nanmax(numeric)
        denom = max_val - min_val if max_val != min_val else 1.0
        tick_count = 4 if isinstance(spec.time_tick, str) else max(2, int(spec.time_tick))
        tick_vals = np.linspace(min_val, max_val, tick_count)
        tick_payload = [
            {"frac": float((val - min_val) / denom), "label": _format_numeric(val)}
            for val in tick_vals
        ]
        tick_payload = _subsample_tick_labels(tick_payload, spec.time_label_max)
        return {
            "name": axis_name,
            "min_label": _format_numeric(min_val),
            "max_label": _format_numeric(max_val),
            "ticks": tick_payload,
        }

    return {
        "x": _axis_payload(x_dim, "x", "Longitude"),
        "y": _axis_payload(y_dim, "y", "Latitude"),
        "time": _time_payload(),
    }


def axis_rig_css(spec: AxisRigSpec) -> str:
    return """
    [data-axis-rig="true"] .axis-label {
      display: none;
    }

    .cd-axis-rig {
      position: absolute;
      inset: 0;
      width: var(--cd-cube-size, var(--cube-size));
      height: var(--cd-cube-size, var(--cube-size));
      transform-style: preserve-3d;
      pointer-events: none;
      color: var(--cd-axis-color);
      font-size: var(--cd-axis-font, var(--cube-axis-font-size, 13px));
      letter-spacing: 0.04em;
      /* Axis rig lives in cube-local coords; out-z anchors to front face, Y labels shift left for legibility. */
      --cd-axis-color: rgba(25, 25, 25, 0.9);
      --cd-axis-out-x: 16px;
      --cd-axis-out-y: 14px;
      --cd-axis-front-z: calc(0.5 * var(--cd-cube-size, var(--cube-size)));
      --cd-axis-out-z: calc(var(--cd-axis-front-z) + 6px);
      --cd-axis-line-w: var(--cd-axis-stroke, 2px);
      --cd-axis-tick-w: var(--cd-axis-stroke, 1px);
      --cd-axis-tick-l: var(--cd-axis-tick-l, 8px);
      --cd-axis-label-gap: 16px;
      --cd-axis-end-nudge: 6px;
      --cd-axis-x-name-drop: 18px;
      --cd-axis-time-name-drop: 24px;
      --cd-axis-time-label-drop: 18px;
      --cd-axis-y-extra-left: 22px;
      --cd-bb-rot-x: 0rad;
      --cd-bb-rot-y: 0rad;
    }

    .cd-axis-rig--debug {
      outline: 1px dashed rgba(0, 255, 255, 0.6);
    }

    .cd-axis-rig--hide-ticks .cd-axis-ticks {
      display: none;
    }

    .cd-axis-rig--hide-end-labels .cd-axis-end {
      display: none;
    }

    .cd-axis-rig--hide-names .cd-axis-name {
      display: none;
    }

    .cd-axis-group {
      position: absolute;
      transform-style: preserve-3d;
    }

    .cd-axis-line {
      position: absolute;
      background: var(--cd-axis-color);
    }

    .cd-axis-ticks {
      position: absolute;
      inset: 0;
    }

    .cd-axis-tick {
      position: absolute;
    }

    .cd-axis-tick-mark {
      position: absolute;
      background: var(--cd-axis-color);
    }

    .cd-axis-label {
      position: absolute;
      white-space: nowrap;
    }

    .cd-axis-label-face {
      display: inline-block;
      padding: var(--cd-axis-pill-px, 0px);
      transform-style: preserve-3d;
      transform: rotateX(var(--cd-bb-rot-x)) rotateY(var(--cd-bb-rot-y));
    }

    .cd-axis-label-face--time {
      transform: rotateX(var(--cd-bb-rot-x)) rotateY(var(--cd-bb-rot-y));
    }

    /* X axis (longitude) - front bottom edge */
    .cd-axis-x {
      left: 0;
      bottom: 0;
      width: 100%;
      height: 0;
      transform: translate3d(0, var(--cd-axis-out-y), var(--cd-axis-out-z));
    }

    .cd-axis-x .cd-axis-line {
      left: 0;
      top: 0;
      width: 100%;
      height: var(--cd-axis-line-w);
    }

    .cd-axis-x .cd-axis-tick {
      top: 0;
      transform: translateX(-50%);
    }

    .cd-axis-x .cd-axis-tick-mark {
      width: var(--cd-axis-tick-w);
      height: var(--cd-axis-tick-l);
      left: 50%;
      top: calc(-0.5 * var(--cd-axis-tick-l) + 0.5 * var(--cd-axis-line-w));
      transform: translateX(-50%);
    }

    .cd-axis-x .cd-axis-tick-label {
      position: absolute;
      left: 50%;
      top: calc(-1 * var(--cd-axis-label-gap));
      transform: translateX(-50%);
    }

    .cd-axis-x .cd-axis-end--min {
      left: 0;
      top: var(--cd-axis-x-name-drop);
      transform: translateX(calc(-1 * var(--cd-axis-end-nudge)));
    }

    .cd-axis-x .cd-axis-end--max {
      left: 100%;
      top: var(--cd-axis-x-name-drop);
      transform: translateX(calc(-100% + var(--cd-axis-end-nudge)));
    }

    .cd-axis-x .cd-axis-name {
      left: 50%;
      top: var(--cd-axis-x-name-drop);
      transform: translateX(-50%);
    }

    /* Y axis (latitude) - front left edge */
    .cd-axis-y {
      left: 0;
      bottom: 0;
      width: 0;
      height: 100%;
      transform: translate3d(calc(-1 * var(--cd-axis-out-x)), 0, var(--cd-axis-out-z));
    }

    .cd-axis-y .cd-axis-line {
      left: 0;
      bottom: 0;
      width: var(--cd-axis-line-w);
      height: 100%;
    }

    .cd-axis-y .cd-axis-tick {
      left: 0;
      transform: translateY(50%);
    }

    .cd-axis-y .cd-axis-tick-mark {
      width: var(--cd-axis-tick-l);
      height: var(--cd-axis-tick-w);
      left: calc(-1 * var(--cd-axis-tick-l) + 0.5 * var(--cd-axis-line-w));
      top: 50%;
      transform: translateY(-50%);
    }

    .cd-axis-y .cd-axis-tick-label {
      position: absolute;
      left: calc(
        -1 * (var(--cd-axis-label-gap) + var(--cd-axis-tick-l) + 12px + var(--cd-axis-y-extra-left))
      );
      top: 50%;
      transform: translateY(-50%);
    }

    .cd-axis-y .cd-axis-end--min {
      left: calc(
        -1 * (var(--cd-axis-label-gap) + var(--cd-axis-tick-l) + 12px + var(--cd-axis-y-extra-left))
      );
      bottom: 0;
      transform: translateY(calc(var(--cd-axis-end-nudge)));
    }

    .cd-axis-y .cd-axis-end--max {
      left: calc(
        -1 * (var(--cd-axis-label-gap) + var(--cd-axis-tick-l) + 12px + var(--cd-axis-y-extra-left))
      );
      bottom: 100%;
      transform: translateY(calc(-100% - var(--cd-axis-end-nudge)));
    }

    .cd-axis-y .cd-axis-name {
      left: calc(
        -1 * (var(--cd-axis-label-gap) + var(--cd-axis-tick-l) + 12px + var(--cd-axis-y-extra-left))
      );
      bottom: 50%;
      transform: translateY(50%);
    }

    .cd-axis-y .cd-axis-label-face {
      transform-origin: 100% 50%;
    }

    /* Time axis - bottom right edge, rotated into depth */
    .cd-axis-time {
      left: 100%;
      bottom: 0;
      width: 100%;
      height: 0;
      transform-origin: left center;
      transform: translate3d(var(--cd-axis-out-x), var(--cd-axis-out-y), var(--cd-axis-out-z)) rotateY(90deg);
    }

    .cd-axis-time .cd-axis-line {
      left: 0;
      top: 0;
      width: 100%;
      height: var(--cd-axis-line-w);
    }

    .cd-axis-time .cd-axis-tick {
      top: 0;
      transform: translateX(-50%);
    }

    .cd-axis-time .cd-axis-tick-mark {
      width: var(--cd-axis-tick-w);
      height: var(--cd-axis-tick-l);
      left: 50%;
      top: calc(-0.5 * var(--cd-axis-tick-l) + 0.5 * var(--cd-axis-line-w));
      transform: translateX(-50%);
    }

    .cd-axis-time .cd-axis-tick-label {
      position: absolute;
      left: 50%;
      top: var(--cd-axis-time-label-drop);
      transform: translateX(-50%);
    }

    .cd-axis-time .cd-axis-end--min {
      left: 0;
      top: var(--cd-axis-time-label-drop);
      transform: translateX(calc(-1 * var(--cd-axis-end-nudge)));
    }

    .cd-axis-time .cd-axis-end--max {
      left: 100%;
      top: var(--cd-axis-time-label-drop);
      transform: translateX(calc(-100% + var(--cd-axis-end-nudge)));
    }

    .cd-axis-time .cd-axis-name {
      left: 50%;
      top: var(--cd-axis-time-name-drop);
      transform: translateX(-50%);
    }
    """


def axis_rig_html(viewer_id: str, spec: AxisRigSpec) -> str:
    classes = ["cd-axis-rig"]
    if spec.debug:
        classes.append("cd-axis-rig--debug")
    if not spec.show_ticks:
        classes.append("cd-axis-rig--hide-ticks")
    if not spec.show_end_labels:
        classes.append("cd-axis-rig--hide-end-labels")
    if not spec.show_axis_names:
        classes.append("cd-axis-rig--hide-names")

    style = (
        f"--cd-axis-out-x: {spec.out_x_px}px;"
        f" --cd-axis-out-y: {spec.out_y_px}px;"
        f" --cd-axis-out-z: calc(var(--cd-axis-front-z) + {spec.out_z_px}px);"
        f" --cd-axis-line-w: {spec.axis_line_w_px}px;"
        f" --cd-axis-tick-w: {spec.tick_w_px}px;"
        f" --cd-axis-tick-l: {spec.tick_l_px}px;"
        f" --cd-axis-end-nudge: {spec.end_nudge_px}px;"
    )

    class_attr = " ".join(classes)

    return f"""
      <div class=\"{class_attr}\" id=\"cd-axis-rig-{viewer_id}\" data-viewer-id=\"{viewer_id}\" data-time-label-max=\"{spec.time_label_max}\" style=\"{style}\">
        <div class=\"cd-axis-group cd-axis-x\" data-axis=\"x\">
          <div class=\"cd-axis-line\"></div>
          <div class=\"cd-axis-ticks\"></div>
          <div class=\"cd-axis-label cd-axis-end cd-axis-end--min\"><span class=\"cd-axis-label-face\"></span></div>
          <div class=\"cd-axis-label cd-axis-end cd-axis-end--max\"><span class=\"cd-axis-label-face\"></span></div>
          <div class=\"cd-axis-label cd-axis-name\"><span class=\"cd-axis-label-face\"></span></div>
        </div>
        <div class=\"cd-axis-group cd-axis-y\" data-axis=\"y\">
          <div class=\"cd-axis-line\"></div>
          <div class=\"cd-axis-ticks\"></div>
          <div class=\"cd-axis-label cd-axis-end cd-axis-end--min\"><span class=\"cd-axis-label-face\"></span></div>
          <div class=\"cd-axis-label cd-axis-end cd-axis-end--max\"><span class=\"cd-axis-label-face\"></span></div>
          <div class=\"cd-axis-label cd-axis-name\"><span class=\"cd-axis-label-face\"></span></div>
        </div>
        <div class=\"cd-axis-group cd-axis-time\" data-axis=\"time\">
          <div class=\"cd-axis-line\"></div>
          <div class=\"cd-axis-ticks\"></div>
          <div class=\"cd-axis-label cd-axis-end cd-axis-end--min\"><span class=\"cd-axis-label-face cd-axis-label-face--time\"></span></div>
          <div class=\"cd-axis-label cd-axis-end cd-axis-end--max\"><span class=\"cd-axis-label-face cd-axis-label-face--time\"></span></div>
          <div class=\"cd-axis-label cd-axis-name\"><span class=\"cd-axis-label-face cd-axis-label-face--time\"></span></div>
        </div>
      </div>
    """


def axis_rig_meta_script(viewer_id: str, meta: dict[str, Any]) -> str:
    payload = json.dumps(meta)
    return (
        "<script>"
        "window.__CD_AXIS_META__ = Object.assign({}, window.__CD_AXIS_META__ || {}, "
        f"{{\"{viewer_id}\": {payload}}});"
        "</script>"
    )


def axis_rig_js(viewer_id: str) -> str:
    return f"""
      const axisRig = document.getElementById("cd-axis-rig-{viewer_id}");
      if (axisRig) {{
        const target =
          (cubeRotation && cubeRotation.querySelector(".cd-cube"))
          || cubeRotation
          || cubeWrapper
          || scene;
        if (target && axisRig.parentElement !== target) {{
          target.appendChild(axisRig);
        }}

        const axisMeta = (window.__CD_AXIS_META__ || {{}})["{viewer_id}"] || null;
        const labelMax = parseInt(axisRig.dataset.timeLabelMax || "10", 10);

        const readRotationFromMatrix = (el) => {{
          if (!el) return null;
          const transform = window.getComputedStyle(el).transform;
          if (!transform || transform === "none") return null;
          try {{
            const matrix = new DOMMatrixReadOnly(transform);
            const rotY = Math.atan2(matrix.m13, matrix.m11);
            const rotX = Math.atan2(matrix.m32, matrix.m33);
            return {{ rotX, rotY }};
          }} catch (err) {{
            return null;
          }}
        }};

        updateAxisRigBillboard = () => {{
          let rotX = rotationX;
          let rotY = rotationY;
          if (!Number.isFinite(rotX) || !Number.isFinite(rotY)) {{
            const fallback = readRotationFromMatrix(cubeRotation || rotationTarget);
            if (fallback) {{
              rotX = fallback.rotX;
              rotY = fallback.rotY;
            }} else {{
              rotX = 0;
              rotY = 0;
            }}
          }}
          axisRig.style.setProperty("--cd-bb-rot-x", (-rotX) + "rad");
          axisRig.style.setProperty("--cd-bb-rot-y", (-rotY) + "rad");
        }};

        const renderAxis = (axisKey, axisGroup, meta, options = {{}}) => {{
          if (!axisGroup || !meta) return;
          const endMin = axisGroup.querySelector(".cd-axis-end--min .cd-axis-label-face");
          const endMax = axisGroup.querySelector(".cd-axis-end--max .cd-axis-label-face");
          const nameEl = axisGroup.querySelector(".cd-axis-name .cd-axis-label-face");
          if (axisKey === "time") {{
            // Time runs front (max/tN) to back (min/t0) along the depth edge.
            if (endMin) endMin.textContent = meta.max_label || "";
            if (endMax) endMax.textContent = meta.min_label || "";
          }} else {{
            if (endMin) endMin.textContent = meta.min_label || "";
            if (endMax) endMax.textContent = meta.max_label || "";
          }}
          if (nameEl) nameEl.textContent = meta.name || "";

          const ticksHost = axisGroup.querySelector(".cd-axis-ticks");
          if (!ticksHost || !Array.isArray(meta.ticks)) return;
          ticksHost.innerHTML = "";

          const ticks = meta.ticks;
          let labelStep = 1;
          if (options.subsampleLabels && labelMax > 0 && ticks.length > labelMax) {{
            labelStep = Math.max(1, Math.ceil(ticks.length / labelMax));
          }}

          ticks.forEach((tick, idx) => {{
            const tickEl = document.createElement("div");
            tickEl.className = "cd-axis-tick";

            if (axisKey === "y") {{
              tickEl.style.bottom = (tick.frac * 100) + "%";
            }} else if (axisKey === "time") {{
              // Depth axis: frac=1 (newest) is front, so flip to map to left=0%.
              tickEl.style.left = ((1 - tick.frac) * 100) + "%";
            }} else {{
              tickEl.style.left = (tick.frac * 100) + "%";
            }}

            const mark = document.createElement("div");
            mark.className = "cd-axis-tick-mark";
            tickEl.appendChild(mark);

            if (tick.label && (!options.subsampleLabels || (idx % labelStep === 0) || idx === ticks.length - 1)) {{
              const label = document.createElement("div");
              label.className = "cd-axis-tick-label";
              const labelFace = document.createElement("span");
              labelFace.className = axisKey === "time" ? "cd-axis-label-face cd-axis-label-face--time" : "cd-axis-label-face";
              labelFace.textContent = tick.label;
              label.appendChild(labelFace);
              tickEl.appendChild(label);
            }}

            ticksHost.appendChild(tickEl);
          }});
        }};

        if (axisMeta) {{
          renderAxis("x", axisRig.querySelector(".cd-axis-x"), axisMeta.x || null);
          renderAxis("y", axisRig.querySelector(".cd-axis-y"), axisMeta.y || null);
          renderAxis("time", axisRig.querySelector(".cd-axis-time"), axisMeta.time || null, {{ subsampleLabels: true }});
        }}

        updateAxisRigBillboard();
      }}
    """


__all__ = ["AxisRigSpec", "resolve_axis_rig_spec", "build_axis_rig_meta", "axis_rig_css", "axis_rig_html", "axis_rig_meta_script", "axis_rig_js"]
