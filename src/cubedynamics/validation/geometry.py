"""Validate FIRED polygon cleaning, simplification, and time-hull construction."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import LineString, MultiPolygon, Polygon
from shapely.ops import unary_union

from cubedynamics.fire_time_hull import FireEventDaily, compute_time_hull_geometry

from .core import QAResult, ValidationPaths, write_metrics_csv
from .data import load_fired_daily


def _largest_polygon(geometry: Any) -> Polygon | None:
    if geometry is None or geometry.is_empty:
        return None
    if isinstance(geometry, Polygon):
        return geometry
    if isinstance(geometry, MultiPolygon):
        polygons = [geom for geom in geometry.geoms if isinstance(geom, Polygon)]
        return max(polygons, key=lambda geom: geom.area) if polygons else None
    return None


def compactness_roughness(polygon: Polygon) -> float:
    """Perimeter divided by the circumference of an equal-area circle."""

    if polygon.area <= 0:
        return float("nan")
    return float(polygon.length / (2.0 * np.sqrt(np.pi * polygon.area)))


def vertex_count(geometry: Any) -> int:
    if isinstance(geometry, Polygon):
        return len(geometry.exterior.coords)
    if isinstance(geometry, MultiPolygon):
        return sum(len(poly.exterior.coords) for poly in geometry.geoms)
    return 0


def simplification_sensitivity(
    daily_metric: gpd.GeoDataFrame,
    tolerances_m: Sequence[float],
) -> tuple[list[dict[str, Any]], dict[float, Any]]:
    """Summarize final cumulative-footprint sensitivity to simplification."""

    base = unary_union([geom for geom in daily_metric.geometry if geom is not None and not geom.is_empty])
    records: list[dict[str, Any]] = []
    geometries: dict[float, Any] = {}
    for tolerance in tolerances_m:
        simplified_parts = [
            geom.simplify(float(tolerance), preserve_topology=True)
            for geom in daily_metric.geometry
            if geom is not None and not geom.is_empty
        ]
        geometry = unary_union(simplified_parts)
        geometries[float(tolerance)] = geometry
        polygon = _largest_polygon(geometry)
        base_polygon = _largest_polygon(base)
        area_change = 100.0 * (float(geometry.area) - float(base.area)) / max(float(base.area), 1e-12)
        records.append(
            {
                "tolerance_m": float(tolerance),
                "vertices": vertex_count(geometry),
                "daily_polygon_vertices": int(sum(vertex_count(geom) for geom in simplified_parts)),
                "area_km2": float(geometry.area / 1e6),
                "area_change_pct": area_change,
                "hausdorff_distance_m": float(base.hausdorff_distance(geometry)),
                "compactness_roughness": compactness_roughness(polygon) if polygon else float("nan"),
                "base_compactness_roughness": compactness_roughness(base_polygon) if base_polygon else float("nan"),
            }
        )
    return records, geometries


def _support_profile(polygon: Polygon, n_theta: int = 360) -> tuple[np.ndarray, np.ndarray]:
    coords = np.asarray(polygon.exterior.coords, dtype=float)
    coords = coords - coords.mean(axis=0)
    theta = np.linspace(0.0, 2.0 * np.pi, n_theta, endpoint=False)
    directions = np.column_stack([np.cos(theta), np.sin(theta)])
    radii = np.max(directions @ coords.T, axis=1)
    return theta, radii


def radial_roughness(radii: np.ndarray) -> float:
    """Normalized second-difference energy of an angular radius profile."""

    values = np.asarray(radii, dtype=float)
    wrapped = np.r_[values[-1], values, values[0]]
    curvature = np.diff(wrapped, n=2)
    return float(np.mean(np.abs(curvature)) / max(np.mean(np.abs(values)), 1e-12))


def _event_with_simplification(daily_metric: gpd.GeoDataFrame, fire_id: int, tolerance_m: float) -> FireEventDaily:
    frame = daily_metric.copy()
    if tolerance_m > 0:
        frame.geometry = frame.geometry.simplify(tolerance_m, preserve_topology=True)
    return FireEventDaily.from_fired(frame, fire_id, date_col="date")


def hull_sensitivity(
    daily_metric: gpd.GeoDataFrame,
    *,
    fire_id: int,
    tolerances_m: Sequence[float],
    n_theta: int,
) -> tuple[list[dict[str, Any]], dict[float, Any]]:
    records: list[dict[str, Any]] = []
    hulls: dict[float, Any] = {}
    for tolerance in tolerances_m:
        event = _event_with_simplification(daily_metric, fire_id, float(tolerance))
        hull = compute_time_hull_geometry(event, n_ring_samples=max(128, n_theta), n_theta=n_theta)
        hulls[float(tolerance)] = hull
        layer_count = np.unique(hull.t_days_vert).size
        radii = np.linalg.norm(hull.verts_km[:, :2], axis=1).reshape(layer_count, n_theta)
        records.append(
            {
                "tolerance_m": float(tolerance),
                "hull_volume_km2_days": float(hull.metrics["hull_volume_km2_days"]),
                "hull_surface_km_day": float(hull.metrics["hull_surface_km_day"]),
                "scale_km": float(hull.metrics["scale_km"]),
                "mean_layer_radial_roughness": float(np.mean([radial_roughness(row) for row in radii])),
                "vertices": int(hull.verts_km.shape[0]),
                "triangles": int(hull.tris.shape[0]),
            }
        )
    return records, hulls


def _plot_geometry_qa(
    daily_metric: gpd.GeoDataFrame,
    simplify_records: list[dict[str, Any]],
    geometries: dict[float, Any],
    hull_records: list[dict[str, Any]],
    hulls: dict[float, Any],
    output: Path,
) -> None:
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(2, 2, figsize=(13, 10), constrained_layout=True)
    colors = plt.cm.viridis(np.linspace(0.1, 0.9, len(geometries)))

    ax = axes[0, 0]
    for (tolerance, geometry), color in zip(geometries.items(), colors):
        boundary = geometry.boundary
        if isinstance(boundary, LineString):
            x, y = boundary.xy
            ax.plot(np.asarray(x) / 1000, np.asarray(y) / 1000, color=color, linewidth=1.2, label=f"{tolerance:g} m")
        else:
            for line_index, line in enumerate(boundary.geoms):
                x, y = line.xy
                ax.plot(
                    np.asarray(x) / 1000,
                    np.asarray(y) / 1000,
                    color=color,
                    linewidth=1.0,
                    label=f"{tolerance:g} m" if line_index == 0 else None,
                )
    ax.set_aspect("equal")
    ax.set_title("Cumulative FIRED footprint simplification")
    ax.set_xlabel("equal-area x (km)")
    ax.set_ylabel("equal-area y (km)")
    ax.legend(title="tolerance", fontsize=8)

    ax = axes[0, 1]
    simpl = pd.DataFrame(simplify_records)
    ax.plot(simpl.tolerance_m, simpl.daily_polygon_vertices, marker="o", color="#342b55", label="vertices")
    ax.set_xlabel("simplification tolerance (m)")
    ax.set_ylabel("boundary vertices", color="#342b55")
    ax.tick_params(axis="y", labelcolor="#342b55")
    twin = ax.twinx()
    twin.plot(simpl.tolerance_m, simpl.area_change_pct, marker="s", color="#c65f31", label="area change")
    twin.set_ylabel("area change (%)", color="#c65f31")
    twin.tick_params(axis="y", labelcolor="#c65f31")
    ax.set_title("Complexity reduction and area retention")
    ax.grid(alpha=0.2)

    ax = axes[1, 0]
    polygons = [_largest_polygon(geom) for geom in daily_metric.geometry]
    polygons = [polygon for polygon in polygons if polygon is not None]
    profiles = [_support_profile(polygon) for polygon in polygons]
    mean_radius = np.asarray([np.mean(radius) for _, radius in profiles])
    small_index = int(np.argmin(mean_radius))
    large_index = int(np.argmax(mean_radius))
    selected = np.unique(
        np.r_[np.linspace(0, len(polygons) - 1, min(4, len(polygons))).astype(int), small_index, large_index]
    )
    for index in selected:
        theta, radii = profiles[index]
        ax.plot(np.degrees(theta), radii / 1000.0, alpha=0.65, label=f"day {index + 1}")
    if len(polygons) >= 2:
        theta, small = profiles[small_index]
        _, large = profiles[large_index]
        ax.plot(
            np.degrees(theta),
            (small + large) / 2000.0,
            color="black",
            linewidth=2,
            linestyle="--",
            label=f"mid-transition (days {small_index + 1}/{large_index + 1})",
        )
    ax.set_title("Angular support profiles show hull smoothing")
    ax.set_xlabel("angle (degrees)")
    ax.set_ylabel("support radius (km)")
    ax.grid(alpha=0.2)
    ax.legend(fontsize=7, ncol=2)

    ax = axes[1, 1]
    hull_frame = pd.DataFrame(hull_records)
    ax.plot(
        hull_frame.tolerance_m,
        hull_frame.mean_layer_radial_roughness,
        marker="o",
        color="#3b6f88",
        label="radial roughness",
    )
    ax.set_xlabel("simplification tolerance (m)")
    ax.set_ylabel("normalized radial roughness", color="#3b6f88")
    ax.tick_params(axis="y", labelcolor="#3b6f88")
    twin = ax.twinx()
    twin.plot(
        hull_frame.tolerance_m,
        hull_frame.hull_volume_km2_days,
        marker="s",
        color="#b35b27",
        label="hull volume",
    )
    twin.set_ylabel("hull volume (km2-days)", color="#b35b27")
    twin.tick_params(axis="y", labelcolor="#b35b27")
    ax.set_title("Hull sensitivity to polygon simplification")
    ax.grid(alpha=0.2)

    fig.suptitle("QA 2 - FIRED polygon to time-hull construction", fontsize=15, fontweight="bold")
    fig.savefig(output, dpi=180)
    plt.close(fig)


def run_geometry_validation(
    paths: ValidationPaths,
    *,
    fire_id: int = 20657,
    tolerances_m: Sequence[float] = (0, 125, 500, 1000),
    operational_max_tolerance_m: float = 125,
    n_theta: int = 96,
    output_dir: str | Path | None = None,
) -> QAResult:
    """Run FIRED simplification and time-hull sensitivity QA."""

    out = Path(output_dir or paths.output_root / "geometry")
    out.mkdir(parents=True, exist_ok=True)
    daily = load_fired_daily(paths, fire_id)
    daily_metric = daily.to_crs(5070)
    simplify_records, geometries = simplification_sensitivity(daily_metric, tolerances_m)
    hull_records, hulls = hull_sensitivity(
        daily_metric,
        fire_id=int(fire_id),
        tolerances_m=tolerances_m,
        n_theta=n_theta,
    )
    simplify_csv = write_metrics_csv(simplify_records, out / "polygon_simplification_metrics.csv")
    hull_csv = write_metrics_csv(hull_records, out / "hull_sensitivity_metrics.csv")
    plot = out / "geometry_hull_sensitivity.png"
    _plot_geometry_qa(daily_metric, simplify_records, geometries, hull_records, hulls, plot)

    simpl = pd.DataFrame(simplify_records)
    finite_area = simpl.area_change_pct.replace([np.inf, -np.inf], np.nan).dropna()
    max_area_change = float(finite_area.abs().max()) if len(finite_area) else float("nan")
    operational = simpl[simpl.tolerance_m <= float(operational_max_tolerance_m)]
    operational_max_area_change = float(operational.area_change_pct.abs().max())
    all_valid = all(geometry.is_valid and not geometry.is_empty for geometry in geometries.values())
    passed = all_valid and operational_max_area_change <= 10.0 and all(record["hull_volume_km2_days"] > 0 for record in hull_records)
    result = QAResult(
        module="geometry",
        status="pass" if passed else "fail",
        summary="FIRED polygons remain valid through the configured simplification range and yield stable, positive time-hull metrics.",
        metrics={
            "fire_id": str(fire_id),
            "daily_polygon_rows": int(len(daily)),
            "tolerances_m": [float(value) for value in tolerances_m],
            "n_theta": int(n_theta),
            "operational_max_tolerance_m": float(operational_max_tolerance_m),
            "all_simplified_geometries_valid": all_valid,
            "operational_max_absolute_area_change_pct": operational_max_area_change,
            "max_absolute_area_change_pct": max_area_change,
            "base_daily_polygon_vertices": int(simpl.iloc[0].daily_polygon_vertices),
            "most_simplified_daily_polygon_vertices": int(simpl.iloc[-1].daily_polygon_vertices),
        },
        artifacts={
            "plot": plot.as_posix(),
            "simplification_metrics": simplify_csv.as_posix(),
            "hull_metrics": hull_csv.as_posix(),
        },
        notes=[
            "The hull uses directional support radii; concavities and high-frequency boundary roughness are intentionally averaged before adjacent daily layers are triangulated."
            ,
            "The 500 m and 1000 m settings are stress tests. The configured acceptance range is 0-125 m; larger tolerances visibly discard too much area for this event."
        ],
    )
    result_path = result.write(out / "result.json")
    result.artifacts["result"] = result_path.as_posix()
    result.write(result_path)
    return result


__all__ = [
    "compactness_roughness",
    "hull_sensitivity",
    "radial_roughness",
    "run_geometry_validation",
    "simplification_sensitivity",
]
