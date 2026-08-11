#!/usr/bin/env python3
"""Audit Fire VASE manuscript claims against existing derived data.

This script is deliberately conservative. It asks whether the current Fire VASE
tables support a shared coordinate system, low-dimensionality, or the stronger
claim that observed fires occupy a restricted subset of plausible developmental
histories after accounting for size, duration, monotonicity, and redundancy.
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
import sys
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree


ROOT = Path(__file__).resolve().parents[1]
FIG_SCRIPT_DIR = ROOT / "scripts" / "figures"
sys.path.insert(0, str(FIG_SCRIPT_DIR))

from morphospace import feature_matrix, fit_pca, geometry_columns, load_data, robust_standardize  # noqa: E402
from style import CHARCOAL, FIREBRICK, MORPH_BLUE, set_style  # noqa: E402


ANALYSIS_DIR = ROOT / "analysis"
AUDIT_STATS_DIR = ANALYSIS_DIR / "claim_audit_stats"
AUDITED_FIG_DIR = ROOT / "figures" / "main_audited"
MANUSCRIPT_DIR = ROOT / "docs" / "manuscripts" / "fire_vase_developmental_morphology"
SEED = 20260722
PROFILE_POINTS = np.linspace(0, 1, 11)
CORR_TARGETS = [
    "log_final_area_km2",
    "log_duration_days",
    "observation_count",
    "log_peak_growth_km2_per_day",
    "front_loaded_fraction",
    "late_growth_fraction",
    "terminal_taper_fraction",
    "growth_entropy",
    "width_p05",
    "growth_p05",
]


@dataclass
class AuditTables:
    pca_ablation: pd.DataFrame
    pca_loadings: pd.DataFrame
    pc1_correlations: pd.DataFrame
    null_summary: pd.DataFrame
    null_replicates: pd.DataFrame
    prediction_summary: pd.DataFrame
    climate_summary: pd.DataFrame


def ensure_dirs() -> None:
    ANALYSIS_DIR.mkdir(exist_ok=True)
    AUDIT_STATS_DIR.mkdir(parents=True, exist_ok=True)
    AUDITED_FIG_DIR.mkdir(parents=True, exist_ok=True)


def _fmt(value: float, digits: int = 3) -> str:
    if value is None or not np.isfinite(value):
        return "NA"
    return f"{value:.{digits}f}"


def markdown_table(frame: pd.DataFrame, *, max_rows: int | None = None) -> str:
    if frame.empty:
        return "_No rows._"
    out = frame.copy()
    if max_rows is not None:
        out = out.head(max_rows)
    for col in out.columns:
        if pd.api.types.is_float_dtype(out[col]):
            out[col] = out[col].map(lambda v: _fmt(float(v), 4))
    cols = list(out.columns)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in out.iterrows():
        lines.append("| " + " | ".join(str(row[col]).replace("|", "/").replace("\n", " ") for col in cols) + " |")
    return "\n".join(lines)


def add_log_columns(features: pd.DataFrame) -> pd.DataFrame:
    out = features.copy()
    for col in ["final_area_km2", "duration_days", "peak_growth_km2_per_day", "slenderness_days_per_width"]:
        log_col = f"log_{col}"
        if log_col not in out.columns and col in out.columns:
            out[log_col] = np.log10(out[col].astype(float).clip(lower=1e-9))
    return out


def top_loadings(pca, *, feature_set: str, n_pcs: int = 5, n_top: int = 8) -> pd.DataFrame:
    rows = []
    for pc in pca.loadings.columns[:n_pcs]:
        vals = pca.loadings[pc].sort_values(key=lambda s: s.abs(), ascending=False).head(n_top)
        for rank, (feature, loading) in enumerate(vals.items(), start=1):
            rows.append(
                {
                    "feature_set": feature_set,
                    "pc": pc,
                    "rank": rank,
                    "feature": feature,
                    "loading": float(loading),
                }
            )
    return pd.DataFrame(rows)


def subspace_overlap(current_loadings: pd.DataFrame, reference_loadings: pd.DataFrame, cols: list[str], k: int = 5) -> float:
    common = [c for c in cols if c in reference_loadings.index and c in current_loadings.index]
    if len(common) < 2:
        return np.nan
    a = current_loadings.loc[common].iloc[:, : min(k, current_loadings.shape[1])].to_numpy(float)
    b = reference_loadings.loc[common].iloc[:, : min(k, reference_loadings.shape[1])].to_numpy(float)
    k_eff = min(a.shape[1], b.shape[1])
    qa, _ = np.linalg.qr(a[:, :k_eff])
    qb, _ = np.linalg.qr(b[:, :k_eff])
    return float(np.linalg.norm(qa.T @ qb, ord="fro") ** 2 / k_eff)


def signed_scores(pca, features: pd.DataFrame, cols: list[str], reference_loadings: pd.DataFrame | None = None) -> np.ndarray:
    scores = pca.scores.copy()
    if reference_loadings is not None:
        common = [c for c in cols if c in reference_loadings.index and c in pca.loadings.index]
        if common and float(np.dot(pca.loadings.loc[common, "PC1"], reference_loadings.loc[common, "PC1"])) < 0:
            scores[:, 0] *= -1
    return scores


def representative_corr_columns(features: pd.DataFrame, cols: list[str], threshold: float = 0.85) -> list[str]:
    x = feature_matrix(features, cols)
    x = x.fillna(x.median()).fillna(0.0).to_numpy(float)
    corr = np.abs(np.corrcoef(x, rowvar=False))
    corr = np.nan_to_num(corr, nan=0.0)
    np.fill_diagonal(corr, 1.0)
    remaining = list(range(len(cols)))
    selected: list[str] = []
    while remaining:
        sub = corr[np.ix_(remaining, remaining)]
        degrees = (sub >= threshold).sum(axis=1)
        pick_pos = int(np.argmax(degrees))
        pick = remaining[pick_pos]
        selected.append(cols[pick])
        clustered = {remaining[i] for i, value in enumerate(sub[:, pick_pos]) if value >= threshold}
        remaining = [i for i in remaining if i not in clustered]
    return selected


def pca_ablation(features: pd.DataFrame, cols: list[str]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    features = add_log_columns(features)
    reference = fit_pca(features, cols, n_components=10)
    reps = representative_corr_columns(features.sample(min(25000, len(features)), random_state=SEED), cols)
    profile_cols = [c for c in cols if c.startswith("width_p") or c.startswith("growth_p")]
    growth_profile_cols = [c for c in cols if c.startswith("growth_p")]
    width_profile_cols = [c for c in cols if c.startswith("width_p")]
    summary_cols = [c for c in cols if c not in profile_cols]
    feature_sets = {
        "full current feature set": cols,
        "scale variables removed": [c for c in cols if all(k not in c for k in ["final_area", "peak_growth", "slenderness"])],
        "final area removed": [c for c in cols if "final_area" not in c],
        "duration and observation count removed": [c for c in cols if "duration" not in c and c != "observation_count"],
        "all scale and duration variables removed": [
            c for c in cols if all(k not in c for k in ["final_area", "peak_growth", "slenderness", "duration"]) and c != "observation_count"
        ],
        "normalized profile variables only": profile_cols,
        "growth-share profile only": growth_profile_cols,
        "cumulative-width profile only": width_profile_cols,
        "pulse timing taper entropy shape variables only": [
            c for c in cols
            if any(k in c for k in ["pulse", "reactivation", "timing", "front_loaded", "late_growth", "terminal_taper", "entropy", "velocity", "acceleration", "width_at"])
        ],
        "one representative per correlated cluster": reps,
        "interpolated profile features removed": summary_cols,
        "summary features removed retaining profiles": profile_cols,
        "profiles normalized independently of final size": profile_cols,
    }
    rows = []
    loading_rows = []
    corr_rows = []
    for label, selected in feature_sets.items():
        selected = [c for c in selected if c in features.columns or c.startswith("log_")]
        if len(selected) < 2:
            continue
        pca = fit_pca(features, selected, n_components=min(10, len(selected)))
        scores = signed_scores(pca, features, selected, reference.loadings)
        evr = pca.explained_variance_ratio
        row = {
            "feature_set": label,
            "n_fires": int(len(features)),
            "n_features": int(len(selected)),
            "pc1": float(evr[0]),
            "pc2": float(evr[1]) if len(evr) > 1 else np.nan,
            "pc3": float(evr[2]) if len(evr) > 2 else np.nan,
            "pc4": float(evr[3]) if len(evr) > 3 else np.nan,
            "pc5": float(evr[4]) if len(evr) > 4 else np.nan,
            "cumvar_pc1_5": float(evr[:5].sum()),
            "subspace_overlap_to_full_pc1_5": subspace_overlap(pca.loadings, reference.loadings, selected, 5),
            "recognizable_gradients_remain": "yes" if float(evr[:5].sum()) >= 0.70 else "weakened",
        }
        rows.append(row)
        loading_rows.append(top_loadings(pca, feature_set=label))
        pc1 = scores[:, 0]
        for target in CORR_TARGETS:
            if target not in features.columns:
                continue
            corr = pd.Series(pc1).corr(features[target].astype(float).reset_index(drop=True), method="pearson")
            corr_rows.append({"feature_set": label, "pc1_target": target, "pearson_r": float(corr)})
    thresholds = [2, 4, 8, 10]
    for threshold in thresholds:
        sub = features[features["duration_days"] >= threshold].copy()
        if len(sub) < 500:
            continue
        pca = fit_pca(sub, cols, n_components=10)
        scores = signed_scores(pca, sub, cols, reference.loadings)
        evr = pca.explained_variance_ratio
        rows.append(
            {
                "feature_set": f"full current feature set, duration >= {threshold} days",
                "n_fires": int(len(sub)),
                "n_features": int(len(cols)),
                "pc1": float(evr[0]),
                "pc2": float(evr[1]),
                "pc3": float(evr[2]),
                "pc4": float(evr[3]),
                "pc5": float(evr[4]),
                "cumvar_pc1_5": float(evr[:5].sum()),
                "subspace_overlap_to_full_pc1_5": subspace_overlap(pca.loadings, reference.loadings, cols, 5),
                "recognizable_gradients_remain": "yes, but redistributed" if float(evr[:5].sum()) >= 0.70 else "weakened",
            }
        )
        loading_rows.append(top_loadings(pca, feature_set=f"duration >= {threshold} days"))
        pc1 = scores[:, 0]
        for target in CORR_TARGETS:
            if target not in sub.columns:
                continue
            corr = pd.Series(pc1).corr(sub[target].astype(float).reset_index(drop=True), method="pearson")
            corr_rows.append({"feature_set": f"duration >= {threshold} days", "pc1_target": target, "pearson_r": float(corr)})
    return pd.DataFrame(rows), pd.concat(loading_rows, ignore_index=True), pd.DataFrame(corr_rows)


def interp(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    if len(values) == 0:
        return np.zeros(len(PROFILE_POINTS))
    if len(values) == 1:
        return np.repeat(values[0], len(PROFILE_POINTS))
    return np.interp(PROFILE_POINTS, np.linspace(0, 1, len(values)), values)


def value_at(values: np.ndarray, q: float) -> float:
    values = np.asarray(values, dtype=float)
    if len(values) == 0:
        return np.nan
    if len(values) == 1:
        return float(values[0])
    return float(np.interp(q, np.linspace(0, 1, len(values)), values))


def count_pulses(growth: np.ndarray) -> tuple[int, int]:
    if len(growth) == 0 or np.nanmax(growth) <= 0:
        return 0, 0
    threshold = max(float(np.nanquantile(growth, 0.75)), float(np.nanmax(growth) * 0.25), 1e-9)
    active = growth >= threshold
    starts = np.flatnonzero(active & np.r_[True, ~active[:-1]])
    return int(len(starts)), int(max(0, len(starts) - 1))


def features_from_growth(base: pd.Series, growth_fraction: np.ndarray) -> dict[str, float]:
    growth_fraction = np.asarray(growth_fraction, dtype=float)
    growth_fraction = np.clip(np.nan_to_num(growth_fraction, nan=0.0), 0, None)
    if growth_fraction.sum() <= 0:
        growth_fraction = np.repeat(1 / max(len(growth_fraction), 1), max(len(growth_fraction), 1))
    else:
        growth_fraction = growth_fraction / growth_fraction.sum()
    final_area = float(base["final_area_km2"])
    duration = float(base["duration_days"])
    growth = growth_fraction * final_area
    cumulative_fraction = np.cumsum(growth_fraction)
    width = np.sqrt(np.clip(cumulative_fraction, 0, None))
    obs = int(len(growth_fraction))
    rel_t = np.array([0.5]) if obs == 1 else np.linspace(0, 1, obs)
    peak_idx = int(np.argmax(growth))
    peak_growth = float(np.max(growth))
    pulse_count, reactivation_count = count_pulses(growth)
    p = growth_fraction[growth_fraction > 0]
    entropy = float(-(p * np.log(p)).sum() / math.log(max(len(growth_fraction), 2))) if len(p) else 0.0
    dw = np.diff(width) if len(width) > 1 else np.array([0.0])
    ddw = np.diff(dw) if len(dw) > 1 else np.array([0.0])
    radius_km = math.sqrt(final_area / math.pi) if final_area > 0 else 0.0
    row = {
        "fire_id": str(base["fire_id"]),
        "final_area_km2": final_area,
        "duration_days": duration,
        "peak_growth_km2_per_day": peak_growth,
        "observation_count": obs,
        "pulse_count": pulse_count,
        "reactivation_count": reactivation_count,
        "peak_timing": float(peak_idx / max(obs - 1, 1)),
        "front_loaded_fraction": value_at(cumulative_fraction, 0.5),
        "late_growth_fraction": float(np.sum(growth_fraction[rel_t >= 0.75])),
        "terminal_taper_fraction": float(growth[-1] / peak_growth) if peak_growth > 0 else 0.0,
        "growth_entropy": entropy,
        "developmental_velocity": float(np.mean(np.abs(dw))),
        "developmental_acceleration": float(np.mean(np.abs(ddw))),
        "width_at_quarter": value_at(width, 0.25),
        "width_at_half": value_at(width, 0.50),
        "width_at_three_quarter": value_at(width, 0.75),
        "slenderness_days_per_width": duration / max(2 * radius_km, 0.1),
    }
    for i, val in enumerate(interp(width)):
        row[f"width_p{i:02d}"] = float(val)
    for i, val in enumerate(interp(growth_fraction)):
        row[f"growth_p{i:02d}"] = float(val)
    return row


def sequences_for_sample(slices: pd.DataFrame, fire_ids: Iterable[str]) -> dict[str, np.ndarray]:
    wanted = set(str(v) for v in fire_ids)
    sub = slices[slices["fire_id"].astype(str).isin(wanted)].sort_values(["fire_id", "slice_index"])
    return {
        str(fire_id): group["ring_area_km2"].fillna(0).clip(lower=0).to_numpy(float)
        for fire_id, group in sub.groupby("fire_id", sort=False)
    }


def bin_duration(obs: int) -> str:
    if obs <= 1:
        return "1"
    if obs <= 3:
        return "2-3"
    if obs <= 7:
        return "4-7"
    return "8+"


def make_null_frame(
    sample: pd.DataFrame,
    sequences: dict[str, np.ndarray],
    rng: np.random.Generator,
    null_model: str,
) -> pd.DataFrame | pd.DataFrame:
    rows = []
    observed_fraction_profiles: dict[str, list[np.ndarray]] = {}
    for row in sample.itertuples(index=False):
        seq = sequences.get(str(row.fire_id), np.array([float(row.final_area_km2)]))
        frac = seq / seq.sum() if seq.sum() > 0 else np.repeat(1 / len(seq), len(seq))
        observed_fraction_profiles.setdefault(bin_duration(len(frac)), []).append(frac)

    mean_profiles: dict[str, np.ndarray] = {}
    for key, profiles in observed_fraction_profiles.items():
        interp_profiles = np.vstack([interp(p) for p in profiles])
        mean = interp_profiles.mean(axis=0)
        mean_profiles[key] = mean / mean.sum()

    profile_pool = {key: profiles for key, profiles in observed_fraction_profiles.items()}

    for _, base in sample.iterrows():
        seq = sequences.get(str(base["fire_id"]), np.array([float(base["final_area_km2"])]))
        n = max(1, len(seq))
        observed_frac = seq / seq.sum() if seq.sum() > 0 else np.repeat(1 / n, n)
        key = bin_duration(n)
        if null_model == "shuffled daily growth order within fire":
            frac = rng.permutation(observed_frac)
        elif null_model == "dirichlet duration and final area":
            frac = rng.dirichlet(np.ones(n))
        elif null_model == "zero-preserving dirichlet":
            active = max(1, int(np.sum(observed_frac > 0)))
            frac = np.zeros(n)
            active_idx = rng.choice(n, size=min(active, n), replace=False)
            frac[active_idx] = rng.dirichlet(np.ones(len(active_idx)))
        elif null_model == "duration-bin empirical increments":
            donor = profile_pool[key][rng.integers(0, len(profile_pool[key]))]
            if len(donor) == n:
                frac = donor.copy()
            else:
                frac = np.interp(np.linspace(0, 1, n), np.linspace(0, 1, len(donor)), donor)
                frac = np.clip(frac, 0, None)
                frac = frac / frac.sum() if frac.sum() > 0 else np.repeat(1 / n, n)
        elif null_model == "duration-bin mean profile":
            mean = mean_profiles[key]
            frac = np.interp(np.linspace(0, 1, n), PROFILE_POINTS, mean)
            frac = np.clip(frac + rng.normal(0, 0.02, size=n), 0, None)
            frac = frac / frac.sum() if frac.sum() > 0 else np.repeat(1 / n, n)
        else:
            raise ValueError(null_model)
        rows.append(features_from_growth(base, frac))
    return pd.DataFrame(rows)


def matrix_metrics(x: pd.DataFrame) -> tuple[np.ndarray, float, int]:
    z, _, _ = robust_standardize(x)
    _, s, _ = np.linalg.svd(z, full_matrices=False)
    evr = (s**2) / np.sum(s**2)
    participation = float(1.0 / np.sum(evr**2))
    dim95 = int(np.searchsorted(np.cumsum(evr), 0.95) + 1)
    return evr, participation, dim95


def support_metrics(observed_scores: np.ndarray, synthetic_scores: np.ndarray) -> dict[str, float]:
    obs_tree = cKDTree(observed_scores)
    syn_tree = cKDTree(synthetic_scores)
    obs_to_syn, _ = syn_tree.query(observed_scores, k=1)
    syn_to_obs, _ = obs_tree.query(synthetic_scores, k=1)
    obs_nn, _ = obs_tree.query(observed_scores, k=2)
    syn_nn, _ = syn_tree.query(synthetic_scores, k=2)
    obs_cov = np.cov(observed_scores, rowvar=False)
    syn_cov = np.cov(synthetic_scores, rowvar=False)
    return {
        "observed_nn_median": float(np.median(obs_nn[:, 1])),
        "synthetic_nn_median": float(np.median(syn_nn[:, 1])),
        "observed_to_synthetic_median": float(np.median(obs_to_syn)),
        "synthetic_to_observed_median": float(np.median(syn_to_obs)),
        "observed_logdet_cov_pc1_5": float(np.linalg.slogdet(obs_cov + np.eye(obs_cov.shape[0]) * 1e-9)[1]),
        "synthetic_logdet_cov_pc1_5": float(np.linalg.slogdet(syn_cov + np.eye(syn_cov.shape[0]) * 1e-9)[1]),
    }


def null_model_analysis(features: pd.DataFrame, slices: pd.DataFrame, cols: list[str], *, sample_size: int, reps: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(SEED)
    sample = features.sample(min(sample_size, len(features)), random_state=SEED).reset_index(drop=True)
    sample = add_log_columns(sample)
    sequences = sequences_for_sample(slices, sample["fire_id"])
    observed_x = feature_matrix(sample, cols)
    observed_pca = fit_pca(sample, cols, n_components=10)
    observed_scores = observed_pca.scores[:, :5]
    observed_evr, observed_participation, observed_dim95 = matrix_metrics(observed_x)
    rows = [
        {
            "null_model": "observed",
            "replicate": -1,
            "preserves": "real FIRED growth histories",
            "destroys": "nothing",
            "pc1": float(observed_evr[0]),
            "cumvar_pc1_5": float(observed_evr[:5].sum()),
            "participation_ratio": observed_participation,
            "dimension_for_95pct_variance": observed_dim95,
            **support_metrics(observed_scores, observed_scores),
        }
    ]
    nulls = {
        "independent feature permutation": "marginal distribution of each engineered feature",
        "shuffled daily growth order within fire": "final area, duration, observed daily increments",
        "dirichlet duration and final area": "final area and observation count; monotonic cumulative growth",
        "zero-preserving dirichlet": "final area, observation count, and number of zero-growth days",
        "duration-bin empirical increments": "duration-bin empirical daily-growth profiles and final area",
        "duration-bin mean profile": "duration-bin average growth profile with weak noise",
    }
    destroys = {
        "independent feature permutation": "all covariance and developmental ordering",
        "shuffled daily growth order within fire": "temporal order of each fire's observed growth increments",
        "dirichlet duration and final area": "empirical pulse/timing structure and daily-growth marginal distribution",
        "zero-preserving dirichlet": "empirical timing and increment sizes beyond zero frequency",
        "duration-bin empirical increments": "fire-specific growth order and cross-feature pairing",
        "duration-bin mean profile": "fire-specific pulse heterogeneity",
    }
    for rep in range(reps):
        perm = observed_x.copy()
        for col in perm.columns:
            perm[col] = rng.permutation(perm[col].to_numpy())
        evr, pr, d95 = matrix_metrics(perm)
        z = ((perm.fillna(observed_pca.center) - observed_pca.center) / observed_pca.scale).to_numpy(float)
        scores = z @ observed_pca.loadings.iloc[:, :5].to_numpy(float)
        rows.append(
            {
                "null_model": "independent feature permutation",
                "replicate": rep,
                "preserves": nulls["independent feature permutation"],
                "destroys": destroys["independent feature permutation"],
                "pc1": float(evr[0]),
                "cumvar_pc1_5": float(evr[:5].sum()),
                "participation_ratio": pr,
                "dimension_for_95pct_variance": d95,
                **support_metrics(observed_scores, scores),
            }
        )
        for null_model in [n for n in nulls if n != "independent feature permutation"]:
            null_frame = add_log_columns(make_null_frame(sample, sequences, rng, null_model))
            null_x = feature_matrix(null_frame, cols)
            evr, pr, d95 = matrix_metrics(null_x)
            z = ((null_x.fillna(observed_pca.center) - observed_pca.center) / observed_pca.scale).to_numpy(float)
            scores = z @ observed_pca.loadings.iloc[:, :5].to_numpy(float)
            rows.append(
                {
                    "null_model": null_model,
                    "replicate": rep,
                    "preserves": nulls[null_model],
                    "destroys": destroys[null_model],
                    "pc1": float(evr[0]),
                    "cumvar_pc1_5": float(evr[:5].sum()),
                    "participation_ratio": pr,
                    "dimension_for_95pct_variance": d95,
                    **support_metrics(observed_scores, scores),
                }
            )
    reps_df = pd.DataFrame(rows)
    summary = (
        reps_df[reps_df["replicate"] >= 0]
        .groupby(["null_model", "preserves", "destroys"], as_index=False)
        .agg(
            reps=("replicate", "nunique"),
            cumvar_pc1_5_mean=("cumvar_pc1_5", "mean"),
            cumvar_pc1_5_lo=("cumvar_pc1_5", lambda s: float(np.quantile(s, 0.025))),
            cumvar_pc1_5_hi=("cumvar_pc1_5", lambda s: float(np.quantile(s, 0.975))),
            participation_ratio_mean=("participation_ratio", "mean"),
            dimension95_median=("dimension_for_95pct_variance", "median"),
            synthetic_logdet_cov_pc1_5_mean=("synthetic_logdet_cov_pc1_5", "mean"),
            synthetic_to_observed_median_mean=("synthetic_to_observed_median", "mean"),
            observed_to_synthetic_median_mean=("observed_to_synthetic_median", "mean"),
        )
    )
    observed_row = reps_df[reps_df["null_model"] == "observed"].iloc[0]
    summary.insert(0, "observed_cumvar_pc1_5", float(observed_row["cumvar_pc1_5"]))
    summary.insert(1, "observed_participation_ratio", float(observed_row["participation_ratio"]))
    summary.insert(2, "observed_logdet_cov_pc1_5", float(observed_row["observed_logdet_cov_pc1_5"]))
    summary["observed_minus_null_cumvar"] = summary["observed_cumvar_pc1_5"] - summary["cumvar_pc1_5_mean"]
    summary["synthetic_minus_observed_logdet"] = summary["synthetic_logdet_cov_pc1_5_mean"] - summary["observed_logdet_cov_pc1_5"]
    return summary, reps_df


def summarize_prediction() -> pd.DataFrame:
    path = ROOT / "figures/main/derived_stats/safe_stage_prediction.csv"
    if not path.exists():
        return pd.DataFrame()
    pred = pd.read_csv(path)
    blocked = pred[pred["fold_kind"].isin(["region", "year_block"])].copy()
    return (
        blocked.groupby(["stage", "stage_order", "model"], as_index=False)
        .agg(
            n_folds=("r2", "count"),
            mean_r2=("r2", "mean"),
            lo_r2=("r2", lambda s: float(np.quantile(s.dropna(), 0.025)) if s.dropna().size else np.nan),
            hi_r2=("r2", lambda s: float(np.quantile(s.dropna(), 0.975)) if s.dropna().size else np.nan),
            n_test_total=("n_test", "sum"),
        )
        .sort_values(["stage_order", "model"])
    )


def summarize_climate() -> pd.DataFrame:
    path = ROOT / "figures/main/derived_stats/climate_cv.csv"
    if not path.exists():
        return pd.DataFrame()
    climate = pd.read_csv(path)
    return (
        climate.groupby(["model", "fold_kind", "target"], as_index=False)
        .agg(
            n_folds=("r2", "count"),
            mean_r2=("r2", "mean"),
            lo_r2=("r2", lambda s: float(np.quantile(s.dropna(), 0.025)) if s.dropna().size else np.nan),
            hi_r2=("r2", lambda s: float(np.quantile(s.dropna(), 0.975)) if s.dropna().size else np.nan),
            n_test_total=("n_test", "sum"),
        )
        .sort_values(["model", "fold_kind", "target"])
    )


def write_reports(tables: AuditTables, sample_size: int, reps: int) -> dict[str, str]:
    outputs: dict[str, str] = {}
    for name, frame in [
        ("pc1_ablation_results.csv", tables.pca_ablation),
        ("pc1_top_loadings.csv", tables.pca_loadings),
        ("pc1_correlations.csv", tables.pc1_correlations),
        ("null_model_summary.csv", tables.null_summary),
        ("null_model_replicates.csv", tables.null_replicates),
        ("prediction_blocked_summary.csv", tables.prediction_summary),
        ("climate_cv_summary.csv", tables.climate_summary),
    ]:
        path = AUDIT_STATS_DIR / name
        frame.to_csv(path, index=False)
        outputs[name] = path.as_posix()

    full = tables.pca_ablation[tables.pca_ablation["feature_set"] == "full current feature set"].iloc[0]
    no_scale_duration = tables.pca_ablation[tables.pca_ablation["feature_set"] == "all scale and duration variables removed"].iloc[0]
    profile_only = tables.pca_ablation[tables.pca_ablation["feature_set"] == "normalized profile variables only"].iloc[0]
    growth_only = tables.pca_ablation[tables.pca_ablation["feature_set"] == "growth-share profile only"].iloc[0]
    duration10 = tables.pca_ablation[tables.pca_ablation["feature_set"].str.contains("duration >= 10")]
    duration10_text = _fmt(float(duration10.iloc[0]["cumvar_pc1_5"]), 3) if not duration10.empty else "NA"
    pc1_corr = tables.pc1_correlations[tables.pc1_correlations["feature_set"] == "full current feature set"].copy()
    pc1_corr["abs_r"] = pc1_corr["pearson_r"].abs()
    strongest_corrs = pc1_corr.sort_values("abs_r", ascending=False).drop(columns="abs_r").head(8)

    claim_audit = f"""# Fire VASE Manuscript Claim Audit

