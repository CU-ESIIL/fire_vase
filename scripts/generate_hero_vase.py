#!/usr/bin/env python3
"""Generate the transparent VPD-colored Fire VASE homepage hero.

The render is built from the Fire VASE data lake rather than from a hand-drawn
illustration. By default it selects a dramatic high-VPD, multi-pulse fire and
renders cumulative fire growth as a surface of revolution colored by daily VPD.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/fire_vase_matplotlib")

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import colormaps
from matplotlib.colors import Normalize


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_LAKE = REPO_ROOT / "data_lake" / "fire-vase-data-lake-v0.1"
DEFAULT_OUTPUT = REPO_ROOT / "docs" / "assets" / "hero-vase-vpd.png"
DEFAULT_METADATA = REPO_ROOT / "docs" / "assets" / "hero-vase-vpd.json"


def resolve_data_root(data_lake: Path) -> Path:
    """Return the data-lake files root for package or restored-root inputs."""
    path = data_lake.expanduser().resolve()
    candidates = [path, path / "files"]
    for candidate in candidates:
        if (candidate / "scratch" / "fire_vase_run_full" / "tables" / "vase_slices.parquet").exists():
            return candidate
    raise FileNotFoundError(f"Could not find Fire VASE tables under {path}")


def load_tables(data_root: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load event features and daily VASE slices needed for ranking/rendering."""
    morphology_root = data_root / "scratch" / "fire_vase_developmental_morphology"
    table_root = data_root / "scratch" / "fire_vase_run_full" / "tables"
    features = pd.read_parquet(morphology_root / "developmental_morphospace_features.parquet")
    slices = pd.read_parquet(table_root / "vase_slices.parquet")
    return features, slices


def choose_dramatic_event(features: pd.DataFrame) -> pd.Series:
    """Rank climate-complete fires by size, duration, VPD, and pulse complexity."""
    candidates = features[features["climate_available"]].copy()
    candidates = candidates[
        (candidates["observation_count"] >= 8)
        & (candidates["duration_days"] >= 10)
        & (candidates["final_area_km2"] >= 20)
        & candidates["max_vpd_kpa"].notna()
    ].copy()
    if candidates.empty:
        raise ValueError("No climate-complete dramatic fire candidates found.")

    rank_columns = [
        "final_area_km2",
        "duration_days",
        "max_vpd_kpa",
        "mean_vpd_kpa",
        "pulse_count",
        "reactivation_count",
        "growth_entropy",
    ]
    for column in rank_columns:
        candidates[f"{column}_rank"] = candidates[column].rank(pct=True)

    candidates["hero_score"] = (
        0.24 * candidates["final_area_km2_rank"]
        + 0.16 * candidates["duration_days_rank"]
        + 0.24 * candidates["max_vpd_kpa_rank"]
        + 0.14 * candidates["mean_vpd_kpa_rank"]
        + 0.12 * candidates["pulse_count_rank"]
        + 0.06 * candidates["reactivation_count_rank"]
        + 0.04 * candidates["growth_entropy_rank"]
    )
    return candidates.sort_values("hero_score", ascending=False).iloc[0]


