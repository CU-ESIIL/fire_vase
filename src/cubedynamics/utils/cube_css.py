"""Helpers for emitting lightweight CSS cube HTML scaffolding."""

from __future__ import annotations

import html
from pathlib import Path
from typing import Any, Dict, List, Sequence

DEFAULT_FACES = {
    "front": "none",
    "back": "none",
    "right": "none",
    "left": "none",
    "top": "none",
    "bottom": "none",
}


def _face_style(face_uri: str) -> str:
    base_style = "background: rgba(255, 255, 255, 0.05);"
    if face_uri.lower() == "none":
        return base_style
    return "background-image: url('{0}'); background-size: cover; background-position: center;".format(
        face_uri
    )


def _colorbar_labels(breaks: Sequence[float] | None, labels: Sequence[str] | None) -> str:
    if not breaks:
        return "<span id=\"cb-min\"></span><span id=\"cb-max\"></span>"
    spans: List[str] = []
    for idx, val in enumerate(breaks):
        label = labels[idx] if labels and idx < len(labels) else f"{val:.2f}"
        spans.append(f"<span class=\"cb-tick\" data-tick=\"{val:.2f}\">{label}</span>")
    return "".join(spans)


def _axis_section(axis: Dict[str, Any] | None) -> str:
    if not axis:
        return ""
    name = axis.get("name")
    if not name:
        return ""
    range_text = axis.get("range") or ""
    ticks = axis.get("ticks") or []
    ticks_html = ""
    if ticks:
        tick_labels = " \u00b7 ".join(html.escape(str(t)) for t in ticks)
        ticks_html = f"<div class='axis-ticks'>{tick_labels}</div>"
    range_html = f"<span class='axis-range'>{html.escape(str(range_text))}</span>" if range_text else ""
    return (
        "<div class='axis-row'>"
        f"<span class='axis-title'>{html.escape(str(name))}:</span>"
        f"{range_html}"
        f"{ticks_html}"
        "</div>"
    )