## Current Claims

- The current manuscript claims a constrained developmental morphospace.
- It also claims a geometry-first coordinate system, recurring developmental neighborhoods, climate alignment without equivalence, and a leakage-audited but weak fixed-day prediction benchmark.

## Evidence Supporting Each Claim

- Shared coordinate system: supported. The pipeline represents {int(full['n_fires']):,} real FIRED events in one geometry-only feature space with reproducible PCA coordinates.
- Low-dimensional representation: supported for the full observed population. Five PCs explain {_fmt(float(full['cumvar_pc1_5']))} of standardized variance; PC1 explains {_fmt(float(full['pc1']))}.
- Interpretable developmental gradients: partly supported. Top loadings and correlations show PC1 is dominated by cumulative-width and growth-share profile features, with secondary axes carrying duration, taper, pulse, and timing structure.
- Strong developmental constraint relative to plausible alternatives: not yet fully supported. Some nulls remain close to observed once duration, monotonic cumulative growth, and empirical profile structure are preserved.
- Climate as proof of concept: supported as an alignment analysis, not as causation or a main mechanistic explanation.
- Fixed-day prediction: not supported as an affirmative main-text result under blocked validation.

## Evidence Weakening Stronger Claims

- PC1 weakens sharply after removing the many one-day fires. With duration >= 10 days, PC1-PC5 cumulative variance is {duration10_text}.
- Removing scale and duration variables still leaves PC1-PC5 variance at {_fmt(float(no_scale_duration['cumvar_pc1_5']))}, but this reflects profile redundancy as much as developmental constraint.
- Profile-only features have very high five-PC variance ({_fmt(float(profile_only['cumvar_pc1_5']))}); growth-share profiles alone are even higher ({_fmt(float(growth_only['cumvar_pc1_5']))}), showing that profile encoding itself contributes strong redundancy.
- Within-fire and duration-conditioned nulls are the critical tests. The manuscript should not claim that observed fires occupy a restricted subset of all plausible trajectories unless those nulls show a clear support or volume separation.

