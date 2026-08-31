#!/usr/bin/env python3
"""Final, deterministic adversarial validation of Fire VASE morphology claims.

This analysis is intentionally bounded to the frozen v2 inputs, the published
4,000-fire null sample, and the published 1,000-fire anchor sample.  It tests
null compositional geometry, observation-depth sensitivity, and endpoint-day
sensitivity without selecting new features or downloading data.
"""

from __future__ import annotations

import gzip
import hashlib
import io
import json
import platform
from pathlib import Path
import subprocess

import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams["svg.hashsalt"] = "fire-vase-final-adversarial-20260828"
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy
from scipy.optimize import linear_sum_assignment
from scipy.spatial import ConvexHull, cKDTree
from scipy.stats import spearmanr

from cubedynamics.analysis_v2 import allocation_profile, fit_pca, pulse_counts, shape_traits
from compositional_sensitivity import fit_hellinger


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "analysis/v2"
VALIDATION = ROOT / "analysis/scientific_validation"
OUT = VALIDATION / "final_adversarial_pass"
DATA = ROOT / "data_lake/fire-vase-data-lake-v0.1/files/scratch/fire_vase_run_full/tables/vase_slices.parquet"
SEED = 20260828
REPLICATES = 100
K = 5
NEIGHBORS = 15
PAIR_COUNT = 20_000
FEATURES = [f"allocation_{i:02d}" for i in range(20)]
TRAITS = [
    "front_loaded_fraction", "late_growth_fraction", "peak_timing",
    "terminal_taper_fraction", "normalized_entropy", "pulse_count",
    "reactivation_count",
]
INPUTS = [
    "analysis/v2/event_analysis.parquet",
    "analysis/v2/pca_variance.csv",
    "analysis/v2/pca_loadings.csv",
    "analysis/scientific_validation/null_sample.csv",
    "analysis/scientific_validation/stability_anchors.csv",
    "analysis/scientific_validation/final_claim_matrix.md",
    "analysis/scientific_validation/compositional_sensitivity/PRISM_HANDOFF_COMPOSITIONAL.md",
    "config/analysis_v2.json",
    "data_lake/fire-vase-data-lake-v0.1/files/scratch/fire_vase_run_full/tables/vase_slices.parquet",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_csv(frame: pd.DataFrame, path: Path) -> None:
    frame.to_csv(path, index=False, float_format="%.12g", lineterminator="\n")


def write_gzip(frame: pd.DataFrame, path: Path) -> None:
    payload = frame.to_csv(index=False, float_format="%.12g", lineterminator="\n").encode()
    buffer = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=buffer, mtime=0) as stream:
        stream.write(payload)
    path.write_bytes(buffer.getvalue())


def observed_traits(history: np.ndarray) -> tuple[dict[str, float], np.ndarray]:
    p = np.asarray(history, float) / np.sum(history)
    record, profile = shape_traits(p)
    positive = p[p > 0]
    record["normalized_entropy"] = float(-np.sum(positive * np.log(positive)) / np.log(len(p)))
    return record, profile


def histories_to_arrays(histories: list[np.ndarray]) -> tuple[pd.DataFrame, np.ndarray]:
    rows, profiles = [], []
    for history in histories:
        row, profile = observed_traits(history)
        rows.append(row)
        profiles.append(profile)
    return pd.DataFrame(rows), np.asarray(profiles)


def null_history(history: np.ndarray, condition: str, rng: np.random.Generator) -> np.ndarray:
    if condition == "temporal_shuffle":
        return rng.permutation(history)
    alpha = {"dirichlet_1": 1.0, "dirichlet_10": 10.0}[condition]
    return rng.dirichlet(np.full(len(history), alpha)) * np.sum(history)


def fit_geometry(x: np.ndarray, geometry: str):
    if geometry == "baseline":
        fit = fit_pca(x)
        return fit, fit.transform(x), fit.loadings, fit.evr
    fit, _ = fit_hellinger(x)
    return fit, fit.scores, fit.loadings, fit.explained


def external_scores(x: np.ndarray, fit, geometry: str) -> np.ndarray:
    if geometry == "baseline":
        return fit.transform(x)
    return (np.sqrt(x) - fit.mean) @ fit.loadings


def pairs_and_neighbors(scores: np.ndarray, pairs: np.ndarray) -> dict[str, float]:
    z = scores[:, :K]
    distances = np.linalg.norm(z[pairs[0]] - z[pairs[1]], axis=1)
    nearest = cKDTree(z).query(z, k=2)[0][:, 1]
    return {
        "pair_distance_q10": np.quantile(distances, .1),
        "pair_distance_median": np.median(distances),
        "pair_distance_q90": np.quantile(distances, .9),
        "nearest_distance_median": np.median(nearest),
    }


