"""Build static PDF contact sheets of fire VASE hulls.

The output is intentionally static and print-friendly: hull thumbnails colored
by daily climate rings, compact metric labels, and a shared colorbar. It is
meant as a companion to the interactive Plotly VASE panel examples.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.colors import Normalize
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

from cubedynamics.fire_time_hull import (
    FireEventDaily,
    compute_time_hull_geometry,
    normalize_dates,
    _load_real_gridmet_cube,
)


def _load_real_candidates(
    *,
    cache_dir: Path,
    candidates_csv: Path,
    max_events: int | None,
) -> tuple[gpd.GeoDataFrame, list[Any], str]:
    daily_path = cache_dir / "fired_conus-ak_daily_nov2001-march2021.gpkg"
    if not daily_path.exists():
        raise FileNotFoundError(f"Missing cached FIRED daily layer: {daily_path}")
    if not candidates_csv.exists():
        raise FileNotFoundError(f"Missing candidate events CSV: {candidates_csv}")

    candidates = pd.read_csv(candidates_csv)
    ids = candidates["event_id"].tolist()
    if max_events is not None:
        ids = ids[: int(max_events)]
    daily = gpd.read_file(daily_path)
    daily = daily[daily["id"].isin(ids)].copy()
    if "ig_date" in daily.columns and "date" not in daily.columns:
        daily = daily.rename(columns={"ig_date": "date"})
    return daily, ids, "FIRED cached candidates"


def _set_equal_3d_limits(ax, verts: np.ndarray) -> None:
    mins = np.nanmin(verts, axis=0)
    maxs = np.nanmax(verts, axis=0)
    center = (mins + maxs) / 2.0
    span = float(np.nanmax(maxs - mins))
    span = max(span, 1.0)
    ax.set_xlim(center[0] - span * 0.55, center[0] + span * 0.55)
    ax.set_ylim(center[1] - span * 0.55, center[1] + span * 0.55)
    ax.set_zlim(max(0.0, mins[2] - 0.3), maxs[2] + span * 0.25)


def _temperature_label(variable: str, temperature_units: str) -> str:
    if variable.lower() in {"tmmx", "tmmn", "tmean", "tmin", "tmax"}:
        return f"{variable} ({temperature_units.upper()})"
    if variable.lower() == "vpd":
        return "vpd (kPa)"
    if variable.lower() == "vs":
        return "wind speed (m/s)"
    return variable


def _convert_temperature_values(values: np.ndarray, *, variable: str, temperature_units: str) -> np.ndarray:
    arr = np.asarray(values, dtype=float)
    if variable.lower() not in {"tmmx", "tmmn", "tmean", "tmin", "tmax"}:
        return arr
    if not np.isfinite(arr).any():
        return arr

    # gridMET temperature variables are stored as Kelvin in the real NetCDF
    # files. Refuse to silently convert fixture/normalized values.
    finite_median = float(np.nanmedian(arr))
    if finite_median < 150.0:
        raise ValueError(
            f"{variable} values do not look like Kelvin temperatures; median={finite_median:.3f}. "
            "Cannot label this panel as Celsius/Fahrenheit."
        )

    if temperature_units == "c":
        return arr - 273.15
    if temperature_units == "f":
        return (arr - 273.15) * 9.0 / 5.0 + 32.0
    if temperature_units == "k":
        return arr
    raise ValueError("temperature_units must be one of 'c', 'f', or 'k'.")


def _layer_climate_values(
    hull,
    event: FireEventDaily,
    *,
    variable: str,
    temperature_units: str,
    gridmet_cache_dir: Path,
    time_buffer_days: int,
) -> tuple[np.ndarray, np.ndarray]:
    layer_days, vertex_layer = np.unique(np.asarray(hull.t_days_vert, dtype=float), return_inverse=True)
    layer_dates = normalize_dates(
        hull.event.t0 + pd.to_timedelta(layer_days - np.nanmin(layer_days), unit="D")
    )
    climate = _load_real_gridmet_cube(
        event.centroid_lat,
        event.centroid_lon,
        event.t0 - pd.Timedelta(days=time_buffer_days),
        event.t1 + pd.Timedelta(days=time_buffer_days),
        variable=variable,
        cache_dir=gridmet_cache_dir,
    )
    series = climate.sel(time=layer_dates, method="nearest").mean(dim=[dim for dim in climate.dims if dim != "time"])
    values = _convert_temperature_values(
        np.asarray(series.values, dtype=float),
        variable=variable,
        temperature_units=temperature_units,
    )
    return layer_days, values


def _band_faces_and_values(
    hull,
    *,
    layer_days: np.ndarray | None,
    layer_values: np.ndarray | None,
) -> tuple[list[np.ndarray], np.ndarray | None]:
    verts = np.asarray(hull.verts_km, dtype=float)
    if layer_days is None or layer_values is None:
        return [verts[tri] for tri in np.asarray(hull.tris, dtype=int)], None

    t_days = np.asarray(hull.t_days_vert, dtype=float)
    faces: list[np.ndarray] = []
    face_values: list[float] = []
    for layer_idx in range(len(layer_days) - 1):
        lower = np.flatnonzero(t_days == layer_days[layer_idx])
        upper = np.flatnonzero(t_days == layer_days[layer_idx + 1])
        if lower.size == 0 or upper.size == 0 or lower.size != upper.size:
            continue
        n_ring = int(lower.size)
        # Each quadrilateral spans one between-date wall segment. Assigning one
        # value to the whole quad preserves horizontal date bands and avoids
        # false diagonal color splits from triangulation.
        band_value = float(layer_values[layer_idx + 1])
        for ring_idx in range(n_ring):
            nxt = (ring_idx + 1) % n_ring
            faces.append(
                verts[
                    [
                        lower[ring_idx],
                        lower[nxt],
                        upper[nxt],
                        upper[ring_idx],
                    ]
                ]
            )
            face_values.append(band_value)

    if not faces:
        return [verts[tri] for tri in np.asarray(hull.tris, dtype=int)], None
    return faces, np.asarray(face_values, dtype=float)


def _draw_hull(
    ax,
    hull,
    *,
    layer_days: np.ndarray | None,
    layer_values: np.ndarray | None,
    norm: Normalize | None,
    cmap_name: str,
) -> None:
    verts = np.asarray(hull.verts_km, dtype=float)
    faces, face_values = _band_faces_and_values(
        hull,
        layer_days=layer_days,
        layer_values=layer_values,
    )
    if face_values is not None and norm is not None:
        cmap = plt.get_cmap(cmap_name)
        facecolors = cmap(norm(face_values))
    else:
        facecolors = "#b41616"
    poly = Poly3DCollection(
        faces,
        facecolors=facecolors,
        edgecolors="#222222",
        linewidths=0.08,
        alpha=0.96,
    )
    ax.add_collection3d(poly)
    _set_equal_3d_limits(ax, verts)
    ax.view_init(elev=18, azim=-62)
    ax.set_axis_off()
    ax.set_box_aspect((1.0, 1.0, 1.4))


def _metrics_text(hull) -> str:
    metrics = dict(hull.metrics)
    space = float(metrics.get("scale_km", np.nan))
    time = float(metrics.get("duration_days", metrics.get("days", np.nan)))
    volume = float(metrics.get("hull_volume_km2_days", metrics.get("volume_km2_days", np.nan)))
    peak = float(metrics.get("footprint_area_peak_km2", np.nan))
    ot_v = volume / max(time, 1.0) if np.isfinite(volume) and np.isfinite(time) else np.nan
    if not np.isfinite(ot_v) and np.isfinite(peak):
        ot_v = peak
    return (
        f"space {space:.1f}\n"
        f"time {time:.0f}\n"
        f"volume {volume:.0f}\n"
        f"OT v {ot_v:.2f}"
    )


def build_pdf_panel(
    *,
    fired_daily: gpd.GeoDataFrame,
    event_ids: list[Any],
    title: str,
    output: Path,
    columns: int = 8,
    rows: int | None = None,
    n_ring_samples: int = 64,
    n_theta: int = 64,
    climate_variable: str = "tmmx",
    temperature_units: str = "c",
    time_buffer_days: int = 1,
    gridmet_cache_dir: Path = Path("artifacts/fire-vase-gridmet-real/gridmet-cache"),
    cmap_name: str = "viridis",
) -> dict[str, Any]:
    output.parent.mkdir(parents=True, exist_ok=True)
    if rows is None:
        rows = max(1, int(np.ceil(len(event_ids) / max(1, columns))))
    per_page = columns * rows
    built = 0
    failures: list[dict[str, str]] = []
    items: list[dict[str, Any]] = []
    all_climate_values: list[np.ndarray] = []

    for event_id in event_ids:
        try:
            event = FireEventDaily.from_fired(fired_daily, event_id, date_col="date")
            hull = compute_time_hull_geometry(
                event,
                n_ring_samples=n_ring_samples,
                n_theta=n_theta,
            )
            layer_days, layer_values = _layer_climate_values(
                hull,
                event,
                variable=climate_variable,
                temperature_units=temperature_units,
                gridmet_cache_dir=gridmet_cache_dir,
                time_buffer_days=time_buffer_days,
            )
            all_climate_values.append(layer_values[np.isfinite(layer_values)])
            items.append(
                {
                    "event_id": event_id,
                    "hull": hull,
                    "layer_days": layer_days,
                    "layer_values": layer_values,
                }
            )
            built += 1
        except Exception as exc:
            failures.append({"event_id": str(event_id), "error": str(exc)})
            items.append({"event_id": event_id, "error": str(exc)})

    finite_all = np.concatenate([vals for vals in all_climate_values if vals.size]) if all_climate_values else np.array([])
    if finite_all.size:
        vmin = float(np.nanpercentile(finite_all, 2))
        vmax = float(np.nanpercentile(finite_all, 98))
        if not np.isfinite(vmin) or not np.isfinite(vmax) or vmax <= vmin:
            vmin = float(np.nanmin(finite_all))
            vmax = float(np.nanmax(finite_all))
            if vmax <= vmin:
                vmax = vmin + 1e-9
        norm = Normalize(vmin=vmin, vmax=vmax)
    else:
        norm = None

    with PdfPages(output) as pdf:
        for page_start in range(0, len(items), per_page):
            page_items = items[page_start : page_start + per_page]
            fig_height = max(9.0, rows * 3.0 + 0.8)
            fig = plt.figure(figsize=(16, fig_height), constrained_layout=False)
            fig.patch.set_facecolor("white")
            fig.suptitle(
                f"{title} - page {page_start // per_page + 1}",
                fontsize=16,
                fontweight="bold",
                y=0.995,
            )
            grid = fig.add_gridspec(
                rows,
                columns,
                left=0.02,
                right=0.985,
                top=0.95,
                bottom=0.085,
                wspace=0.02,
                hspace=0.18,
            )
            for idx, item in enumerate(page_items):
                row = idx // columns
                col = idx % columns
                ax = fig.add_subplot(grid[row, col], projection="3d")
                if "hull" in item:
                    hull = item["hull"]
                    _draw_hull(
                        ax,
                        hull,
                        layer_days=item.get("layer_days"),
                        layer_values=item.get("layer_values"),
                        norm=norm,
                        cmap_name=cmap_name,
                    )
                    ax.text2D(
                        0.07,
                        -0.05,
                        _metrics_text(hull),
                        transform=ax.transAxes,
                        ha="left",
                        va="top",
                        fontsize=11,
                        fontweight="bold",
                        color="black",
                        linespacing=0.88,
                    )
                else:
                    ax.set_axis_off()
                    ax.text2D(
                        0.5,
                        0.5,
                        f"event {item['event_id']}\nfailed",
                        transform=ax.transAxes,
                        ha="center",
                        va="center",
                        fontsize=9,
                        color="#555555",
                    )
            if norm is not None:
                cax = fig.add_axes([0.35, 0.025, 0.30, 0.018])
                sm = plt.cm.ScalarMappable(norm=norm, cmap=plt.get_cmap(cmap_name))
                sm.set_array([])
                cbar = fig.colorbar(sm, cax=cax, orientation="horizontal")
                cbar.ax.tick_params(labelsize=8)
                fig.text(
                    0.5,
                    0.05,
                    _temperature_label(climate_variable, temperature_units),
                    ha="center",
                    va="bottom",
                    fontsize=10,
                    fontweight="bold",
                )
            pdf.savefig(fig)
            plt.close(fig)

    return {"output": str(output), "events_requested": len(event_ids), "events_rendered": built, "failures": failures}


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a static PDF panel from cached real FIRED events.")
    parser.add_argument("--max-events", type=int, default=None, help="Maximum events to render.")
    parser.add_argument("--columns", type=int, default=8)
    parser.add_argument("--rows", type=int, default=None)
    parser.add_argument("--climate-variable", default="tmmx")
    parser.add_argument("--temperature-units", choices=("c", "f", "k"), default="c")
    parser.add_argument("--time-buffer-days", type=int, default=1)
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path("artifacts/fire-vase-gridmet-real/fired-cache"),
    )
    parser.add_argument(
        "--candidates-csv",
        type=Path,
        default=Path("artifacts/fire-vase-gridmet-real/candidate_events.csv"),
    )
    parser.add_argument(
        "--gridmet-cache-dir",
        type=Path,
        default=Path("artifacts/fire-vase-gridmet-real/gridmet-cache"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output PDF path.",
    )
    args = parser.parse_args()

    fired_daily, event_ids, label = _load_real_candidates(
        cache_dir=args.cache_dir,
        candidates_csv=args.candidates_csv,
        max_events=args.max_events,
    )
    title = f"{label} colored by gridMET {_temperature_label(args.climate_variable, args.temperature_units)}"
    default_name = (
        f"fire_vase_real_non_prescribed_{args.climate_variable}_"
        f"{args.temperature_units}_static_panel.pdf"
    )
    output = args.output or Path("output/pdf") / default_name
    result = build_pdf_panel(
        fired_daily=fired_daily,
        event_ids=event_ids,
        title=title,
        output=output,
        columns=args.columns,
        rows=args.rows,
        climate_variable=args.climate_variable,
        temperature_units=args.temperature_units,
        time_buffer_days=args.time_buffer_days,
        gridmet_cache_dir=args.gridmet_cache_dir,
    )
    print(result["output"])
    if result["failures"]:
        print(f"failures: {len(result['failures'])}")


if __name__ == "__main__":
    main()