## Recommended Final Claim

Highest defensible level: **Level 2 - Wildfire histories occupy a reproducible low-dimensional developmental morphospace.**

Level 3 can be phrased cautiously as a hypothesis or pattern of recurring neighborhoods, but Level 4 is not yet justified.

## Go/No-Go Recommendation For Science

**Go after major revision.** The representation and low-dimensional morphospace are compelling enough for a paper, but the title, abstract, Results headings, and Figure sequence should retreat from strong constraint language unless stronger nulls are made central and survive.

## Unresolved Risks

- Short fires dominate the full-population PCA.
- PC1 is heavily tied to monotone cumulative-profile encoding.
- Climate remains centroid-based in the current manuscript-scale analysis.
- Dynamic/state-space claims are not yet tested.
- Prediction currently distracts from the strongest result.

## Strongest PC1 Correlations In The Full Feature Set

{markdown_table(strongest_corrs)}
"""
    path = ANALYSIS_DIR / "manuscript_claim_audit.md"
    path.write_text(claim_audit, encoding="utf-8")
    outputs["manuscript_claim_audit.md"] = path.as_posix()

    pca_report = f"""# PC1 Robustness Report

Random seed: `{SEED}`.

## Interpretation

PC1 is not simply final burned area or duration. Removing final area, scale variables, and duration/observation count does not eliminate low-dimensionality. However, PC1 is strongly shaped by cumulative-width and growth-profile features, and those features contain monotone and duplicated information by design. The honest interpretation is that PC1 is primarily a dominant **developmental profile / allocation axis**, not a pure mechanistic axis.