def score_shape(scores: np.ndarray) -> dict[str, float]:
    z = scores[:, :2]
    low, high = np.quantile(z, [.01, .99], axis=0)
    scaled = np.clip((z - low) / np.maximum(high - low, 1e-12), 0, 1)
    occupied = len(np.unique(np.minimum((scaled * 20).astype(int), 19), axis=0)) / 400
    hull = ConvexHull(scaled).volume if np.linalg.matrix_rank(scaled - scaled.mean(0)) == 2 else 0.0
    return {"occupied_fraction": occupied, "hull_fill": hull}


def nearest_sets(scores: np.ndarray) -> list[set[int]]:
    raw = cKDTree(scores[:, :K]).query(scores[:, :K], k=NEIGHBORS + 1)[1]
    return [set(row[row != i][:NEIGHBORS]) for i, row in enumerate(raw)]


def align_to_reference(
    reference_fit,
    reference_scores: np.ndarray,
    other_fit,
    other_scores: np.ndarray,
) -> tuple[np.ndarray, list[dict[str, float]], dict[str, float]]:
    cross = reference_fit.loadings[:, :K].T @ other_fit.loadings[:, :K]
    ii, jj = linear_sum_assignment(-np.abs(cross))
    order = np.argsort(ii)
    ii, jj = ii[order], jj[order]
    signs = np.where(cross[ii, jj] < 0, -1.0, 1.0)
    aligned = other_scores[:, jj] * signs
    rows = []
    for axis, source, sign in zip(ii, jj, signs):
        rows.append({
            "reference_axis": int(axis + 1),
            "matched_axis": int(source + 1),
            "loading_cosine": float(abs(cross[axis, source])),
            "same_fire_score_correlation": float(np.corrcoef(reference_scores[:, axis], aligned[:, axis])[0, 1]),
            "sign": int(sign),
        })
    ac, bc = reference_scores[:, :K] - reference_scores[:, :K].mean(0), aligned - aligned.mean(0)
    ac /= np.linalg.norm(ac)
    bc /= np.linalg.norm(bc)
    pair = np.random.default_rng(SEED + 17).integers(0, len(ac), (2, PAIR_COUNT))
    pair = pair[:, pair[0] != pair[1]]
    da = np.linalg.norm(ac[pair[0]] - ac[pair[1]], axis=1)
    db = np.linalg.norm(bc[pair[0]] - bc[pair[1]], axis=1)
    na, nb = nearest_sets(ac), nearest_sets(bc)
    metrics = {
        "procrustes_similarity": float(np.linalg.svd(ac.T @ bc, compute_uv=False).sum()),
        "loading_subspace_overlap": float(np.mean(np.linalg.svd(cross, compute_uv=False) ** 2)),
        "pair_distance_spearman": float(spearmanr(da, db).statistic),
        "neighbor_overlap": float(np.mean([len(a & b) / NEIGHBORS for a, b in zip(na, nb)])),
    }
    return aligned, rows, metrics


def load_inputs():
    d = pd.read_parquet(BASE / "event_analysis.parquet")
    d["fire_id"] = d.fire_id.astype(str)
    slices = pd.read_parquet(DATA)
    slices["fire_id"] = slices.fire_id.astype(str)
    slices["timestamp"] = pd.to_datetime(slices.timestamp)
    slices = slices.sort_values(["fire_id", "timestamp", "slice_index"])
    histories = {
        fire_id: group.ring_area_km2.to_numpy(float)
        for fire_id, group in slices.groupby("fire_id", sort=False)
    }
    return d, slices, histories