def resample_profile(event_slices: pd.DataFrame, samples: int = 260) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Interpolate daily width and VPD to a smooth vertical vase profile."""
    event_slices = event_slices.sort_values("slice_index").reset_index(drop=True)
    z_daily = np.linspace(0.0, 1.0, len(event_slices))
    z = np.linspace(0.0, 1.0, samples)
    width = np.interp(z, z_daily, event_slices["normalized_vase_width"].to_numpy(float))
    vpd = np.interp(z, z_daily, event_slices["vpd_kpa"].to_numpy(float))

    # Give the cumulative-growth surface a physical lip and base so it reads as
    # a vase, while preserving the daily cumulative-width profile.
    width = np.maximum(width, 0.035)
    lip = 0.075 * np.exp(-((z - 1.0) / 0.045) ** 2)
    base = 0.035 * np.exp(-((z - 0.0) / 0.055) ** 2)
    radius = width + lip + base
    return z, radius, vpd


def lit_facecolors(z: np.ndarray, radius: np.ndarray, vpd: np.ndarray, theta: np.ndarray) -> np.ndarray:
    """Color the vase by VPD and modulate with a simple directional light."""
    cmap = colormaps["inferno"]
    norm = Normalize(vmin=float(np.nanmin(vpd)), vmax=float(np.nanmax(vpd)))
    base = cmap(norm(vpd))[:, None, :]
    colors = np.repeat(base, len(theta), axis=1)

    dr_dz = np.gradient(radius, z)
    theta_grid, _ = np.meshgrid(theta, z)
    slope = dr_dz[:, None]
    z_scale = 1.65
    normals = np.stack(
        [
            z_scale * np.cos(theta_grid),
            z_scale * np.sin(theta_grid),
            -slope * np.ones_like(theta_grid),
        ],
        axis=-1,
    )
    normals /= np.linalg.norm(normals, axis=-1, keepdims=True)
    light = np.array([-0.45, -0.72, 0.53])
    light /= np.linalg.norm(light)
    intensity = np.clip(np.sum(normals * light, axis=-1), 0.0, 1.0)

    ambient = 0.30
    diffuse = 0.86 * intensity
    rim = 0.32 * np.clip(np.sin(theta_grid - 0.4), 0.0, 1.0) ** 7
    shade = np.clip(ambient + diffuse + rim, 0.0, 1.35)
    colors[..., :3] = np.clip(colors[..., :3] * shade[..., None], 0.0, 1.0)
    colors[..., 3] = 0.96
    return colors


def render_vase(event_slices: pd.DataFrame, output: Path) -> None:
    """Render a transparent, close-cropped 3D VASE image."""
    z, radius, vpd = resample_profile(event_slices)
    theta = np.linspace(0.0, 2.0 * np.pi, 320)
    theta_grid, z_grid = np.meshgrid(theta, z)
    radius_grid = radius[:, None]
    x = radius_grid * np.cos(theta_grid)
    y = radius_grid * np.sin(theta_grid)
    z_plot = 1.65 * z_grid
    facecolors = lit_facecolors(z, radius, vpd, theta)

    fig = plt.figure(figsize=(12, 12), dpi=220)
    fig.patch.set_alpha(0.0)
    ax = fig.add_subplot(111, projection="3d")
    ax.set_facecolor((0, 0, 0, 0))
    ax.plot_surface(
        x,
        y,
        z_plot,
        facecolors=facecolors,
        linewidth=0,
        antialiased=True,
        shade=False,
        rcount=len(z),
        ccount=len(theta),
    )

    # Subtle daily rings make the object read as a stacked fire history.
    daily = event_slices.sort_values("slice_index").reset_index(drop=True)
    z_daily = np.linspace(0.0, 1.0, len(daily))
    radius_daily = np.interp(z_daily, z, radius)
    for idx, (zz, rr, day_vpd) in enumerate(zip(z_daily, radius_daily, daily["vpd_kpa"], strict=True)):
        if idx % 2 and idx not in {0, len(daily) - 1}:
            continue
        ring_color = colormaps["inferno"](Normalize(daily["vpd_kpa"].min(), daily["vpd_kpa"].max())(day_vpd))
        ax.plot(
            rr * np.cos(theta),
            rr * np.sin(theta),
            np.full_like(theta, 1.65 * zz),
            color=(1.0, 0.86, 0.48, 0.30),
            linewidth=0.9,
        )
        ax.plot(
            rr * np.cos(theta[:90]),
            rr * np.sin(theta[:90]),
            np.full(90, 1.65 * zz),
            color=(*ring_color[:3], 0.45),
            linewidth=1.1,
        )

    ax.view_init(elev=18, azim=-56, roll=0)
    ax.set_axis_off()
    ax.set_proj_type("persp", focal_length=0.55)
    ax.set_box_aspect((1.0, 1.0, 1.68))
    ax.set_xlim(-0.82, 0.88)
    ax.set_ylim(-0.58, 0.80)
    ax.set_zlim(-0.05, 1.70)
    plt.subplots_adjust(0, 0, 1, 1)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, transparent=True, bbox_inches="tight", pad_inches=0.0)
    plt.close(fig)


def write_metadata(event: pd.Series, event_slices: pd.DataFrame, output: Path, metadata: Path) -> None:
    """Write a small JSON sidecar so the hero image remains traceable."""
    payload = {
        "output": output.relative_to(REPO_ROOT).as_posix(),
        "source": "Fire VASE data lake",
        "fire_id": str(event["fire_id"]),
        "year": int(event["year"]),
        "region": str(event["region"]),
        "shape_label": str(event["shape_label"]),
        "final_area_km2": float(event["final_area_km2"]),
        "duration_days": float(event["duration_days"]),
        "observation_count": int(event["observation_count"]),
        "pulse_count": int(event["pulse_count"]),
        "reactivation_count": int(event["reactivation_count"]),
        "mean_vpd_kpa": float(event["mean_vpd_kpa"]),
        "max_vpd_kpa": float(event["max_vpd_kpa"]),
        "daily_vpd_min_kpa": float(event_slices["vpd_kpa"].min()),
        "daily_vpd_max_kpa": float(event_slices["vpd_kpa"].max()),
        "render_note": "Transparent 3D surface of cumulative normalized VASE width, colored by daily centroid gridMET VPD.",
    }
    metadata.write_text(json.dumps(payload, indent=2) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-lake", type=Path, default=DEFAULT_DATA_LAKE)
    parser.add_argument("--fire-id", default=None, help="Optional fire_id override. Defaults to ranked dramatic case.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    args = parser.parse_args()

    data_root = resolve_data_root(args.data_lake)
    features, slices = load_tables(data_root)
    if args.fire_id is None:
        event = choose_dramatic_event(features)
    else:
        matches = features[features["fire_id"].astype(str) == str(args.fire_id)]
        if matches.empty:
            raise ValueError(f"fire_id {args.fire_id!r} was not found in morphospace features.")
        event = matches.iloc[0]

    event_slices = slices[slices["fire_id"].astype(str) == str(event["fire_id"])].copy()
    event_slices = event_slices[event_slices["climate_available"] & event_slices["vpd_kpa"].notna()]
    if event_slices.empty:
        raise ValueError(f"fire_id {event['fire_id']!r} has no daily VPD slices.")

    render_vase(event_slices, args.output)
    write_metadata(event, event_slices, args.output, args.metadata)
    print(f"Rendered {args.output}")
    print(f"Metadata {args.metadata}")
    print(
        f"fire_id={event['fire_id']} shape={event['shape_label']} "
        f"area={event['final_area_km2']:.1f} km2 mean_vpd={event['mean_vpd_kpa']:.2f} kPa"
    )


if __name__ == "__main__":
    main()