def write_css_cube_static(
    *,
    out_html: str = "cube_da.html",
    size_px: int = 260,
    faces: Dict[str, str] | None = None,
    colorbar_b64: str | None = None,
    title: str = "Cube Viewer",
    time_label: str = "time",
    x_label: str = "x",
    y_label: str = "y",
    legend_title: str | None = None,
    css_vars: Dict[str, str] | None = None,
    colorbar_breaks: Sequence[float] | None = None,
    colorbar_labels: Sequence[str] | None = None,
    coord: Any | None = None,
    annotations: Sequence[Any] | None = None,
    axis_info: Dict[str, Any] | None = None,
) -> Path:
    """Write a standalone HTML page with a simple CSS-based cube skeleton.

    Parameters
    ----------
    out_html:
        Output HTML path.
    size_px:
        Width/height of the cube in pixels.
    faces:
        Optional mapping of cube face names to data URIs (or ``"none"``).
    colorbar_b64:
        Optional base64-encoded PNG that will be used as the colorbar image.
    title:
        Title text rendered above the cube.
    time_label, x_label, y_label:
        Axis labels placed around the cube to indicate coordinate directions.
    """

    face_map = {**DEFAULT_FACES, **(faces or {})}
    size = int(size_px)
    half = size / 2

    colorbar = (
        f'<img class="colorbar-img" src="data:image/png;base64,{colorbar_b64}" alt="colorbar" />'
        if colorbar_b64
        else ""
    )

    css_vars = css_vars or {}
    bg_color = css_vars.get("--cube-bg-color", "#000")
    panel_color = css_vars.get("--cube-panel-color", "#000")
    shadow_strength = css_vars.get("--cube-shadow-strength", "0.2")
    title_color = css_vars.get("--cube-title-color", "#f7f7f7")
    axis_color = css_vars.get("--cube-axis-color", "#f7f7f7")
    legend_color = css_vars.get("--cube-legend-color", "#f7f7f7")
    title_font_size = css_vars.get("--cube-title-font-size", "18px")
    axis_font_size = css_vars.get("--cube-axis-font-size", "12px")
    legend_font_size = css_vars.get("--cube-legend-font-size", "10px")
    font_family = css_vars.get(
        "--cube-font-family", "system-ui, -apple-system, sans-serif"
    )

    legend_block = (
        f"<div class=\"colorbar-title\">{legend_title}</div>" if legend_title else ""
    )

    tick_block = _colorbar_labels(colorbar_breaks, colorbar_labels)

    axis_info = axis_info or {}
    axis_rows = [
        _axis_section(axis_info.get("time")),
        _axis_section(axis_info.get("y")),
        _axis_section(axis_info.get("x")),
    ]
    axis_info_html = (
        "<div class=\"cube-axis-info\">" + "".join([row for row in axis_rows if row]) + "</div>"
        if any(axis_rows)
        else ""
    )

    html = f"""
<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"UTF-8\" />
  <title>{title}</title>
  <style>
    :root {{
      --cube-size: {size}px;
      --cube-bg-color: {bg_color};
      --cube-panel-color: {panel_color};
      --cube-shadow-strength: {shadow_strength};
      --cube-title-color: {title_color};
      --cube-axis-color: {axis_color};
      --cube-legend-color: {legend_color};
      --cube-title-font-size: {title_font_size};
      --cube-axis-font-size: {axis_font_size};
      --cube-legend-font-size: {legend_font_size};
      --cube-font-family: {font_family};
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
      width: min(1180px, 100%);
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
    .cube-inner {{
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 10px;
    }}
    .cube-scene {{
      position: relative;
      width: 900px;
      height: 680px;
      display: flex;
      align-items: center;
      justify-content: center;
      perspective: 1600px;
      transform: scale(var(--cube-zoom, 1));
      transform-origin: center center;
      transition: transform 120ms ease-out;
    }}
    #cube {{
      position: relative;
      width: var(--cube-size);
      height: var(--cube-size);
      transform-style: preserve-3d;
      transform: translateZ(0px) rotateX(var(--rotX, 20deg)) rotateY(var(--rotY, -30deg));
    }}
    .face {{
      position: absolute;
      width: var(--cube-size);
      height: var(--cube-size);
      background-size: cover;
      background-position: center;
      border: 1px solid #222;
      box-sizing: border-box;
      background-color: rgba(255,255,255,0.02);
    }}
    #front  {{ transform: translateZ({half}px); { _face_style(face_map['front']) } }}
    #back   {{ transform: rotateY(180deg) translateZ({half}px); { _face_style(face_map['back']) } }}
    #right  {{ transform: rotateY(90deg) translateZ({half}px); { _face_style(face_map['right']) } }}
    #left   {{ transform: rotateY(-90deg) translateZ({half}px); { _face_style(face_map['left']) } }}
    #top    {{ transform: rotateX(90deg) translateZ({half}px); { _face_style(face_map['top']) } }}
    #bottom {{ transform: rotateX(-90deg) translateZ({half}px); { _face_style(face_map['bottom']) } }}
    .cube-outline {{
      position: absolute;
      inset: 0;
      width: var(--cube-size);
      height: var(--cube-size);
      transform-style: preserve-3d;
      border: 1px solid rgba(255,255,255,0.15);
      pointer-events: none;
    }}
    .cube-label {{
      position: absolute;
      font-size: var(--cube-axis-font-size);
      letter-spacing: 0.04em;
      padding: 4px 8px;
      border-radius: 6px;
      border: 1px solid rgba(0,0,0,0.08);
      pointer-events: none;
      color: var(--cube-axis-color);
      background: rgba(255,255,255,0.08);
      transform-style: preserve-3d;
      backdrop-filter: blur(3px);
    }}
    .cube-label-time {{
      transform: translate3d(-44px, 50%, {half}px) rotateY(90deg) rotateX(90deg);
    }}
    .cube-label-y {{
      transform: translate3d({half}px, -46px, 0px) rotateX(90deg);
    }}
    .cube-label-x {{
      transform: translate3d(0px, {half + 14}px, {half}px) rotateY(0deg);
    }}
    .cube-axis-info {{
      display: flex;
      flex-direction: column;
      gap: 4px;
      align-items: center;
      color: var(--cube-axis-color);
      font-size: var(--cube-axis-font-size);
    }}
    .axis-row {{
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 2px;
    }}
    .axis-title {{
      font-weight: 700;
      color: var(--cube-axis-color);
      text-transform: lowercase;
    }}
    .axis-range {{
      opacity: 0.95;
    }}
    .axis-ticks {{
      font-size: calc(var(--cube-axis-font-size) * 0.95);
      opacity: 0.85;
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
  </style>

</head>
<body>

<div class=\"cube-figure\" id=\"cube-figure\">
  <div class=\"cube-title\">{title}</div>
  <div class=\"cube-main\">
    <div class=\"cube-inner\" id=\"cube-inner\">
      <div class=\"cube-scene\" id=\"cube-scene\">
        <div id=\"cube\">
          <div id=\"front\"  class=\"face\"></div>
          <div id=\"back\"   class=\"face\"></div>
          <div id=\"right\"  class=\"face\"></div>
          <div id=\"left\"   class=\"face\"></div>
          <div id=\"top\"    class=\"face\"></div>
          <div id=\"bottom\" class=\"face\"></div>
          <div class=\"cube-outline\"></div>
          <div class=\"cube-label cube-label-time\">{time_label}</div>
          <div class=\"cube-label cube-label-y\">{y_label}</div>
          <div class=\"cube-label cube-label-x\">{x_label}</div>
        </div>
      </div>
      {axis_info_html}
    </div>
  </div>
  <div class=\"cube-legend-panel\">
    <div class=\"cube-legend-card\">
      {legend_block}
      <div class=\"colorbar-wrapper\">{colorbar}</div>
      <div class=\"colorbar-labels\">{tick_block}</div>
    </div>
  </div>
</div>

<script>
class CubeScene {{
  constructor(config) {{
    this.config = config || {{}};
    this.cube = document.getElementById("cube");
    this.scene = document.getElementById("cube-scene");
    this.rotX = parseFloat(document.body.getAttribute("data-rot-x") || 20);
    this.rotY = parseFloat(document.body.getAttribute("data-rot-y") || -30);
    this.zoom = parseFloat(document.body.getAttribute("data-zoom") || 1.0);
    this.dragging = false;
    this.lastX = 0;
    this.lastY = 0;
    this.apply();
    this.bind();
  }}

  apply() {{
    this.cube.style.setProperty("--rotX", this.rotX + "deg");
    this.cube.style.setProperty("--rotY", this.rotY + "deg");
    this.scene.style.setProperty("--cube-zoom", this.zoom);
  }}

  bind() {{
    document.addEventListener("mousedown", e => {{
      this.dragging = true;
      this.lastX = e.clientX;
      this.lastY = e.clientY;
    }});
    document.addEventListener("mouseup", () => {{ this.dragging = false; }});
    document.addEventListener("mousemove", e => {{
      if (!this.dragging) return;
      const dx = e.clientX - this.lastX;
      const dy = e.clientY - this.lastY;
      this.lastX = e.clientX;
      this.lastY = e.clientY;
      this.rotY += dx * 0.4;
      this.rotX -= dy * 0.4;
      this.apply();
    }});

    this.scene.addEventListener("wheel", e => {{
      e.preventDefault();
      this.zoom += (e.deltaY > 0) ? -0.08 : 0.08;
      this.zoom = Math.min(Math.max(this.zoom, 0.3), 3.0);
      this.apply();
    }}, {{ passive: false }});
  }}
}}

const cbMin = document.body.getAttribute("data-cb-min");
const cbMax = document.body.getAttribute("data-cb-max");
if (cbMin !== null) {{
  const minEl = document.getElementById("cb-min");
  if (minEl) minEl.innerText = cbMin;
}}
if (cbMax !== null) {{
  const maxEl = document.getElementById("cb-max");
  if (maxEl) maxEl.innerText = cbMax;
}}

const annotations = {annotations or []};
void annotations; // placeholder for future overlay wiring

new CubeScene({{}});
</script>

</body>
</html>
"""

    out_path = Path(out_html)
    out_path.write_text(html, encoding="utf-8")
    return out_path


__all__ = ["write_css_cube_static", "DEFAULT_FACES"]