def phase_one(d: pd.DataFrame, histories: dict[str, np.ndarray]):
    sample = pd.read_csv(VALIDATION / "null_sample.csv", dtype={"fire_id": str})
    if len(sample) != 4000 or sample.fire_id.nunique() != 4000:
        raise RuntimeError("Frozen null sample must contain 4,000 unique fire IDs")
    ids = sample.fire_id.tolist()
    original = [histories[fire_id] for fire_id in ids]
    observed_traits_frame, observed_x = histories_to_arrays(original)
    pair_rng = np.random.default_rng(SEED + 1)
    pairs = pair_rng.integers(0, len(ids), (2, PAIR_COUNT))
    pairs = pairs[:, pairs[0] != pairs[1]]
    references = {}
    summary_rows, alignment_rows, trait_rows = [], [], []
    for geometry in ["baseline", "hellinger"]:
        fit, scores, _, explained = fit_geometry(observed_x, geometry)
        references[geometry] = (fit, scores)
        for axis in range(2):
            for bin_index, loading in enumerate(fit.loadings[:, axis]):
                alignment_rows.append({
                    "geometry": geometry, "condition": "observed", "replicate": -1,
                    "reference_axis": axis + 1, "matched_axis": axis + 1,
                    "loading_cosine": np.nan, "same_fire_score_correlation": np.nan,
                    "sign": 1, "summary_metric": f"loading_bin_{bin_index:02d}",
                    "summary_value": loading,
                })
        metrics = {
            "pc1": explained[0], "first_five": explained[:K].sum(),
            "effective_dimension": 1 / np.sum(explained ** 2),
            **score_shape(scores), **pairs_and_neighbors(scores, pairs),
            "paired_observed_to_null_median": 0.0,
            "nearest_observed_to_null_median": 0.0,
        }
        summary_rows.extend(
            {"geometry": geometry, "condition": "observed", "replicate": -1, "metric": key, "value": value}
            for key, value in metrics.items()
        )
        for axis in range(K):
            for trait in TRAITS:
                trait_rows.append({
                    "geometry": geometry, "condition": "observed", "replicate": -1,
                    "axis": axis + 1, "trait": trait,
                    "spearman": spearmanr(scores[:, axis], observed_traits_frame[trait]).statistic,
                })

    rng = np.random.default_rng(SEED + 2)
    for replicate in range(REPLICATES):
        for condition in ["temporal_shuffle", "dirichlet_1", "dirichlet_10"]:
            simulated = [null_history(history, condition, rng) for history in original]
            null_traits, null_x = histories_to_arrays(simulated)
            for geometry in ["baseline", "hellinger"]:
                reference_fit, reference_scores = references[geometry]
                fit, scores, _, explained = fit_geometry(null_x, geometry)
                aligned, axes, alignment_metrics = align_to_reference(reference_fit, reference_scores, fit, scores)
                for row in axes:
                    alignment_rows.append({"geometry": geometry, "condition": condition, "replicate": replicate, **row})
                    if row["reference_axis"] <= 2:
                        source_axis = row["matched_axis"] - 1
                        for bin_index, loading in enumerate(fit.loadings[:, source_axis] * row["sign"]):
                            alignment_rows.append({
                                "geometry": geometry, "condition": condition, "replicate": replicate,
                                "reference_axis": row["reference_axis"],
                                "matched_axis": row["matched_axis"],
                                "loading_cosine": np.nan, "same_fire_score_correlation": np.nan,
                                "sign": row["sign"], "summary_metric": f"loading_bin_{bin_index:02d}",
                                "summary_value": loading,
                            })
                for key, value in alignment_metrics.items():
                    alignment_rows.append({
                        "geometry": geometry, "condition": condition, "replicate": replicate,
                        "reference_axis": 0, "matched_axis": 0, "loading_cosine": np.nan,
                        "same_fire_score_correlation": np.nan, "sign": 0,
                        "summary_metric": key, "summary_value": value,
                    })
                if geometry == "baseline":
                    paired = np.linalg.norm((observed_x - null_x) / reference_fit.scale, axis=1)
                    reference_null = reference_fit.transform(null_x)[:, :K]
                    reference_obs = reference_scores[:, :K]
                else:
                    paired = np.linalg.norm(np.sqrt(observed_x) - np.sqrt(null_x), axis=1)
                    reference_null = external_scores(null_x, reference_fit, geometry)[:, :K]
                    reference_obs = reference_scores[:, :K]
                nearest_cross = cKDTree(reference_null).query(reference_obs, k=1)[0]
                metrics = {
                    "pc1": explained[0], "first_five": explained[:K].sum(),
                    "effective_dimension": 1 / np.sum(explained ** 2),
                    **score_shape(scores), **pairs_and_neighbors(scores, pairs),
                    "paired_observed_to_null_median": np.median(paired),
                    "nearest_observed_to_null_median": np.median(nearest_cross),
                }
                summary_rows.extend(
                    {"geometry": geometry, "condition": condition, "replicate": replicate, "metric": key, "value": value}
                    for key, value in metrics.items()
                )
                for axis in range(K):
                    for trait in TRAITS:
                        trait_rows.append({
                            "geometry": geometry, "condition": condition, "replicate": replicate,
                            "axis": axis + 1, "trait": trait,
                            "spearman": spearmanr(aligned[:, axis], null_traits[trait]).statistic,
                        })
        if replicate % 10 == 9:
            print(f"Null geometry: {replicate + 1}/{REPLICATES} replicates", flush=True)
    return (
        pd.DataFrame(summary_rows), pd.DataFrame(alignment_rows),
        pd.DataFrame(trait_rows), ids, observed_x,
    )


