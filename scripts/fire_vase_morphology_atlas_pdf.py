#!/usr/bin/env python3
"""Build a visual fire VASE morphology atlas from real FIRED/gridMET caches."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/cubedynamics-mpl-cache")

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xarray as xr
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Polygon


CATEGORY_COLORS = {
    "single flash": "#b12a1c",
    "skinny persistent": "#1f6f78",
    "compact steady": "#5f8d4e",
    "front-loaded plateau": "#7f3b2d",
    "late surge": "#7251b5",
    "broad rapid": "#d18700",
    "multi-pulse complex": "#2f4858",
}


def _read_fired(daily_path: Path, events_path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    daily_cols = ["id", "date", "event_day", "event_dur", "dy_ar_km2", "tot_ar_km2"]
    daily = gpd.read_file(daily_path, include_fields=daily_cols)
    events = gpd.read_file(events_path)
    daily = pd.DataFrame(daily.drop(columns="geometry", errors="ignore"))
    for col in ("date",):
        daily[col] = pd.to_datetime(daily[col])
    for col in ("ig_date", "last_date"):
        events[col] = pd.to_datetime(events[col])
    projected = events.to_crs("EPSG:5070").geometry.centroid
    centroids = projected.to_crs("EPSG:4326")
    events = pd.DataFrame(events.drop(columns="geometry"))
    events["centroid_lon"] = centroids.x
    events["centroid_lat"] = centroids.y
    return daily, events


def _region_from_lonlat(lon: float, lat: float) -> str:
    if lat >= 50 and -170 <= lon <= -130:
        return "alaska"
    if 18 <= lat <= 23 and -161 <= lon <= -154:
        return "hawaii"
    if lon < -112:
        return "west"
    if lon < -96:
        return "intermountain"
    if lon < -84:
        return "central"
    return "east"


def _count_pulses(values: np.ndarray) -> int:
    values = np.asarray(values, dtype=float)
    if len(values) <= 1 or not np.isfinite(values).any():
        return int(len(values) == 1 and values[0] > 0)
    peak = float(np.nanmax(values))
    if peak <= 0:
        return 0
    threshold = max(0.1, peak * 0.25, float(np.nanquantile(values, 0.75)))
    return int(np.sum(values >= threshold))


def build_shape_tables(daily: pd.DataFrame, events: pd.DataFrame) -> tuple[pd.DataFrame, dict[int, pd.DataFrame]]:
    profiles: dict[int, pd.DataFrame] = {}
    rows: list[dict] = []
    events_ix = events.set_index("id", drop=False)
    for fire_id, group in daily.groupby("id", sort=False):
        if fire_id not in events_ix.index:
            continue
        event = events_ix.loc[fire_id]
        if isinstance(event, pd.DataFrame):
            event = event.iloc[0]
        group = group.sort_values(["date", "event_day"]).copy()
        growth = group["dy_ar_km2"].fillna(0).clip(lower=0).to_numpy(float)
        cumulative = np.cumsum(growth)
        final_area = float(event.get("tot_ar_km2", np.nan))
        if not np.isfinite(final_area) or final_area <= 0:
            final_area = float(np.nanmax(cumulative)) if len(cumulative) else 0.0
        duration_days = float(event.get("event_dur", np.nan))
        if not np.isfinite(duration_days) or duration_days <= 0:
            duration_days = max(1.0, float((group["date"].max() - group["date"].min()).days + 1))
        obs = int(len(group))
        peak_idx = int(np.nanargmax(growth)) if len(growth) else 0
        peak_timing = float(peak_idx / max(obs - 1, 1))
        pulses = _count_pulses(growth)
        front_loaded = float(cumulative[min(len(cumulative) - 1, max(0, obs // 2 - 1))] / final_area) if final_area > 0 and obs else np.nan
        terminal_taper = float(growth[-1] / np.nanmax(growth)) if len(growth) and np.nanmax(growth) > 0 else np.nan
        radius_km = float(np.sqrt(final_area / np.pi)) if final_area > 0 else 0.0
        slenderness = float(duration_days / max(2 * radius_km, 0.1))
        normalized_width = np.sqrt(np.maximum(cumulative, 0) / max(final_area, 1e-9))
        profile = pd.DataFrame(
            {
                "fire_id": fire_id,
                "date": group["date"].to_numpy(),
                "growth_km2": growth,
                "cumulative_km2": cumulative,
                "normalized_width": normalized_width,
                "relative_time": np.linspace(0, 1, obs) if obs > 1 else np.array([0.5]),
            }
        )
        profiles[int(fire_id)] = profile
        rows.append(
            {
                "fire_id": int(fire_id),
                "year": int(event.get("ig_year", pd.to_datetime(event.get("ig_date")).year)),
                "region": _region_from_lonlat(float(event["centroid_lon"]), float(event["centroid_lat"])),
                "final_area_km2": final_area,
                "duration_days": duration_days,
                "observation_count": obs,
                "pulse_count": pulses,
                "peak_timing": peak_timing,
                "front_loaded_fraction": front_loaded,
                "terminal_taper_fraction": terminal_taper,
                "slenderness_days_per_width": slenderness,
                "centroid_lon": float(event["centroid_lon"]),
                "centroid_lat": float(event["centroid_lat"]),
                "ig_date": pd.to_datetime(event["ig_date"]),
                "last_date": pd.to_datetime(event["last_date"]),
            }
        )
    traits = pd.DataFrame(rows)
    traits = assign_categories(traits)
    return traits, profiles


def assign_categories(traits: pd.DataFrame) -> pd.DataFrame:
    out = traits.copy()
    area_q90 = out["final_area_km2"].quantile(0.90)
    duration_q50 = out["duration_days"].quantile(0.50)
    slender_q75 = out["slenderness_days_per_width"].quantile(0.75)
    area_q75 = out["final_area_km2"].quantile(0.75)
    categories = []
    for row in out.itertuples():
        if row.observation_count <= 1 or row.duration_days <= 1:
            cat = "single flash"
        elif row.slenderness_days_per_width >= slender_q75 and row.final_area_km2 <= area_q75:
            cat = "skinny persistent"
        elif row.final_area_km2 >= area_q90 and row.duration_days <= duration_q50:
            cat = "broad rapid"
        elif row.pulse_count >= 3 or row.observation_count >= 6:
            cat = "multi-pulse complex"
        elif row.peak_timing >= 0.66:
            cat = "late surge"
        elif row.front_loaded_fraction >= 0.75 and row.terminal_taper_fraction <= 0.35:
            cat = "front-loaded plateau"
        else:
            cat = "compact steady"
        categories.append(cat)
    out["shape_category"] = categories
    return out


def draw_vase(ax, profile: pd.DataFrame, *, color: str, alpha: float = 0.9) -> None:
    y = profile["relative_time"].to_numpy(float)
    w = profile["normalized_width"].to_numpy(float)
    if len(y) == 1:
        y = np.array([0.45, 0.55])
        w = np.array([max(float(w[0]), 0.08), max(float(w[0]), 0.08)])
    w = 0.44 * np.clip(w, 0.04, 1.0)
    x = np.r_[-w, w[::-1]]
    yy = np.r_[y, y[::-1]]
    ax.add_patch(Polygon(np.c_[x, yy], closed=True, facecolor=color, edgecolor="#222222", linewidth=0.25, alpha=alpha))
    ax.set_xlim(-0.52, 0.52)
    ax.set_ylim(-0.04, 1.04)
    ax.axis("off")


def sample_ids(traits: pd.DataFrame, n: int, *, seed: int = 20260722) -> list[int]:
    rng = np.random.default_rng(seed)
    parts = []
    categories = sorted(traits["shape_category"].unique())
    per = max(1, n // len(categories))
    for cat in categories:
        sub = traits[traits["shape_category"] == cat]
        take = min(len(sub), per)
        if take:
            parts.extend(rng.choice(sub["fire_id"].to_numpy(int), size=take, replace=False).tolist())
    if len(parts) < n:
        rest = traits[~traits["fire_id"].isin(parts)]
        take = min(len(rest), n - len(parts))
        parts.extend(rng.choice(rest["fire_id"].to_numpy(int), size=take, replace=False).tolist())
    return parts[:n]


def load_gridmet_arrays(gridmet_dir: Path) -> dict[str, xr.DataArray]:
    arrays: dict[str, xr.DataArray] = {}
    for variable in ["tmmx", "tmmn", "vpd", "vs"]:
        paths = sorted(gridmet_dir.glob(f"{variable}_*.nc"))
        if not paths:
            continue
        ds = xr.open_mfdataset([str(path) for path in paths], combine="by_coords", chunks={})
        if "day" in ds.dims:
            ds = ds.rename({"day": "time"})
        da = ds[variable] if variable in ds.data_vars else ds[next(iter(ds.data_vars))]
        arrays[variable] = da.sortby("time")
    return arrays


def _convert_values(variable: str, arr: np.ndarray) -> np.ndarray:
    arr = np.asarray(arr, dtype=float)
    if variable in {"tmmx", "tmmn"}:
        return arr - 273.15
    return arr


def climate_sample(traits: pd.DataFrame, gridmet_dir: Path, n: int, seed: int = 20260722) -> pd.DataFrame:
    arrays = load_gridmet_arrays(gridmet_dir)
    if len(arrays) < 4:
        return pd.DataFrame()
    eligible = traits[
        (traits["ig_date"] >= pd.Timestamp("2001-01-01"))
        & (traits["last_date"] <= pd.Timestamp("2003-12-31"))
        & (traits["region"].isin(["west", "intermountain", "central", "east"]))
    ].copy()
    if eligible.empty:
        return pd.DataFrame()
    ids = sample_ids(eligible, min(n, len(eligible)), seed=seed)
    sample = eligible[eligible["fire_id"].isin(ids)].copy()
    rows = []
    lon_min = float(arrays["tmmx"]["lon"].min())
    for row in sample.itertuples():
        start = pd.Timestamp(row.ig_date).normalize()
        end = pd.Timestamp(row.last_date).normalize()
        lon = float(row.centroid_lon)
        if lon_min >= 0 and lon < 0:
            lon += 360
        out = row._asdict()
        for variable, da in arrays.items():
            try:
                selected = da.sel(lon=lon, lat=float(row.centroid_lat), method="nearest").sel(time=slice(start, end))
                vals = _convert_values(variable, selected.values)
            except Exception:
                vals = np.array([], dtype=float)
            if vals.size and np.isfinite(vals).any():
                out[f"{variable}_mean"] = float(np.nanmean(vals))
                out[f"{variable}_max"] = float(np.nanmax(vals))
                out[f"{variable}_min"] = float(np.nanmin(vals))
                if variable == "vs":
                    out["wind_present_fraction"] = float(np.nanmean(vals > 0.1))
            else:
                out[f"{variable}_mean"] = np.nan
                out[f"{variable}_max"] = np.nan
                out[f"{variable}_min"] = np.nan
        rows.append(out)
    return pd.DataFrame(rows)


def page_title(fig, title: str, subtitle: str | None = None) -> None:
    fig.text(0.05, 0.955, title, fontsize=20, fontweight="bold", ha="left", va="top")
    if subtitle:
        fig.text(0.05, 0.918, subtitle, fontsize=9.5, color="#555555", ha="left", va="top")


def plot_many_vases(pdf: PdfPages, traits: pd.DataFrame, profiles: dict[int, pd.DataFrame], ids: list[int], title: str) -> None:
    cols, rows = 18, 12
    fig, axes = plt.subplots(rows, cols, figsize=(16, 10), constrained_layout=False)
    page_title(fig, title, "Each glyph is a real FIRED event profile: vertical axis is observed fire time; width is sqrt(cumulative area), normalized within fire.")
    for ax, fire_id in zip(axes.flat, ids):
        row = traits.loc[traits["fire_id"] == fire_id].iloc[0]
        draw_vase(ax, profiles[int(fire_id)], color=CATEGORY_COLORS[row["shape_category"]])
    for ax in axes.flat[len(ids) :]:
        ax.axis("off")
    fig.subplots_adjust(left=0.035, right=0.985, top=0.86, bottom=0.045, wspace=0.08, hspace=0.08)
    legend_items = sorted(traits["shape_category"].unique())
    handles = [plt.Line2D([0], [0], marker="s", linestyle="", color=CATEGORY_COLORS[c], label=c) for c in legend_items]
    fig.legend(handles=handles, loc="lower center", ncol=4, fontsize=8, frameon=False)
    pdf.savefig(fig)
    plt.close(fig)


def plot_category_exemplars(pdf: PdfPages, traits: pd.DataFrame, profiles: dict[int, pd.DataFrame]) -> None:
    categories = list(CATEGORY_COLORS)
    cols = 14
    fig, axes = plt.subplots(len(categories), cols, figsize=(16, 10), constrained_layout=False)
    page_title(fig, "Shape Categories: Example VASE Profiles", "Rows are rule-based morphology categories computed from real daily FIRED area trajectories.")
    for r, cat in enumerate(categories):
        sub = traits[traits["shape_category"] == cat].sort_values("final_area_km2")
        if sub.empty:
            for ax in axes[r]:
                ax.axis("off")
            continue
        ids = np.linspace(0, len(sub) - 1, min(cols, len(sub))).astype(int)
        for c, idx in enumerate(ids):
            fire_id = int(sub.iloc[idx]["fire_id"])
            draw_vase(axes[r, c], profiles[fire_id], color=CATEGORY_COLORS[cat])
        for ax in axes[r, len(ids) :]:
            ax.axis("off")
        axes[r, 0].text(-0.65, 0.5, f"{cat}\n(n={len(sub):,})", ha="right", va="center", fontsize=8, transform=axes[r, 0].transAxes)
    fig.subplots_adjust(left=0.12, right=0.985, top=0.875, bottom=0.045, wspace=0.05, hspace=0.18)
    pdf.savefig(fig)
    plt.close(fig)


def plot_shape_summary(pdf: PdfPages, traits: pd.DataFrame) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(16, 10))
    page_title(fig, "How Many Stay Skinny? What Shape Categories Appear?", "Categories are population-wide, computed over 278k real FIRED events from daily area profiles.")
    counts = traits["shape_category"].value_counts().reindex(list(CATEGORY_COLORS)).dropna()
    axes[0, 0].barh(counts.index, counts.values, color=[CATEGORY_COLORS[c] for c in counts.index])
    axes[0, 0].invert_yaxis()
    axes[0, 0].set_title("Category counts")
    axes[0, 0].set_xlabel("Events")
    skinny = traits["shape_category"].eq("skinny persistent").sum()
    axes[0, 0].text(0.98, 0.05, f"Skinny persistent: {skinny:,} ({skinny / len(traits):.1%})", ha="right", transform=axes[0, 0].transAxes, fontsize=11)
    order = counts.index.tolist()
    axes[0, 1].boxplot([np.log10(traits.loc[traits["shape_category"] == c, "final_area_km2"].clip(lower=1e-4)) for c in order], tick_labels=order, vert=False, patch_artist=True)
    axes[0, 1].set_title("Final area by category")
    axes[0, 1].set_xlabel("log10 final area km2")
    axes[1, 0].boxplot([traits.loc[traits["shape_category"] == c, "duration_days"] for c in order], tick_labels=order, vert=False, showfliers=False, patch_artist=True)
    axes[1, 0].set_title("Duration by category")
    axes[1, 0].set_xlabel("days")
    axes[1, 1].boxplot([traits.loc[traits["shape_category"] == c, "slenderness_days_per_width"] for c in order], tick_labels=order, vert=False, showfliers=False, patch_artist=True)
    axes[1, 1].set_title("Slenderness by category")
    axes[1, 1].set_xlabel("duration days per diameter-km")
    for ax in axes.flat:
        ax.grid(axis="x", color="#dddddd", linewidth=0.7)
    fig.subplots_adjust(left=0.17, right=0.97, top=0.84, bottom=0.08, wspace=0.28, hspace=0.34)
    pdf.savefig(fig)
    plt.close(fig)


def plot_feature_heatmap(pdf: PdfPages, traits: pd.DataFrame) -> None:
    features = [
        "final_area_km2",
        "duration_days",
        "observation_count",
        "pulse_count",
        "peak_timing",
        "front_loaded_fraction",
        "terminal_taper_fraction",
        "slenderness_days_per_width",
    ]
    med = traits.groupby("shape_category")[features].median().reindex(list(CATEGORY_COLORS)).dropna(how="all")
    z = (med - med.mean()) / med.std(ddof=0).replace(0, 1)
    fig, ax = plt.subplots(figsize=(16, 8.5))
    page_title(fig, "Shape Category Trait Fingerprints", "Standardized median traits show what makes the categories different.")
    im = ax.imshow(z.values, cmap="RdBu_r", vmin=-2, vmax=2, aspect="auto")
    ax.set_yticks(range(len(z.index)))
    ax.set_yticklabels(z.index)
    ax.set_xticks(range(len(features)))
    ax.set_xticklabels([f.replace("_", "\n") for f in features], fontsize=8)
    for i in range(z.shape[0]):
        for j in range(z.shape[1]):
            ax.text(j, i, f"{med.iloc[i, j]:.2g}", ha="center", va="center", fontsize=7)
    fig.colorbar(im, ax=ax, label="standardized median")
    fig.subplots_adjust(left=0.17, right=0.92, top=0.84, bottom=0.18)
    pdf.savefig(fig)
    plt.close(fig)


def plot_climate_vs_shape(pdf: PdfPages, climate: pd.DataFrame) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(16, 10))
    page_title(fig, "Climate Signals Vs Shape", "Real gridMET climate sample, limited to cached 2001-2003 CONUS event windows.")
    if climate.empty:
        fig.text(0.1, 0.5, "No climate sample available from the configured gridMET cache.", fontsize=14)
        pdf.savefig(fig)
        plt.close(fig)
        return
    order = [cat for cat in CATEGORY_COLORS if cat in set(climate["shape_category"])]
    metrics = [
        ("tmmx_mean", "mean tmmx (C)"),
        ("vpd_mean", "mean VPD (kPa)"),
        ("vs_mean", "mean wind speed (m/s)"),
        ("wind_present_fraction", "wind-present fraction"),
    ]
    for ax, (metric, label) in zip(axes.flat, metrics):
        vals = [climate.loc[climate["shape_category"] == cat, metric].dropna() for cat in order]
        ax.boxplot(vals, tick_labels=order, vert=False, showfliers=False, patch_artist=True)
        ax.set_title(label)
        ax.grid(axis="x", color="#dddddd", linewidth=0.7)
    fig.text(0.05, 0.045, f"Climate sample n={len(climate):,}. These are descriptive associations, not causal estimates.", fontsize=9, color="#555555")
    fig.subplots_adjust(left=0.17, right=0.97, top=0.84, bottom=0.10, wspace=0.25, hspace=0.30)
    pdf.savefig(fig)
    plt.close(fig)


def plot_climate_scatter(pdf: PdfPages, climate: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(16, 8))
    page_title(fig, "Shape-Climate Trend Views", "Each point is one real event in the cached climate window.")
    if climate.empty:
        fig.text(0.1, 0.5, "No climate sample available.", fontsize=14)
        pdf.savefig(fig)
        plt.close(fig)
        return
    for cat, sub in climate.groupby("shape_category"):
        color = CATEGORY_COLORS.get(cat, "#444444")
        axes[0].scatter(sub["slenderness_days_per_width"], sub["vpd_mean"], s=12, alpha=0.45, color=color, label=cat)
        axes[1].scatter(sub["final_area_km2"], sub["tmmx_mean"], s=12, alpha=0.45, color=color)
    axes[0].set_xscale("log")
    axes[0].set_xlabel("slenderness days per diameter-km")
    axes[0].set_ylabel("mean VPD (kPa)")
    axes[1].set_xscale("log")
    axes[1].set_xlabel("final area (km2)")
    axes[1].set_ylabel("mean tmmx (C)")
    axes[0].legend(fontsize=7, loc="best", frameon=False)
    for ax in axes:
        ax.grid(color="#dddddd", linewidth=0.7)
    fig.subplots_adjust(left=0.08, right=0.98, top=0.82, bottom=0.12, wspace=0.22)
    pdf.savefig(fig)
    plt.close(fig)


def build_pdf(args) -> dict:
    daily, events = _read_fired(args.daily_gpkg, args.events_gpkg)
    traits, profiles = build_shape_tables(daily, events)
    args.data_output_dir.mkdir(parents=True, exist_ok=True)
    traits_path = args.data_output_dir / "fire_vase_morphology_traits.csv"
    traits_path.parent.mkdir(parents=True, exist_ok=True)
    traits.drop(columns=["ig_date", "last_date"]).to_csv(traits_path, index=False)
    climate = climate_sample(traits, args.gridmet_cache, args.climate_sample_size, seed=args.seed)
    climate_path = args.data_output_dir / "fire_vase_morphology_climate_sample.csv"
    if not climate.empty:
        climate.drop(columns=["ig_date", "last_date"], errors="ignore").to_csv(climate_path, index=False)
    panel_ids = sample_ids(traits, args.panel_size, seed=args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with PdfPages(args.output) as pdf:
        plot_many_vases(pdf, traits, profiles, panel_ids, "Population VASE Panel: Real FIRED Shape Variation")
        plot_category_exemplars(pdf, traits, profiles)
        plot_shape_summary(pdf, traits)
        plot_feature_heatmap(pdf, traits)
        plot_climate_vs_shape(pdf, climate)
        plot_climate_scatter(pdf, climate)
        meta = pdf.infodict()
        meta["Title"] = "Fire VASE Morphology Atlas"
        meta["Author"] = "CubeDynamics"
        meta["Subject"] = "Real FIRED VASE profile panels and shape-climate comparisons"
    report = {
        "pdf": args.output.as_posix(),
        "n_fires": int(len(traits)),
        "panel_size": int(len(panel_ids)),
        "shape_counts": {k: int(v) for k, v in traits["shape_category"].value_counts().to_dict().items()},
        "climate_sample_rows": int(len(climate)),
        "traits_csv": traits_path.as_posix(),
        "climate_csv": climate_path.as_posix() if not climate.empty else None,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    args.manifest.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--daily-gpkg", type=Path, default=Path("artifacts/fire-vase-gridmet-real/fired-cache/fired_conus-ak_daily_nov2001-march2021.gpkg"))
    parser.add_argument("--events-gpkg", type=Path, default=Path("artifacts/fire-vase-gridmet-real/fired-cache/fired_conus-ak_events_nov2001-march2021.gpkg"))
    parser.add_argument("--gridmet-cache", type=Path, default=Path("artifacts/fire-vase-gridmet-real/gridmet-cache"))
    parser.add_argument("--output", type=Path, default=Path("output/pdf/fire_vase_morphology_atlas.pdf"))
    parser.add_argument("--manifest", type=Path, default=Path("output/pdf/fire_vase_morphology_atlas_manifest.json"))
    parser.add_argument("--data-output-dir", type=Path, default=Path("scratch/fire_vase_morphology_atlas"))
    parser.add_argument("--panel-size", type=int, default=216)
    parser.add_argument("--climate-sample-size", type=int, default=900)
    parser.add_argument("--seed", type=int, default=20260722)
    args = parser.parse_args()
    report = build_pdf(args)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