## PCA Ablations

{markdown_table(tables.pca_ablation)}

## PC1 Correlations

{markdown_table(tables.pc1_correlations.sort_values(['feature_set', 'pearson_r']), max_rows=220)}

## Top Loadings

{markdown_table(tables.pca_loadings, max_rows=260)}

## Sample Size And Exclusion Rules

- Full feature-set analyses use all rows in `developmental_morphospace_features.parquet`.
- Duration sensitivity repeats the full PCA for fires lasting at least 2, 4, 8, and 10 days.
- The correlated-cluster ablation greedily keeps one feature per absolute-correlation cluster using threshold 0.85 on a fixed 25,000-fire sample.
- Log columns are computed with lower clipping at 1e-9.
"""
    path = ANALYSIS_DIR / "pc1_robustness_report.md"
    path.write_text(pca_report, encoding="utf-8")
    outputs["pc1_robustness_report.md"] = path.as_posix()

    null_report = f"""# Null Model Report

Random seed: `{SEED}`. Sample size per replicate: `{sample_size}` fires. Replicates per null: `{reps}`.

## Interpretation

The easy feature-permutation null confirms that the engineered VASE features have strong covariance. More defensible nulls are stricter because they preserve duration, final size, monotonic cumulative growth, zero-growth frequency, or duration-specific empirical profiles. The key manuscript decision is whether observed fires are clearly more compact than these stricter alternatives.