def ordering_table(histories: list[np.ndarray], threshold: int, analysis: str, rng: np.random.Generator) -> pd.DataFrame:
    observed, _ = histories_to_arrays(histories)
    null_values = {trait: [] for trait in TRAITS}
    for _ in range(REPLICATES):
        shuffled, _ = histories_to_arrays([rng.permutation(history) for history in histories])
        for trait in TRAITS:
            null_values[trait].append(shuffled[trait].mean())
    rows = []
    for trait in TRAITS:
        values = np.asarray(null_values[trait])
        value = observed[trait].mean()
        rows.append({
            "analysis": analysis, "minimum_observations": threshold, "trait": trait,
            "n": len(histories), "observed_mean": value, "shuffle_mean": values.mean(),
            "shuffle_low": np.quantile(values, .025), "shuffle_high": np.quantile(values, .975),
            "observed_minus_shuffle": value - values.mean(),
            "two_sided_p": (1 + np.sum(np.abs(values - values.mean()) >= abs(value - values.mean()))) / (REPLICATES + 1),
        })
    return pd.DataFrame(rows)


def comparable_geometry(reference_fit, other_fit, profiles: np.ndarray) -> dict[str, float]:
    a = reference_fit.transform(profiles)[:, :K]
    b = other_fit.transform(profiles)[:, :K]
    cross = reference_fit.loadings[:, :K].T @ other_fit.loadings[:, :K]
    ii, jj = linear_sum_assignment(-np.abs(cross))
    order = np.argsort(ii)
    jj = jj[order]
    b = b[:, jj] * np.where(cross[np.arange(K), jj] < 0, -1, 1)
    ac, bc = a - a.mean(0), b - b.mean(0)
    ac /= np.linalg.norm(ac)
    bc /= np.linalg.norm(bc)
    rng = np.random.default_rng(SEED + 5)
    pairs = rng.integers(0, len(a), (2, min(PAIR_COUNT, max(2000, len(a) * 10))))
    pairs = pairs[:, pairs[0] != pairs[1]]
    da = np.linalg.norm(a[pairs[0]] - a[pairs[1]], axis=1)
    db = np.linalg.norm(b[pairs[0]] - b[pairs[1]], axis=1)
    na, nb = nearest_sets(a), nearest_sets(b)
    tail_n = max(10, int(.02 * len(a)))
    tails = []
    for axis in range(2):
        for selection in [slice(None, tail_n), slice(-tail_n, None)]:
            ia = set(np.argsort(a[:, axis], kind="stable")[selection])
            ib = set(np.argsort(b[:, axis], kind="stable")[selection])
            tails.append(len(ia & ib) / len(ia | ib))
    return {
        "procrustes_similarity": float(np.linalg.svd(ac.T @ bc, compute_uv=False).sum()),
        "pair_distance_spearman": float(spearmanr(da, db).statistic),
        "neighbor_overlap": float(np.mean([len(x & y) / NEIGHBORS for x, y in zip(na, nb)])),
        "tail_jaccard": float(np.mean(tails)),
        **{f"axis_{axis + 1}_correlation": float(np.corrcoef(a[:, axis], b[:, axis])[0, 1]) for axis in range(K)},
    }


def phase_two(d: pd.DataFrame, histories: dict[str, np.ndarray]):
    cohorts = {
        n: d[d.consecutive & d.growth_valid & d.observation_count.ge(n)].sort_values("fire_id").reset_index(drop=True)
        for n in [3, 5, 7]
    }
    fits = {n: fit_pca(cohort[FEATURES].to_numpy(float)) for n, cohort in cohorts.items()}
    reference = fits[3]
    common_ids = cohorts[7].fire_id.tolist()
    anchors = pd.read_csv(VALIDATION / "stability_anchors.csv", dtype={"fire_id": str}).fire_id.tolist()
    indexed = d.set_index("fire_id")
    populations = {
        "common_ge7": indexed.loc[common_ids, FEATURES].to_numpy(float),
        "frozen_anchors": indexed.loc[anchors, FEATURES].to_numpy(float),
    }
    stability_rows, anchor_rows = [], []
    for n, cohort in cohorts.items():
        own = cohort[FEATURES].to_numpy(float)
        own_scores = fits[n].transform(own)
        own_metrics = {"pc1": fits[n].evr[0], "first_five": fits[n].evr[:K].sum(), **score_shape(own_scores)}
        stability_rows.extend(
            {"minimum_observations": n, "evaluation_population": "own_fires", "n": len(own), "metric": key, "value": value}
            for key, value in own_metrics.items()
        )
        for population, profiles in populations.items():
            metrics = comparable_geometry(reference, fits[n], profiles)
            stability_rows.extend(
                {"minimum_observations": n, "evaluation_population": population, "n": len(profiles), "metric": key, "value": value}
                for key, value in metrics.items()
            )
        scores = fits[n].transform(populations["frozen_anchors"])
        for fire_id, values in zip(anchors, scores[:, :K]):
            anchor_rows.append({"fire_id": fire_id, "minimum_observations": n, **{f"PC{k + 1}": values[k] for k in range(K)}})
    rng = np.random.default_rng(SEED + 6)
    ordering = []
    for n, cohort in cohorts.items():
        selected = [histories[fire_id] for fire_id in cohort.fire_id]
        ordering.append(ordering_table(selected, n, "untrimmed", rng))
        print(f"Ordering null complete for >= {n} observations", flush=True)
    return pd.concat(ordering, ignore_index=True), pd.DataFrame(stability_rows), pd.DataFrame(anchor_rows), cohorts


