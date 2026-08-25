"""Render and quantify the three-dimensional FIRED time-hull construction."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence

import geopandas as gpd
import numpy as np
import pandas as pd

from cubedynamics.fire_time_hull import (
    FireEventDaily,
    _sample_ring_equal_steps,
    compute_time_hull_geometry,
)

from .core import QAResult, ValidationPaths, write_metrics_csv
from .data import load_fired_daily
from .geometry import _largest_polygon, radial_roughness


def directional_support_layers(
    daily_metric: gpd.GeoDataFrame,
    *,
    n_ring_samples: int,
    n_theta: int,
) -> dict[str, Any]:
    """Reproduce the ring-sampling and directional-support stages by layer."""

    frame = daily_metric.sort_values("date").reset_index(drop=True)
    theta = np.linspace(0.0, 2.0 * np.pi, n_theta, endpoint=False)
    directions = np.column_stack([np.cos(theta), np.sin(theta)])
    raw_rings: list[np.ndarray] = []
    sampled_rings: list[np.ndarray] = []
    radii: list[np.ndarray] = []
    dates: list[pd.Timestamp] = []
    z_days: list[float] = []

    for row_index, row in frame.iterrows():
        polygon = _largest_polygon(row.geometry)
        if polygon is None:
            continue
        sampled = _sample_ring_equal_steps(polygon, n_samples=n_ring_samples)
        if sampled is None:
            continue
        center = sampled.mean(axis=0)
        sampled_centered = sampled - center
        raw = np.asarray(polygon.exterior.coords, dtype=float) - center
        raw_rings.append(raw / 1000.0)
        sampled_rings.append(sampled_centered / 1000.0)
        radii.append((directions @ sampled_centered.T).max(axis=1) / 1000.0)
        dates.append(pd.Timestamp(row["date"]).normalize())
        z_days.append(float(row.get("event_day", row_index + 1)))

    if len(radii) < 2:
        raise ValueError("At least two valid daily polygons are required for 3-D hull QA.")
    return {
        "theta": theta,
        "directions": directions,
        "raw_rings_km": raw_rings,
        "sampled_rings_km": sampled_rings,
        "radii_km": np.asarray(radii, dtype=float),
        "dates": pd.DatetimeIndex(dates),
        "z_days": np.asarray(z_days, dtype=float),
    }


def temporal_averaging_alternatives(
    radii_km: np.ndarray,
    *,
    windows: Sequence[int] = (1, 3, 7),
) -> dict[str, np.ndarray]:
    """Return inspectable temporal averaging choices for daily support radii."""

    frame = pd.DataFrame(np.asarray(radii_km, dtype=float))
    alternatives: dict[str, np.ndarray] = {}
    for window in windows:
        window = int(window)
        if window <= 1:
            alternatives["daily support (production)"] = frame.to_numpy(copy=True)
        else:
            alternatives[f"{window}-day centered mean"] = frame.rolling(
                window=window,
                center=True,
                min_periods=1,
            ).mean().to_numpy()
    alternatives["cumulative envelope"] = np.maximum.accumulate(frame.to_numpy(), axis=0)
    return alternatives


def _mesh_from_radii(radii_km: np.ndarray, theta: np.ndarray, z_days: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    directions = np.column_stack([np.cos(theta), np.sin(theta)])
    layers, angles = radii_km.shape
    points = np.zeros((layers, angles, 3), dtype=float)
    points[:, :, :2] = radii_km[:, :, None] * directions[None, :, :]
    points[:, :, 2] = z_days[:, None]
    triangles: list[tuple[int, int, int]] = []
    for layer in range(layers - 1):
        for angle in range(angles):
            next_angle = (angle + 1) % angles
            lower = layer * angles + angle
            lower_next = layer * angles + next_angle
            upper = (layer + 1) * angles + angle
            upper_next = (layer + 1) * angles + next_angle
            triangles.extend([(lower, lower_next, upper_next), (lower, upper_next, upper)])
    return points.reshape(-1, 3), np.asarray(triangles, dtype=int)


def _alternative_metrics(
    alternatives: dict[str, np.ndarray],
    theta: np.ndarray,
    z_days: np.ndarray,
) -> list[dict[str, Any]]:
    delta = 2.0 * np.pi / len(theta)
    production = next(iter(alternatives.values()))
    records: list[dict[str, Any]] = []
    for decision, radii in alternatives.items():
        next_radii = np.roll(radii, -1, axis=1)
        areas = 0.5 * np.sum(radii * next_radii * np.sin(delta), axis=1)
        integrator = getattr(np, "trapezoid", np.trapz)
        volume = float(integrator(areas, x=z_days))
        displacement = np.abs(radii - production)
        records.append(
            {
                "decision": decision,
                "window_days": 1 if decision.startswith("daily") else (int(decision.split("-")[0]) if "-day" in decision else "cumulative"),
                "mean_layer_area_km2": float(np.mean(areas)),
                "volume_km2_days": volume,
                "mean_radial_roughness": float(np.mean([radial_roughness(row) for row in radii])),
                "mean_abs_radial_change_km": float(np.mean(displacement)),
                "max_abs_radial_change_km": float(np.max(displacement)),
            }
        )
    return records


def _style_3d_axis(ax, *, title: str, limits: tuple[float, float], z_limits: tuple[float, float]) -> None:
    ax.set_title(title, fontsize=9, pad=2)
    ax.set_xlabel("centered x (km)", fontsize=7, labelpad=-2)
    ax.set_ylabel("centered y (km)", fontsize=7, labelpad=-2)
    ax.set_zlabel("event day", fontsize=7, labelpad=-1)
    ax.set_xlim(limits)
    ax.set_ylim(limits)
    ax.set_zlim(z_limits)
    ax.view_init(elev=24, azim=-58)
    ax.tick_params(labelsize=6, pad=0)
    ax.set_box_aspect((1, 1, 1.2))


def _plot_surface(ax, radii: np.ndarray, theta: np.ndarray, z_days: np.ndarray, *, cmap: str = "viridis") -> None:
    theta_closed = np.r_[theta, theta[0]]
    radii_closed = np.column_stack([radii, radii[:, 0]])
    x = radii_closed * np.cos(theta_closed)[None, :]
    y = radii_closed * np.sin(theta_closed)[None, :]
    z = np.repeat(z_days[:, None], len(theta_closed), axis=1)
    ax.plot_surface(x, y, z, cmap=cmap, linewidth=0.12, edgecolor=(0.1, 0.1, 0.1, 0.18), alpha=0.88)


def _plot_hull3d_qa(
    stages: dict[str, Any],
    alternatives: dict[str, np.ndarray],
    output: Path,
) -> None:
    import matplotlib.pyplot as plt

    theta = stages["theta"]
    z_days = stages["z_days"]
    radii = stages["radii_km"]
    max_radius = float(max(np.nanmax(profile) for profile in alternatives.values()))
    limit = (-1.08 * max_radius, 1.08 * max_radius)
    z_limit = (float(z_days.min()), float(z_days.max()))
    selected = np.unique(np.linspace(0, len(z_days) - 1, min(9, len(z_days))).astype(int))
    layer_colors = plt.cm.plasma(np.linspace(0.08, 0.92, len(z_days)))

    fig = plt.figure(figsize=(18, 9), constrained_layout=True)
    axes = [fig.add_subplot(2, 4, index + 1, projection="3d") for index in range(8)]

    for layer in selected:
        ring = stages["raw_rings_km"][layer]
        axes[0].plot(ring[:, 0], ring[:, 1], z_days[layer], color=layer_colors[layer], linewidth=0.8)
    _style_3d_axis(axes[0], title="1. Raw FIRED polygons, stacked by day", limits=limit, z_limits=z_limit)

    for layer in selected:
        ring = stages["sampled_rings_km"][layer]
        axes[1].scatter(ring[:, 0], ring[:, 1], np.full(len(ring), z_days[layer]), color=layer_colors[layer], s=2, alpha=0.75)
    _style_3d_axis(axes[1], title="2. Equal-step boundary samples, day-centered", limits=limit, z_limits=z_limit)

    support_x = radii * np.cos(theta)[None, :]
    support_y = radii * np.sin(theta)[None, :]
    for layer in selected:
        axes[2].plot(
            np.r_[support_x[layer], support_x[layer, 0]],
            np.r_[support_y[layer], support_y[layer, 0]],
            np.full(len(theta) + 1, z_days[layer]),
            color=layer_colors[layer],
            linewidth=1.0,
        )
    _style_3d_axis(axes[2], title="3. Directional maxima form support rings", limits=limit, z_limits=z_limit)

    _plot_surface(axes[3], radii, theta, z_days)
    _style_3d_axis(axes[3], title="4. Adjacent rings triangulated linearly", limits=limit, z_limits=z_limit)

    for ax, (decision, alternative) in zip(axes[4:], alternatives.items()):
        _plot_surface(ax, alternative, theta, z_days)
        _style_3d_axis(ax, title=decision, limits=limit, z_limits=z_limit)

    fig.suptitle(
        "QA 3 - How FIRED polygons become a 3-D time hull, and how averaging changes the shape",
        fontsize=15,
        fontweight="bold",
    )
    fig.savefig(output, dpi=190)
    plt.close(fig)


def _write_interactive_hulls(
    alternatives: dict[str, np.ndarray],
    theta: np.ndarray,
    z_days: np.ndarray,
    output: Path,
) -> Path:
    import plotly.graph_objects as go

    figure = go.Figure()
    for index, (decision, radii) in enumerate(alternatives.items()):
        vertices, triangles = _mesh_from_radii(radii, theta, z_days)
        figure.add_trace(
            go.Mesh3d(
                x=vertices[:, 0],
                y=vertices[:, 1],
                z=vertices[:, 2],
                i=triangles[:, 0],
                j=triangles[:, 1],
                k=triangles[:, 2],
                intensity=vertices[:, 2],
                colorscale="Viridis",
                opacity=0.9,
                flatshading=False,
                name=decision,
                visible=index == 0,
                showscale=index == 0,
                colorbar={"title": "event day"},
            )
        )
    buttons = []
    names = list(alternatives)
    for index, name in enumerate(names):
        visible = [position == index for position in range(len(names))]
        buttons.append(
            {
                "label": name,
                "method": "update",
                "args": [{"visible": visible, "showscale": visible}, {"title": f"3-D hull alternative: {name}"}],
            }
        )
    figure.update_layout(
        title=f"3-D hull alternative: {names[0]}",
        updatemenus=[{"buttons": buttons, "direction": "down", "x": 0.02, "y": 1.08}],
        scene={
            "xaxis_title": "centered x (km)",
            "yaxis_title": "centered y (km)",
            "zaxis_title": "event day",
            "aspectmode": "data",
        },
        margin={"l": 0, "r": 0, "t": 80, "b": 0},
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.write_html(output, include_plotlyjs="cdn", full_html=True)
    return output


def run_hull3d_validation(
    paths: ValidationPaths,
    *,
    fire_id: int = 20657,
    n_theta: int = 96,
    averaging_windows: Sequence[int] = (1, 3, 7),
    output_dir: str | Path | None = None,
) -> QAResult:
    """Run the 3-D construction and averaging-decision hull audit."""

    out = Path(output_dir or paths.output_root / "hull3d")
    out.mkdir(parents=True, exist_ok=True)
    daily_source = load_fired_daily(paths, fire_id)
    event = FireEventDaily.from_fired(daily_source, int(fire_id), date_col="date")
    daily = event.gdf.to_crs(5070)
    stages = directional_support_layers(
        daily,
        n_ring_samples=max(128, int(n_theta)),
        n_theta=int(n_theta),
    )
    alternatives = temporal_averaging_alternatives(stages["radii_km"], windows=averaging_windows)
    records = _alternative_metrics(alternatives, stages["theta"], stages["z_days"])

    production_hull = compute_time_hull_geometry(
        event,
        n_ring_samples=max(128, int(n_theta)),
        n_theta=int(n_theta),
    )
    production_radii = np.linalg.norm(production_hull.verts_km[:, :2], axis=1).reshape(
        len(stages["z_days"]), int(n_theta)
    )
    production_residual = float(np.max(np.abs(production_radii - stages["radii_km"])))

    plot = out / "hull_3d_construction_and_alternatives.png"
    _plot_hull3d_qa(stages, alternatives, plot)
    interactive = _write_interactive_hulls(
        alternatives,
        stages["theta"],
        stages["z_days"],
        out / "hull_averaging_alternatives.html",
    )
    metrics_path = write_metrics_csv(records, out / "hull_averaging_metrics.csv")

    finite_metrics = all(
        np.isfinite(record["volume_km2_days"])
        and record["volume_km2_days"] > 0
        and np.isfinite(record["mean_radial_roughness"])
        for record in records
    )
    passed = production_residual <= 1e-12 and finite_metrics and len(records) == len(averaging_windows) + 1
    result = QAResult(
        module="hull3d",
        status="pass" if passed else "fail",
        summary="The plotted construction exactly reproduces the production directional-support hull and exposes alternative temporal averaging decisions in 3-D.",
        metrics={
            "fire_id": str(fire_id),
            "daily_layers": int(len(stages["z_days"])),
            "ring_samples": int(max(128, n_theta)),
            "directional_angles": int(n_theta),
            "averaging_decisions": list(alternatives),
            "production_max_abs_radial_residual_km": production_residual,
            "largest_alternative_mean_radial_change_km": float(max(record["mean_abs_radial_change_km"] for record in records)),
            "largest_alternative_max_radial_change_km": float(max(record["max_abs_radial_change_km"] for record in records)),
        },
        artifacts={
            "plot": plot.as_posix(),
            "interactive_html": interactive.as_posix(),
            "metrics": metrics_path.as_posix(),
        },
        notes=[
            "The production hull does not temporally average observed days: it computes one directional support ring per FIRED day and triangulates linearly between adjacent rings.",
            "The 3-day, 7-day, and cumulative alternatives are sensitivity scenarios, not silently substituted production choices.",
        ],
    )
    result_path = result.write(out / "result.json")
    result.artifacts["result"] = result_path.as_posix()
    result.write(result_path)
    return result


__all__ = [
    "directional_support_layers",
    "run_hull3d_validation",
    "temporal_averaging_alternatives",
]