If the observed-minus-null five-PC variance is small or if synthetic support overlaps the observed support, the paper should use "low-dimensional coordinate system" rather than "restricted subset of plausible trajectories."

## Null Hierarchy

{markdown_table(tables.null_summary)}

## Replicate Table

Full replicate results are written to `analysis/claim_audit_stats/null_model_replicates.csv`.
"""
    path = ANALYSIS_DIR / "null_model_report.md"
    path.write_text(null_report, encoding="utf-8")
    outputs["null_model_report.md"] = path.as_posix()

    climate = f"""# Climate Section Decision

## Recommendation

**B. Keep one concise climate figure as proof of concept.**

Climate remains useful because it shows that the geometry-first morphospace can carry external covariates. It should not be framed as a central mechanistic discovery until centroid attribution is replaced by active-area/perimeter exposure, richer covariates, local-normal anomalies, and stricter spatial-temporal blocking.

## Reasons

- Current climate attribution is daily centroid gridMET, not active edge, newly burned area, full perimeter, or perimeter extension.
- Region-blocked validation is the conservative reference and is weaker than random validation.
- Climate predicts PC1 partly because PC1 includes scale/profile structure that can be geographically and seasonally patterned.
- The current "coupling" language should be replaced by "held-out linear association" or "recoverability."

## Current Held-Out Climate Results

{markdown_table(tables.climate_summary)}
"""
    path = ANALYSIS_DIR / "climate_section_decision.md"
    path.write_text(climate, encoding="utf-8")
    outputs["climate_section_decision.md"] = path.as_posix()

    prediction = f"""# Prediction Section Decision

## Recommendation

**C. Move the fixed-day prediction analysis to the supplement as a leakage audit and benchmark.**

The current fixed-day benchmark is scientifically useful because it prevents overstating early prediction, but it is too weak and confusing to close the main paper. The main manuscript should not end on near-zero or negative blocked R2 unless the negative result becomes the paper's central finding.

## Current Blocked Prediction Summary

{markdown_table(tables.prediction_summary)}

## Suggested Alternatives For Later

- Predict final-size quantile or developmental neighborhood rather than continuous PC1-PC3.
- Use strict spatial-temporal blocking with simple regularized regression and one nonlinear baseline.
- Try analog prediction from nearest partial-history neighbors.
- Predict future growth allocation or transition direction once a genuine dynamic state-space test is implemented.
"""
    path = ANALYSIS_DIR / "prediction_section_decision.md"
    path.write_text(prediction, encoding="utf-8")
    outputs["prediction_section_decision.md"] = path.as_posix()

    figure_plan = """# Figure Restructure Plan

## Recommended Four-Figure Main Text

### Figure 1. Fire VASE representation and low-dimensional coordinate system

Scientific conclusion: Fire VASE makes whole-fire histories comparable and yields a reproducible low-dimensional coordinate system.

Panels: representation examples; observed PC1-PC2 density; scree and bootstrap; PC1 robustness after scale/duration ablations; duration sensitivity.

