#!/usr/bin/env python3
"""Build a developmental morphology analysis atlas for fire VASEs.

The analysis treats fire VASEs as developmental objects. Morphospace is built
from geometry-first features. Climate is attached afterward from the durable
vase_slices table.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import textwrap
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/cubedynamics-mpl-cache")

import duckdb
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.collections import LineCollection
from matplotlib.patches import Ellipse
from scipy.spatial import cKDTree


STAGES = [
    ("early", 0.00, 0.25),
    ("expansion", 0.25, 0.50),
    ("mature", 0.50, 0.75),
    ("terminal", 0.75, 1.01),
]

CLIMATE_COLS = [
    "maximum_temperature_c",
    "minimum_temperature_c",
    "vpd_kpa",
    "wind_speed_m_s",
]

CATEGORY_COLORS = {
    "single flash": "#b12a1c",
    "skinny persistent": "#1f6f78",
    "compact steady": "#5f8d4e",
    "front-loaded plateau": "#7f3b2d",
    "late surge": "#7251b5",
    "broad rapid": "#d18700",
    "multi-pulse complex": "#2f4858",
}


@dataclass
class PcaResult:
    scores: np.ndarray
    loadings: pd.DataFrame
    explained_variance_ratio: np.ndarray
    center: pd.Series
    scale: pd.Series


def read_tables(table_root: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    con = duckdb.connect()
    slices = con.execute(
        f"""
        select fire_id, slice_index, timestamp, year,
          ring_area_km2, cumulative_area_km2, normalized_vase_width,
          maximum_temperature_c, minimum_temperature_c, vpd_kpa,
          wind_speed_m_s, wind_present, climate_available
        from '{table_root / "vase_slices.parquet"}'
        order by fire_id, slice_index
        """
    ).fetchdf()
    traits = con.execute(
        f"""
        select fire_id, year, region, total_area_km2,
          duration_hours / 24.0 as duration_days,
          peak_growth_km2_per_hour * 24.0 as peak_growth_km2_per_day
        from '{table_root / "fire_traits.parquet"}'
        """
    ).fetchdf()
    slices["fire_id"] = slices["fire_id"].astype(str)
    traits["fire_id"] = traits["fire_id"].astype(str)
    slices["timestamp"] = pd.to_datetime(slices["timestamp"])
    return slices, traits


def _count_pulses(growth: np.ndarray) -> tuple[int, int]:
    growth = np.asarray(growth, dtype=float)
    growth = np.nan_to_num(growth, nan=0.0)
    if growth.size == 0 or growth.max() <= 0:
        return 0, 0
    threshold = max(float(np.nanquantile(growth, 0.75)), float(growth.max() * 0.25), 1e-9)
    active = growth >= threshold
    starts = np.flatnonzero(active & np.r_[True, ~active[:-1]])
    return int(len(starts)), int(max(0, len(starts) - 1))


def _interp_profile(values: np.ndarray, points: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    values = np.nan_to_num(values, nan=0.0)
    if values.size == 0:
        return np.zeros(len(points), dtype=float)
    if values.size == 1:
        return np.repeat(values[0], len(points))
    x = np.linspace(0, 1, values.size)
    return np.interp(points, x, values)


def _value_at_fraction(values: np.ndarray, fraction: float) -> float:
    values = np.asarray(values, dtype=float)
    if values.size == 0:
        return np.nan
    if values.size == 1:
        return float(values[0])
    return float(np.interp(fraction, np.linspace(0, 1, values.size), values))


def _assign_category(row: pd.Series, thresholds: dict[str, float]) -> str:
    if row["observation_count"] <= 1 or row["duration_days"] <= 1:
        return "single flash"
    if (
        row["slenderness_days_per_width"] >= thresholds["slender_q75"]
        and row["final_area_km2"] <= thresholds["area_q75"]
    ):
        return "skinny persistent"
    if row["final_area_km2"] >= thresholds["area_q90"] and row["duration_days"] <= thresholds["duration_q50"]:
        return "broad rapid"
    if row["pulse_count"] >= 3 or row["observation_count"] >= 6:
        return "multi-pulse complex"
    if row["peak_timing"] >= 0.66:
        return "late surge"
    if row["front_loaded_fraction"] >= 0.75 and row["terminal_taper_fraction"] <= 0.35:
        return "front-loaded plateau"
    return "compact steady"


def build_features_and_events(
    slices: pd.DataFrame,
    traits: pd.DataFrame,
    profile_points: int = 11,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    traits_ix = traits.set_index("fire_id", drop=False)
    points = np.linspace(0, 1, profile_points)
    feature_rows: list[dict] = []
    event_rows: list[dict] = []
    stage_rows: list[dict] = []

    for fire_id, group in slices.groupby("fire_id", sort=False):
        if fire_id not in traits_ix.index:
            continue
        trait = traits_ix.loc[fire_id]
        if isinstance(trait, pd.DataFrame):
            trait = trait.iloc[0]
        g = group.sort_values("slice_index").reset_index(drop=True)
        growth = g["ring_area_km2"].fillna(0).clip(lower=0).to_numpy(float)
        cumulative = g["cumulative_area_km2"].ffill().fillna(0).to_numpy(float)
        width = g["normalized_vase_width"].fillna(0).clip(lower=0).to_numpy(float)
        final_area = float(max(trait["total_area_km2"], np.nanmax(cumulative) if cumulative.size else 0.0, 1e-9))
        duration_days = float(max(trait["duration_days"], 0.0))
        obs = int(len(growth))
        rel_t = np.array([0.5]) if obs == 1 else np.linspace(0, 1, obs)
        growth_fraction = growth / final_area
        peak_idx = int(np.nanargmax(growth)) if growth.size else 0
        peak_growth = float(np.nanmax(growth)) if growth.size else 0.0
        pulse_count, reactivation_count = _count_pulses(growth)
        p = growth_fraction[growth_fraction > 0]
        growth_entropy = float(-(p * np.log(p)).sum() / math.log(max(len(growth_fraction), 2))) if p.size else 0.0
        dw = np.diff(width) if len(width) > 1 else np.array([0.0])
        ddw = np.diff(dw) if len(dw) > 1 else np.array([0.0])
        radius_km = math.sqrt(final_area / math.pi) if final_area > 0 else 0.0
        row = {
            "fire_id": fire_id,
            "year": int(trait["year"]),
            "region": trait["region"],
            "final_area_km2": final_area,
            "duration_days": duration_days,
            "peak_growth_km2_per_day": float(trait["peak_growth_km2_per_day"]),
            "observation_count": obs,
            "pulse_count": pulse_count,
            "reactivation_count": reactivation_count,
            "peak_timing": float(peak_idx / max(obs - 1, 1)),
            "front_loaded_fraction": _value_at_fraction(cumulative / final_area, 0.5),
            "late_growth_fraction": float(np.nansum(growth_fraction[rel_t >= 0.75])),
            "terminal_taper_fraction": float(growth[-1] / peak_growth) if peak_growth > 0 else 0.0,
            "growth_entropy": growth_entropy,
            "developmental_velocity": float(np.nanmean(np.abs(dw))),
            "developmental_acceleration": float(np.nanmean(np.abs(ddw))),
            "width_at_quarter": _value_at_fraction(width, 0.25),
            "width_at_half": _value_at_fraction(width, 0.50),
            "width_at_three_quarter": _value_at_fraction(width, 0.75),
            "slenderness_days_per_width": duration_days / max(2 * radius_km, 0.1),
            "climate_available": bool(g["climate_available"].all()),
        }
        for i, val in enumerate(_interp_profile(width, points)):
            row[f"width_p{i:02d}"] = float(val)
        for i, val in enumerate(_interp_profile(growth_fraction, points)):
            row[f"growth_p{i:02d}"] = float(val)
        climate_ok = g[g["climate_available"]]
        if not climate_ok.empty:
            row["mean_maximum_temperature_c"] = float(climate_ok["maximum_temperature_c"].mean())
            row["mean_minimum_temperature_c"] = float(climate_ok["minimum_temperature_c"].mean())
            row["mean_vpd_kpa"] = float(climate_ok["vpd_kpa"].mean())
            row["max_vpd_kpa"] = float(climate_ok["vpd_kpa"].max())
            row["mean_wind_speed_m_s"] = float(climate_ok["wind_speed_m_s"].mean())
            row["wind_present_fraction"] = float(climate_ok["wind_present"].astype(float).mean())
        else:
            for col in [
                "mean_maximum_temperature_c",
                "mean_minimum_temperature_c",
                "mean_vpd_kpa",
                "max_vpd_kpa",
                "mean_wind_speed_m_s",
                "wind_present_fraction",
            ]:
                row[col] = np.nan
        feature_rows.append(row)

        for stage, lo, hi in STAGES:
            mask = (rel_t >= lo) & (rel_t < hi)
            if not np.any(mask):
                continue
            climate_mask = mask & g["climate_available"].to_numpy(bool)
            stage_rows.append(
                {
                    "fire_id": fire_id,
                    "stage": stage,
                    "stage_midpoint": (lo + min(hi, 1.0)) / 2,
                    "stage_growth_fraction": float(np.nansum(growth_fraction[mask])),
                    "stage_width_mean": float(np.nanmean(width[mask])),
                    "stage_width_change": float(np.nanmax(width[mask]) - np.nanmin(width[mask])),
                    "stage_observation_count": int(np.sum(mask)),
                    "stage_tmax_mean_c": float(g.loc[climate_mask, "maximum_temperature_c"].mean()) if np.any(climate_mask) else np.nan,
                    "stage_vpd_mean_kpa": float(g.loc[climate_mask, "vpd_kpa"].mean()) if np.any(climate_mask) else np.nan,
                    "stage_wind_mean_m_s": float(g.loc[climate_mask, "wind_speed_m_s"].mean()) if np.any(climate_mask) else np.nan,
                    "stage_wind_present_fraction": float(g.loc[climate_mask, "wind_present"].astype(float).mean()) if np.any(climate_mask) else np.nan,
                }
            )

        event_specs = [
            ("first_observed_development", 0),
            ("emergence_5pct_area", int(np.argmax((cumulative / final_area) >= 0.05)) if final_area > 0 else 0),
            ("first_major_burst", int(np.argmax(growth >= max(peak_growth * 0.25, 1e-9))) if peak_growth > 0 else 0),
            ("peak_expansion", peak_idx),
            ("final_meaningful_expansion", int(np.flatnonzero(growth >= max(peak_growth * 0.10, final_area * 0.01, 1e-9))[-1]) if peak_growth > 0 else obs - 1),
            ("geometric_quiescence", obs - 1),
        ]
        if obs > 2 and peak_growth > 0:
            after_peak = np.flatnonzero((np.arange(obs) > peak_idx) & (growth <= peak_growth * 0.25))
            if after_peak.size:
                event_specs.append(("slowdown_after_peak", int(after_peak[0])))
            active = growth >= max(peak_growth * 0.25, 1e-9)
            starts = np.flatnonzero(active & np.r_[True, ~active[:-1]])
            if starts.size > 1:
                event_specs.append(("secondary_burst", int(starts[1])))
        seen = set()
        for event_name, idx in event_specs:
            idx = int(np.clip(idx, 0, max(obs - 1, 0)))
            key = (event_name, idx)
            if key in seen:
                continue
            seen.add(key)
            event_rows.append(
                {
                    "fire_id": fire_id,
                    "event_name": event_name,
                    "slice_index": idx,
                    "relative_time": float(rel_t[idx]),
                    "timestamp": g.loc[idx, "timestamp"],
                    "ring_area_km2": float(growth[idx]),
                    "cumulative_area_km2": float(cumulative[idx]),
                }
            )

    features = pd.DataFrame(feature_rows)
    thresholds = {
        "area_q75": float(features["final_area_km2"].quantile(0.75)),
        "area_q90": float(features["final_area_km2"].quantile(0.90)),
        "duration_q50": float(features["duration_days"].quantile(0.50)),
        "slender_q75": float(features["slenderness_days_per_width"].quantile(0.75)),
    }
    features["shape_label"] = features.apply(lambda row: _assign_category(row, thresholds), axis=1)
    return features, pd.DataFrame(event_rows), pd.DataFrame(stage_rows)


def fit_pca(frame: pd.DataFrame, columns: list[str], n_components: int = 5) -> PcaResult:
    x = frame[columns].astype(float).replace([np.inf, -np.inf], np.nan)
    center = x.median()
    x = x.fillna(center)
    scale = x.std(ddof=0).replace(0, 1.0)
    z = ((x - center) / scale).to_numpy(float)
    u, s, vt = np.linalg.svd(z, full_matrices=False)
    scores = u[:, :n_components] * s[:n_components]
    ev = (s**2) / max(z.shape[0] - 1, 1)
    evr = ev / ev.sum()
    loadings = pd.DataFrame(vt[:n_components].T, index=columns, columns=[f"PC{i}" for i in range(1, n_components + 1)])
    return PcaResult(scores=scores, loadings=loadings, explained_variance_ratio=evr[:n_components], center=center, scale=scale)


def add_morphospace(features: pd.DataFrame) -> tuple[pd.DataFrame, PcaResult, list[str]]:
    geometry_cols = [
        "final_area_km2",
        "duration_days",
        "peak_growth_km2_per_day",
        "observation_count",
        "pulse_count",
        "reactivation_count",
        "peak_timing",
        "front_loaded_fraction",
        "late_growth_fraction",
        "terminal_taper_fraction",
        "growth_entropy",
        "developmental_velocity",
        "developmental_acceleration",
        "slenderness_days_per_width",
    ]
    profile_cols = [c for c in features.columns if c.startswith("width_p") or c.startswith("growth_p")]
    log_features = features.copy()
    for col in ["final_area_km2", "duration_days", "peak_growth_km2_per_day", "slenderness_days_per_width"]:
        log_features[f"log_{col}"] = np.log10(log_features[col].astype(float).clip(lower=1e-9))
    geometry_cols = [
        "log_final_area_km2",
        "log_duration_days",
        "log_peak_growth_km2_per_day",
        "log_slenderness_days_per_width",
        *[c for c in geometry_cols if not c.endswith("_km2") and not c.endswith("_days") and not c.endswith("_per_day") and not c.endswith("_per_width")],
        *profile_cols,
    ]
    pca = fit_pca(log_features, geometry_cols, n_components=5)
    out = features.copy()
    for i in range(pca.scores.shape[1]):
        out[f"morph_pc{i + 1}"] = pca.scores[:, i]
    return out, pca, geometry_cols


def assign_representatives(features: pd.DataFrame, n_representatives: int = 36, neighbors: int = 6) -> pd.DataFrame:
    pc_cols = ["morph_pc1", "morph_pc2", "morph_pc3"]
    pc = features[pc_cols].to_numpy(float)
    lo = np.nanquantile(pc, 0.01, axis=0)
    hi = np.nanquantile(pc, 0.99, axis=0)
    clipped = np.clip(pc, lo, hi)
    scale = clipped.std(axis=0)
    scale[scale == 0] = 1.0
    z = (clipped - clipped.mean(axis=0)) / scale

    candidate = (
        pd.DataFrame(z, columns=pc_cols)
        .round(4)
        .drop_duplicates()
        .sample(frac=1.0, random_state=20260722)
    )
    candidate_idx = candidate.index.to_numpy(int)
    candidate_z = z[candidate_idx]
    start = int(np.argmin(np.sum((candidate_z - np.median(candidate_z, axis=0)) ** 2, axis=1)))
    selected_positions = [start]
    min_dist = np.linalg.norm(candidate_z - candidate_z[start], axis=1)
    for _ in range(1, min(n_representatives, len(candidate_z))):
        next_pos = int(np.argmax(min_dist))
        selected_positions.append(next_pos)
        min_dist = np.minimum(min_dist, np.linalg.norm(candidate_z - candidate_z[next_pos], axis=1))
    selected_idx = candidate_idx[selected_positions]

    medoid_tree = cKDTree(z[selected_idx])
    _, assigned = medoid_tree.query(z, k=1)
    represented = pd.Series(assigned).value_counts().to_dict()
    all_tree = cKDTree(z)
    reps = []
    for rep_num, feature_idx in enumerate(selected_idx, start=1):
        row = features.iloc[int(feature_idx)].copy()
        _, neighbor_idx = all_tree.query(z[int(feature_idx)], k=min(neighbors + 1, len(features)))
        neighbor_ids = [features.iloc[int(i)]["fire_id"] for i in np.ravel(neighbor_idx) if features.iloc[int(i)]["fire_id"] != row["fire_id"]]
        row["representative_id"] = f"M{rep_num:02d}"
        row["represented_fire_count"] = int(represented.get(rep_num - 1, 0))
        row["neighbor_fire_ids"] = ",".join(neighbor_ids[:neighbors])
        reps.append(row)
    reps_df = pd.DataFrame(reps).sort_values(["morph_pc1", "morph_pc2"]).reset_index(drop=True)
    return reps_df


def build_stage_table(features: pd.DataFrame, profile_store: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for row in features.itertuples(index=False):
        profile = profile_store[row.fire_id]
        for stage, lo, hi in STAGES:
            stage_rows = profile[(profile["relative_time"] >= lo) & (profile["relative_time"] < hi)]
            if stage_rows.empty:
                continue
            growth = stage_rows["growth_fraction"].to_numpy(float)
            width = stage_rows["width"].to_numpy(float)
            climate_rows = stage_rows[stage_rows["climate_available"]]
            rows.append(
                {
                    "fire_id": row.fire_id,
                    "stage": stage,
                    "stage_midpoint": (lo + min(hi, 1.0)) / 2,
                    "stage_growth_fraction": float(np.nansum(growth)),
                    "stage_width_mean": float(np.nanmean(width)),
                    "stage_width_change": float(np.nanmax(width) - np.nanmin(width)),
                    "stage_observation_count": int(len(stage_rows)),
                    "stage_tmax_mean_c": float(climate_rows["tmax"].mean()) if not climate_rows.empty else np.nan,
                    "stage_vpd_mean_kpa": float(climate_rows["vpd"].mean()) if not climate_rows.empty else np.nan,
                    "stage_wind_mean_m_s": float(climate_rows["wind"].mean()) if not climate_rows.empty else np.nan,
                    "stage_wind_present_fraction": float((climate_rows["wind"] > 0.1).mean()) if not climate_rows.empty else np.nan,
                    "final_area_km2": row.final_area_km2,
                    "pulse_count": row.pulse_count,
                    "morph_pc1": row.morph_pc1,
                    "morph_pc2": row.morph_pc2,
                    "morph_pc3": row.morph_pc3,
                }
            )
    return pd.DataFrame(rows)


def extract_profiles_for_ids(slices: pd.DataFrame, fire_ids: set[str]) -> dict[str, pd.DataFrame]:
    profiles: dict[str, pd.DataFrame] = {}
    wanted = slices[slices["fire_id"].isin(fire_ids)].copy()
    for fire_id, group in wanted.groupby("fire_id", sort=False):
        g = group.sort_values("slice_index").reset_index(drop=True)
        obs = len(g)
        rel_t = np.array([0.5]) if obs == 1 else np.linspace(0, 1, obs)
        final_area = float(max(g["cumulative_area_km2"].max(), 1e-9))
        profiles[fire_id] = pd.DataFrame(
            {
                "relative_time": rel_t,
                "width": g["normalized_vase_width"].fillna(0).clip(lower=0).to_numpy(float),
                "growth_fraction": g["ring_area_km2"].fillna(0).clip(lower=0).to_numpy(float) / final_area,
                "timestamp": g["timestamp"].to_numpy(),
                "tmax": g["maximum_temperature_c"].to_numpy(float),
                "vpd": g["vpd_kpa"].to_numpy(float),
                "wind": g["wind_speed_m_s"].to_numpy(float),
                "climate_available": g["climate_available"].to_numpy(bool),
            }
        )
    return profiles


def _standardized_matrix(frame: pd.DataFrame, columns: list[str]) -> tuple[np.ndarray, list[str]]:
    clean_cols = [c for c in columns if c in frame.columns]
    x = frame[clean_cols].astype(float).replace([np.inf, -np.inf], np.nan)
    x = x.fillna(x.median())
    x = x.fillna(0.0)
    scale = x.std(ddof=0).replace(0, 1.0)
    z = ((x - x.mean()) / scale).to_numpy(float)
    return z, clean_cols


def _ols_r2(x: np.ndarray, y: np.ndarray, seed: int) -> float:
    mask = np.isfinite(y) & np.isfinite(x).all(axis=1)
    x = x[mask]
    y = y[mask]
    if len(y) < 200 or np.nanstd(y) <= 0:
        return np.nan
    rng = np.random.default_rng(seed)
    order = rng.permutation(len(y))
    split = max(50, int(len(y) * 0.75))
    train = order[:split]
    test = order[split:]
    x_train = np.c_[np.ones(len(train)), x[train]]
    x_test = np.c_[np.ones(len(test)), x[test]]
    coef = np.linalg.pinv(x_train).dot(y[train])
    pred = x_test.dot(coef)
    ss_res = float(np.sum((y[test] - pred) ** 2))
    ss_tot = float(np.sum((y[test] - y[test].mean()) ** 2))
    return 1.0 - ss_res / ss_tot if ss_tot > 0 else np.nan


def build_coupling_tables(features: pd.DataFrame, stage_table: pd.DataFrame, seed: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    climate_features = [
        "mean_maximum_temperature_c",
        "mean_minimum_temperature_c",
        "mean_vpd_kpa",
        "max_vpd_kpa",
        "mean_wind_speed_m_s",
        "wind_present_fraction",
    ]
    morph_targets = ["morph_pc1", "morph_pc2", "morph_pc3"]
    complete = features[features["climate_available"]].copy()
    cx, _ = _standardized_matrix(complete, climate_features)
    gx, _ = _standardized_matrix(complete, ["morph_pc1", "morph_pc2", "morph_pc3", "morph_pc4", "morph_pc5"])
    rows = []
    for target in morph_targets:
        rows.append({"question": "P(morphology | climate)", "target": target, "r2": _ols_r2(cx, complete[target].to_numpy(float), seed)})
    for target in climate_features:
        rows.append({"question": "P(climate | morphology)", "target": target, "r2": _ols_r2(gx, complete[target].to_numpy(float), seed + 1)})
    coupling = pd.DataFrame(rows)

    control_rows = []
    stage_order = {name: i for i, (name, _, _) in enumerate(STAGES)}
    for stage, sub in stage_table.dropna(subset=["stage"]).groupby("stage"):
        sub = sub.dropna(subset=["stage_tmax_mean_c", "stage_vpd_mean_kpa", "stage_wind_mean_m_s"])
        if len(sub) < 300:
            continue
        climate_cols = ["stage_tmax_mean_c", "stage_vpd_mean_kpa", "stage_wind_mean_m_s", "stage_wind_present_fraction"]
        geometry_cols = ["stage_growth_fraction", "stage_width_mean", "stage_width_change", "stage_observation_count", "pulse_count"]
        climate_x, _ = _standardized_matrix(sub, climate_cols)
        geometry_x, _ = _standardized_matrix(sub, geometry_cols)
        combined_x = np.c_[geometry_x, climate_x]
        for target in ["morph_pc1", "morph_pc2", "morph_pc3"]:
            control_rows.extend(
                [
                    {
                        "stage": stage,
                        "stage_order": stage_order[stage],
                        "target": target,
                        "model": "climate only",
                        "r2": _ols_r2(climate_x, sub[target].to_numpy(float), seed),
                    },
                    {
                        "stage": stage,
                        "stage_order": stage_order[stage],
                        "target": target,
                        "model": "geometry only",
                        "r2": _ols_r2(geometry_x, sub[target].to_numpy(float), seed + 1),
                    },
                    {
                        "stage": stage,
                        "stage_order": stage_order[stage],
                        "target": target,
                        "model": "geometry + climate",
                        "r2": _ols_r2(combined_x, sub[target].to_numpy(float), seed + 2),
                    },
                ]
            )
    return coupling, pd.DataFrame(control_rows)


def build_matched_pairs(features: pd.DataFrame, seed: int, sample_size: int = 25000, n_pairs: int = 8) -> pd.DataFrame:
    complete = features[features["climate_available"]].copy()
    climate_cols = ["mean_maximum_temperature_c", "mean_vpd_kpa", "mean_wind_speed_m_s", "wind_present_fraction"]
    complete = complete.dropna(subset=climate_cols + ["morph_pc1", "morph_pc2", "morph_pc3"])
    if len(complete) > sample_size:
        complete = complete.sample(sample_size, random_state=seed)
    geom, _ = _standardized_matrix(complete, ["morph_pc1", "morph_pc2", "morph_pc3"])
    clim, _ = _standardized_matrix(complete, climate_cols)
    geom_tree = cKDTree(geom)
    clim_tree = cKDTree(clim)
    rows = []
    for mode, tree, other_matrix, label_a, label_b in [
        ("similar morphology, different climate", geom_tree, clim, "geometry_distance", "climate_distance"),
        ("similar climate, different morphology", clim_tree, geom, "climate_distance", "geometry_distance"),
    ]:
        distances, indices = tree.query(tree.data, k=min(30, len(complete)))
        candidates = []
        for i in range(len(complete)):
            neighbor_ids = np.ravel(indices[i])[1:]
            neighbor_dists = np.ravel(distances[i])[1:]
            if len(neighbor_ids) == 0:
                continue
            other_dists = np.linalg.norm(other_matrix[neighbor_ids] - other_matrix[i], axis=1)
            jpos = int(np.argmax(other_dists))
            candidates.append((float(other_dists[jpos]), float(neighbor_dists[jpos]), i, int(neighbor_ids[jpos])))
        candidates = sorted(candidates, reverse=True)[:n_pairs]
        for rank, (other_dist, near_dist, i, j) in enumerate(candidates, start=1):
            a = complete.iloc[i]
            b = complete.iloc[j]
            rows.append(
                {
                    "comparison_type": mode,
                    "rank": rank,
                    "fire_id_a": a["fire_id"],
                    "fire_id_b": b["fire_id"],
                    label_a: near_dist,
                    label_b: other_dist,
                    "area_a_km2": float(a["final_area_km2"]),
                    "area_b_km2": float(b["final_area_km2"]),
                    "tmax_a_c": float(a["mean_maximum_temperature_c"]),
                    "tmax_b_c": float(b["mean_maximum_temperature_c"]),
                    "vpd_a_kpa": float(a["mean_vpd_kpa"]),
                    "vpd_b_kpa": float(b["mean_vpd_kpa"]),
                    "wind_a_m_s": float(a["mean_wind_speed_m_s"]),
                    "wind_b_m_s": float(b["mean_wind_speed_m_s"]),
                }
            )
    return pd.DataFrame(rows)


def page_title(fig: plt.Figure, title: str, subtitle: str | None = None) -> None:
    fig.text(0.045, 0.955, title, fontsize=20, fontweight="bold", ha="left", va="top")
    if subtitle:
        fig.text(0.045, 0.920, subtitle, fontsize=9.5, color="#555555", ha="left", va="top")


def draw_vase_3d(ax: plt.Axes, profile: pd.DataFrame, *, climate_col: str | None = None, cmap: str = "viridis", color: str = "#b12a1c") -> None:
    ax.set_aspect("equal")
    ax.axis("off")
    p = profile.copy()
    if p.empty:
        return
    if len(p) == 1:
        p = pd.concat([p, p], ignore_index=True)
        p.loc[:, "relative_time"] = [0.45, 0.55]
    y = p["relative_time"].to_numpy(float)
    w = np.clip(p["width"].to_numpy(float), 0.035, 1.0)
    x_left = -0.42 * w
    x_right = 0.42 * w
    ell_h = 0.055
    if climate_col and climate_col in p:
        vals = p[climate_col].to_numpy(float)
        finite = vals[np.isfinite(vals)]
        if finite.size:
            norm = plt.Normalize(float(np.nanquantile(finite, 0.05)), float(np.nanquantile(finite, 0.95)))
            colors = plt.get_cmap(cmap)(norm(vals))
        else:
            colors = [color] * len(p)
    else:
        colors = [color] * len(p)
    segments = []
    for i in range(len(y) - 1):
        segments.append([(x_left[i], y[i]), (x_left[i + 1], y[i + 1])])
        segments.append([(x_right[i], y[i]), (x_right[i + 1], y[i + 1])])
    ax.add_collection(LineCollection(segments, colors="#252525", linewidths=0.35, alpha=0.75))
    for yi, wi, ci in zip(y, w, colors):
        ax.add_patch(Ellipse((0, yi), width=0.84 * wi, height=ell_h, facecolor=ci, edgecolor="#252525", linewidth=0.25, alpha=0.78))
    ax.plot(x_left, y, color="#202020", lw=0.8)
    ax.plot(x_right, y, color="#202020", lw=0.8)
    ax.set_xlim(-0.5, 0.5)
    ax.set_ylim(-0.03, 1.04)


def plot_overview(pdf: PdfPages, features: pd.DataFrame, pca: PcaResult, coupling: pd.DataFrame) -> None:
    fig = plt.figure(figsize=(16, 10))
    page_title(fig, "Fire VASE Developmental Morphospace", "Geometry defines the morphospace; climate is attached afterward and evaluated as coupling.")
    ax = fig.add_axes([0.06, 0.16, 0.52, 0.64])
    sample = features.sample(min(60000, len(features)), random_state=7)
    ax.scatter(sample["morph_pc1"], sample["morph_pc2"], s=2, alpha=0.12, color="#333333", rasterized=True)
    ax.set_xlabel(f"PC1 ({pca.explained_variance_ratio[0]:.1%} geometry variance)")
    ax.set_ylabel(f"PC2 ({pca.explained_variance_ratio[1]:.1%} geometry variance)")
    ax.set_title("Continuous geometry-first morphospace")
    ax.grid(color="#e6e6e6", lw=0.6)
    txt = [
        f"Fires represented: {len(features):,}",
        f"Climate-complete fires: {features['climate_available'].sum():,}",
        f"Geometry PC1-PC5 variance: {pca.explained_variance_ratio[:5].sum():.1%}",
        f"Median duration: {features['duration_days'].median():.1f} days",
        f"Median final area: {features['final_area_km2'].median():.2f} km2",
    ]
    fig.text(0.64, 0.72, "\n".join(txt), fontsize=15, fontweight="bold", va="top")
    summary = (
        "Interpretation: categories are labels placed inside the space, not the axes of the space. "
        "The first pass estimates coupling with linear information proxies, so low R2 should be read "
        "as weak linear recoverability rather than proof of no relationship."
    )
    fig.text(0.64, 0.48, textwrap.fill(summary, 52), fontsize=11, color="#444444", va="top")
    cou = coupling.pivot_table(index="question", values="r2", aggfunc="mean").reset_index()
    fig.text(0.64, 0.30, "Mean directional coupling proxy", fontsize=12, fontweight="bold")
    y = 0.25
    for row in cou.itertuples():
        fig.text(0.64, y, f"{row.question}: R2={row.r2:.3f}", fontsize=11)
        y -= 0.045
    pdf.savefig(fig)
    plt.close(fig)


def plot_morphospace_medoids(pdf: PdfPages, features: pd.DataFrame, reps: pd.DataFrame, profiles: dict[str, pd.DataFrame]) -> None:
    fig = plt.figure(figsize=(16, 10))
    page_title(fig, "Figure 2: Morphospace With Representative Fire VASEs", "Medoids are selected by farthest-point coverage in PC1-PC3. Counts are fires assigned to each nearest medoid.")
    ax = fig.add_axes([0.06, 0.11, 0.62, 0.76])
    sample = features.sample(min(80000, len(features)), random_state=11)
    ax.scatter(sample["morph_pc1"], sample["morph_pc2"], c="#777777", s=1.8, alpha=0.10, rasterized=True)
    ax.scatter(reps["morph_pc1"], reps["morph_pc2"], c="#b12a1c", s=18, zorder=3)
    for row in reps.itertuples():
        ax.text(row.morph_pc1, row.morph_pc2, row.representative_id, fontsize=6, color="#111111")
    ax.set_xlabel("Morphology PC1")
    ax.set_ylabel("Morphology PC2")
    ax.grid(color="#e6e6e6", lw=0.6)
    slots = reps.head(12).reset_index(drop=True)
    for i, row in slots.iterrows():
        x = 0.72 + (i % 3) * 0.085
        y = 0.67 - (i // 3) * 0.18
        vase_ax = fig.add_axes([x, y, 0.070, 0.13])
        draw_vase_3d(vase_ax, profiles[row["fire_id"]], color=CATEGORY_COLORS.get(row["shape_label"], "#b12a1c"))
        fig.text(x + 0.035, y - 0.012, f"{row['representative_id']} n={int(row['represented_fire_count']):,}", ha="center", fontsize=7)
    pdf.savefig(fig)
    plt.close(fig)


def plot_loading_page(pdf: PdfPages, pca: PcaResult) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(16, 9))
    page_title(fig, "What Dimensions Organize Wildfire Development?", "Largest absolute geometry-feature loadings for the first three morphospace axes.")
    for ax, pc in zip(axes, ["PC1", "PC2", "PC3"]):
        vals = pca.loadings[pc].sort_values(key=lambda s: s.abs(), ascending=False).head(12).sort_values()
        ax.barh(vals.index, vals.values, color=np.where(vals.values > 0, "#b12a1c", "#1f6f78"))
        ax.axvline(0, color="#222222", lw=0.8)
        ax.set_title(f"{pc} ({pca.explained_variance_ratio[int(pc[-1]) - 1]:.1%})")
        ax.tick_params(labelsize=7)
        ax.grid(axis="x", color="#e6e6e6")
    fig.subplots_adjust(left=0.17, right=0.98, top=0.83, bottom=0.08, wspace=0.45)
    pdf.savefig(fig)
    plt.close(fig)


def plot_field_guide(pdf: PdfPages, reps: pd.DataFrame, profiles: dict[str, pd.DataFrame]) -> None:
    for page, start in enumerate(range(0, len(reps), 9), start=1):
        sub = reps.iloc[start : start + 9].reset_index(drop=True)
        fig = plt.figure(figsize=(16, 10))
        page_title(fig, f"Figure 3: Morphological Field Guide, Page {page}", "Each representative is a real medoid VASE. Rings are observed developmental slices; colors show maximum temperature where available.")
        for i, row in sub.iterrows():
            col = i % 3
            rr = i // 3
            left = 0.055 + col * 0.315
            bottom = 0.64 - rr * 0.285
            ax = fig.add_axes([left, bottom, 0.105, 0.205])
            draw_vase_3d(ax, profiles[row["fire_id"]], climate_col="tmax", cmap="plasma", color=CATEGORY_COLORS.get(row["shape_label"], "#b12a1c"))
            label = (
                f"{row['representative_id']} fire {row['fire_id']}\n"
                f"{row['shape_label']} | represents {int(row['represented_fire_count']):,}\n"
                f"area {row['final_area_km2']:.1f} km2 | duration {row['duration_days']:.1f} d | pulses {int(row['pulse_count'])}\n"
                f"tmax {row['mean_maximum_temperature_c']:.1f} C | VPD {row['mean_vpd_kpa']:.2f} kPa | wind {row['mean_wind_speed_m_s']:.1f} m/s\n"
                f"neighbors: {row['neighbor_fire_ids']}"
            )
            fig.text(left + 0.12, bottom + 0.16, label, fontsize=7.8, va="top")
        pdf.savefig(fig)
        plt.close(fig)


def plot_climate_morphospace(pdf: PdfPages, features: pd.DataFrame) -> None:
    complete = features[features["climate_available"]].copy()
    sample = complete.sample(min(70000, len(complete)), random_state=13)
    fig, axes = plt.subplots(1, 3, figsize=(16, 8.5))
    page_title(fig, "Figure 4: Climate Mapped Onto Morphospace", "Climate is evaluated after geometry defines the morphospace.")
    specs = [
        ("mean_maximum_temperature_c", "Mean maximum temperature (C)", "plasma"),
        ("mean_vpd_kpa", "Mean VPD (kPa)", "viridis"),
        ("mean_wind_speed_m_s", "Mean wind speed (m/s)", "cividis"),
    ]
    for ax, (col, title, cmap) in zip(axes, specs):
        sc = ax.scatter(sample["morph_pc1"], sample["morph_pc2"], c=sample[col], s=2, alpha=0.35, cmap=cmap, rasterized=True)
        ax.set_title(title)
        ax.set_xlabel("Morphology PC1")
        ax.grid(color="#e6e6e6", lw=0.6)
        fig.colorbar(sc, ax=ax, fraction=0.046)
    axes[0].set_ylabel("Morphology PC2")
    fig.subplots_adjust(left=0.06, right=0.97, top=0.82, bottom=0.10, wspace=0.25)
    pdf.savefig(fig)
    plt.close(fig)


def plot_coupling(pdf: PdfPages, coupling: pd.DataFrame, control: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(16, 8.5))
    page_title(fig, "Figure 6: Developmental Control Profile", "Predictive information proxies compare climate-only, geometry-only, and combined models through development.")
    pivot = coupling.pivot_table(index="target", columns="question", values="r2", aggfunc="mean").fillna(0)
    pivot = pivot.rename(
        index={
            "morph_pc1": "morph PC1",
            "morph_pc2": "morph PC2",
            "morph_pc3": "morph PC3",
            "mean_maximum_temperature_c": "mean Tmax",
            "mean_minimum_temperature_c": "mean Tmin",
            "mean_vpd_kpa": "mean VPD",
            "max_vpd_kpa": "max VPD",
            "mean_wind_speed_m_s": "mean wind",
            "wind_present_fraction": "wind frequency",
        }
    )
    pivot.plot(kind="barh", ax=axes[0], color=["#7251b5", "#1f6f78"])
    axes[0].set_title("Directional coupling over whole fire")
    axes[0].set_xlabel("Held-out R2")
    axes[0].grid(axis="x", color="#e6e6e6")
    agg = control.groupby(["stage", "stage_order", "model"])["r2"].mean().reset_index().sort_values("stage_order")
    for model, color in [("climate only", "#7251b5"), ("geometry only", "#1f6f78"), ("geometry + climate", "#b12a1c")]:
        sub = agg[agg["model"] == model]
        axes[1].plot(sub["stage"], sub["r2"], marker="o", label=model, color=color)
    axes[1].set_title("Information about final morphospace position by stage")
    axes[1].set_ylabel("Mean held-out R2 across PC1-PC3")
    axes[1].set_ylim(bottom=min(0, float(agg["r2"].min()) - 0.02), top=max(0.1, float(agg["r2"].max()) + 0.05))
    axes[1].grid(axis="y", color="#e6e6e6")
    axes[1].legend(frameon=False)
    axes[0].tick_params(axis="y", labelsize=9)
    fig.subplots_adjust(left=0.12, right=0.97, top=0.82, bottom=0.14, wspace=0.32)
    pdf.savefig(fig)
    plt.close(fig)


def plot_matched_pairs(pdf: PdfPages, pairs: pd.DataFrame, profiles: dict[str, pd.DataFrame]) -> None:
    fig = plt.figure(figsize=(16, 10))
    page_title(fig, "Figure 5: Matched Comparisons", "Pairs estimate resilience: similar morphology under different climate, and similar climate with different morphology.")
    rows = pairs.groupby("comparison_type").head(3).reset_index(drop=True)
    for i, row in rows.iterrows():
        top = 0.76 - i * 0.135
        for j, fire_id in enumerate([row["fire_id_a"], row["fire_id_b"]]):
            ax = fig.add_axes([0.055 + j * 0.085, top - 0.065, 0.06, 0.105])
            draw_vase_3d(ax, profiles[str(fire_id)], climate_col="vpd", cmap="viridis")
        text = (
            f"{row['comparison_type']} | {row['fire_id_a']} vs {row['fire_id_b']}\n"
            f"area {row['area_a_km2']:.1f}/{row['area_b_km2']:.1f} km2, "
            f"tmax {row['tmax_a_c']:.1f}/{row['tmax_b_c']:.1f} C, "
            f"VPD {row['vpd_a_kpa']:.2f}/{row['vpd_b_kpa']:.2f} kPa, "
            f"wind {row['wind_a_m_s']:.1f}/{row['wind_b_m_s']:.1f} m/s"
        )
        fig.text(0.23, top, text, fontsize=9, va="center")
    pdf.savefig(fig)
    plt.close(fig)


def write_pdf(
    output: Path,
    features: pd.DataFrame,
    reps: pd.DataFrame,
    profiles: dict[str, pd.DataFrame],
    pca: PcaResult,
    coupling: pd.DataFrame,
    control: pd.DataFrame,
    pairs: pd.DataFrame,
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with PdfPages(output) as pdf:
        plot_overview(pdf, features, pca, coupling)
        plot_morphospace_medoids(pdf, features, reps, profiles)
        plot_loading_page(pdf, pca)
        plot_field_guide(pdf, reps, profiles)
        plot_climate_morphospace(pdf, features)
        plot_matched_pairs(pdf, pairs, profiles)
        plot_coupling(pdf, coupling, control)
        meta = pdf.infodict()
        meta["Title"] = "Fire VASE Developmental Morphology Atlas"
        meta["Author"] = "CubeDynamics"
        meta["Subject"] = "Continuous wildfire developmental morphospace and climate coupling"


def run(args: argparse.Namespace) -> dict:
    slices, traits = read_tables(args.table_root)
    features, events, stage_table = build_features_and_events(slices, traits, profile_points=args.profile_points)
    features, pca, geometry_cols = add_morphospace(features)
    reps = assign_representatives(features, n_representatives=args.n_representatives, neighbors=6)
    stage_table = stage_table.merge(
        features[["fire_id", "final_area_km2", "pulse_count", "morph_pc1", "morph_pc2", "morph_pc3"]],
        on="fire_id",
        how="left",
    )
    coupling, control = build_coupling_tables(features, stage_table, seed=args.seed)
    pairs = build_matched_pairs(features, seed=args.seed)
    profile_ids = set(reps["fire_id"].astype(str))
    if not pairs.empty:
        profile_ids.update(pairs["fire_id_a"].astype(str))
        profile_ids.update(pairs["fire_id_b"].astype(str))
    profiles = extract_profiles_for_ids(slices, profile_ids)

    args.data_output_dir.mkdir(parents=True, exist_ok=True)
    features_path = args.data_output_dir / "developmental_morphospace_features.parquet"
    reps_path = args.data_output_dir / "developmental_morphospace_medoids.parquet"
    events_path = args.data_output_dir / "developmental_geometry_events.parquet"
    stage_path = args.data_output_dir / "developmental_stage_table.parquet"
    coupling_path = args.data_output_dir / "developmental_climate_coupling.parquet"
    control_path = args.data_output_dir / "developmental_control_profile.parquet"
    pairs_path = args.data_output_dir / "developmental_matched_pairs.parquet"
    loadings_path = args.data_output_dir / "developmental_morphospace_loadings.csv"

    features.to_parquet(features_path, index=False)
    reps.to_parquet(reps_path, index=False)
    events.to_parquet(events_path, index=False)
    stage_table.to_parquet(stage_path, index=False)
    coupling.to_parquet(coupling_path, index=False)
    control.to_parquet(control_path, index=False)
    pairs.to_parquet(pairs_path, index=False)
    pca.loadings.to_csv(loadings_path)

    write_pdf(args.output, features, reps, profiles, pca, coupling, control, pairs)

    report = {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "input_table_root": args.table_root.as_posix(),
        "pdf": args.output.as_posix(),
        "n_fires": int(len(features)),
        "n_climate_complete_fires": int(features["climate_available"].sum()),
        "n_representatives": int(len(reps)),
        "morphospace_explained_variance_pc1_to_pc5": [float(v) for v in pca.explained_variance_ratio[:5]],
        "mean_directional_coupling_r2": {
            row["question"]: float(row["r2"])
            for row in coupling.groupby("question")["r2"].mean().reset_index().to_dict("records")
        },
        "outputs": {
            "features": features_path.as_posix(),
            "medoids": reps_path.as_posix(),
            "geometry_events": events_path.as_posix(),
            "stage_table": stage_path.as_posix(),
            "climate_coupling": coupling_path.as_posix(),
            "control_profile": control_path.as_posix(),
            "matched_pairs": pairs_path.as_posix(),
            "loadings": loadings_path.as_posix(),
        },
        "notes": [
            "Morphospace PCA is fit on geometry-only VASE profile and developmental trait features.",
            "Climate is evaluated afterward from the full daily gridMET-attributed vase_slices table.",
            "Coupling R2 values are first-pass linear information proxies, not optimized predictive models.",
        ],
    }
    args.manifest.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--table-root", type=Path, default=Path("scratch/fire_vase_run_full/tables"))
    parser.add_argument("--data-output-dir", type=Path, default=Path("scratch/fire_vase_developmental_morphology"))
    parser.add_argument("--output", type=Path, default=Path("output/pdf/fire_vase_developmental_morphology_atlas.pdf"))
    parser.add_argument("--manifest", type=Path, default=Path("output/pdf/fire_vase_developmental_morphology_atlas_manifest.json"))
    parser.add_argument("--profile-points", type=int, default=11)
    parser.add_argument("--n-representatives", type=int, default=36)
    parser.add_argument("--seed", type=int, default=20260722)
    args = parser.parse_args()
    report = run(args)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
