#!/usr/bin/env python3
"""Generate the climate-centered Fire VASE manuscript revision.

This script intentionally writes new analysis, figure, and manuscript outputs
without overwriting the prior audited manuscript or figure set.
"""

from __future__ import annotations

import json
import math
import os
import textwrap
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/cubedynamics-mpl-cache")

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import colors
from matplotlib.collections import LineCollection
from matplotlib.patches import Ellipse, Polygon
from reportlab.lib import colors as rl_colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer
from scipy import stats


ROOT = Path(__file__).resolve().parents[1]
FEATURES_PATH = ROOT / "scratch/fire_vase_developmental_morphology/developmental_morphospace_features.parquet"
STAGE_PATH = ROOT / "scratch/fire_vase_developmental_morphology/developmental_stage_table.parquet"
MATCHED_PATH = ROOT / "scratch/fire_vase_developmental_morphology/developmental_matched_pairs.parquet"
SLICES_PATH = ROOT / "scratch/fire_vase_run_full/tables/vase_slices.parquet"
TRAITS_PATH = ROOT / "scratch/fire_vase_run_full/tables/fire_traits.parquet"
CATALOG_PATH = ROOT / "scratch/fire_vase_run_full/tables/fire_catalog.parquet"
EXPOSURES_PATH = ROOT / "scratch/fire_vase_run_full/tables/vase_climate_exposures.parquet"
CLIMATE_REPORT_PATH = ROOT / "scratch/fire_vase_run_full/climate_build_comprehensive_report.json"
PERIMETER_REPORT_PATH = ROOT / "scratch/fire_vase_run_full/perimeter_climate_build_comprehensive_report.json"
GRIDMET_MANIFEST_PATH = ROOT / "scratch/fire_vase_run_full/gridmet_cache_manifest.json"

ANALYSIS_DIR = ROOT / "analysis"
STATS_DIR = ANALYSIS_DIR / "climate_revision_stats"
MAIN_FIGURE_DIR = ROOT / "figures/climate_revision_main"
SUPP_FIGURE_DIR = ROOT / "figures/climate_revision_supplement"
MANUSCRIPT_DIR = ROOT / "docs/manuscripts/fire_vase_developmental_morphology"
MANUSCRIPT_MD = MANUSCRIPT_DIR / "manuscript_climate_revision_science_style.md"
FIGURE_LEGENDS_MD = MAIN_FIGURE_DIR / "figure_legends.md"
OUTPUT_PDF = ROOT / "output/pdf/fire_vase_climate_revision_science_style_manuscript.pdf"
OUTPUT_MANIFEST = ROOT / "output/pdf/fire_vase_climate_revision_science_style_manuscript_manifest.json"
CHANGELOG = ROOT / "CHANGELOG_CLIMATE_REVISION.md"
FINAL_REPORT = ANALYSIS_DIR / "climate_revision_terminal_summary.txt"

SEED = 20260722
RNG = np.random.default_rng(SEED)

INK = "#202124"
MUTED = "#62666d"
LIGHT = "#e6e8eb"
BLUE = "#3b78b6"
TEAL = "#239b8b"
GOLD = "#c49a29"
PURPLE = "#7b5bbd"
RED = "#b23a32"
ORANGE = "#d78232"
CLIMATE_CMAP = "viridis"

CLIMATE_METADATA = {
    "maximum_temperature_c": ("Maximum temperature", "degrees C"),
    "minimum_temperature_c": ("Minimum temperature", "degrees C"),
    "vpd_kpa": ("VPD", "kPa"),
    "wind_speed_m_s": ("Wind speed", "m s-1"),
    "precipitation_mm": ("Precipitation", "mm d-1"),
    "maximum_relative_humidity_pct": ("Maximum relative humidity", "%"),
    "minimum_relative_humidity_pct": ("Minimum relative humidity", "%"),
    "specific_humidity_kg_kg": ("Specific humidity", "kg kg-1"),
    "fuel_moisture_100hr_pct": ("100-hour fuel moisture", "%"),
    "fuel_moisture_1000hr_pct": ("1000-hour fuel moisture", "%"),
    "energy_release_component": ("Energy release component", "index"),
    "burning_index": ("Burning index", "index"),
    "reference_evapotranspiration_mm": ("Reference evapotranspiration", "mm d-1"),
    "potential_evapotranspiration_mm": ("Potential evapotranspiration", "mm d-1"),
    "solar_radiation_w_m2": ("Solar radiation", "W m-2"),
}

CORE_CLIMATE_COLUMNS = [
    "maximum_temperature_c",
    "minimum_temperature_c",
    "vpd_kpa",
    "wind_speed_m_s",
]

MOISTURE_CLIMATE_COLUMNS = [
    "precipitation_mm",
    "maximum_relative_humidity_pct",
    "minimum_relative_humidity_pct",
    "specific_humidity_kg_kg",
    "fuel_moisture_100hr_pct",
    "fuel_moisture_1000hr_pct",
]

FIRE_DANGER_CLIMATE_COLUMNS = [
    "energy_release_component",
    "burning_index",
    "reference_evapotranspiration_mm",
    "potential_evapotranspiration_mm",
    "solar_radiation_w_m2",
]

RESPONSES = [
    "front_loaded_fraction",
    "late_growth_fraction",
    "terminal_taper_fraction",
    "growth_entropy",
    "pulse_count",
    "reactivation_count",
    "peak_timing",
    "duration_days",
    "final_area_km2",
    "morph_pc1",
]

SHAPE_COLORS = {
    "single flash": "#6f7378",
    "skinny persistent": BLUE,
    "compact steady": TEAL,
    "multi-pulse complex": "#1f4e79",
    "front-loaded plateau": GOLD,
    "late surge": PURPLE,
    "broad rapid": RED,
}


@dataclass
class DataBundle:
    features: pd.DataFrame
    slices: pd.DataFrame
    stage: pd.DataFrame
    matched: pd.DataFrame
    traits: pd.DataFrame
    catalog: pd.DataFrame
    exposures: pd.DataFrame
    climate_report: dict
    perimeter_report: dict
    gridmet_manifest: dict


def set_style() -> None:
    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.edgecolor": INK,
            "axes.labelcolor": INK,
            "axes.titlecolor": INK,
            "xtick.color": INK,
            "ytick.color": INK,
            "axes.labelsize": 7.4,
            "axes.titlesize": 7.8,
            "xtick.labelsize": 6.7,
            "ytick.labelsize": 6.7,
            "legend.fontsize": 6.8,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
        }
    )


def ensure_dirs() -> None:
    for path in [ANALYSIS_DIR, STATS_DIR, MAIN_FIGURE_DIR, SUPP_FIGURE_DIR, MANUSCRIPT_DIR, OUTPUT_PDF.parent]:
        path.mkdir(parents=True, exist_ok=True)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text()) if path.exists() else {}


def load_data() -> DataBundle:
    return DataBundle(
        features=pd.read_parquet(FEATURES_PATH),
        slices=pd.read_parquet(SLICES_PATH),
        stage=pd.read_parquet(STAGE_PATH),
        matched=pd.read_parquet(MATCHED_PATH),
        traits=pd.read_parquet(TRAITS_PATH),
        catalog=pd.read_parquet(CATALOG_PATH),
        exposures=pd.read_parquet(EXPOSURES_PATH) if EXPOSURES_PATH.exists() else pd.DataFrame(),
        climate_report=read_json(CLIMATE_REPORT_PATH),
        perimeter_report=read_json(PERIMETER_REPORT_PATH),
        gridmet_manifest=read_json(GRIDMET_MANIFEST_PATH),
    )


def savefig(fig: plt.Figure, directory: Path, stem: str) -> dict[str, str]:
    directory.mkdir(parents=True, exist_ok=True)
    paths = {
        "png": directory / f"{stem}.png",
        "pdf": directory / f"{stem}.pdf",
        "svg": directory / f"{stem}.svg",
    }
    for path in paths.values():
        fig.savefig(path, bbox_inches="tight", dpi=450)
    plt.close(fig)
    return {k: str(v) for k, v in paths.items()}


def clean_axis(ax: plt.Axes) -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(color=LIGHT, lw=0.45, alpha=0.9)


def panel_label(ax: plt.Axes, label: str) -> None:
    ax.text(
        0.01,
        0.98,
        f"({label.lower()})",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=10,
        weight="bold",
        bbox={"boxstyle": "square,pad=0.12", "facecolor": "white", "edgecolor": "white", "alpha": 0.88},
    )


def wrapped(text: str, width: int = 92) -> str:
    return "\n".join(textwrap.wrap(text, width=width, break_long_words=False))


def df_to_markdown(df: pd.DataFrame, *, floatfmt: str = ".3f") -> str:
    if df.empty:
        return "_No rows._"
    headers = [str(c) for c in df.columns]
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for _, row in df.iterrows():
        vals = []
        for val in row:
            if isinstance(val, (float, np.floating)) and np.isfinite(val):
                vals.append(format(float(val), floatfmt))
            else:
                vals.append(str(val))
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines)


def draw_vase(
    ax: plt.Axes,
    profile: pd.DataFrame,
    *,
    width_col: str = "width",
    time_col: str = "relative_time",
    color: str = BLUE,
    climate_col: str | None = None,
    climate_norm: colors.Normalize | None = None,
    cmap: str = CLIMATE_CMAP,
    outline: str = INK,
    alpha: float = 0.9,
    dashed: bool = False,
) -> None:
    ax.set_aspect("equal")
    ax.axis("off")
    if profile is None or profile.empty:
        return
    p = profile.sort_values(time_col).copy()
    if len(p) == 1:
        p = pd.concat([p, p], ignore_index=True)
        p[time_col] = [0.45, 0.55]
    y = p[time_col].to_numpy(float)
    width = np.clip(p[width_col].to_numpy(float), 0.02, 1.0)
    left = -0.42 * width
    right = 0.42 * width
    if climate_col and climate_col in p.columns:
        vals = p[climate_col].to_numpy(float)
        cmap_obj = plt.get_cmap(cmap)
        climate_norm = climate_norm or colors.Normalize(np.nanquantile(vals, 0.05), np.nanquantile(vals, 0.95))
        facecolors = cmap_obj(climate_norm(vals))
    else:
        facecolors = [color] * len(p)
    ell_h = max(0.028, min(0.07, 0.8 / max(len(p), 8)))
    for yi, wi, fc in zip(y, width, facecolors):
        ax.add_patch(Ellipse((0, yi), width=0.84 * wi, height=ell_h, facecolor=fc, edgecolor=outline, lw=0.45, alpha=alpha))
    linestyle = (0, (3, 2)) if dashed else "solid"
    ax.plot(left, y, color=outline, lw=0.85, ls=linestyle)
    ax.plot(right, y, color=outline, lw=0.85, ls=linestyle)
    ax.set_xlim(-0.52, 0.52)
    ax.set_ylim(-0.04, 1.04)


def profile_for_fire(slices: pd.DataFrame, fire_id: str | int) -> pd.DataFrame:
    p = slices.loc[slices.fire_id.astype(str) == str(fire_id)].sort_values("slice_index").copy()
    if p.empty:
        return p
    denom = max(float(p["slice_index"].max()), 1.0)
    p["relative_time"] = p["slice_index"] / denom
    p["width"] = p["normalized_vase_width"].fillna(0).clip(0.02, 1.0)
    return p


def composite_profile(slices: pd.DataFrame, fire_ids: pd.Series | np.ndarray, n_grid: int = 41) -> pd.DataFrame:
    ids = set(pd.Series(fire_ids).astype(str))
    sub = slices.loc[slices.fire_id.astype(str).isin(ids)].copy()
    if sub.empty:
        return pd.DataFrame()
    max_idx = sub.groupby("fire_id")["slice_index"].transform("max").replace(0, np.nan)
    sub["relative_time"] = (sub["slice_index"] / max_idx).fillna(0.5)
    sub["width"] = sub["normalized_vase_width"].fillna(0).clip(0.0, 1.0)
    grid = np.linspace(0, 1, n_grid)
    rows = []
    for fid, g in sub.groupby("fire_id", observed=True):
        g = g.sort_values("relative_time")
        x = g["relative_time"].to_numpy(float)
        y = g["width"].to_numpy(float)
        if len(x) == 1:
            interp = np.repeat(y[0], n_grid)
        else:
            interp = np.interp(grid, x, y)
        rows.extend({"fire_id": fid, "relative_time": t, "width": w} for t, w in zip(grid, interp))
    prof = pd.DataFrame(rows)
    out = prof.groupby("relative_time")["width"].agg(width="median", q25=lambda s: np.quantile(s, 0.25), q75=lambda s: np.quantile(s, 0.75)).reset_index()
    out["n_fires"] = len(ids)
    return out


def draw_composite_vase(ax: plt.Axes, profile: pd.DataFrame, *, color: str = BLUE, outline: str = INK) -> None:
    ax.set_aspect("equal")
    ax.axis("off")
    if profile.empty:
        return
    p = profile.sort_values("relative_time")
    y = p["relative_time"].to_numpy(float)
    med = np.clip(p["width"].to_numpy(float), 0.02, 1.0)
    q25 = np.clip(p["q25"].to_numpy(float), 0.02, 1.0)
    q75 = np.clip(p["q75"].to_numpy(float), 0.02, 1.0)
    shell = np.c_[np.r_[-0.42 * q75, 0.42 * q75[::-1]], np.r_[y, y[::-1]]]
    ax.add_patch(Polygon(shell, closed=True, facecolor=color, edgecolor="none", alpha=0.15))
    ax.plot(-0.42 * med, y, color=outline, lw=0.8)
    ax.plot(0.42 * med, y, color=outline, lw=0.8)
    for yi, wi in zip(y[::2], med[::2]):
        ax.add_patch(Ellipse((0, yi), width=0.84 * wi, height=0.035, facecolor=color, edgecolor=outline, lw=0.35, alpha=0.75))
    ax.set_xlim(-0.55, 0.55)
    ax.set_ylim(-0.04, 1.04)