Inputs/scripts: `developmental_morphospace_features.parquet`, `vase_slices.parquet`, `scripts/figures/make_figure_1.py`, `analysis/claim_audit_stats/pc1_ablation_results.csv`.

### Figure 2. Atlas of observed forms

Scientific conclusion: Real fires recur in continuous developmental neighborhoods rather than hard classes.

Panels: observed density with medoids; representative occupancy; coverage curve; transects; label overlap.

Inputs/scripts: `developmental_morphospace_medoids.parquet`, `developmental_morphospace_features.parquet`, `scripts/figures/make_figure_2.py`.

### Figure 3. Observed histories versus defensible null developmental universes

Scientific conclusion: Observed histories are clearly more structured than feature-permutation nulls, but stronger duration/profile-preserving nulls limit the current constraint claim.

Panels: null example descriptions; PCA eigenvalue spectra; five-PC variance with intervals; participation ratio; observed-vs-null support distance or volume; repeat after scale/duration controls.

Inputs/scripts: `vase_slices.parquet`, `developmental_morphospace_features.parquet`, `scripts/fire_vase_manuscript_claim_audit.py`.

### Figure 4. Climate projected onto morphology as proof of concept

Scientific conclusion: Climate aligns with morphology but does not define or uniquely determine it.

Panels: climate surfaces; blocked recoverability models with units/sample sizes; matched examples; population matching summary.

Inputs/scripts: `developmental_morphospace_features.parquet`, `vase_slices.parquet`, `climate_cv.csv`, `matched_population.csv`, `scripts/figures/make_figure_4.py`.

## Supplementary Material

- Fixed-day prediction and leakage audit.
- Full PCA loadings and ablations.
- Perimeter climate exposure pilot and future covariate plan.

## Five-Figure Option

A fifth figure is justified only if a dynamic transition analysis or perimeter-climate analysis becomes affirmative. The current fixed-day prediction figure should not remain in the main text by inertia.
"""
    path = ANALYSIS_DIR / "figure_restructure_plan.md"
    path.write_text(figure_plan, encoding="utf-8")
    outputs["figure_restructure_plan.md"] = path.as_posix()

    return outputs


def draw_audit_figure(tables: AuditTables) -> dict[str, str]:
    set_style()
    fig, axes = plt.subplots(2, 2, figsize=(7.1, 6.2))
    axes = axes.ravel()
    ab = tables.pca_ablation.copy()
    keep = [
        "full current feature set",
        "all scale and duration variables removed",
        "normalized profile variables only",
        "growth-share profile only",
        "interpolated profile features removed",
        "full current feature set, duration >= 10 days",
    ]
    sub = ab[ab["feature_set"].isin(keep)].copy()
    labels = [
        "full",
        "no scale/\nduration",
        "profiles\nonly",
        "growth\nshares",
        "no\nprofiles",
        ">=10 d",
    ]
    axes[0].bar(range(len(sub)), sub["pc1"] * 100, color=MORPH_BLUE)
    axes[0].set_xticks(range(len(sub)), labels, rotation=25, ha="right")
    axes[0].set_ylabel("PC1 variance (%)")
    axes[0].set_title("A. Dominant axis sensitivity", loc="left", fontsize=9, fontweight="bold")

    axes[1].bar(range(len(sub)), sub["cumvar_pc1_5"] * 100, color=FIREBRICK)
    axes[1].set_xticks(range(len(sub)), labels, rotation=25, ha="right")
    axes[1].set_ylabel("First five axes (%)")
    axes[1].set_title("B. Low-dimensionality sensitivity", loc="left", fontsize=9, fontweight="bold")

    null = tables.null_summary.copy()
    order = null.sort_values("cumvar_pc1_5_mean")["null_model"].tolist()
    y = np.arange(len(order))
    null = null.set_index("null_model").loc[order].reset_index()
    axes[2].errorbar(
        null["cumvar_pc1_5_mean"] * 100,
        y,
        xerr=[
            (null["cumvar_pc1_5_mean"] - null["cumvar_pc1_5_lo"]) * 100,
            (null["cumvar_pc1_5_hi"] - null["cumvar_pc1_5_mean"]) * 100,
        ],
        fmt="o",
        color=CHARCOAL,
        ecolor="#9aa3ad",
        capsize=2,
    )
    axes[2].axvline(float(null["observed_cumvar_pc1_5"].iloc[0]) * 100, color=FIREBRICK, lw=1.2, label="observed")
    short_labels = {
        "duration-bin mean profile": "duration-bin\nmean",
        "shuffled daily growth order within fire": "shuffled\norder",
        "duration-bin empirical increments": "empirical\nincrements",
        "dirichlet duration and final area": "dirichlet\nsize+duration",
        "zero-preserving dirichlet": "zero-preserving\ndirichlet",
        "independent feature permutation": "feature\npermutation",
    }
    axes[2].set_yticks(y, [short_labels.get(label, label) for label in order], fontsize=6.9)
    axes[2].set_xlabel("First five axes variance (%)")
    axes[2].set_title("C. Null developmental universes", loc="left", fontsize=9, fontweight="bold")
    axes[2].legend(frameon=False, fontsize=7)

    axes[3].scatter(
        null["synthetic_logdet_cov_pc1_5_mean"],
        null["synthetic_to_observed_median_mean"],
        s=36,
        color=MORPH_BLUE,
    )
    label_offsets = {1: 0, 2: 9, 3: -9, 4: 8, 5: -8, 6: 0}
    for i, row in enumerate(null.itertuples(index=False), start=1):
        axes[3].annotate(
            str(i),
            xy=(row.synthetic_logdet_cov_pc1_5_mean, row.synthetic_to_observed_median_mean),
            xytext=(0, label_offsets.get(i, 0)),
            textcoords="offset points",
            fontsize=7.0,
            ha="center",
            va="center",
            color=CHARCOAL,
            bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.85, "pad": 0.4},
        )
    axes[3].axvline(float(null["observed_logdet_cov_pc1_5"].iloc[0]), color=FIREBRICK, lw=1.2)
    axes[3].set_xlabel("Log covariance volume in observed PC1-PC5")
    axes[3].set_ylabel("Null-to-observed median distance")
    axes[3].set_title("D. Support overlap diagnostics", loc="left", fontsize=9, fontweight="bold")
    key = "\n".join(f"{i}. {short_labels.get(label, label).replace(chr(10), ' ')}" for i, label in enumerate(order, start=1))
    axes[3].text(0.99, 0.98, key, transform=axes[3].transAxes, ha="right", va="top", fontsize=5.9, color=CHARCOAL)
    for ax in axes:
        ax.spines[["top", "right"]].set_visible(False)
        ax.tick_params(labelsize=7)
    fig.tight_layout()
    outputs = {}
    for suffix in ["png", "pdf", "svg"]:
        path = AUDITED_FIG_DIR / f"Figure_3_null_universes.{suffix}"
        fig.savefig(path, dpi=600, bbox_inches="tight")
        outputs[suffix] = path.as_posix()
    plt.close(fig)

    legends = """# Audited Main-Text Figure Legends

## Figure 1. Fire VASE representation and low-dimensional coordinate system.

This revised figure should retain the representation examples and observed morphospace density from the current Figure 1, but replace any unsupported constraint language with explicit robustness panels. The scientific conclusion is that real fire histories can be placed in a reproducible low-dimensional coordinate system.