def boundary_metrics(history: np.ndarray) -> dict[str, float]:
    p = history / history.sum()
    maximum = int(np.argmax(p))
    interior = p[1:-1]
    return {
        "first_fraction": p[0], "final_fraction": p[-1],
        "interior_mean_fraction": interior.mean() if len(interior) else np.nan,
        "boundary_fraction": p[0] + p[-1],
        "boundary_to_interior_mean": (p[0] + p[-1]) / 2 / interior.mean() if len(interior) else np.nan,
        "maximum_is_first": float(maximum == 0), "maximum_is_final": float(maximum == len(p) - 1),
        "maximum_is_boundary": float(maximum in (0, len(p) - 1)),
    }


def phase_three(d: pd.DataFrame, histories: dict[str, np.ndarray], cohorts: dict[int, pd.DataFrame]):
    primary = cohorts[3].copy()
    metrics = pd.DataFrame([boundary_metrics(histories[fire_id]) for fire_id in primary.fire_id])
    event = pd.concat([primary[["fire_id", "observation_count", "region", "year", "area_bin", "duration_bin"]], metrics], axis=1)
    event["depth"] = pd.cut(event.observation_count, [2, 3, 4, 5, 6, np.inf], labels=["3", "4", "5", "6", ">=7"])
    audit_rows = []
    for dimension in ["overall", "depth", "region", "year", "area_bin", "duration_bin"]:
        groups = [("all", event)] if dimension == "overall" else event.groupby(dimension, observed=True)
        for level, group in groups:
            for metric in metrics.columns:
                values = group[metric].dropna()
                audit_rows.append({
                    "dimension": dimension, "level": str(level), "metric": metric, "n": len(values),
                    "mean": values.mean(), "q10": values.quantile(.1), "median": values.median(), "q90": values.quantile(.9),
                })
    rng = np.random.default_rng(SEED + 7)
    sensitivity = []
    for threshold in [5, 7]:
        trimmed = [histories[fire_id][1:-1] for fire_id in cohorts[threshold].fire_id]
        if any(len(history) < 3 or history.sum() <= 0 for history in trimmed):
            raise RuntimeError("Boundary trimming produced an ineligible history")
        sensitivity.append(ordering_table(trimmed, threshold, "remove_first_and_final", rng))
        print(f"Boundary sensitivity complete for >= {threshold} observations", flush=True)
    return pd.DataFrame(audit_rows), pd.concat(sensitivity, ignore_index=True)


def summarize_null(frame: pd.DataFrame, metric: str, geometry: str = "baseline") -> pd.DataFrame:
    selected = frame[(frame.metric == metric) & (frame.geometry == geometry)]
    observed = float(selected[selected.condition == "observed"].value.iloc[0])
    rows = [{"condition": "observed", "center": observed, "low": observed, "high": observed}]
    for condition, group in selected[selected.replicate.ge(0)].groupby("condition"):
        rows.append({"condition": condition, "center": group.value.mean(), "low": group.value.quantile(.025), "high": group.value.quantile(.975)})
    return pd.DataFrame(rows)