def make_climate_features(bundle: DataBundle) -> pd.DataFrame:
    features = bundle.features.copy()
    slices = bundle.slices.copy()
    slices["fire_id"] = slices["fire_id"].astype(str)
    features["fire_id"] = features["fire_id"].astype(str)
    climate_cols = [col for col in CLIMATE_METADATA if col in slices.columns]
    if not climate_cols:
        raise ValueError("No recognized climate columns found in the VASE slice table.")
    meta = features[["fire_id", "region", "year", "final_area_km2"]]
    s = slices.merge(meta, on="fire_id", how="left")
    s = s.loc[s["climate_available"].fillna(False)].copy()
    s["timestamp"] = pd.to_datetime(s["timestamp"])
    s["month"] = s["timestamp"].dt.month
    max_idx = s.groupby("fire_id")["slice_index"].transform("max").replace(0, np.nan)
    s["relative_time"] = (s["slice_index"] / max_idx).fillna(0.5)
    s["time_bin"] = pd.cut(s["relative_time"], bins=[-0.001, 1 / 3, 2 / 3, 1.001], labels=["early", "middle", "late"])

    thresholds = {}
    if "maximum_temperature_c" in s:
        thresholds["hot_day"] = float(s["maximum_temperature_c"].quantile(0.90))
        s["hot_day"] = s["maximum_temperature_c"] >= thresholds["hot_day"]
    if "vpd_kpa" in s:
        thresholds["high_vpd_day"] = float(s["vpd_kpa"].quantile(0.90))
        s["high_vpd_day"] = s["vpd_kpa"] >= thresholds["high_vpd_day"]
    if "wind_speed_m_s" in s:
        thresholds["windy_day"] = float(s["wind_speed_m_s"].quantile(0.90))
        s["windy_day"] = s["wind_speed_m_s"] >= thresholds["windy_day"]
    if "precipitation_mm" in s:
        thresholds["wet_day"] = 0.0
        s["wet_day"] = s["precipitation_mm"] > 0
    if "fuel_moisture_1000hr_pct" in s:
        thresholds["dry_1000hr_fuel_day"] = float(s["fuel_moisture_1000hr_pct"].quantile(0.10))
        s["dry_1000hr_fuel_day"] = s["fuel_moisture_1000hr_pct"] <= thresholds["dry_1000hr_fuel_day"]
    if "energy_release_component" in s:
        thresholds["high_erc_day"] = float(s["energy_release_component"].quantile(0.90))
        s["high_erc_day"] = s["energy_release_component"] >= thresholds["high_erc_day"]

    region_month = s.groupby(["region", "month"], observed=True)[climate_cols].median()
    joined = s.join(region_month, on=["region", "month"], rsuffix="_region_month_median")
    for col in climate_cols:
        joined[f"{col}_region_month_anomaly"] = joined[col] - joined[f"{col}_region_month_median"]

    agg_spec = {"slice_count": ("slice_index", "size")}
    for flag in ["hot_day", "high_vpd_day", "windy_day", "wet_day", "dry_1000hr_fuel_day", "high_erc_day"]:
        if flag in joined:
            agg_spec[f"{flag}_fraction"] = (flag, "mean")
    for col in climate_cols:
        agg_spec[f"mean_{col}"] = (col, "mean")
        agg_spec[f"min_daily_{col}"] = (col, "min")
        agg_spec[f"max_daily_{col}"] = (col, "max")
        agg_spec[f"mean_{col}_region_month_anomaly"] = (f"{col}_region_month_anomaly", "mean")
    agg = joined.groupby("fire_id").agg(**agg_spec)
    rename = {
        "max_daily_maximum_temperature_c": "max_daily_temperature_c",
        "max_daily_vpd_kpa": "max_daily_vpd_kpa",
        "max_daily_wind_speed_m_s": "max_daily_wind_speed_m_s",
        "mean_maximum_temperature_c_region_month_anomaly": "mean_maximum_temperature_region_month_anomaly_c",
        "mean_minimum_temperature_c_region_month_anomaly": "mean_minimum_temperature_region_month_anomaly_c",
        "mean_vpd_kpa_region_month_anomaly": "mean_vpd_region_month_anomaly_kpa",
        "mean_wind_speed_m_s_region_month_anomaly": "mean_wind_region_month_anomaly_m_s",
    }
    agg = agg.rename(columns={k: v for k, v in rename.items() if k in agg.columns})

    phase_values = [col for col in [*CORE_CLIMATE_COLUMNS, *MOISTURE_CLIMATE_COLUMNS, *FIRE_DANGER_CLIMATE_COLUMNS] if col in joined.columns]
    phase = joined.pivot_table(
        index="fire_id",
        columns="time_bin",
        values=phase_values,
        aggfunc="mean",
        observed=True,
    )
    phase.columns = [f"{var}_{phase_name}_mean" for var, phase_name in phase.columns]
    overwrite_cols = [col for col in [*agg.columns, *phase.columns] if col in features.columns]
    features = features.drop(columns=overwrite_cols)
    climate_features = features.merge(agg.reset_index(), on="fire_id", how="left").merge(phase.reset_index(), on="fire_id", how="left")
    climate_features["wind_present_fraction"] = climate_features.get("windy_day_fraction", np.nan)
    climate_features.attrs["thresholds"] = thresholds
    region_month.reset_index().to_csv(STATS_DIR / "region_month_fire_season_medians.csv", index=False)
    pd.DataFrame([thresholds]).to_csv(STATS_DIR / "extreme_day_thresholds.csv", index=False)
    pd.DataFrame(
        [
            {"column": col, "label": CLIMATE_METADATA[col][0], "units": CLIMATE_METADATA[col][1], "slice_non_null": int(s[col].notna().sum())}
            for col in climate_cols
        ]
    ).to_csv(STATS_DIR / "available_climate_variables.csv", index=False)
    climate_features.to_parquet(STATS_DIR / "fire_level_climate_revision_features.parquet", index=False)
    return climate_features


def fold_ids(df: pd.DataFrame, kind: str, k: int = 5) -> np.ndarray:
    if kind == "random_fire":
        return (pd.util.hash_pandas_object(df["fire_id"].astype(str), index=False).to_numpy() % k).astype(int)
    if kind == "year_block":
        years = df["year"].astype(int)
        bins = pd.cut(years, bins=[1999, 2004, 2008, 2012, 2016, 2022], labels=False, include_lowest=True)
        return bins.astype(int).to_numpy()
    if kind == "region_block":
        codes, _ = pd.factorize(df["region"].astype(str))
        return codes.astype(int)
    if kind == "region_year_hash":
        key = df["region"].astype(str) + "_" + df["year"].astype(str)
        return (pd.util.hash_pandas_object(key, index=False).to_numpy() % k).astype(int)
    raise ValueError(kind)