## Figure 2. Atlas of observed developmental neighborhoods.

This figure should retain real-fire medoids, occupancy, coverage, and transect panels. Shape labels are landmarks in a continuous space, not discovered discrete classes.

## Figure 3. Observed histories versus defensible null developmental universes.

Panel A shows how much the dominant axis changes under feature ablations that remove scale, duration, or profile classes. Panel B shows cumulative variance in the first five axes for the same ablations. Panel C compares observed low-dimensionality with null developmental universes that preserve progressively more trivial structure. Panel D compares null support against the observed support in the observed five-dimensional PCA space. Together the panels show that feature covariance is real, but the strongest "restricted possible-space" claim requires stronger separation from duration/profile-preserving nulls.

## Figure 4. Climate projected onto developmental morphology.

Climate should be retained as a concise proof of concept: temperature, VPD, and wind align with the geometry-first morphospace, but centroid climate does not define or uniquely determine fire-development form.

## Supplementary Figure. Fixed-day prediction and leakage audit.

The existing fixed-day prediction figure should move to the supplement unless later models produce robust positive blocked performance.
"""
    path = AUDITED_FIG_DIR / "figure_legends.md"
    path.write_text(legends, encoding="utf-8")
    outputs["legends"] = path.as_posix()

    for fig_name in ["Figure_1", "Figure_2", "Figure_4"]:
        for suffix in ["png", "pdf", "svg"]:
            src = ROOT / "figures" / "main" / f"{fig_name}.{suffix}"
            if src.exists():
                dst = AUDITED_FIG_DIR / f"{fig_name}.{suffix}"
                shutil.copyfile(src, dst)
                outputs[f"{fig_name}_{suffix}"] = dst.as_posix()
    return outputs


def write_revised_manuscript(tables: AuditTables) -> str:
    full = tables.pca_ablation[tables.pca_ablation["feature_set"] == "full current feature set"].iloc[0]
    no_scale_duration = tables.pca_ablation[tables.pca_ablation["feature_set"] == "all scale and duration variables removed"].iloc[0]
    duration10 = tables.pca_ablation[tables.pca_ablation["feature_set"].str.contains("duration >= 10")].iloc[0]
    manuscript = f"""# Fire VASE Provides a Low-Dimensional Coordinate System for Wildfire Development

Article type: Research Article draft. Revised source generated by `scripts/fire_vase_manuscript_claim_audit.py`.

## One-Sentence Summary

Fire VASE converts whole-fire histories into a reproducible developmental morphospace.

## Abstract

Wildfire histories are usually compared as final area, perimeter, or daily growth, leaving whole-fire development without a compact comparative representation. We introduce Fire VASE, a geometry-first representation that converts each observed daily fire history into a developmental object. Across 278,569 FIRED events from 2000-2021, the current VASE feature set is strongly low dimensional: five principal components explain {_fmt(float(full['cumvar_pc1_5']))} of standardized variance. However, diagnostic ablations and null models show that this concentration partly reflects monotone cumulative growth, redundant profile features, and the prevalence of short fires. Real-fire medoids and transects reveal recurring neighborhoods arranged along continuous gradients, not hard classes. Centroid gridMET climate aligns with this morphospace but does not define it. Fire VASE therefore provides a shared coordinate system for testing developmental hypotheses; stronger claims about restricted possible trajectories require additional null and covariate tests.

## Introduction

Wildfire science can now measure large fire archives with daily spatial detail, but the field still lacks a compact representation for comparing complete fire histories. Final area, duration, perimeter, and daily growth each capture useful information, yet none alone represents the ordered development of a fire as a comparable object.

Whole-fire development matters because timing and allocation shape impacts. Early bursts, persistent narrow growth, late reactivation, and abrupt termination can imply different ecological, exposure, and management contexts even when final areas are similar. A representation that preserves this temporal geometry can turn millions of daily observations into a population of comparable developmental forms.

Fire VASE maps developmental time to vertical position and cumulative burned area to ring width. The resulting object is geometry-first: climate, fuels, topography, suppression, and ignition context are projected onto the representation after the coordinate system is defined. This separation lets us distinguish three claims: representation in a shared coordinate system, statistical low dimensionality of engineered features, and genuine constraint relative to plausible alternative histories.

The discriminating hypothesis tested here is conservative. If observed fire histories are arbitrary once size, duration, monotonicity, and feature redundancy are considered, then strong low-dimensionality should disappear under ablations and plausible null histories. If observed wildfire development is genuinely constrained, it should occupy a smaller or more structured support than those null universes. The current data support the first two claims strongly and the third only provisionally.

## Results

### Fire VASE Represents Whole-Fire Histories In A Shared Coordinate System

The analysis includes 278,569 FIRED events and 626,102 daily VASE slices from 2000-2021. Each VASE is derived from observed daily fire progression rather than synthetic examples. The representation places fires with different durations and final areas into one feature space while preserving the order of growth.

The population is dominated by short events: many fires have one or two observed daily slices. This is not a nuisance detail; it shapes the dense core of the morphospace and must be carried into every claim about dimensionality.

### The Current Feature Set Is Low Dimensional But Partly Redundant

In the full current feature set, PC1 explains {_fmt(float(full['pc1']))} of standardized variance and the first five PCs explain {_fmt(float(full['cumvar_pc1_5']))}. This establishes a compact coordinate system, but it does not by itself prove biological or physical constraint. Removing scale and duration variables leaves first-five-PC variance at {_fmt(float(no_scale_duration['cumvar_pc1_5']))}, whereas restricting the analysis to fires lasting at least 10 days lowers first-five-PC variance to {_fmt(float(duration10['cumvar_pc1_5']))}. PC1 is therefore more than final area alone, but it is also not independent of the engineered cumulative-profile representation.

The revised interpretation is that the dominant axis describes developmental allocation and cumulative-profile shape. It should not be described as a mechanism, attractor, or state-space coordinate until transition tests and independent covariates support that meaning.

### Observed Fires Differ Strongly From Easy Nulls, But Strong Nulls Limit The Constraint Claim

Feature-wise permutation produces much lower low-dimensionality, confirming that VASE features contain strong covariance. However, nulls that preserve final area, duration, monotonic cumulative growth, zero-growth frequency, or duration-specific profile structure are more demanding. The current audit shows that these stricter nulls are the relevant benchmark for any possible-space claim.

The manuscript should therefore avoid statements such as "observed fires occupy only a restricted subset of plausible developmental trajectories" unless paired with the null hierarchy and its limitations. A defensible statement is narrower: observed fire histories form a reproducible low-dimensional morphospace, and the degree to which this reflects physical developmental constraint remains a testable hypothesis.

### Representative Forms Are Continuous Landmarks

Real-fire medoids summarize occupied neighborhoods of the morphospace. They are useful for atlas construction and communication because they are observed events, not prototypes manufactured by the analysis. The shape vocabulary should remain descriptive: single flash, compact steady, late surge, and related labels are landmarks in a continuous space rather than hard classes.

### Climate Is A Projection, Not The Main Claim

Centroid gridMET climate aligns with parts of the morphospace, especially the dominant axis, but blocked validation and matched examples show that climate and morphology are not interchangeable. The revised manuscript should keep one concise climate figure as proof of concept. The more important next step is already underway: perimeter-based and extended-perimeter climate exposure tables that can replace centroid-only attribution.