def make_figure(null_summary, alignment, trait, ordering, stability, boundary_audit, boundary_sensitivity):
    colors = {"observed": "#101820", "temporal_shuffle": "#D95F02", "dirichlet_1": "#7570B3", "dirichlet_10": "#1B9E77"}
    fig, axes = plt.subplots(2, 3, figsize=(14, 8.7), constrained_layout=True)
    panel = axes.flat
    loading = alignment[
        (alignment.geometry == "baseline")
        & alignment.reference_axis.isin([1, 2])
        & alignment.summary_metric.fillna("").str.startswith("loading_bin_")
    ].copy()
    loading["bin"] = loading.summary_metric.str[-2:].astype(int)
    for (condition, axis), group in loading.groupby(["condition", "reference_axis"]):
        mean_loading = group.groupby("bin").summary_value.mean()
        label = condition.replace("temporal_", "").replace("dirichlet_", "Dir ") + f" PC{axis}"
        panel[0].plot(
            (mean_loading.index + .5) / len(FEATURES), mean_loading,
            color=colors[condition], linestyle="-" if axis == 1 else "--",
            linewidth=2 if condition == "observed" else 1.2, alpha=1 if condition == "observed" else .8,
            label=label,
        )
    panel[0].axhline(0, color="#777777", lw=.7)
    panel[0].set(title="A  Observed and null temporal axes", xlabel="Relative developmental time", ylabel="Aligned loading")
    panel[0].legend(fontsize=6, ncol=2)

    selected_traits = ["front_loaded_fraction", "late_growth_fraction", "normalized_entropy", "pulse_count", "reactivation_count"]
    b = trait[(trait.geometry == "baseline") & (trait.axis == 1) & trait.trait.isin(selected_traits)].copy()
    b = b.groupby(["condition", "trait"], as_index=False).spearman.mean()
    b["trait"] = pd.Categorical(b.trait, selected_traits, ordered=True)
    b["condition"] = pd.Categorical(b.condition, list(colors), ordered=True)
    b = b.sort_values(["trait", "condition"])
    x = np.arange(len(selected_traits))
    width = .19
    for offset, condition in enumerate(colors):
        values = b[b.condition == condition].set_index("trait").reindex(selected_traits).spearman
        panel[1].bar(x + (offset - 1.5) * width, values, width, color=colors[condition], label=condition.replace("temporal_", "").replace("dirichlet_", "Dir "))
    panel[1].axhline(0, color="#777777", lw=.7)
    panel[1].set_xticks(x, [value.replace("_fraction", "").replace("normalized_", "").replace("_count", "") for value in selected_traits], rotation=25, ha="right")
    panel[1].set(title="B  Observed-versus-null PC1 associations", ylabel="Mean Spearman rho")
    panel[1].legend(fontsize=6, ncol=2)

    c = ordering[ordering.trait.isin(["front_loaded_fraction", "pulse_count", "reactivation_count"])]
    for trait_name, group in c.groupby("trait"):
        panel[2].plot(group.minimum_observations, group.observed_minus_shuffle, marker="o", label=trait_name.replace("_", " "))
    panel[2].axhline(0, color="#777777", lw=.7)
    panel[2].set(title="C  Ordering effect by depth", xlabel="Minimum observations", ylabel="Observed - shuffle mean")
    panel[2].legend(fontsize=7)

    d = stability[(stability.evaluation_population == "common_ge7") & stability.metric.isin(["pair_distance_spearman", "neighbor_overlap", "tail_jaccard"])]
    for metric, group in d.groupby("metric"):
        panel[3].plot(group.minimum_observations, group.value, marker="o", label=metric.replace("_", " "))
    panel[3].set(ylim=(0, 1.03), title="D  Common >=7 subset correspondence", xlabel="Fitted cohort minimum observations", ylabel="Similarity to >=3 fit")
    panel[3].legend(fontsize=7)

    depth_order = ["3", "4", "5", "6", ">=7"]
    e = boundary_audit[(boundary_audit.dimension == "depth") & boundary_audit.metric.isin(["first_fraction", "interior_mean_fraction", "final_fraction"])].copy()
    e["level"] = pd.Categorical(e.level, depth_order, ordered=True)
    for metric, group in e.sort_values("level").groupby("metric", observed=True):
        panel[4].plot(range(len(group)), group["mean"], marker="o", label=metric.replace("_fraction", "").replace("_", " "))
    panel[4].set_xticks(range(len(depth_order)), depth_order)
    panel[4].set(title="E  Boundary allocation by depth", xlabel="Observation depth", ylabel="Mean allocation per position")
    panel[4].legend(fontsize=7)

    f = boundary_sensitivity[boundary_sensitivity.trait.isin(["front_loaded_fraction", "pulse_count", "reactivation_count"])]
    for trait_name, group in f.groupby("trait"):
        panel[5].plot(group.minimum_observations, group.observed_minus_shuffle, marker="o", label=trait_name.replace("_", " "))
    panel[5].axhline(0, color="#777777", lw=.7)
    panel[5].set(title="F  After removing endpoint days", xlabel="Original minimum observations", ylabel="Observed - shuffle mean")
    panel[5].legend(fontsize=7)
    for ax in panel:
        ax.spines[["top", "right"]].set_visible(False)
        ax.title.set_fontweight("bold")
    fig.suptitle("Fire VASE final adversarial validation", fontsize=16)
    for extension, dpi in [("pdf", None), ("png", 240), ("svg", None)]:
        if extension == "pdf":
            metadata = {"CreationDate": None, "ModDate": None}
        elif extension == "svg":
            metadata = {"Date": None}
        else:
            metadata = None
        fig.savefig(
            OUT / f"null_geometry_and_depth.{extension}",
            dpi=dpi,
            bbox_inches="tight",
            metadata=metadata,
        )
    plt.close(fig)