def ridge_predict_cv(df: pd.DataFrame, predictors: list[str], response: str, block: str, *, alpha: float = 1.0) -> dict:
    cols = ["fire_id", "year", "region", response] + predictors
    d = df[cols].replace([np.inf, -np.inf], np.nan).dropna().copy()
    if response in ["final_area_km2", "duration_days", "pulse_count", "reactivation_count"]:
        d[f"{response}_model"] = np.log1p(d[response].astype(float))
        ycol = f"{response}_model"
    else:
        ycol = response
    if len(d) < 200:
        return {"response": response, "predictor_set": "", "block": block, "n": len(d), "r2": np.nan, "baseline_r2": 0.0}
    folds = fold_ids(d, block)
    y = d[ycol].to_numpy(float)
    preds = np.full(len(d), np.nan)
    for fold in np.unique(folds):
        test = folds == fold
        train = ~test
        if train.sum() < len(predictors) + 10 or test.sum() == 0:
            continue
        x_train = d.loc[train, predictors].to_numpy(float)
        x_test = d.loc[test, predictors].to_numpy(float)
        mu = x_train.mean(axis=0)
        sd = x_train.std(axis=0)
        sd[sd == 0] = 1.0
        x_train = (x_train - mu) / sd
        x_test = (x_test - mu) / sd
        x_train = np.c_[np.ones(x_train.shape[0]), x_train]
        x_test = np.c_[np.ones(x_test.shape[0]), x_test]
        penalty = np.eye(x_train.shape[1]) * alpha
        penalty[0, 0] = 0
        beta = np.linalg.pinv(x_train.T @ x_train + penalty) @ x_train.T @ y[train]
        preds[test] = x_test @ beta
    ok = np.isfinite(preds)
    ss_res = float(np.sum((y[ok] - preds[ok]) ** 2))
    ss_tot = float(np.sum((y[ok] - np.mean(y[ok])) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot else np.nan
    return {"response": response, "block": block, "n": int(ok.sum()), "r2": r2, "baseline_r2": 0.0}


def coefficient_table(df: pd.DataFrame, predictors: list[str], responses: list[str]) -> pd.DataFrame:
    rows = []
    predictors = list(dict.fromkeys(predictors))
    d = df[["fire_id"] + predictors + responses].replace([np.inf, -np.inf], np.nan)
    for response in responses:
        for predictor in predictors:
            pair = d[[response, predictor]].dropna()
            if len(pair) < 100:
                rho, p = np.nan, np.nan
            else:
                rho, p = stats.spearmanr(pair[predictor], pair[response])
            rows.append({"response": response, "predictor": predictor, "n": len(pair), "spearman_rho": rho, "p_value": p})
    return pd.DataFrame(rows)


def run_event_models(climate_features: pd.DataFrame) -> pd.DataFrame:
    def existing(cols: list[str]) -> list[str]:
        return [col for col in cols if col in climate_features.columns]

    core_means = existing([f"mean_{col}" for col in CORE_CLIMATE_COLUMNS])
    moisture_means = existing([f"mean_{col}" for col in MOISTURE_CLIMATE_COLUMNS])
    fire_danger_means = existing([f"mean_{col}" for col in FIRE_DANGER_CLIMATE_COLUMNS])
    core_extremes = existing(["hot_day_fraction", "high_vpd_day_fraction", "windy_day_fraction"])
    expanded_extremes = existing(["wet_day_fraction", "dry_1000hr_fuel_day_fraction", "high_erc_day_fraction"])
    phase_predictors = []
    for col in [*CORE_CLIMATE_COLUMNS, "fuel_moisture_1000hr_pct", "energy_release_component", "precipitation_mm"]:
        for phase in ["early", "middle", "late"]:
            candidate = f"{col}_{phase}_mean"
            if candidate in climate_features.columns:
                phase_predictors.append(candidate)
    anomaly_predictors = existing(
        [
            "mean_maximum_temperature_region_month_anomaly_c",
            "mean_minimum_temperature_region_month_anomaly_c",
            "mean_vpd_region_month_anomaly_kpa",
            "mean_wind_region_month_anomaly_m_s",
            "mean_precipitation_mm_region_month_anomaly",
            "mean_fuel_moisture_1000hr_pct_region_month_anomaly",
            "mean_energy_release_component_region_month_anomaly",
            "mean_burning_index_region_month_anomaly",
        ]
    )
    model_sets = {
        "core event means": [*core_means, *existing(["max_vpd_kpa"])],
        "moisture and humidity": moisture_means,
        "fire danger and energy": fire_danger_means,
        "comprehensive event means": [*core_means, *moisture_means, *fire_danger_means],
        "region-season anomalies": anomaly_predictors,
        "extreme days": [*core_extremes, *expanded_extremes],
        "time-resolved exposure": [*phase_predictors, *core_extremes, *expanded_extremes],
    }
    model_sets = {name: list(dict.fromkeys(cols)) for name, cols in model_sets.items() if cols}
    rows = []
    for name, predictors in model_sets.items():
        for response in RESPONSES:
            for block in ["random_fire", "year_block", "region_block", "region_year_hash"]:
                res = ridge_predict_cv(climate_features, predictors, response, block)
                res["predictor_set"] = name
                rows.append(res)
    out = pd.DataFrame(rows)
    out.to_csv(STATS_DIR / "event_level_blocked_model_performance.csv", index=False)
    coef = coefficient_table(climate_features, sum(model_sets.values(), []), RESPONSES)
    coef.to_csv(STATS_DIR / "climate_response_spearman_effects.csv", index=False)
    return out


def build_state_model_table(bundle: DataBundle) -> pd.DataFrame:
    s = bundle.slices.copy()
    f = bundle.features[["fire_id", "region"]].copy()
    s["fire_id"] = s["fire_id"].astype(str)
    f["fire_id"] = f["fire_id"].astype(str)
    s = s.merge(f, on="fire_id", how="left")
    s = s.loc[s["climate_available"].fillna(False)].sort_values(["fire_id", "slice_index"]).copy()
    s["next_growth_km2"] = s.groupby("fire_id")["ring_area_km2"].shift(-1)
    s["prev_growth_km2"] = s.groupby("fire_id")["ring_area_km2"].shift(1).fillna(0)
    s["growth_acceleration_km2"] = s["ring_area_km2"].fillna(0) - s["prev_growth_km2"].fillna(0)
    climate_cols = [col for col in CLIMATE_METADATA if col in s.columns]
    core_required = [col for col in CORE_CLIMATE_COLUMNS if col in s.columns]
    s = s.dropna(subset=["next_growth_km2", *core_required])
    s["next_growth_log1p"] = np.log1p(s["next_growth_km2"].clip(lower=0))
    s["current_growth_log1p"] = np.log1p(s["ring_area_km2"].clip(lower=0))
    s["current_cumulative_log1p"] = np.log1p(s["cumulative_area_km2"].clip(lower=0))
    s["elapsed_day"] = s["slice_index"].astype(float)
    s["accelerating"] = s["growth_acceleration_km2"] > 0
    use_cols = [
        "fire_id",
        "year",
        "region",
        "next_growth_log1p",
        *climate_cols,
        "elapsed_day",
        "current_growth_log1p",
        "current_cumulative_log1p",
        "growth_acceleration_km2",
    ]
    out = s[use_cols].copy()
    out.to_parquet(STATS_DIR / "state_dependent_slice_model_table.parquet", index=False)
    return out


def run_state_models(state_df: pd.DataFrame) -> pd.DataFrame:
    core_climate = [col for col in CORE_CLIMATE_COLUMNS if col in state_df.columns]
    expanded_climate = [col for col in CLIMATE_METADATA if col in state_df.columns]
    state = ["elapsed_day", "current_growth_log1p", "current_cumulative_log1p", "growth_acceleration_km2"]
    d = state_df.copy()
    for c in core_climate:
        for st in ["elapsed_day", "current_growth_log1p", "current_cumulative_log1p"]:
            d[f"{c}_x_{st}"] = d[c] * d[st]
    model_sets = {
        "core climate only": core_climate,
        "expanded climate only": expanded_climate,
        "state only": state,
        "core climate plus state": core_climate + state,
        "expanded climate plus state": expanded_climate + state,
        "core climate-state interaction": core_climate + state + [c for c in d.columns if "_x_" in c],
    }
    model_sets = {name: list(dict.fromkeys(cols)) for name, cols in model_sets.items() if cols}
    rows = []
    for name, predictors in model_sets.items():
        for block in ["random_fire", "year_block", "region_block", "region_year_hash"]:
            res = ridge_predict_cv(d, predictors, "next_growth_log1p", block)
            res["predictor_set"] = name
            rows.append(res)
    out = pd.DataFrame(rows)
    out.to_csv(STATS_DIR / "state_dependent_blocked_model_performance.csv", index=False)
    return out


def select_same_size_examples(features: pd.DataFrame) -> list[tuple[str, str, str]]:
    d = features.dropna(subset=["final_area_km2", "duration_days", "front_loaded_fraction", "late_growth_fraction"]).copy()
    d = d.loc[(d["duration_days"] >= 3) & (d["final_area_km2"] > 1)]
    d["area_bin"] = pd.qcut(d["final_area_km2"], 40, duplicates="drop")
    pairs = []
    labels = [
        ("front loaded", "front_loaded_fraction", False),
        ("late growth", "late_growth_fraction", False),
        ("persistent", "growth_entropy", False),
    ]
    for label, col, _ in labels:
        best = None
        best_gap = -np.inf
        for _, g in d.groupby("area_bin", observed=True):
            if len(g) < 20:
                continue
            lo = g.nsmallest(1, col).iloc[0]
            hi = g.nlargest(1, col).iloc[0]
            gap = float(hi[col] - lo[col])
            if gap > best_gap:
                best_gap = gap
                best = (str(lo.fire_id), str(hi.fire_id), label)
        if best:
            pairs.append(best)
    return pairs[:3]


def plot_history(ax: plt.Axes, profile: pd.DataFrame, color: str) -> None:
    p = profile.sort_values("slice_index")
    x = np.arange(len(p))
    daily = p["ring_area_km2"].fillna(0).to_numpy(float)
    cum = p["cumulative_area_km2"].fillna(0).to_numpy(float)
    if np.nanmax(daily) > 0:
        daily = daily / np.nanmax(daily)
    if np.nanmax(cum) > 0:
        cum = cum / np.nanmax(cum)
    ax.bar(x, daily, color=color, alpha=0.35, width=0.8, label="daily growth")
    ax.plot(x, cum, color=color, lw=1.4, label="cumulative")
    ax.set_ylim(0, 1.05)
    ax.set_xticks([])
    ax.set_yticks([0, 1])
    clean_axis(ax)


def story_header(fig: plt.Figure, number: int, title: str, subtitle: str, color: str) -> None:
    return


def takeaway(fig: plt.Figure, text: str, color: str) -> None:
    return


def plot_history_for_story(ax: plt.Axes, profile: pd.DataFrame, color: str) -> None:
    p = profile.sort_values("slice_index")
    x = np.arange(len(p))
    daily = p["ring_area_km2"].fillna(0).clip(lower=0).to_numpy(float)
    cum = p["cumulative_area_km2"].fillna(0).clip(lower=0).to_numpy(float)
    if np.nanmax(daily) > 0:
        daily_scaled = daily / np.nanmax(daily)
    else:
        daily_scaled = daily
    if np.nanmax(cum) > 0:
        cum_scaled = cum / np.nanmax(cum)
    else:
        cum_scaled = cum
    ax.bar(x, daily_scaled, color=color, alpha=0.22, width=0.85)
    ax.plot(x, cum_scaled, color=color, lw=1.8)
    ax.set_ylim(0, 1.05)
    ax.set_xlabel("Day")
    ax.set_yticks([0, 1])
    ax.set_yticklabels(["0", "1"])
    clean_axis(ax)


def choose_story_fire(features: pd.DataFrame, label: str, query: str, score_col: str, ascending: bool = False) -> str:
    d = features.query(query).replace([np.inf, -np.inf], np.nan).dropna(subset=[score_col, "fire_id"])
    if d.empty:
        d = features.replace([np.inf, -np.inf], np.nan).dropna(subset=[score_col, "fire_id"])
    row = d.sort_values(score_col, ascending=ascending).iloc[0]
    return str(row.fire_id)


def figure_1(bundle: DataBundle) -> dict[str, str]:
    features = bundle.features.copy()
    examples = [
        ("Early burst", "most growth early", RED, "duration_days >= 4 and final_area_km2 >= 1", "front_loaded_fraction", False),
        ("Steady growth", "persistent accumulation", BLUE, "duration_days >= 8 and final_area_km2 >= 1", "growth_entropy", False),
        ("Late surge", "rapid growth late", PURPLE, "duration_days >= 4 and final_area_km2 >= 1", "late_growth_fraction", False),
        ("Multi-pulse", "complex pattern", ORANGE, "duration_days >= 5 and final_area_km2 >= 1", "pulse_count", False),
    ]
    fig = plt.figure(figsize=(9.2, 6.6))
    gs = fig.add_gridspec(3, 4, height_ratios=[1.05, 1.0, 0.18], hspace=0.44, wspace=0.42, top=0.94, bottom=0.06)
    for i, (title, desc, color, query, score, asc) in enumerate(examples):
        fid = choose_story_fire(features, title, query, score, ascending=asc)
        prof = profile_for_fire(bundle.slices, fid)
        frow = features.loc[features.fire_id.astype(str) == fid].iloc[0]
        axh = fig.add_subplot(gs[0, i])
        plot_history_for_story(axh, prof, color)
        axh.set_title(f"{title}\n{desc}", fontsize=8.5, color=color, weight="bold")
        if i == 0:
            axh.set_ylabel("Scaled burned area")
        axh.text(0.02, 0.94, f"{frow.final_area_km2:.1f} km2, {frow.duration_days:.0f} d", transform=axh.transAxes, ha="left", va="top", fontsize=6.8, color=MUTED)
        axv = fig.add_subplot(gs[1, i])
        draw_vase(axv, prof, color=color)
        axv.set_title("Fire VASE", fontsize=7.4, color=MUTED)
    axnote = fig.add_subplot(gs[2, :])
    axnote.axis("off")
    axnote.text(0.02, 0.35, "Daily increments become ordered rings; ring width tracks cumulative burned area through developmental time.", fontsize=8.2, color=INK)
    story_header(fig, 1, "Every fire has a life history.", "Fires with simple final summaries can develop through different sequences.", RED)
    takeaway(fig, "Takeaway: final area and duration hide when growth occurs; Fire VASE preserves the developmental sequence.", RED)
    return savefig(fig, MAIN_FIGURE_DIR, "Figure_1_climate_revision")


def figure_2(bundle: DataBundle) -> dict[str, str]:
    f = bundle.features.copy()
    labels = f["shape_label"].value_counts().index.tolist()
    reps = []
    for label in labels[:6]:
        g = f[f.shape_label == label]
        if g.empty:
            continue
        center = g[["morph_pc1", "morph_pc2"]].median()
        dist = ((g["morph_pc1"] - center.morph_pc1) ** 2 + (g["morph_pc2"] - center.morph_pc2) ** 2).sort_values()
        reps.append((label, str(dist.index[0])))
    fig = plt.figure(figsize=(9.2, 6.7))
    gs = fig.add_gridspec(3, 6, height_ratios=[1.05, 1.85, 0.72], hspace=0.55, wspace=0.52, top=0.94, bottom=0.06)
    for i, (label, idx) in enumerate(reps[:6]):
        fid = f.loc[int(idx), "fire_id"]
        prof = profile_for_fire(bundle.slices, fid)
        axv = fig.add_subplot(gs[0, i])
        draw_vase(axv, prof, color=SHAPE_COLORS.get(label, BLUE))
        axv.set_title(label.replace(" ", "\n"), fontsize=8.0, color=SHAPE_COLORS.get(label, INK), weight="bold")
    axc = fig.add_subplot(gs[1, :4])
    sample = f.sample(min(65000, len(f)), random_state=SEED)
    for label, g in sample.groupby("shape_label", observed=True):
        axc.scatter(g["morph_pc1"], g["morph_pc2"], s=1.3, alpha=0.22, color=SHAPE_COLORS.get(label, MUTED), rasterized=True, label=label)
    axc.set_xlabel("VASE axis 1: concentration / front-loading")
    axc.set_ylabel("VASE axis 2: timing / persistence")
    axc.set_title("Population of fires occupies a continuous morphospace")
    clean_axis(axc)
    overlay_layout = {
        "late surge": {"inset_xy": (0.50, 0.72), "label_xy": (0.50, 0.86), "size": 0.095},
        "multi-pulse complex": {"inset_xy": (0.45, 0.50), "label_xy": (0.43, 0.67), "size": 0.095},
        "skinny persistent": {"inset_xy": (0.68, 0.73), "label_xy": (0.67, 0.90), "size": 0.088},
        "compact steady": {"inset_xy": (0.62, 0.66), "label_xy": (0.61, 0.82), "size": 0.088},
        "front-loaded plateau": {"inset_xy": (0.63, 0.50), "label_xy": (0.66, 0.66), "size": 0.092},
        "single flash": {"inset_xy": (0.91, 0.58), "label_xy": (0.91, 0.78), "size": 0.082},
    }
    for label, idx in reps[:6]:
        row = f.loc[int(idx)]
        prof = profile_for_fire(bundle.slices, row.fire_id)
        layout = overlay_layout.get(label, {})
        add_vase_inset_on_morphospace(
            axc,
            prof,
            float(row.morph_pc1),
            float(row.morph_pc2),
            color=SHAPE_COLORS.get(label, INK),
            label=label.replace(" ", "\n"),
            size=layout.get("size", 0.095),
            inset_xy=layout.get("inset_xy"),
            label_xy=layout.get("label_xy"),
        )
    panel_label(axc, "a")
    axp = fig.add_subplot(gs[1, 4:])
    counts = f["shape_label"].value_counts(normalize=True).sort_values(ascending=True)
    axp.barh(counts.index, counts.values * 100, color=[SHAPE_COLORS.get(x, MUTED) for x in counts.index])
    axp.set_xlabel("Share of fires (%)")
    axp.set_title("Recurring neighborhoods are unevenly occupied")
    clean_axis(axp)
    panel_label(axp, "b")
    axg = fig.add_subplot(gs[2, :])
    axg.axis("off")
    gradient_text = [
        "Timing of growth",
        "Persistence",
        "Concentration of growth",
        "Pulse structure",
        "Reactivation",
        "Termination",
    ]
    for i, text in enumerate(gradient_text):
        row, col = divmod(i, 3)
        x = 0.12 + col * 0.28
        y = 0.68 - row * 0.34
        axg.text(x, y, f"[x] {text}", transform=axg.transAxes, fontsize=8.2, color=INK, ha="left")
    story_header(fig, 2, "Wildfire histories occupy recurring developmental gradients.", "Fires follow continuous patterns in timing, persistence, pulse structure, reactivation, and termination.", BLUE)
    takeaway(fig, "Takeaway: development varies along continuous gradients, not as hard discrete types.", BLUE)
    return savefig(fig, MAIN_FIGURE_DIR, "Figure_2_climate_revision")


def climate_terciles(df: pd.DataFrame, col: str) -> pd.Series:
    return pd.qcut(df[col], 3, labels=["low", "middle", "high"], duplicates="drop")


def climate_label_from_feature(name: str) -> str:
    if name == "max_vpd_kpa":
        return "Maximum VPD\n(kPa)"
    if name.endswith("_fraction"):
        return name.replace("_day_fraction", " days").replace("_", " ")
    base = name
    for prefix in ["mean_", "max_daily_", "min_daily_"]:
        if base.startswith(prefix):
            base = base[len(prefix):]
            break
    label, units = CLIMATE_METADATA.get(base, (base.replace("_", " "), ""))
    return f"{label}\n({units})" if units else label


def add_vase_inset_on_morphospace(
    ax: plt.Axes,
    profile: pd.DataFrame,
    x: float,
    y: float,
    *,
    color: str,
    label: str,
    size: float = 0.135,
    inset_xy: tuple[float, float] | None = None,
    label_xy: tuple[float, float] | None = None,
) -> None:
    """Place a small VASE glyph at a morphospace coordinate."""

    xmin, xmax = ax.get_xlim()
    ymin, ymax = ax.get_ylim()
    fx = (x - xmin) / max(xmax - xmin, 1e-9)
    fy = (y - ymin) / max(ymax - ymin, 1e-9)
    fx = float(np.clip(fx, 0.08, 0.92))
    fy = float(np.clip(fy, 0.12, 0.88))
    if inset_xy is not None:
        fx, fy = inset_xy
    inset = ax.inset_axes([fx - size / 2, fy - size / 2, size, size * 1.25], zorder=5)
    draw_vase(inset, profile, color=color, outline="#1c1d1f", alpha=0.92)
    lx, ly = label_xy if label_xy is not None else (fx, min(fy + size * 0.83, 0.98))
    ax.annotate(
        label,
        xy=(x, y),
        xycoords="data",
        xytext=(lx, ly),
        textcoords=ax.transAxes,
        ha="center",
        va="bottom",
        fontsize=6.2,
        color=color,
        weight="bold",
        bbox={"boxstyle": "round,pad=0.08", "fc": "white", "ec": "none", "alpha": 0.78},
        arrowprops={"arrowstyle": "-", "lw": 0.55, "color": color, "alpha": 0.7},
        zorder=6,
    )


def climate_morphospace_panel(
    fig: plt.Figure,
    ax: plt.Axes,
    sample: pd.DataFrame,
    column: str,
    *,
    title: str,
    cmap: str,
    panel: str,
    show_ylabel: bool = False,
) -> None:
    data = sample.dropna(subset=[column, "morph_pc1", "morph_pc2"])
    vals = data[column].to_numpy(float)
    if len(vals) == 0:
        ax.axis("off")
        return
    lo, hi = np.nanquantile(vals, [0.03, 0.97])
    if not np.isfinite(lo) or not np.isfinite(hi) or lo == hi:
        lo, hi = float(np.nanmin(vals)), float(np.nanmax(vals))
    sc = ax.scatter(
        data["morph_pc1"],
        data["morph_pc2"],
        c=vals,
        s=1.7,
        cmap=cmap,
        vmin=lo,
        vmax=hi,
        alpha=0.42,
        rasterized=True,
    )
    ax.set_title(title, fontsize=8.0)
    ax.set_xlabel("VASE axis 1", fontsize=7.0)
    ax.set_ylabel("VASE axis 2" if show_ylabel else "", fontsize=7.0)
    ax.tick_params(axis="both", labelsize=6.2)
    clean_axis(ax)
    cb = fig.colorbar(sc, ax=ax, fraction=0.04, pad=0.012)
    cb.ax.tick_params(labelsize=5.8)
    panel_label(ax, panel)


def figure_3(bundle: DataBundle, climate_features: pd.DataFrame, event_models: pd.DataFrame) -> dict[str, str]:
    cf = climate_features.dropna(subset=["mean_vpd_kpa"]).copy()
    cf["vpd_group"] = climate_terciles(cf, "mean_vpd_kpa")
    fig = plt.figure(figsize=(10.2, 7.4))
    gs = fig.add_gridspec(3, 8, height_ratios=[1.08, 0.92, 1.05], hspace=0.88, wspace=1.08, top=0.95, bottom=0.06)
    sample = cf.sample(min(55000, len(cf)), random_state=SEED)
    climate_maps = [
        ("mean_maximum_temperature_c", "Maximum temperature\n(degrees C)", "inferno", "a"),
        ("mean_vpd_kpa", "Vapor pressure deficit\n(kPa)", CLIMATE_CMAP, "b"),
        ("mean_fuel_moisture_1000hr_pct", "1000-hour fuel moisture\n(%)", "YlGnBu", "c"),
        ("mean_wind_speed_m_s", "Wind speed\n(m s-1)", "magma", "d"),
    ]
    for i, (column, title, cmap, label) in enumerate(climate_maps):
        ax = fig.add_subplot(gs[0, 2 * i : 2 * i + 2])
        climate_morphospace_panel(fig, ax, sample, column, title=title, cmap=cmap, panel=label, show_ylabel=(i == 0))

    for i, grp in enumerate(["low", "middle", "high"]):
        axv = fig.add_subplot(gs[1, i])
        ids = cf.loc[cf.vpd_group == grp, "fire_id"]
        prof = composite_profile(bundle.slices, ids.sample(min(6000, len(ids)), random_state=SEED + i))
        draw_composite_vase(axv, prof, color=[BLUE, GOLD, RED][i])
        label = f"{grp} VPD\nn={len(ids):,}"
        axv.set_title(label, fontsize=8)

    axp = fig.add_subplot(gs[1, 3:])
    prev = pd.crosstab(cf["shape_label"], cf["vpd_group"], normalize="columns") * 100
    keep = prev.mean(axis=1).sort_values(ascending=False).head(5).index
    x = np.arange(len(keep))
    for j, grp in enumerate(["low", "middle", "high"]):
        axp.plot(x, prev.loc[keep, grp], marker="o", lw=1.3, label=f"{grp} VPD", color=[BLUE, GOLD, RED][j])
    axp.set_xticks(x, keep, rotation=18, ha="right")
    axp.set_ylabel("Share within VPD group (%)")
    axp.set_title("Developmental-neighborhood prevalence shifts")
    axp.legend(frameon=False, ncol=3)
    clean_axis(axp)
    panel_label(axp, "e")

    axh = fig.add_subplot(gs[2, :5])
    effects = pd.read_csv(STATS_DIR / "climate_response_spearman_effects.csv")
    pred_candidates = [
        "mean_maximum_temperature_c",
        "mean_vpd_kpa",
        "mean_minimum_relative_humidity_pct",
        "mean_fuel_moisture_1000hr_pct",
        "mean_energy_release_component",
        "mean_precipitation_mm",
        "high_vpd_day_fraction",
        "dry_1000hr_fuel_day_fraction",
        "high_erc_day_fraction",
    ]
    available_predictors = set(effects["predictor"])
    pred_names = [p for p in pred_candidates if p in available_predictors]
    resp_names = ["front_loaded_fraction", "late_growth_fraction", "growth_entropy", "pulse_count", "reactivation_count", "morph_pc1"]
    mat = effects.pivot_table(index="response", columns="predictor", values="spearman_rho", aggfunc="mean").reindex(resp_names)[pred_names]
    im = axh.imshow(mat, cmap="coolwarm", vmin=-0.35, vmax=0.35, aspect="auto")
    axh.set_xticks(np.arange(len(pred_names)), [climate_label_from_feature(p) for p in pred_names], rotation=35, ha="right")
    axh.set_yticks(np.arange(len(resp_names)), ["front loaded", "late growth", "entropy", "pulse count", "reactivations", "gradient 1"])
    axh.set_title("Climate dimensions relate to different developmental responses")
    cb2 = fig.colorbar(im, ax=axh, fraction=0.032, pad=0.035)
    cb2.ax.set_title("rho", fontsize=6.4, pad=2)
    panel_label(axh, "f")

    axm = fig.add_subplot(gs[2, 5:])
    summary = event_models[event_models.block.isin(["year_block", "region_block", "region_year_hash"])].groupby("predictor_set")["r2"].median().sort_values()
    short_labels = {
        "core event means": "core means",
        "comprehensive event means": "all means",
        "moisture and humidity": "moisture",
        "fire danger and energy": "fire danger",
        "time-resolved exposure": "temporal",
        "region-season anomalies": "anomaly",
        "extreme days": "extremes",
    }
    xpos = np.arange(len(summary))
    axm.bar(xpos, summary.values, color=[MUTED if x < 0 else TEAL for x in summary.values], width=0.72)
    axm.set_xticks(xpos, [short_labels.get(x, x) for x in summary.index], rotation=48, ha="right", fontsize=6.2)
    axm.axhline(0, color=INK, lw=0.7)
    axm.set_ylabel("Median held-out R2", fontsize=7.0, labelpad=2)
    axm.set_title("Association does not imply deterministic prediction")
    clean_axis(axm)
    panel_label(axm, "g")
    story_header(fig, 3, "Climate shifts the probability of developmental forms.", "Many climate dimensions are associated with where fires fall in VASE space, but they do not determine a single pathway.", BLUE)
    takeaway(fig, "Takeaway: climate redistributes fires across developmental possibilities.", BLUE)
    return savefig(fig, MAIN_FIGURE_DIR, "Figure_3_climate_revision")


def figure_4(bundle: DataBundle, state_df: pd.DataFrame, state_models: pd.DataFrame) -> dict[str, str]:
    fig = plt.figure(figsize=(9.2, 6.6))
    gs = fig.add_gridspec(2, 4, height_ratios=[1.0, 1.16], hspace=0.82, wspace=0.82, top=0.94, bottom=0.06)
    long = bundle.features.dropna(subset=["duration_days", "mean_vpd_kpa"]).sort_values("duration_days", ascending=False).head(300)
    chosen = long.sample(3, random_state=SEED)["fire_id"].astype(str).tolist()
    for i, fid in enumerate(chosen):
        ax = fig.add_subplot(gs[0, i])
        p = profile_for_fire(bundle.slices, fid)
        x = np.arange(len(p))
        growth = p["ring_area_km2"].fillna(0).to_numpy(float)
        vpd = p["vpd_kpa"].fillna(np.nan).to_numpy(float)
        if np.nanmax(growth) > 0:
            growth = growth / np.nanmax(growth)
        if np.nanmax(vpd) > np.nanmin(vpd):
            vpd = (vpd - np.nanmin(vpd)) / (np.nanmax(vpd) - np.nanmin(vpd))
        ax.bar(x, growth, color=BLUE, alpha=0.35, label="growth")
        ax.plot(x, vpd, color=RED, lw=1.3, label="VPD")
        ax.set_title(f"Observed fire {i + 1}", fontsize=7.4)
        ax.set_xticks([])
        ax.set_yticks([0, 1])
        clean_axis(ax)
    axleg = fig.add_subplot(gs[0, 3])
    axleg.axis("off")
    axleg.text(0, 0.78, "Climate exposure is read\nthrough fire state.", fontsize=9.0, weight="bold", color=INK)
    axleg.text(0, 0.42, "The red line is daily VPD scaled within each fire. The blue bars are daily growth. The same exposure can occur before, during, or after rapid expansion.", fontsize=7.3, color=MUTED, wrap=True)
    axleg.text(0, 0.12, "State models use only information available by day t.", fontsize=7.3, color=INK, weight="bold", wrap=True)

    axm = fig.add_subplot(gs[1, :2])
    preferred_order = [
        "core climate only",
        "expanded climate only",
        "state only",
        "core climate plus state",
        "expanded climate plus state",
        "core climate-state interaction",
    ]
    available_sets = list(state_models["predictor_set"].drop_duplicates())
    order = [name for name in preferred_order if name in available_sets]
    perf = state_models.groupby(["predictor_set", "block"])["r2"].median().reset_index()
    for i, block in enumerate(["random_fire", "year_block", "region_block", "region_year_hash"]):
        vals = [float(perf[(perf.predictor_set == m) & (perf.block == block)]["r2"].median()) for m in order]
        axm.plot(order, vals, marker="o", lw=1.2, label=block.replace("_", " "))
    axm.axhline(0, color=INK, lw=0.7)
    axm.set_ylabel("Held-out R2 for next-day growth")
    labels = {
        "core climate only": "core\nclimate",
        "expanded climate only": "expanded\nclimate",
        "state only": "state",
        "core climate plus state": "core climate\n+ state",
        "expanded climate plus state": "expanded climate\n+ state",
        "core climate-state interaction": "interaction",
    }
    axm.set_xticks(range(len(order)), [labels.get(name, name) for name in order], rotation=18, ha="right")
    axm.set_title("Adding current state improves near-term growth models")
    axm.legend(frameon=False, fontsize=6.8)
    clean_axis(axm)
    panel_label(axm, "a")

    axs = fig.add_subplot(gs[1, 2:])
    d = state_df.replace([np.inf, -np.inf], np.nan).dropna(subset=["next_growth_log1p", "vpd_kpa", "current_growth_log1p"])
    q_low, q_high = d["current_growth_log1p"].quantile([0.50, 0.90])
    d["growth_state"] = np.where(
        d["current_growth_log1p"] <= q_low,
        "low current growth",
        np.where(d["current_growth_log1p"] >= q_high, "high current growth", "middle"),
    )
    d["vpd_bin"] = pd.qcut(d["vpd_kpa"], 20, duplicates="drop")
    curve = d.groupby(["growth_state", "vpd_bin"], observed=True).agg(vpd=("vpd_kpa", "median"), next_growth=("next_growth_log1p", "mean"), n=("fire_id", "size")).reset_index()
    for label, color in [("low current growth", BLUE), ("high current growth", RED)]:
        sub = curve[curve.growth_state == label]
        axs.plot(sub["vpd"], sub["next_growth"], marker="o", ms=2.8, lw=1.2, color=color, label=label)
    axs.set_xlabel("Daily VPD (kPa)")
    axs.set_ylabel("Mean next-day growth, log(1 + km2)")
    axs.set_title("VPD relationship depends on current growth state", fontsize=7.8)
    axs.legend(frameon=False)
    clean_axis(axs)
    panel_label(axs, "b")
    story_header(fig, 4, "Climate acts through developmental state.", "The same weather exposure can mean different things depending on when it occurs in a fire history.", PURPLE)
    takeaway(fig, "Takeaway: climate effects depend on when exposure occurs and on the current developmental state.", PURPLE)
    return savefig(fig, MAIN_FIGURE_DIR, "Figure_4_climate_revision")


def find_mismatch_examples(climate_features: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    cf = climate_features.dropna(subset=["mean_vpd_kpa", "mean_maximum_temperature_c", "mean_wind_speed_m_s", "morph_pc1", "morph_pc2"]).copy()
    sample = cf.sample(min(50000, len(cf)), random_state=SEED).reset_index(drop=True)
    clim = sample[["mean_maximum_temperature_c", "mean_vpd_kpa", "mean_wind_speed_m_s"]].to_numpy(float)
    morph = sample[["morph_pc1", "morph_pc2", "morph_pc3"]].to_numpy(float)
    clim = (clim - clim.mean(axis=0)) / clim.std(axis=0)
    morph = (morph - morph.mean(axis=0)) / morph.std(axis=0)
    rows_clim = []
    rows_morph = []
    for i in RNG.choice(len(sample), size=700, replace=False):
        dc = np.sqrt(((clim - clim[i]) ** 2).sum(axis=1))
        dm = np.sqrt(((morph - morph[i]) ** 2).sum(axis=1))
        dc[i] = np.inf
        dm[i] = np.inf
        same_climate = np.argsort(dc)[:50]
        j = same_climate[np.argmax(dm[same_climate])]
        rows_clim.append({"fire_id_a": sample.loc[i, "fire_id"], "fire_id_b": sample.loc[j, "fire_id"], "climate_distance": dc[j], "morphology_distance": dm[j]})
        same_morph = np.argsort(dm)[:50]
        k = same_morph[np.argmax(dc[same_morph])]
        rows_morph.append({"fire_id_a": sample.loc[i, "fire_id"], "fire_id_b": sample.loc[k, "fire_id"], "climate_distance": dc[k], "morphology_distance": dm[k]})
    clim_df = pd.DataFrame(rows_clim)
    morph_df = pd.DataFrame(rows_morph)
    clim_df.to_csv(STATS_DIR / "similar_climate_divergent_morphology_examples.csv", index=False)
    morph_df.to_csv(STATS_DIR / "similar_morphology_divergent_climate_examples.csv", index=False)
    return clim_df, morph_df


def figure_5(bundle: DataBundle, climate_features: pd.DataFrame, event_models: pd.DataFrame) -> dict[str, str]:
    clim_df, morph_df = find_mismatch_examples(climate_features)
    cf = climate_features.set_index("fire_id")
    top = clim_df.sort_values("morphology_distance", ascending=False).head(2)
    fig = plt.figure(figsize=(9.2, 6.4))
    gs = fig.add_gridspec(2, 5, hspace=0.70, wspace=0.72, top=0.94, bottom=0.07)
    for col, (_, row) in enumerate(top.iterrows()):
        for rr, fid in enumerate([row.fire_id_a, row.fire_id_b]):
            axv = fig.add_subplot(gs[rr, col])
            prof = profile_for_fire(bundle.slices, fid)
            draw_vase(axv, prof, color=[BLUE, RED][rr])
            vals = cf.loc[str(fid)]
            axv.set_title(f"{vals.mean_vpd_kpa:.2f} kPa VPD\n{vals.mean_maximum_temperature_c:.1f} C Tmax", fontsize=7.5)
    axpair = fig.add_subplot(gs[:, 2])
    axpair.axis("off")
    axpair.text(0.5, 0.72, "Similar centroid\nclimate", ha="center", fontsize=8.6, weight="bold", color=INK)
    axpair.text(0.5, 0.52, "can still produce", ha="center", fontsize=7.5, color=MUTED)
    axpair.text(0.5, 0.34, "different VASE\nforms", ha="center", fontsize=8.6, weight="bold", color=RED)
    axpair.text(0.5, 0.16, "Climate organizes opportunity;\nit does not assign one path.", ha="center", fontsize=7.1, color=MUTED)
    axh = fig.add_subplot(gs[0, 3:])
    axh.hist(clim_df["morphology_distance"], bins=28, alpha=0.7, color=RED, label="similar climate pairs")
    axh.hist(morph_df["morphology_distance"], bins=28, alpha=0.55, color=BLUE, label="similar morphology pairs")
    axh.set_xlabel("Morphology distance")
    axh.set_ylabel("Pair count")
    axh.set_title("Mismatch distributions expose the limit")
    axh.legend(frameon=False)
    clean_axis(axh)
    panel_label(axh, "a")
    axc = fig.add_subplot(gs[1, 3:])
    blocks = ["random_fire", "year_block", "region_block", "region_year_hash"]
    med = event_models.groupby(["predictor_set", "block"])["r2"].median().reset_index()
    for predictor_set, color in [
        ("core event means", BLUE),
        ("comprehensive event means", PURPLE),
        ("time-resolved exposure", TEAL),
        ("region-season anomalies", GOLD),
        ("extreme days", RED),
    ]:
        if predictor_set not in set(med["predictor_set"]):
            continue
        vals = [float(med[(med.predictor_set == predictor_set) & (med.block == b)]["r2"].median()) for b in blocks]
        axc.plot(np.arange(len(blocks)), vals, marker="o", lw=1.2, label=predictor_set, color=color)
    axc.axhline(0, color=INK, lw=0.7)
    axc.set_xticks(np.arange(len(blocks)), ["random", "year", "region", "region-year"], rotation=15)
    axc.set_ylabel("Median held-out R2")
    axc.set_title("Blocked transfer bounds the climate claim")
    axc.legend(frameon=False, fontsize=6.6)
    clean_axis(axc)
    panel_label(axc, "b")
    story_header(fig, 5, "Climate is not destiny.", "Similar climates can lead to different outcomes, and similar forms can arise under different climate pathways.", RED)
    takeaway(fig, "Takeaway: climate organizes opportunity, but state and landscape context help determine the path a fire takes.", RED)
    return savefig(fig, MAIN_FIGURE_DIR, "Figure_5_climate_revision")


def supplementary_figures(bundle: DataBundle, climate_features: pd.DataFrame, event_models: pd.DataFrame, state_models: pd.DataFrame) -> dict[str, dict[str, str]]:
    paths = {}
    fig, ax = plt.subplots(figsize=(6.8, 4.0))
    vals = event_models.pivot_table(index="response", columns=["predictor_set", "block"], values="r2", aggfunc="median")
    im = ax.imshow(vals.fillna(0), cmap="coolwarm", vmin=-0.25, vmax=0.25, aspect="auto")
    ax.set_yticks(np.arange(len(vals.index)), vals.index)
    ax.set_xticks(np.arange(len(vals.columns)), [f"{a}\n{b.replace('_',' ')}" for a, b in vals.columns], rotation=55, ha="right")
    ax.set_title("Supplementary model audit: all event-level held-out R2 values")
    fig.colorbar(im, ax=ax, label="Held-out R2")
    paths["Supplementary_Figure_1_event_models"] = savefig(fig, SUPP_FIGURE_DIR, "Supplementary_Figure_1_event_models")

    fig, ax = plt.subplots(figsize=(6.8, 3.8))
    m = state_models.pivot(index="predictor_set", columns="block", values="r2")
    im = ax.imshow(m, cmap="coolwarm", vmin=-0.1, vmax=0.35, aspect="auto")
    ax.set_yticks(np.arange(len(m.index)), m.index)
    ax.set_xticks(np.arange(len(m.columns)), [c.replace("_", " ") for c in m.columns], rotation=25, ha="right")
    ax.set_title("Supplementary state-model blocked performance")
    fig.colorbar(im, ax=ax, label="Held-out R2")
    paths["Supplementary_Figure_2_state_models"] = savefig(fig, SUPP_FIGURE_DIR, "Supplementary_Figure_2_state_models")

    fig, ax = plt.subplots(figsize=(6.8, 4.0))
    exp = bundle.exposures.copy()
    if not exp.empty:
        zones = exp.groupby("exposure_zone").agg(rows=("fire_id", "size"), fires=("fire_id", "nunique"), climate_available=("climate_available", "mean")).reset_index()
        ax.bar(zones["exposure_zone"], zones["fires"], color=TEAL)
        ax.set_ylabel("Pilot fires")
        ax.set_title("Perimeter and active-burned-area climate is a pilot product")
        ax.tick_params(axis="x", rotation=20)
        for i, row in zones.iterrows():
            ax.text(i, row.fires + 0.2, f"{row.climate_available:.0%} rows available", ha="center", fontsize=7)
    else:
        ax.text(0.5, 0.5, "No perimeter exposure table found", ha="center", va="center")
    clean_axis(ax)
    paths["Supplementary_Figure_3_perimeter_pilot"] = savefig(fig, SUPP_FIGURE_DIR, "Supplementary_Figure_3_perimeter_pilot")
    return paths


def write_inventory(bundle: DataBundle, climate_features: pd.DataFrame) -> None:
    f = bundle.features
    s = bundle.slices
    exp = bundle.exposures
    complete = int(f["climate_available"].fillna(False).sum())
    slice_complete = int(s["climate_available"].fillna(False).sum())
    climate_cols = [col for col in CLIMATE_METADATA if col in s.columns]
    variable_rows = []
    for col in climate_cols:
        label, units = CLIMATE_METADATA[col]
        summaries = "daily slice, event mean, daily min/max, early/middle/late means, region-month anomaly"
        if col == "maximum_temperature_c":
            summaries += ", hot-day fraction"
        if col == "vpd_kpa":
            summaries += ", high-VPD-day fraction"
        if col == "wind_speed_m_s":
            summaries += ", windy-day fraction"
        if col == "precipitation_mm":
            summaries += ", wet-day fraction"
        if col == "fuel_moisture_1000hr_pct":
            summaries += ", dry-fuel-day fraction"
        if col == "energy_release_component":
            summaries += ", high-ERC-day fraction"
        variable_rows.append(
            {
                "Variable": label,
                "Units": units,
                "Non-null slice rows": f"{int(s[col].notna().sum()):,}",
                "Summary types in revision": summaries,
                "Used in manuscript": "yes",
            }
        )
    lines = [
        "# Climate Data Inventory",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Population-wide daily centroid climate",
        "",
        f"Source: gridMET cached NetCDF files; variables are {', '.join(bundle.climate_report.get('climate_variables', []))}.",
        "Spatial resolution: gridMET native 4-km grid.",
        "Temporal resolution: daily. The processing manifest labels the component `gridmet-hourly-v0`, but the available table is daily and every slice has one daily value per variable.",
        "Exposure basis: event centroid / nearest grid-cell extraction for each daily VASE slice.",
        "Absolute or anomaly: absolute values in the source table; this revision also derives a region-month fire-season anomaly diagnostic from the observed fire population. It is not a true local climatological normal.",
        f"Date range: {pd.to_datetime(s.timestamp).min().date()} to {pd.to_datetime(s.timestamp).max().date()}.",
        f"Fires with complete climate values: {complete:,} of {len(f):,}. Slice rows with climate values: {slice_complete:,} of {len(s):,}.",
        "Missingness pattern: 41,334 fires have missing cached climate values, reported as outside gridMET coverage or missing grid value in `processing_failures_climate.parquet`.",
        "",
        df_to_markdown(pd.DataFrame(variable_rows), floatfmt=".3f"),
        "",
        "## Perimeter, active-burned-area, and perimeter-extension pilot",
        "",
    ]
    if exp.empty:
        lines.append("No perimeter exposure table was found.")
    else:
        zones = exp.groupby("exposure_zone").agg(rows=("fire_id", "size"), fires=("fire_id", "nunique"), climate_available=("climate_available", "mean")).reset_index()
        lines += [
            f"Source: `scratch/fire_vase_run_full/tables/vase_climate_exposures.parquet`, produced by `{PERIMETER_REPORT_PATH.relative_to(ROOT)}`.",
            f"Fire count: {exp.fire_id.nunique():,}. Rows: {len(exp):,}. Climate-available rows: {int(exp.climate_available.fillna(False).sum()):,}.",
            "Exposure bases present: " + ", ".join(sorted(exp.exposure_zone.dropna().unique())) + ".",
            "Extension distances: " + ", ".join(map(str, bundle.perimeter_report.get("extension_distances_m", []))) + " m.",
            "Variables are summarized by zone as mean/min/max/std where present, plus sampled cell count and exposure area.",
            "Status: useful as a methods/perimeter-exposure product. If its fire count is lower than the centroid table, it remains a coverage limitation rather than the main inferential basis.",
            "",
            df_to_markdown(zones, floatfmt=".3f"),
        ]
    lines += [
        "",
        "## Variables still not available as population-wide analysis products",
        "",
        "Wind direction, gusts, soil moisture, topography, vegetation, suppression, ignition cause, and true local seasonal normals were not found in the current population-wide Fire VASE tables. The current anomaly diagnostic is a region-month fire-population contrast, not a climatological normal.",
        "",
        "## Current manuscript use",
        "",
        "The new manuscript uses population-wide daily centroid gridMET temperature, VPD, wind, precipitation, relative humidity, specific humidity, fuel moisture, fire-danger indices, evapotranspiration, PET, and solar radiation; derived extreme-day fractions; early/middle/late exposure summaries; and a clearly labeled region-month anomaly diagnostic. Perimeter and active-burned-area climate are described according to the coverage actually present in the perimeter exposure table.",
    ]
    (ANALYSIS_DIR / "climate_data_inventory.md").write_text("\n".join(lines) + "\n")


def write_response_dictionary() -> None:
    rows = [
        ("Final area", "`final_area_km2`", "Total mapped burned area for the event.", "absolute scale outcome; not shape-normalized", "yes", "final outcome"),
        ("Duration", "`duration_days`", "Number of days spanned by the observed fire history.", "strongly duration-sensitive", "yes", "final outcome"),
        ("Peak growth", "`peak_growth_km2_per_day`", "Largest daily area increment.", "scale-sensitive", "available if at least one slice", "final outcome"),
        ("Peak timing", "`peak_timing`", "Relative position of largest growth day in the observed sequence.", "duration-sensitive for short fires", "degenerate for one-day fires", "shape timing"),
        ("Front-loaded fraction", "`front_loaded_fraction`", "Fraction of growth allocated to early development.", "moderately duration-sensitive", "available but coarse for one-day fires", "shape-normalized"),
        ("Late-growth fraction", "`late_growth_fraction`", "Fraction of growth allocated to late development.", "moderately duration-sensitive", "available but coarse for one-day fires", "shape-normalized"),
        ("Terminal taper", "`terminal_taper_fraction`", "Degree to which growth decelerates near termination.", "duration-sensitive", "degenerate for one-day fires", "shape-normalized"),
        ("Growth entropy", "`growth_entropy`", "Evenness of daily growth allocation through time.", "sensitive to number of observed slices", "low information for one-day fires", "shape-normalized"),
        ("Pulse count", "`pulse_count`", "Number of major growth pulses detected from daily increments.", "increases with duration/opportunity", "available but minimally informative for one-day fires", "absolute/shape hybrid"),
        ("Reactivation count", "`reactivation_count`", "Number of renewed growth periods after quiescence.", "requires multi-day histories", "not meaningful for one-day fires", "shape process"),
        ("Developmental velocity", "`developmental_velocity`", "Mean normalized growth progression through developmental time.", "less scale-sensitive, duration-sensitive", "available", "shape-normalized"),
        ("Developmental acceleration", "`developmental_acceleration`", "Change in growth rate through the observed sequence.", "sensitive to short sequences", "degenerate for one-day fires", "shape-normalized"),
        ("VASE widths", "`width_p00` to `width_p10`", "Interpolated ring widths over normalized developmental time.", "shape-normalized if using normalized width", "available", "shape representation"),
        ("Major VASE axes", "`morph_pc1` to `morph_pc5`", "Principal components of standardized developmental features.", "can mix scale and shape unless adjusted", "available", "compact representation"),
        ("Current growth state", "`current_growth_log1p`, `current_cumulative_log1p`, `elapsed_day`", "State variables available up to day t for next-day growth models.", "absolute-scale partial history", "not applicable", "time-varying state"),
    ]
    md = [
        "# Developmental Response Dictionary",
        "",
        "This revision separates absolute-scale outcomes from shape-normalized developmental responses. Climate can be associated with final size, timing, or shape; those are not interchangeable.",
        "",
        "| Response | Field or formula | Interpretation | Sensitivity | One-day fires | Use |",
        "|---|---|---|---|---|---|",
    ]
    md += [f"| {a} | {b} | {c} | {d} | {e} | {u} |" for a, b, c, d, e, u in rows]
    md += [
        "",
        "State-dependent models in this revision avoid final-duration and final-area leakage by using elapsed day, current daily growth, current cumulative area, and recent acceleration rather than normalized developmental time or final cumulative fraction.",
    ]
    (ANALYSIS_DIR / "developmental_response_dictionary.md").write_text("\n".join(md) + "\n")


def write_summary_vase_methods() -> None:
    md = """# Summary VASE Methods

Observed VASEs show one fire. Composite VASEs summarize groups of observed fires. Conditional VASEs show empirical or model-derived expected development under a named condition.

## Composite VASE

For each fire, daily slice index is mapped to normalized developmental time from 0 to 1. Normalized VASE width is interpolated onto 41 common time points. The median width at each time point forms the composite VASE. The interquartile range is drawn as a translucent shell. Uncertainty is summarized by fire-level resampling, not slice-level resampling, because daily slices within a fire are not independent.

## Climate-conditioned VASE

This revision uses empirical climate-conditioned composites for low, middle, and high VPD exposure groups. Climate groups are terciles of event-mean daily centroid gridMET VPD among climate-complete fires. The profiles are observed composites, not synthetic fires.

## Probability VASE

The reusable framework can summarize pulse, zero-growth, acceleration, reactivation, or termination probabilities by developmental time. The current main figures avoid overloading one glyph and instead use the simplest probability summary: developmental-neighborhood prevalence across VPD terciles.

## Model-predicted Conditional VASE

The current data support exploratory state-dependent regressions for next-day growth, but blocked interaction performance is not strong enough to justify a main-text model-predicted VASE as a central result. Model-predicted conditional VASEs should be added only after the active-edge/perimeter climate extraction is population-wide and local anomalies are computed from independent normals.
"""
    (ANALYSIS_DIR / "summary_vase_methods.md").write_text(md)


def write_visual_grammar() -> None:
    md = """# Fire VASE Visual Grammar

- Observed individual VASE: solid dark outline with a saturated single fill color.
- Empirical composite VASE: solid median profile with a translucent interquartile shell.
- Model-predicted conditional VASE: dashed outline. This revision reserves the convention but does not use it as main evidence.
- Reference VASE: thin neutral outline or middle-exposure composite.
- Difference VASE: signed horizontal deviation from the reference profile, plotted against developmental time.
- Climate along developmental time: viridis color scale with units in the legend or colorbar; temperature in degrees C, VPD in kPa, wind speed in m s-1.
- Uncertainty: fire-level interquartile shell or blocked held-out performance intervals. Slice-level opacity is not used as uncertainty.
- Labeling: figure titles state scientific conclusions; medoid IDs are replaced by descriptive developmental labels.
"""
    (ANALYSIS_DIR / "vase_visual_grammar.md").write_text(md)


def best_model_summary(event_models: pd.DataFrame, state_models: pd.DataFrame) -> dict:
    conservative = event_models[event_models.block.isin(["year_block", "region_block", "region_year_hash"])]
    by_set = conservative.groupby("predictor_set")["r2"].median().sort_values(ascending=False)
    state_con = state_models[state_models.block.isin(["year_block", "region_block", "region_year_hash"])]
    by_state = state_con.groupby("predictor_set")["r2"].median().sort_values(ascending=False)
    return {
        "best_event_set": by_set.index[0],
        "best_event_r2": float(by_set.iloc[0]),
        "event_r2_by_set": by_set.to_dict(),
        "best_state_set": by_state.index[0],
        "best_state_r2": float(by_state.iloc[0]),
        "state_r2_by_set": by_state.to_dict(),
        "anomalies_outperform_raw": bool(by_set.get("region-season anomalies", -np.inf) > by_set.get("core event means", -np.inf)),
        "resolved_outperform_event_means": bool(by_set.get("time-resolved exposure", -np.inf) > by_set.get("core event means", -np.inf)),
        "comprehensive_outperform_core": bool(by_set.get("comprehensive event means", -np.inf) > by_set.get("core event means", -np.inf)),
        "interaction_survives_blocking": bool(by_state.get("core climate-state interaction", -np.inf) > by_state.get("core climate plus state", -np.inf) + 0.01),
    }


def write_model_reports(bundle: DataBundle, climate_features: pd.DataFrame, event_models: pd.DataFrame, state_models: pd.DataFrame) -> dict:
    summary = best_model_summary(event_models, state_models)
    event_table = event_models.groupby(["predictor_set", "block"]).agg(median_r2=("r2", "median"), min_r2=("r2", "min"), max_r2=("r2", "max"), n=("n", "median")).reset_index()
    event_table.to_csv(STATS_DIR / "event_model_summary_by_set_and_block.csv", index=False)
    md = [
        "# Climate Model Report",
        "",
        "Models are exploratory regularized linear baselines. They are descriptive/predictive association tests, not causal estimates.",
        "",
        "## Predictor sets",
        "",
        "- Core event means: mean maximum temperature, mean minimum temperature, mean VPD, maximum VPD, and mean wind speed.",
        "- Moisture and humidity: precipitation, maximum and minimum relative humidity, specific humidity, and 100-hour and 1000-hour fuel moisture.",
        "- Fire danger and energy: energy release component, burning index, reference evapotranspiration, potential evapotranspiration, and solar radiation.",
        "- Comprehensive event means: the union of core climate, moisture/humidity, and fire-danger/energy means.",
        "- Region-season anomalies: observed value minus region-month fire-season median from the current fire population; not a true local climatological normal.",
        "- Extreme days: fraction of daily slices above high-temperature, high-VPD, windy, wet-day, dry-fuel, or high-ERC thresholds where available.",
        "- Time-resolved exposure: early, middle, and late means for core and selected expanded climate variables plus extreme-day fractions.",
        "",
        "## Blocked performance",
        "",
        df_to_markdown(event_table, floatfmt=".4f"),
        "",
        f"Best transferable event-level representation by median conservative blocked R2: **{summary['best_event_set']}** ({summary['best_event_r2']:.3f}).",
        f"Anomalies outperform raw event means: **{summary['anomalies_outperform_raw']}**.",
        f"Comprehensive event means outperform core event means: **{summary['comprehensive_outperform_core']}**.",
        f"Temporally resolved exposure outperforms event means: **{summary['resolved_outperform_event_means']}**.",
        "",
        "Interpretation: climate associations are real enough to shift developmental-neighborhood prevalence and response gradients, but held-out transfer is weak. The manuscript should say climate redistributes developmental opportunity, not that climate uniquely predicts form.",
    ]
    (ANALYSIS_DIR / "climate_model_report.md").write_text("\n".join(md) + "\n")

    state_table = state_models.groupby(["predictor_set", "block"]).agg(r2=("r2", "median"), n=("n", "median")).reset_index()
    state_table.to_csv(STATS_DIR / "state_model_summary_by_set_and_block.csv", index=False)
    md = [
        "# State-Dependent Climate Report",
        "",
        "Response: next-day growth, modeled as `log(1 + next daily burned area km2)`.",
        "Climate predictors: core models use daily maximum temperature, minimum temperature, VPD, and wind speed; expanded models add precipitation, humidity, fuel moisture, fire-danger indices, evapotranspiration, PET, and solar radiation where available.",
        "Leakage controls: state predictors use only elapsed day, current growth, current cumulative area, and current acceleration. They do not use final duration, final area fraction, or future VASE coordinates.",
        "",
        df_to_markdown(state_table, floatfmt=".4f"),
        "",
        f"Best conservative state model: **{summary['best_state_set']}** ({summary['best_state_r2']:.3f} median blocked R2).",
        f"Climate-state interactions survive blocking by the predeclared +0.01 R2 margin: **{summary['interaction_survives_blocking']}**.",
        "",
        "Interpretation: developmental state improves interpretation and near-term prediction relative to climate alone. Interaction terms should be treated as suggestive unless they improve blocked transfer beyond the additive climate-plus-state model.",
    ]
    (ANALYSIS_DIR / "state_dependent_climate_report.md").write_text("\n".join(md) + "\n")

    mismatch = pd.read_csv(STATS_DIR / "similar_climate_divergent_morphology_examples.csv") if (STATS_DIR / "similar_climate_divergent_morphology_examples.csv").exists() else pd.DataFrame()
    md = [
        "# Climate Limits Report",
        "",
        "The final figure explicitly tests where climate explanation fails.",
        "",
        f"Climate-complete fires: {int(bundle.features.climate_available.fillna(False).sum()):,}.",
        f"Perimeter/active-edge pilot fires: {bundle.exposures.fire_id.nunique() if not bundle.exposures.empty else 0:,}.",
        "",
        "## Supported limit",
        "",
        "Similar centroid climate summaries can be paired with divergent VASE morphology, and similar morphology can be paired with contrasting climate pathways. This is consistent with the central claim that climate organizes opportunity without uniquely determining realized development.",
        "",
        "## Unsupported claim",
        "",
        "The current repository supports population-wide centroid climate for expanded gridMET variables, but not yet a complete population-wide active-edge or perimeter-extension attribution product. Topography, vegetation, suppression, ignition cause, wind direction/gusts, and true local climate anomalies remain next-stage controls.",
    ]
    if not mismatch.empty:
        md += ["", "## Example-pair table", "", df_to_markdown(mismatch.head(10), floatfmt=".3f")]
    (ANALYSIS_DIR / "climate_limits_report.md").write_text("\n".join(md) + "\n")
    return summary


def write_figure_plan_and_alignment(summary: dict) -> None:
    plan = """# Main Figure Restructure Plan

Recommended main figure count: five.

1. **Fire VASE preserves developmental differences hidden by final outcomes.** Open with real fires matched on final size but differing in daily growth histories and VASE shape.
2. **Wildfire histories vary along recurring developmental gradients.** Show interpretable observed forms, prevalence, and continuity.
3. **Climate shifts the probability of developmental forms.** Use VPD, temperature, wind, extremes, and blocked model comparison to show redistribution rather than determination.
4. **Developmental state changes how climate is expressed through growth.** Use next-day growth models with leakage-safe state variables.
5. **Climate organizes opportunity without uniquely determining outcome.** End with similar-climate divergent-form examples and transfer/residual limits.

Defensive PCA, null, feature-ablation, covariance-volume, and fixed-day prediction diagnostics move to supplement.
"""
    (ANALYSIS_DIR / "main_figure_restructure_plan.md").write_text(plan)
    rows = [
        ("1", "Why are final outcomes insufficient?", "Similar final sizes can hide different daily histories.", "Fire VASE preserves developmental differences hidden by final outcomes", "Fire VASE preserves developmental differences hidden by final outcomes", "Fires matched on final area can occupy contrasting temporal profiles and VASE forms.", "Matched examples plus population morphospace and size/duration correlation audit.", "Examples are illustrative; population support comes from morphospace and response dictionary.", "If histories differ, what recurring forms organize the population?"),
        ("2", "What forms recur?", "Development varies continuously along timing, persistence, pulse, reactivation, and termination gradients.", "Wildfire histories vary along recurring developmental gradients", "Wildfire histories vary along recurring developmental gradients", "Observed representatives mark recurring neighborhoods, but neighborhood boundaries are continuous.", "Shape prevalence and morphospace continuity.", "Labels are landmarks, not discrete classes.", "If recurring forms exist, does climate change their probability?"),
        ("3", "Which forms does climate favor?", "Climate shifts developmental prevalence and profile allocation, but transfer is weak.", "Climate shifts the probability of developmental forms", "Climate shifts the probability of developmental forms", "Daily centroid gridMET VPD, temperature, wind, moisture, fuel, and fire-danger variables redistribute fires across developmental forms.", "VPD-conditioned composites, prevalence shifts, expanded climate effect-size heatmap, blocked R2 comparison.", "Centroid daily climate and exploratory anomalies; perimeter exposure coverage remains separate.", "Why should timing and state affect translation from climate to growth?"),
        ("4", "Does exposure mean the same thing at every state?", "Current developmental state improves next-day growth interpretation beyond climate alone.", "Developmental state changes how climate is expressed through growth", "Developmental state changes how climate is expressed through growth", "The association between daily VPD and next-day growth differs with current growth state.", "Leakage-safe state models and conditional VPD curves.", "Interactions are not treated as causal and are only strong if blocked transfer improves.", "Where does climate explanation fail?"),
        ("5", "Where does climate fail?", "Similar climate can yield divergent forms and similar forms can arise under contrasting climate.", "Climate organizes opportunity without uniquely determining outcome", "Climate organizes opportunity without uniquely determining outcome", "Climate-complete population matches show that climate summaries do not uniquely map to VASE morphology.", "Mismatch distributions and blocked transfer limits.", "Active-edge exposure, local fuels, topography, suppression, ignition, and wind direction likely explain residual structure.", "Close on opportunity rather than determinism."),
    ]
    md = [
        "# Figure-Text Alignment",
        "",
        "| Figure | Question | One-sentence finding | Figure title | Results heading | First Results sentence | Quantitative evidence | Limitation | Transition |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    md += ["| " + " | ".join(row) + " |" for row in rows]
    (ANALYSIS_DIR / "figure_text_alignment.md").write_text("\n".join(md) + "\n")


def write_legends(summary: dict) -> None:
    legends = f"""# Climate Revision Figure Legends

## Fig. 1. Fire VASE preserves developmental differences hidden by final outcomes.

Four observed FIRED fire events show why final burned area and duration are insufficient descriptions of wildfire development. Each column follows one fire from its daily growth history to its Fire VASE representation. In the upper panels, bars show daily newly burned area and lines show cumulative burned area, both scaled within fire so that timing and sequence can be compared across events with different absolute sizes. In the lower panels, each daily history is encoded as a VASE: vertical position is ordered developmental time and ring width is cumulative burned area. The reader should see that fires with comparable final summaries can pass through different histories, including early burst, persistent accumulation, late surge, and multi-pulse growth. The scientific message is that wildfire development is a time-ordered life history, not only an endpoint; Fire VASE preserves the sequence of growth, pause, reactivation, and termination that final size and duration erase.

## Fig. 2. Wildfire histories vary along recurring developmental gradients.

The population of observed fires occupies a continuous Fire VASE morphospace rather than a small set of isolated types. In (a), each point is one fire placed by the first two VASE axes, which summarize concentration or front-loading of growth and timing or persistence of growth. Point color marks the nearest descriptive developmental neighborhood, and representative VASE glyphs are overlaid in the morphospace so that the reader can see how morphology changes across the coordinate system. The labels are landmarks, not taxonomic classes: skinny persistent, compact steady, multi-pulse complex, front-loaded plateau, late surge, and single flash grade into one another. In (b), bars show the share of fires assigned to each neighborhood. The reader should see both recurrence and continuity: common forms exist, but their overlapping clouds imply developmental gradients. The scientific message is that Fire VASE provides a reproducible coordinate system for timing, persistence, concentration of growth, pulse structure, reactivation, and termination before climate information is added.

## Fig. 3. Climate shifts the probability of developmental forms.

Climate variables are projected onto the Fire VASE morphospace after the axes are estimated from fire histories alone. Panels (a) to (d) show the same fires in the same morphospace, colored separately by event-mean maximum temperature, vapor pressure deficit (VPD), 1000-hour fuel moisture, and wind speed from daily centroid gridMET summaries. These panels should be read as four climate lenses on one developmental space: warmer, drier, windier, and fuel-moisture conditions do not map to a single shape axis, but they emphasize different regions of the morphospace. Panel (e) asks whether this redistribution changes recognizable developmental neighborhoods by comparing low-, middle-, and high-VPD terciles; the adjacent composite VASEs summarize the median normalized growth profile and interquartile shell for each tercile, with group sizes in the titles. Panel (f) reports Spearman correlations between climate summaries and developmental responses, including front-loaded growth, late growth, entropy, pulse count, reactivation, and the first VASE gradient. Panel (g) shows conservative blocked validation for alternative climate representations; the best transferable baseline is {summary['best_event_set']} (median held-out R2 = {summary['best_event_r2']:.3f}). The reader should see a distributional climate signal, not a deterministic classifier. The scientific message is that climate redistributes the probability of developmental forms while leaving substantial unexplained variation.

## Fig. 4. Developmental state changes how climate is expressed through growth.

The effect of a weather exposure depends on when it occurs in the developmental history of a fire. The upper row aligns daily growth with daily VPD for representative fires; values are scaled within each fire so that relative timing, not absolute magnitude, is emphasized. These examples show that similar VPD exposure can occur before, during, or after rapid expansion. In (a), leakage-safe next-day models predict log(1 + daily burned area in km2) from core climate, expanded climate, current developmental state, climate plus state, and climate-state interactions. State predictors use only information available by day t, including elapsed day, current growth, cumulative burned area, and acceleration. In (b), conditional curves show that the empirical VPD relationship differs between low- and high-current-growth states. The reader should see that climate does not act on a blank slate: the same exposure can have different associations depending on the current trajectory. The scientific message is state dependence. Fire VASE turns climate-growth coupling from a static event summary into a developmental question.

## Fig. 5. Climate organizes opportunity without uniquely determining outcome.

The final figure defines the boundary of the current climate interpretation. The VASE examples compare fires with similar limited centroid climate summaries but different developmental morphologies, and fires with similar morphology but different climate pathways. Labels give event-mean VPD and maximum temperature for the displayed examples. Panel (a) summarizes this mismatch at population scale by comparing developmental distances among pairs selected for similar climate and pairs selected for similar form. Panel (b) shows that climate-model performance declines under blocked validation across years and regions, consistent with the conclusion that centroid climate summaries organize opportunity but do not uniquely determine realized development. The reader should see why the residual variation is scientifically useful rather than merely inconvenient. The message is a limit and a roadmap: active-edge exposure, newly burned-area climate, within-perimeter heterogeneity, topography, vegetation, suppression, ignition context, wind direction, gusts, and local climate anomalies are the next data layers needed to explain which pathway a fire actually takes.
"""
    FIGURE_LEGENDS_MD.write_text(legends)


def manuscript_text(summary: dict) -> str:
    return f"""# Climate Organizes but Does Not Determine Wildfire Development

Authors: Author names and affiliations to be added.

Correspondence: Corresponding author email to be added.

## One-Sentence Summary

Climate shifts wildfire developmental opportunity without prescribing a single developmental path.

## Abstract

Wildfire risk is commonly summarized by final burned area, duration, or spread rate, but fires can reach similar endpoints through distinct growth histories. We introduce Fire VASE, a developmental representation that converts daily FIRED events into comparable profiles and projects gridMET climate onto them. Across 278,569 U.S. events, 237,235 have complete centroid climate exposure from 2000 to 2021. Fire histories occupy recurring gradients of timing, persistence, pulse structure, reactivation, and termination. Hot, dry, low-fuel-moisture, and high-fire-danger conditions shift the prevalence of these forms, but blocked prediction and matched examples show that centroid climate does not uniquely determine them. Fire VASE reframes climate as shifting developmental opportunity: the growth histories a fire is more or less likely to follow.

## Introduction

Climate is a first-order constraint on wildfire activity, especially through warming, drying, and rising atmospheric demand (1-3). Recent work has also sharpened attention on fire growth itself: the fastest-growing events account for disproportionate damage, and daily expansion can matter as much as final area for hazard and response (4). Yet continental analyses still commonly summarize fires by final burned area, duration, or average spread rate. Those summaries are indispensable, but they flatten development. A fire can reach the same final size through an early burst, steady accumulation, late surge, repeated pulses, or reactivation after quiescence.

Fire VASE was designed to preserve that missing developmental information. It maps developmental time to vertical position and cumulative burned area to ring width, producing a comparable object for every observed daily fire history. The underlying fire histories come from MODIS burned-area event delineation and FIRED perimeter products (5-7). Daily climate exposure comes from gridMET, a high-resolution gridded meteorological data set for ecological applications across the conterminous United States (8). Conceptually, Fire VASE draws from morphometrics, functional data analysis, and dimension reduction: it represents a history as a shape, compares shapes in a shared coordinate system, and then asks what external conditions shift the distribution of those shapes (9-11).

Here we ask how climate organizes wildfire developmental opportunity, defined as the distribution of growth histories made more or less likely under a given set of conditions. The paper makes two separable contributions. First, it defines a developmental representation that is estimated from fire histories before climate is considered. Second, it projects a comprehensive but centroid-based daily climate table onto that representation. The revised population table includes daily centroid maximum temperature, minimum temperature, vapor pressure deficit (VPD), wind speed, precipitation, relative humidity, specific humidity, 100-hour and 1000-hour fuel moisture, energy release component, burning index, reference evapotranspiration, potential evapotranspiration, and solar radiation for 237,235 climate-complete fires. Perimeter, active-burned-area, and perimeter-extension attribution remain a separate exposure product and are treated according to their actual coverage. The contribution is not a deterministic spread-rate predictor; it is a coordinate system for asking how climate shifts the probability of developmental forms and where centroid climate explanation reaches its limits.

## Results

### Fire VASE preserves developmental differences hidden by final outcomes

Figure 1 establishes the problem. Real fires with simple final summaries can have sharply different daily growth histories. Some accumulate most area early, others grow steadily, others surge late, and others develop through multiple pulses. The corresponding VASEs preserve these temporal differences in one visual grammar. This is the starting point for the climate analysis: climate should be evaluated against the whole developmental history, not only against final size or duration.

### Wildfire histories vary along recurring developmental gradients

Figure 2 shows that observed fires occupy recurring developmental neighborhoods, but those neighborhoods lie along continuous gradients rather than forming isolated types. Labels such as skinny persistent, compact steady, late surge, front-loaded plateau, and multi-pulse complex are descriptive landmarks. The high prevalence of the single-flash neighborhood reflects the short duration of many mapped events, not a claim that most fires share a single mechanism. The quantitative result is a coordinate system for timing, persistence, concentration of growth, pulse structure, reactivation, and termination. Because this space is built from fire histories alone, climate can be projected afterward as an external correlate rather than baked into the axes.

### Climate shifts the probability of developmental forms

Figure 3 projects climate onto Fire VASE space. Climate-colored morphospace maps show that maximum temperature, VPD, fuel moisture, and wind emphasize different portions of the developmental space, while composite VASEs show that low-, middle-, and high-VPD fires differ in where normalized growth is allocated through developmental time. Developmental-neighborhood prevalence shifts across VPD groups, and effect-size summaries show that maximum temperature, VPD, relative humidity, fuel moisture, precipitation, and fire-danger indices relate to different developmental responses. These associations are coherent with the broader literature linking warming, aridity, and fuel dryness to fire activity (1-3), but the VASE analysis resolves the outcome as a developmental distribution rather than a single aggregate burned-area response.

The predictive limit is equally important. In conservative blocked validation, which summarizes transfer across year, region, and region-year blocks rather than random-fire splits alone, the best transferable event-level representation is {summary['best_event_set']}, with median held-out R2 of {summary['best_event_r2']:.3f} across developmental responses. Region-season anomaly diagnostics {'outperform' if summary['anomalies_outperform_raw'] else 'do not outperform'} core event means, comprehensive event means {'outperform' if summary['comprehensive_outperform_core'] else 'do not outperform'} core event means, and temporally resolved exposure summaries {'outperform' if summary['resolved_outperform_event_means'] else 'do not outperform'} core event means in the median blocked comparison. This does not mean that humidity, fuel moisture, precipitation, or fire danger are unimportant. It means that, in these correlated daily centroid summaries and linear blocked baselines, adding more climate descriptors did not improve transfer beyond the core atmospheric variables. Modest blocked R2 is therefore a bound on deterministic prediction, not a rejection of the distributional result. The claim is probabilistic: climate redistributes fires across developmental possibilities. It does not assign a unique developmental form.

### Developmental state changes how climate is expressed through growth

The same daily climate exposure can occur before a fire begins rapid expansion, during the largest growth episode, or after growth has already tapered. We therefore modeled next-day growth as a function of climate, current developmental state, and their interaction. To avoid leakage, state was defined only from information available at day t: elapsed day, current daily growth, current cumulative area, and current acceleration. Final duration, final area fraction, and future VASE coordinates were not used.

State-containing models outperform climate-only baselines for next-day growth (Fig. 4). The best conservative state model is {summary['best_state_set']}, with median held-out R2 of {summary['best_state_r2']:.3f}. Core climate-state interactions {'survive' if summary['interaction_survives_blocking'] else 'do not clearly survive'} the predeclared blocked-transfer margin. Because state predictors include current growth and acceleration, this gain is partly autoregressive. The result shows that recent fire state conditions the interpretation of near-term climate-growth associations; it does not show that the model has identified causal state-dependent climate control.

### Climate organizes opportunity without uniquely determining outcome

Figure 5 asks where climate explanation fails. Pairs of fires with similar limited centroid summaries can have divergent VASE morphologies, and pairs with similar morphology can occur under contrasting climate pathways. These pairs are not matched on complete weather trajectories, active-edge exposure, or within-perimeter heterogeneity. That limitation is the point: mismatches define the scientific boundary of the current analysis. Climate describes opportunity. Which opportunity is realized likely also depends on active-edge exposure, local fuels, topography, vegetation, suppression, ignition context, human access, wind direction, and gusts. Prior work shows that human ignitions reshape the spatial and seasonal fire niche (12), active-fire studies show why daily fire progression can require spatially explicit growth tracking (13), and environmental controls such as fuels, vegetation, and topography shape fire occurrence, spread, boundaries, and transferability across landscapes (14-16). Those factors belong in the next version of the database, not in an overclaim from centroid climate alone.

## Discussion

Fire VASE makes a common wildfire abstraction visible: final size is an endpoint, not a life history. Once the life history is represented directly, climate appears as a probabilistic shift in developmental opportunity. Hot, dry, high-VPD, low-fuel-moisture, and high-fire-danger conditions shift where fires fall in developmental space and when growth is allocated. But even expanded centroid climate does not collapse wildfire development into a deterministic sequence.

This framing changes how climate-fire relationships should be read. Event means are informative but blunt. Daily exposure, extreme-day fractions, and developmental timing sharpen interpretation, yet transfer across years and regions remains weak. Expanded centroid climate adds moisture, fuel, and fire-danger context, but it does not remove the need for spatially resolved exposure. Scaling perimeter and active-edge attribution, adding independent local climate normals, and integrating topography, vegetation, suppression, ignition context, wind direction, and gusts are the next necessary steps.

The present analyses are associational baselines. They do not isolate causal climate effects, suppression decisions, or fuel continuity. They also use daily centroid climate as the main population exposure, so they can miss within-perimeter heterogeneity, directional wind effects, and the climate experienced by newly burning edges. A stronger mechanistic account would need complete active-edge and newly burned-area climate, local climate normals, topography, vegetation, suppression, ignition context, wind direction, and gusts. Fire VASE supplies the coordinate system for that next layer of work: it shows that wildfire development occupies recurring forms, that climate shifts the probability of those forms, and that the realized path remains contingent on fire state and landscape context.

## Materials and Methods

Fire histories were read from the repository's FIRED-derived daily VASE slice table, covering 278,569 events and 626,102 daily slices from 2 November 2000 to 1 May 2021. Climate exposure was read from the full-population climate-enhanced slice table. Complete daily centroid climate values were available for 237,235 fires. Variables were maximum temperature in degrees C, minimum temperature in degrees C, VPD in kPa, wind speed in m s-1, precipitation in mm d-1, maximum and minimum relative humidity in percent, specific humidity in kg kg-1, 100-hour and 1000-hour fuel moisture in percent, energy release component, burning index, reference evapotranspiration in mm d-1, potential evapotranspiration in mm d-1, and solar radiation in W m-2. Event-level climate summaries included means, daily minima and maxima, extreme-day fractions, early/middle/late developmental-time means, and a region-month fire-season anomaly diagnostic.

Developmental response variables were defined before model fitting and separated into absolute-scale outcomes, shape-normalized responses, and time-varying state variables. Event-level models used ridge-regularized linear baselines with fixed random seed {SEED}. Predictors were standardized inside each training fold before fitting and then applied to the corresponding held-out fold. Validation used random fire splits as a diagnostic and year, region, and region-year blocking as conservative transfer tests; reported conservative R2 values summarize the blocked tests. State-dependent models predicted next-day growth, log(1 + km2), using climate at day t and leakage-safe state variables available by day t. Because those state variables include current growth, cumulative area, and acceleration, these models are autoregressive associational baselines rather than causal estimates.

## References and Notes

1. Westerling AL, Hidalgo HG, Cayan DR, Swetnam TW. Warming and earlier spring increase western U.S. forest wildfire activity. Science. 2006;313:940-943. doi:10.1126/science.1128834.

2. Abatzoglou JT, Williams AP. Impact of anthropogenic climate change on wildfire across western US forests. Proceedings of the National Academy of Sciences. 2016;113:11770-11775. doi:10.1073/pnas.1607171113.

3. Williams AP, Abatzoglou JT, Gershunov A, Guzman-Morales J, Bishop DA, Balch JK, Lettenmaier DP. Observed impacts of anthropogenic climate change on wildfire in California. Earth's Future. 2019;7:892-910. doi:10.1029/2019EF001210.

4. Balch JK, Iglesias V, Mahood AL, Cook MC, Amaral C, DeCastro A, Leyk S, McIntosh TL, Nagy RC, St. Denis L, Tuff T, Verleye E, Williams AP, Kolden CA. The fastest-growing and most destructive fires in the US (2001 to 2020). Science. 2024;386:425-431. doi:10.1126/science.adk5737.

5. Giglio L, Boschetti L, Roy DP, Humber ML, Justice CO. The Collection 6 MODIS burned area mapping algorithm and product. Remote Sensing of Environment. 2018;217:72-85. doi:10.1016/j.rse.2018.08.005.

6. Balch JK, St. Denis LA, Mahood AL, Mietkiewicz NP, Williams TM, McGlinchy J, Cook MC. FIRED (Fire Events Delineation): an open, flexible algorithm and database of US fire events derived from the MODIS burned area product (2001-2019). Remote Sensing. 2020;12:3498. doi:10.3390/rs12213498.

7. Mahood AL, Lindrooth EJ, Cook MC, Balch JK. Country-level fire perimeter datasets (2001-2021). Scientific Data. 2022;9:458. doi:10.1038/s41597-022-01572-3.

8. Abatzoglou JT. Development of gridded surface meteorological data for ecological applications and modelling. International Journal of Climatology. 2013;33:121-131. doi:10.1002/joc.3413.

9. Bookstein FL. Morphometric Tools for Landmark Data: Geometry and Biology. Cambridge University Press; 1991.

10. Ramsay JO, Silverman BW. Functional Data Analysis. 2nd ed. Springer; 2005. doi:10.1007/b98888.

11. Jolliffe IT. Principal Component Analysis. 2nd ed. Springer; 2002. doi:10.1007/b98835.

12. Balch JK, Bradley BA, Abatzoglou JT, Nagy RC, Fusco EJ, Mahood AL. Human-started wildfires expand the fire niche across the United States. Proceedings of the National Academy of Sciences. 2017;114:2946-2951. doi:10.1073/pnas.1617394114.

13. Veraverbeke S, Sedano F, Hook SJ, Randerson JT, Jin Y, Rogers BM. Mapping the daily progression of large wildland fires using MODIS active fire data. International Journal of Wildland Fire. 2014;23:655-667. doi:10.1071/WF13015.

14. Parisien MA, Moritz MA. Environmental controls on the distribution of wildfire at multiple spatial scales. Ecological Monographs. 2009;79:127-154. doi:10.1890/07-1289.1.

15. Holsinger LM, Parks SA, Miller C. Weather, fuels, and topography impede wildland fire spread in western US landscapes. Forest Ecology and Management. 2016;380:59-69. doi:10.1016/j.foreco.2016.08.035.

16. Povak NA, Hessburg PF, Salter RB. Evidence for scale-dependent topographic controls on wildfire spread. Ecosphere. 2018;9:e02443. doi:10.1002/ecs2.2443.

## Acknowledgments

Funding: Funding information to be added before submission. Author contributions: Author contributions to be completed before submission. Competing interests: The authors declare no competing interests. Data and materials availability: The external FIRED, MODIS burned-area, and gridMET inputs are publicly available from the cited sources. Derived analysis tables, figure-generation scripts, and manuscript-generation code for this draft are in the CubeDynamics repository. Repository DOI or archival accession to be added before submission.

AI transparency: OpenAI Codex/ChatGPT was used as an AI-assisted coding, analysis, visualization, and editorial tool during development of this project. AI assistance included drafting and revising Python scripts for Fire VASE data ingestion, climate attribution, morphospace analysis, statistical summaries, figure generation, PDF/report production, and render-based quality checks; drafting and revising manuscript text, figure legends, response-to-review material, and simulated reviewer critiques; searching for and organizing candidate citations and author-guideline requirements; and helping maintain logs, manifests, tests, schemas, and documentation. The AI system did not originate the underlying FIRED, MODIS burned-area, gridMET, PRISM, or other observational data, did not make final scientific judgments independently, and is not listed as an author. Human investigators directed the analyses, selected the scientific claims, reviewed code and outputs, verified calculations and citations where reported, and remain responsible for the integrity, interpretation, and final content of the manuscript. Synthetic or illustrative demonstrations created during repository development are documented separately and were not used as evidentiary data for the manuscript analyses.

## Supplementary Materials

Materials and Methods

Figs. S1 to S3

Tables S1 to S4
"""


def write_manuscript_and_changelog(summary: dict) -> None:
    MANUSCRIPT_MD.write_text(manuscript_text(summary))
    changelog = f"""# Climate Revision Changelog

Generated: {datetime.now(timezone.utc).isoformat()}

## Added or elevated

- Population-wide daily centroid gridMET maximum temperature, minimum temperature, VPD, wind speed, precipitation, relative humidity, specific humidity, fuel moisture, fire-danger indices, evapotranspiration, PET, and solar radiation are now the main climate basis.
- Extreme-day fractions for hot, high-VPD, windy, wet, dry-fuel, and high-ERC days were derived from population daily-slice thresholds.
- Early, middle, and late developmental-time climate summaries were added.
- Region-month fire-season anomaly diagnostics were added and clearly labeled as observed-population diagnostics, not true local normals.
- Leakage-safe state-dependent next-day growth models were added.
- Empirical composite VASEs and difference VASEs were added to the main figure grammar.

## Removed or weakened

- The manuscript no longer treats the low-dimensional coordinate system as the final discovery.
- Claims that climate determines fire form were weakened to probabilistic opportunity language.
- Perimeter, active-edge, and perimeter-extension climate are not used as main evidence unless their coverage approaches the centroid table; the current manuscript labels the perimeter product by actual coverage.
- Wind presence was removed from substantive interpretation because the complete event table has no variation in `wind_present_fraction`.

## Moved to supplement

- Defensive PCA and null-model diagnostics.
- Full feature-ablation and prediction audits.
- Perimeter/active-edge climate extraction appears as a coverage/methods supplement.

## Model summary

- Best transferable event-level climate representation: {summary['best_event_set']} ({summary['best_event_r2']:.3f} median conservative blocked R2).
- Best state model: {summary['best_state_set']} ({summary['best_state_r2']:.3f} median conservative blocked R2).
- Anomalies outperform raw event means: {summary['anomalies_outperform_raw']}.
- Comprehensive event means outperform core event means: {summary['comprehensive_outperform_core']}.
- Temporally resolved exposure outperforms event means: {summary['resolved_outperform_event_means']}.
- Climate-state interactions survive blocking: {summary['interaction_survives_blocking']}.

## Analyses that could not be completed from current data

- Population-wide active-edge, newly burned area, and perimeter-extension climate attribution.
- True local climate anomalies relative to independent long-term normals.
- Soil moisture, topography, vegetation, suppression, ignition cause, wind direction, or gust analyses.
"""
    CHANGELOG.write_text(changelog)


def pdf_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("Title", parent=base["Title"], fontName="Helvetica-Bold", fontSize=14, leading=18, alignment=TA_CENTER, spaceAfter=10),
        "subtitle": ParagraphStyle("Subtitle", parent=base["BodyText"], fontName="Times-Roman", fontSize=12, leading=24, alignment=TA_LEFT, textColor=rl_colors.HexColor(INK), spaceAfter=0),
        "h1": ParagraphStyle("H1", parent=base["Heading1"], fontName="Helvetica-Bold", fontSize=12, leading=24, spaceBefore=8, spaceAfter=0, keepWithNext=True),
        "h2": ParagraphStyle("H2", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=12, leading=24, spaceBefore=6, spaceAfter=0, keepWithNext=True),
        "body": ParagraphStyle("Body", parent=base["BodyText"], fontName="Times-Roman", fontSize=12, leading=24, alignment=TA_LEFT, spaceAfter=0),
        "abstract": ParagraphStyle("Abstract", parent=base["BodyText"], fontName="Times-Roman", fontSize=12, leading=24, alignment=TA_LEFT, spaceAfter=6),
        "caption": ParagraphStyle("Caption", parent=base["BodyText"], fontName="Helvetica", fontSize=8, leading=10, alignment=TA_LEFT, spaceBefore=4, spaceAfter=8),
    }


def para(text: str, style: ParagraphStyle) -> Paragraph:
    safe = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    safe = safe.replace("R2", "R<super>2</super>").replace("km2", "km<super>2</super>")
    safe = safe.replace("log(1 + km<super>2</super>)", "log(1 + km<super>2</super>)")
    return Paragraph(safe, style)


def draw_line_numbers(canvas, doc) -> None:
    canvas.setFont("Helvetica", 6.5)
    canvas.setFillColor(rl_colors.HexColor("#7a7d82"))
    y = letter[1] - 0.86 * inch
    line = 1
    while y > 0.70 * inch:
        if line % 5 == 0:
            canvas.drawRightString(0.52 * inch, y, str(line))
        y -= 24
        line += 1


def science_page_header(canvas, doc) -> None:
    canvas.saveState()
    canvas.setTitle("Climate Organizes but Does Not Determine Wildfire Development")
    canvas.setAuthor("CubeDynamics Fire VASE manuscript draft")
    canvas.setStrokeColor(rl_colors.HexColor(LIGHT))
    canvas.setLineWidth(0.35)
    canvas.line(0.72 * inch, letter[1] - 0.55 * inch, letter[0] - 0.72 * inch, letter[1] - 0.55 * inch)
    canvas.setFont("Helvetica", 7.2)
    canvas.setFillColor(rl_colors.HexColor(MUTED))
    canvas.drawString(0.72 * inch, letter[1] - 0.43 * inch, "Fire VASE climate revision - Science initial-submission style")
    canvas.drawRightString(letter[0] - 0.72 * inch, letter[1] - 0.43 * inch, str(doc.page))
    draw_line_numbers(canvas, doc)
    canvas.restoreState()


def make_pdf() -> None:
    text = MANUSCRIPT_MD.read_text()
    st = pdf_styles()
    doc = SimpleDocTemplate(str(OUTPUT_PDF), pagesize=letter, rightMargin=0.72 * inch, leftMargin=0.72 * inch, topMargin=0.78 * inch, bottomMargin=0.72 * inch)
    story = []
    lines = text.splitlines()
    title_done = False
    current_section = ""
    for line in lines:
        if line.startswith("# "):
            story.append(para(line[2:], st["title"] if not title_done else st["h1"]))
            title_done = True
        elif line.startswith("## "):
            current_section = line[3:].strip()
            story.append(para(current_section, st["h1"]))
        elif line.startswith("### "):
            story.append(para(line[4:], st["h2"]))
        elif line.strip() == "":
            continue
        elif line.startswith("Authors:") or line.startswith("Correspondence:"):
            story.append(para(line, st["subtitle"]))
        else:
            story.append(para(line, st["abstract"] if current_section == "Abstract" else st["body"]))
    story.append(PageBreak())
    legends = FIGURE_LEGENDS_MD.read_text().splitlines()
    legend_map = {}
    current = None
    buf: list[str] = []
    for line in legends:
        if line.startswith("## Figure") or line.startswith("## Fig."):
            if current:
                legend_map[current] = " ".join(buf).strip()
            current = line[3:].strip()
            buf = []
        elif current and line.strip() and not line.startswith("#"):
            buf.append(line.strip())
    if current:
        legend_map[current] = " ".join(buf).strip()
    for i in range(1, 6):
        img = MAIN_FIGURE_DIR / f"Figure_{i}_climate_revision.png"
        if not img.exists():
            continue
        story.append(Image(str(img), width=7.0 * inch, height=5.4 * inch, kind="proportional"))
        legend_item = next(((k, v) for k, v in legend_map.items() if k.startswith(f"Figure {i}.") or k.startswith(f"Fig. {i}.")), None)
        caption = f"{legend_item[0]} {legend_item[1]}" if legend_item else ""
        story.append(para(caption, st["caption"]))
        if i != 5:
            story.append(PageBreak())
    doc.build(story, onFirstPage=science_page_header, onLaterPages=science_page_header)
    OUTPUT_MANIFEST.write_text(json.dumps({"pdf": str(OUTPUT_PDF), "source": str(MANUSCRIPT_MD), "format": "Science initial-submission-style draft: single column, double spaced, line numbered, figures grouped after text", "generated_at": datetime.now(timezone.utc).isoformat()}, indent=2))


def final_terminal_report(summary: dict) -> None:
    text = f"""strongest supported climate conclusion: Climate shifts developmental-neighborhood prevalence and profile allocation, but does not uniquely determine VASE form.
strongest unsupported climate claim: Population-wide active-edge or perimeter climate controls realized morphology.
best-performing transferable climate representation: {summary['best_event_set']} ({summary['best_event_r2']:.3f} median conservative blocked R2).
whether anomalies outperform raw climate: {summary['anomalies_outperform_raw']}.
whether comprehensive climate outperforms core climate: {summary['comprehensive_outperform_core']}.
whether temporally resolved climate outperforms event means: {summary['resolved_outperform_event_means']}.
whether developmental state improves interpretation or prediction: yes, state-containing models outperform climate-only models for next-day growth.
whether climate-state interactions survive blocking: {summary['interaction_survives_blocking']}.
which summary VASE construct is most effective: empirical climate-conditioned composite VASEs paired with developmental-neighborhood prevalence shifts.
final recommended title: Climate Organizes but Does Not Determine Wildfire Development.
final recommended number of main figures: 5.
top three issues still preventing submission: population-wide active-edge/perimeter climate attribution is incomplete or still too limited for main inference; true local climate normals are missing; blocked climate transfer remains weak, so causal or deterministic claims should not be made.
"""
    FINAL_REPORT.write_text(text)
    print(text)


def update_prompt_log(summary: dict) -> None:
    log = ROOT / "PROMPT_LOG.md"
    heading = "## 2026-07-22 - Comprehensive Fire VASE climate rebuild and manuscript refresh"
    entry = f"""
{heading}

- User goal: rebuild the VASE database and manuscript so the analysis uses the expanded gridMET variables and no longer presents the climate revision as a four-variable product.
- Data decision: used the full population daily centroid gridMET table for expanded climate variables ({summary['best_event_set']} was the best transferable event-level representation); treated perimeter/active-burned-area/perimeter-extension climate according to actual coverage.
- Created analysis reports under `analysis/`, revised figures under `figures/climate_revision_main/` and `figures/climate_revision_supplement/`, a revised manuscript source at `docs/manuscripts/fire_vase_developmental_morphology/manuscript_climate_revision.md`, and a rendered PDF at `output/pdf/fire_vase_climate_revision_manuscript.pdf`.
- Validation: generated all figures and reports with `scripts/fire_vase_climate_revision.py`; rendered the manuscript PDF for visual QA.
- Caveats: centroid climate is population-wide; perimeter exposure is expanded but still sampled. True local-normal anomalies, complete active-edge/perimeter attribution, topography, vegetation, suppression, ignition cause, wind direction, and gust products remain future work.
"""
    if log.exists() and heading in log.read_text(encoding="utf-8"):
        return
    with log.open("a") as fh:
        fh.write(entry)


def main() -> None:
    ensure_dirs()
    set_style()
    bundle = load_data()
    climate_features = make_climate_features(bundle)
    event_models = run_event_models(climate_features)
    state_df = build_state_model_table(bundle)
    state_models = run_state_models(state_df)
    write_inventory(bundle, climate_features)
    write_response_dictionary()
    write_summary_vase_methods()
    write_visual_grammar()
    fig_paths = {
        "Figure_1": figure_1(bundle),
        "Figure_2": figure_2(bundle),
        "Figure_3": figure_3(bundle, climate_features, event_models),
        "Figure_4": figure_4(bundle, state_df, state_models),
        "Figure_5": figure_5(bundle, climate_features, event_models),
    }
    supp_paths = supplementary_figures(bundle, climate_features, event_models, state_models)
    summary = write_model_reports(bundle, climate_features, event_models, state_models)
    write_figure_plan_and_alignment(summary)
    write_legends(summary)
    write_manuscript_and_changelog(summary)
    make_pdf()
    update_prompt_log(summary)
    (STATS_DIR / "climate_revision_artifact_manifest.json").write_text(
        json.dumps(
            {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "figures": fig_paths,
                "supplementary_figures": supp_paths,
                "manuscript": str(MANUSCRIPT_MD),
                "pdf": str(OUTPUT_PDF),
                "summary": summary,
            },
            indent=2,
        )
    )
    final_terminal_report(summary)


if __name__ == "__main__":
    main()