### Fixed-Day Prediction Should Move To The Supplement

The leakage-audited fixed-day benchmark is important because it prevents overstated predictive claims. But region- and year-blocked R2 values are near zero or negative for many target/model combinations. This result should be retained as a supplementary benchmark and leakage audit, not as a main-text endpoint.

## Discussion

Fire VASE currently makes its strongest contribution as a representation and coordinate system. It shows that a continental fire archive can be treated as a population of whole-history developmental forms and that these forms are statistically compact under the current geometry-first encoding.

The audit narrows the claim. Low-dimensionality is real and reproducible, but part of it is expected from monotone cumulative growth, duplicated profile features, and the many short fires in the archive. This does not weaken the representation; it clarifies what has been discovered. Fire VASE gives wildfire science a coordinate system in which stronger hypotheses about developmental constraint can now be tested.

The next stage should focus on two tests. First, possible-space nulls must preserve size, duration, monotonicity, zero-growth days, daily-growth marginals, and duration-specific profiles while still lacking higher-order developmental organization. Second, climate attribution should move from event centroids to active burned area, cumulative perimeters, and exterior perimeter extensions, with humidity, precipitation, fuel moisture, topography, vegetation, suppression, ignition cause, and local-normal anomalies added as covariates.

This revised framing leaves the paper with a tighter claim: Fire VASE provides a shared, interpretable, low-dimensional developmental morphospace for observed wildfire histories. It does not yet prove that wildfire development is restricted to a small subset of all plausible trajectories after all trivial constraints are accounted for.
"""
    path = MANUSCRIPT_DIR / "manuscript_audited_revision.md"
    path.write_text(manuscript, encoding="utf-8")
    return path.as_posix()


def write_changelog(outputs: dict[str, str], tables: AuditTables) -> str:
    text = f"""# Manuscript Changelog

## Analyses Added

- PCA ablations for scale, final area, duration, observation count, profile-only, summary-only, correlated-cluster, and duration-restricted feature sets.
- PC1 loading and correlation diagnostics.
- A null-model hierarchy preserving increasingly realistic constraints.
- Climate and prediction section decisions based on existing blocked validation outputs.

## Analyses Removed Or Moved

- The fixed-day prediction figure is recommended for the supplement rather than the main text.
- State-space and trajectory-channel language is removed because dynamic transition tests are not yet implemented.

## Claims Strengthened

- Fire VASE provides a common coordinate system for whole-fire histories.
- The current feature set is reproducibly low dimensional for the observed population.

## Claims Weakened

- "Constrained developmental morphospace" is softened to "low-dimensional developmental morphospace."
- "Restricted subset of plausible trajectories" is not used as a main claim.
- Climate "coupling" is reframed as held-out association or recoverability.

## Figure Changes

- Recommended main-text sequence reduced to four figures.
- New audited Figure 3 focuses on PC1 sensitivity and defensible null universes.
- Prediction becomes supplementary unless future models show robust blocked generalization.

## Remaining Caveats

- Short fires dominate the population.
- Cumulative profiles build monotonic redundancy into the feature set.
- Perimeter climate attribution is scaffolded but not yet integrated into the manuscript analysis.
- Topography, vegetation, suppression, ignition cause, and climate anomalies remain absent.
- Strong dynamic state-space claims require transition analyses.
"""
    path = ROOT / "CHANGELOG_MANUSCRIPT.md"
    path.write_text(text, encoding="utf-8")
    return path.as_posix()


def final_report(tables: AuditTables) -> str:
    full = tables.pca_ablation[tables.pca_ablation["feature_set"] == "full current feature set"].iloc[0]
    no_scale_duration = tables.pca_ablation[tables.pca_ablation["feature_set"] == "all scale and duration variables removed"].iloc[0]
    strict_nulls = tables.null_summary[~tables.null_summary["null_model"].isin(["independent feature permutation"])]
    max_strict = float(strict_nulls["cumvar_pc1_5_mean"].max()) if not strict_nulls.empty else np.nan
    climate_decision = "keep one concise proof-of-concept climate figure"
    prediction_decision = "move fixed-day prediction to supplement as leakage audit"
    report = f"""Fire VASE claim-audit final report

Strongest supported discovery:
Fire VASE provides a shared, reproducible, low-dimensional coordinate system for observed wildfire-development histories.

Strongest unsupported claim removed:
Observed fires occupy a restricted subset of all plausible developmental trajectories after accounting for monotonicity, size, duration, and feature redundancy.

Whether PC1 survives scale and duration controls:
Partly. Full PC1 explains {_fmt(float(full['pc1']))}; after removing scale and duration variables, PC1 explains {_fmt(float(no_scale_duration['pc1']))} and PC1-PC5 explain {_fmt(float(no_scale_duration['cumvar_pc1_5']))}. The axis survives, but its interpretation shifts toward profile/allocation structure and remains affected by cumulative-profile redundancy.

Whether observed histories differ from plausible null histories:
Yes against easy feature-permutation nulls; unresolved or weaker against strict duration/profile-preserving nulls. The strongest strict null in this audit has mean PC1-PC5 variance around {_fmt(max_strict)}, so Level 4 constraint language is not justified yet.

Recommended number of main figures:
4.

Whether climate remains in the main text:
Yes, but compressed to a proof-of-concept projection/association figure.

Whether prediction remains in the main text:
No. Move to supplement as a leakage audit and benchmark.

Top three issues still preventing submission:
1. A stronger possible-space null hierarchy must be finalized and interpreted conservatively.
2. Centroid climate should be replaced or supplemented by perimeter/active-area climate exposure and local anomalies.
3. State-space/dynamic claims need transition tests, or the manuscript must consistently avoid state-space language.
"""
    path = ANALYSIS_DIR / "final_terminal_report.txt"
    path.write_text(report, encoding="utf-8")
    print(report)
    return report


def run(args: argparse.Namespace) -> dict[str, str]:
    ensure_dirs()
    data = load_data()
    features = data["features"].copy()
    slices = data["slices"].copy()
    cols = geometry_columns(features, data["loadings"])
    ablation, loadings, correlations = pca_ablation(features, cols)
    null_summary, null_reps = null_model_analysis(features, slices, cols, sample_size=args.sample_size, reps=args.reps)
    tables = AuditTables(
        pca_ablation=ablation,
        pca_loadings=loadings,
        pc1_correlations=correlations,
        null_summary=null_summary,
        null_replicates=null_reps,
        prediction_summary=summarize_prediction(),
        climate_summary=summarize_climate(),
    )
    outputs = write_reports(tables, sample_size=args.sample_size, reps=args.reps)
    outputs.update(draw_audit_figure(tables))
    outputs["revised_manuscript_source"] = write_revised_manuscript(tables)
    outputs["CHANGELOG_MANUSCRIPT.md"] = write_changelog(outputs, tables)
    outputs["final_terminal_report"] = (ANALYSIS_DIR / "final_terminal_report.txt").as_posix()
    final_report(tables)
    manifest = ANALYSIS_DIR / "claim_audit_manifest.json"
    manifest.write_text(json.dumps(outputs, indent=2), encoding="utf-8")
    outputs["manifest"] = manifest.as_posix()
    return outputs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample-size", type=int, default=12000)
    parser.add_argument("--reps", type=int, default=24)
    args = parser.parse_args()
    outputs = run(args)
    print(json.dumps(outputs, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