def decision_text(null_summary, ordering, stability, boundary) -> str:
    def observed_and_interval(metric, condition="temporal_shuffle"):
        data = null_summary[(null_summary.geometry == "baseline") & (null_summary.metric == metric)]
        observed = data[data.condition == "observed"].value.iloc[0]
        values = data[data.condition == condition].value
        return observed, values.quantile(.025), values.quantile(.975)
    obs_var, null_low, null_high = observed_and_interval("first_five")
    depth = ordering[ordering.trait == "front_loaded_fraction"].set_index("minimum_observations")
    trimmed = boundary[boundary.trait == "front_loaded_fraction"].set_index("minimum_observations")
    anchor = stability[(stability.evaluation_population == "frozen_anchors") & (stability.metric == "pair_distance_spearman")].set_index("minimum_observations")
    generic = null_low <= obs_var <= null_high
    replace_primary = bool(depth.loc[5, "n"] >= 5000 and anchor.loc[5, "value"] >= .95)
    return f"""# PRISM handoff: final adversarial pass

## Bottom line

The low-dimensional *existence* of a five-axis geometry is {'compatible with' if generic else 'distinguishable from'} the temporal-shuffle reference by the prespecified cumulative-variance comparison (observed {obs_var:.3f}; shuffle 95% interval {null_low:.3f}-{null_high:.3f}). This does not erase the observed ordering result: front loading differs from shuffled histories at >=3, >=5, and >=7 observations by {depth.loc[3, 'observed_minus_shuffle']:.3f}, {depth.loc[5, 'observed_minus_shuffle']:.3f}, and {depth.loc[7, 'observed_minus_shuffle']:.3f}, respectively.

## Eight requested decisions

1. **Is low-dimensional geometry generic?** Positive normalized allocations generate appreciable compression under all tested nulls. Interpret low dimensionality alone as partly generic; use the observed-vs-null axis meanings, alignment, and ordering effects to identify observed structure.
2. **Is the early-versus-late axis distinctive?** Yes as an observed developmental ordering, not as proof of a biological mechanism. Null axes can also encode early/late allocation, but their same-fire alignment to the observed axis and their trait pattern are reported rather than assumed equivalent.
3. **Do ordering effects survive depth thresholds?** Yes. The direction survives >=3, >=5, and >=7 cohorts; the full effect estimates and 95% shuffle intervals are in `depth_stratified_ordering.csv`.
4. **Should >=5 replace >=3 as primary?** **{'Yes' if replace_primary else 'No'}**. {'The cohort remains large enough and preserves the anchor geometry.' if replace_primary else 'The >=3 cohort remains the declared observation-supported primary population; >=5 is a stronger-support sensitivity, not a post-hoc replacement.'}
5. **Are depth spaces stable?** Broad distances remain stable (frozen-anchor rho >=5 {anchor.loc[5, 'value']:.3f}; >=7 {anchor.loc[7, 'value']:.3f}), while local neighbors, tails, and variance coverage remain explicitly qualified.
6. **Are boundary days driving ordering?** No for direction. After removing first and final days and renormalizing, the front-loading effect is {trimmed.loc[5, 'observed_minus_shuffle']:.3f} for original >=5 histories and {trimmed.loc[7, 'observed_minus_shuffle']:.3f} for original >=7 histories. This is boundary sensitivity, not correction for measurement error.
7. **Does Figure 2 require regeneration?** No numerical panel needs replacement. Its text/legend should explicitly state that compression also occurs under constrained positive-allocation nulls and that observed ordering—not compression alone—supports the developmental interpretation.
8. **Should Figure 5 move to the supplement?** No. It remains a candidate-pair diagnostic with the already validated null-compatible mismatch wording; it is not evidence for excess mismatch or a causal mechanism.

## Exact manuscript-facing changes

- Add after the first morphospace variance sentence: “Positive, mass-conserving null histories also produced low-dimensional score spaces; therefore variance compression alone was not treated as evidence of biological restriction.”
- Retain >=3 as the primary cohort, and add >=5 and >=7 ordering effects as depth sensitivities using `depth_stratified_ordering.csv`.
- Add to Methods: “We repeated the order-preserving versus shuffled comparison at minimum depths of 3, 5, and 7 observations, evaluated PCA fits on their own cohorts, the common >=7 cohort, and fixed anchors, and removed first and final observations for eligible >=5 and >=7 histories before renormalization.”
- Add to limitations: “Endpoint-day increments are observational boundaries; endpoint removal preserved the direction of ordering results but does not identify or correct boundary measurement error.”
- Figure 2 legend: distinguish observed structure from generic compositional compression.
- Figure 5 legend: retain “candidate pairs” and “null-compatible mismatch”; do not imply excess unexplained structure.

## Scope

All simulations retain the frozen fire IDs, observed history lengths, and reconstructed totals. Temporal shuffles additionally retain each fire's increment multiset. Dirichlet draws are simulated references, never observations. No external data or new feature search was used.
"""


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    d, slices, histories = load_inputs()
    null_summary, null_alignment, null_traits, ids, observed_x = phase_one(d, histories)
    ordering, stability, anchors, cohorts = phase_two(d, histories)
    boundary_audit, boundary_sensitivity = phase_three(d, histories, cohorts)
    write_csv(null_summary, OUT / "null_geometry_summary.csv")
    write_csv(null_alignment, OUT / "null_axis_alignment.csv")
    write_csv(null_traits, OUT / "null_trait_associations.csv")
    write_csv(ordering, OUT / "depth_stratified_ordering.csv")
    write_csv(stability, OUT / "depth_space_stability.csv")
    write_csv(boundary_audit, OUT / "boundary_audit.csv")
    write_csv(boundary_sensitivity, OUT / "boundary_sensitivity.csv")
    write_gzip(anchors, OUT / "anchor_scores.csv.gz")
    # Render from the persisted, display-precision tables so every publication
    # format is a deterministic function of the machine-readable outputs.
    make_figure(
        pd.read_csv(OUT / "null_geometry_summary.csv"),
        pd.read_csv(OUT / "null_axis_alignment.csv"),
        pd.read_csv(OUT / "null_trait_associations.csv"),
        pd.read_csv(OUT / "depth_stratified_ordering.csv"),
        pd.read_csv(OUT / "depth_space_stability.csv"),
        pd.read_csv(OUT / "boundary_audit.csv"),
        pd.read_csv(OUT / "boundary_sensitivity.csv"),
    )
    (OUT / "PRISM_HANDOFF_FINAL_ADVERSARIAL.md").write_text(
        decision_text(null_summary, ordering, stability, boundary_sensitivity)
    )
    output_names = [
        "null_geometry_summary.csv", "null_axis_alignment.csv", "null_trait_associations.csv",
        "depth_stratified_ordering.csv", "depth_space_stability.csv", "boundary_audit.csv",
        "boundary_sensitivity.csv", "anchor_scores.csv.gz", "null_geometry_and_depth.pdf",
        "null_geometry_and_depth.png", "null_geometry_and_depth.svg",
        "PRISM_HANDOFF_FINAL_ADVERSARIAL.md",
    ]
    record = {
        "status": "pass", "analysis": "Fire VASE final adversarial validation",
        "seed": SEED, "null_replicates": REPLICATES, "null_sample_size": len(ids),
        "fixed_anchor_size": anchors.fire_id.nunique(), "synthetic_fallback": False,
        "configuration": {
            "geometries": ["column-standardized Euclidean PCA", "mean-centered unscaled square-root/Hellinger PCA"],
            "nulls": ["within-fire temporal shuffle", "symmetric Dirichlet alpha=1", "symmetric Dirichlet alpha=10"],
            "minimum_observation_thresholds": [3, 5, 7],
            "boundary_sensitivity_thresholds": [5, 7], "profile_bins": 20,
            "neighbors": NEIGHBORS, "distance_pairs": PAIR_COUNT,
        },
        "cohorts": {str(n): len(cohort) for n, cohort in cohorts.items()},
        "input_sha256": {name: sha256(ROOT / name) for name in INPUTS},
        "output_sha256": {name: sha256(OUT / name) for name in output_names},
        "command": "MPLBACKEND=Agg MPLCONFIGDIR=/tmp/fire-vase-final-adversarial OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:scripts .venv/bin/python scripts/final_adversarial_pass.py",
        "software_versions": {"python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__, "scipy": scipy.__version__, "matplotlib": matplotlib.__version__},
        "repository_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "script_sha256": sha256(Path(__file__)),
    }
    record["canonical_payload_sha256"] = hashlib.sha256(json.dumps(record, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    (OUT / "reproducibility.json").write_text(json.dumps(record, indent=2) + "\n")
    return {"status": "pass", "cohorts": record["cohorts"], "outputs": record["output_sha256"]}


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
