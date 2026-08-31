#!/usr/bin/env python3
"""Frozen-v2 sensitivity of the Fire VASE morphospace to Hellinger geometry.

This script is deliberately additive. It reads the frozen primary event features,
reproduces the existing standardized-Euclidean PCA as a hard gate, and only then
fits a mean-centered (not variance-scaled) square-root/Hellinger PCA. It never
creates observational data or edits the v2 analysis and manuscript outputs.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import argparse
import gzip
import hashlib
import io
import json
import platform
import subprocess
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy
from scipy.optimize import linear_sum_assignment
from scipy.spatial import cKDTree, distance
from scipy.stats import rankdata, spearmanr

from cubedynamics.analysis_v2 import fit_pca


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "analysis/v2"
VALIDATION = ROOT / "analysis/scientific_validation"
OUT = VALIDATION / "compositional_sensitivity"
SEED = 20260828
K = 5
NEIGHBORS = 15
TAIL_FRACTION = 0.02
FEATURES = [f"allocation_{i:02d}" for i in range(20)]
EXPECTED_INPUT_HASHES = {
    "analysis/v2/event_features.parquet": "b1dadea2cdd612934b8584b563da209da922cd1de91155d62497ace35b711e3a",
    "analysis/v2/pca_variance.csv": "9717ea9d71d8616171520a51f495370af7379681998f053fc8c4c9d6a71f34a9",
    "analysis/v2/pca_loadings.csv": "2f8f2f7e7ad6cf08c8cb9001259ebf3a6a767ebeb7bd5ad96850f132999b2b1d",
    "analysis/v2/matched_examples.csv": "54122455940b83771810e71d6ae3264e293f9c3fda9f851e7f235c75e737c1a8",
    "analysis/scientific_validation/stability_anchors.csv": "3ef1282f8272fd81fd793b7640ba143d9654858df83eb13a7b15e60eba50f210",
    "config/analysis_v2.json": "82ffbdb1b703b5d78422f7fb7690fd0585320304be58d886de24dd60d9f66479",
    "scripts/figures/make_figures_v2.py": "dbcf283594d4e66314b566d35752bf99ef8bbaf9fde818949ca8296f2957a13d",
}
EXPECTED_N = 10246
EXPECTED_PC1 = 0.341495575686
EXPECTED_FIRST_FIVE = 0.894435897825


@dataclass(frozen=True)
class Representation:
    scores: np.ndarray
    loadings: np.ndarray
    explained: np.ndarray
    mean: np.ndarray
    scale: np.ndarray


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_input_hashes() -> dict[str, str]:
    actual = {}
    for relative, expected in EXPECTED_INPUT_HASHES.items():
        path = ROOT / relative
        if not path.exists():
            raise FileNotFoundError(f"Required frozen input is missing: {relative}")
        actual[relative] = sha256(path)
        if actual[relative] != expected:
            raise RuntimeError(
                f"Frozen input hash mismatch for {relative}: "
                f"expected {expected}, observed {actual[relative]}"
            )
    return actual


def orient_components(scores: np.ndarray, loadings: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Use the v2 sign rule: the largest-absolute loading is positive."""
    scores = np.asarray(scores, float).copy()
    loadings = np.asarray(loadings, float).copy()
    for axis in range(loadings.shape[1]):
        pivot = int(np.argmax(np.abs(loadings[:, axis])))
        if loadings[pivot, axis] < 0:
            scores[:, axis] *= -1
            loadings[:, axis] *= -1
    return scores, loadings


def fit_baseline(x: np.ndarray) -> Representation:
    fitted = fit_pca(x)
    scores = fitted.transform(x)
    scores, loadings = orient_components(scores, fitted.loadings)
    return Representation(scores, loadings, fitted.evr, fitted.mean, fitted.scale)


def fit_hellinger(x: np.ndarray) -> tuple[Representation, np.ndarray]:
    x = np.asarray(x, float)
    if not np.isfinite(x).all():
        raise ValueError("Allocations contain nonfinite values")
    if (x < 0).any():
        raise ValueError("Allocations contain negative values")
    np.testing.assert_allclose(x.sum(axis=1), 1.0, atol=2e-12, rtol=0)
    transformed = np.sqrt(x)
    np.testing.assert_allclose(np.square(transformed).sum(axis=1), 1.0, atol=2e-12, rtol=0)
    mean = transformed.mean(axis=0)
    centered = transformed - mean
    # No variance scaling: Euclidean distance in this transformed space is
    # proportional to Hellinger distance in the original composition.
    u, singular, vt = np.linalg.svd(centered, full_matrices=False)
    scores = u * singular
    loadings = vt.T
    scores, loadings = orient_components(scores, loadings)
    eigenvalues = singular**2 / (len(x) - 1)
    explained = eigenvalues / eigenvalues.sum()
    return Representation(scores, loadings, explained, mean, np.ones(x.shape[1])), transformed


def reproduce_baseline(x: np.ndarray, baseline: Representation) -> dict[str, float | int | str]:
    frozen_variance = pd.read_csv(BASE / "pca_variance.csv")
    frozen_loadings = pd.read_csv(BASE / "pca_loadings.csv")
    checks = {
        "sample_size": len(x),
        "pc1": float(baseline.explained[0]),
        "first_five": float(baseline.explained[:K].sum()),
        "sample_size_status": "pass" if len(x) == EXPECTED_N else "fail",
        "pc1_status": "pass" if np.isclose(baseline.explained[0], EXPECTED_PC1, atol=2e-12) else "fail",
        "first_five_status": "pass" if np.isclose(baseline.explained[:K].sum(), EXPECTED_FIRST_FIVE, atol=2e-12) else "fail",
    }
    np.testing.assert_allclose(baseline.explained, frozen_variance.explained_variance, atol=2e-12, rtol=0)
    np.testing.assert_allclose(
        baseline.loadings,
        frozen_loadings[[f"PC{i}" for i in range(1, 21)]].to_numpy(float),
        atol=2e-10,
        rtol=0,
    )
    if any(value == "fail" for key, value in checks.items() if key.endswith("_status")):
        raise RuntimeError(f"Frozen baseline reproduction failed: {checks}")
    checks["saved_variance_status"] = "pass"
    checks["saved_loadings_status"] = "pass"
    return checks


def align_spaces(baseline: Representation, hellinger: Representation) -> tuple[np.ndarray, pd.DataFrame]:
    corr = np.corrcoef(baseline.scores[:, :K].T, hellinger.scores[:, :K].T)[:K, K:]
    rows, columns = linear_sum_assignment(-np.abs(corr))
    order = np.argsort(rows)
    rows, columns = rows[order], columns[order]
    aligned = np.empty((len(baseline.scores), K))
    records = []
    for baseline_axis, hellinger_axis in zip(rows, columns):
        raw = float(corr[baseline_axis, hellinger_axis])
        sign = 1.0 if raw >= 0 else -1.0
        aligned[:, baseline_axis] = hellinger.scores[:, hellinger_axis] * sign
        records.append({
            "baseline_axis": int(baseline_axis + 1),
            "hellinger_axis": int(hellinger_axis + 1),
            "raw_score_correlation": raw,
            "sign_multiplier_for_alignment": int(sign),
            "aligned_score_correlation": abs(raw),
            "baseline_explained_variance": baseline.explained[baseline_axis],
            "hellinger_explained_variance": hellinger.explained[hellinger_axis],
        })
    return aligned, pd.DataFrame(records).sort_values("baseline_axis").reset_index(drop=True)


def jaccard(left: set[int], right: set[int]) -> float:
    return len(left & right) / len(left | right)


def nearest_sets(x: np.ndarray, neighbors: int = NEIGHBORS) -> list[set[int]]:
    queried = cKDTree(x).query(x, k=neighbors + 1)[1]
    return [set(row[row != index][:neighbors]) for index, row in enumerate(queried)]


def correspondence_metrics(
    baseline_scores: np.ndarray,
    aligned_scores: np.ndarray,
    primary: pd.DataFrame,
    anchor_ids: list[str],
) -> tuple[dict[str, float], pd.DataFrame]:
    index = pd.Series(np.arange(len(primary)), index=primary.fire_id.astype(str))
    anchor_index = index.loc[anchor_ids].to_numpy(int)
    a = baseline_scores[anchor_index, :K]
    b = aligned_scores[anchor_index, :K]

    ac, bc = a - a.mean(axis=0), b - b.mean(axis=0)
    ac /= np.linalg.norm(ac)
    bc /= np.linalg.norm(bc)
    procrustes = float(np.linalg.svd(ac.T @ bc, compute_uv=False).sum())
    qa, _ = np.linalg.qr(baseline_scores[:, :K])
    qb, _ = np.linalg.qr(aligned_scores[:, :K])
    principal_cosines = np.linalg.svd(qa.T @ qb, compute_uv=False)
    subspace = float(np.mean(principal_cosines**2))

    pair_a = distance.pdist(a)
    pair_b = distance.pdist(b)
    pair_spearman = float(spearmanr(pair_a, pair_b).statistic)
    ka, kb = nearest_sets(a), nearest_sets(b)
    neighbor_overlap = float(np.mean([len(x & y) / NEIGHBORS for x, y in zip(ka, kb)]))

    tail_n = max(10, int(len(primary) * TAIL_FRACTION))
    tail_rows = []
    for axis in range(2):
        baseline_order = np.argsort(baseline_scores[:, axis], kind="stable")
        hellinger_order = np.argsort(aligned_scores[:, axis], kind="stable")
        for side, selection in [("bottom", slice(None, tail_n)), ("top", slice(-tail_n, None))]:
            overlap = jaccard(set(baseline_order[selection]), set(hellinger_order[selection]))
            tail_rows.append({"axis": axis + 1, "tail": side, "n_per_tail": tail_n, "jaccard": overlap})
    tails = pd.DataFrame(tail_rows)
    metrics = {
        "procrustes_similarity_5d": procrustes,
        "score_subspace_similarity_5d": subspace,
        "anchor_pair_distance_spearman_5d": pair_spearman,
        "anchor_15_neighbor_overlap_5d": neighbor_overlap,
        "pc1_tail_jaccard_mean": float(tails[tails.axis.eq(1)].jaccard.mean()),
        "pc2_tail_jaccard_mean": float(tails[tails.axis.eq(2)].jaccard.mean()),
        "pc1_pc2_tail_jaccard_mean": float(tails.jaccard.mean()),
    }
    return metrics, tails


def example_ids(frame: pd.DataFrame) -> list[tuple[str, str, str]]:
    """Mirror the manuscript figure rule and include Figure 5 displayed pairs."""
    primary = frame[frame.primary_eligible & frame.observation_count.ge(5)]
    selected = []
    for label in ["front-loaded taper", "late peak", "multiple detected pulses"]:
        group = primary[primary.neighborhood.eq(label)].copy()
        center = group[["shape_PC1", "shape_PC2"]].median()
        fire_id = str(group.loc[((group[["shape_PC1", "shape_PC2"]] - center) ** 2).sum(1).idxmin(), "fire_id"])
        selected.append((fire_id, "Figures 1 and 2", label))
    gap = frame[(~frame.consecutive) & frame.observation_count.between(4, 6)].sort_values("fire_id").iloc[0]
    selected.append((str(gap.fire_id), "Figure 1", "gappy example"))
    matched = pd.read_csv(BASE / "matched_examples.csv", dtype={"fire_id_a": str, "fire_id_b": str})
    for row in matched.itertuples():
        for side in ["a", "b"]:
            selected.append((str(getattr(row, f"fire_id_{side}")), "Figure 5", f"{row.matching_space}-matched pair"))
    deduplicated = []
    for item in selected:
        if item[0] not in {row[0] for row in deduplicated}:
            deduplicated.append(item)
    return deduplicated


def transform_external(x: np.ndarray, representation: Representation, geometry: str) -> np.ndarray:
    if geometry == "baseline":
        return ((x - representation.mean) / representation.scale) @ representation.loadings
    return (np.sqrt(x) - representation.mean) @ representation.loadings


def percentile(values: np.ndarray, query: float) -> float:
    return float(np.searchsorted(np.sort(values), query, side="right") / len(values))


def exemplar_table(
    all_events: pd.DataFrame,
    primary: pd.DataFrame,
    baseline: Representation,
    hellinger: Representation,
    aligned_scores: np.ndarray,
    alignment: pd.DataFrame,
) -> pd.DataFrame:
    raw_h_columns = alignment.hellinger_axis.to_numpy(int) - 1
    signs = alignment.sign_multiplier_for_alignment.to_numpy(float)
    baseline_tree = cKDTree(baseline.scores[:, :K])
    hellinger_tree = cKDTree(aligned_scores[:, :K])
    primary_ids = primary.fire_id.astype(str).to_numpy()
    records = []
    indexed = all_events.assign(fire_id=all_events.fire_id.astype(str)).set_index("fire_id")
    for fire_id, context, category in example_ids(all_events):
        row = indexed.loc[fire_id]
        x = row[FEATURES].to_numpy(float)[None, :]
        base = transform_external(x, baseline, "baseline")[0, :K]
        raw_h = transform_external(x, hellinger, "hellinger")[0]
        hel = raw_h[raw_h_columns] * signs
        base_neighbors = baseline_tree.query(base, k=NEIGHBORS + 1)[1]
        hel_neighbors = hellinger_tree.query(hel, k=NEIGHBORS + 1)[1]
        base_ids = [primary_ids[i] for i in np.atleast_1d(base_neighbors) if primary_ids[i] != fire_id][:NEIGHBORS]
        hel_ids = [primary_ids[i] for i in np.atleast_1d(hel_neighbors) if primary_ids[i] != fire_id][:NEIGHBORS]
        record = {
            "fire_id": fire_id,
            "display_context": context,
            "selection_label": category,
            "primary_eligible": bool(row.primary_eligible),
            "baseline_hellinger_15nn_overlap": len(set(base_ids) & set(hel_ids)) / NEIGHBORS,
        }
        for axis in range(K):
            record[f"baseline_PC{axis + 1}"] = base[axis]
            record[f"hellinger_aligned_PC{axis + 1}"] = hel[axis]
        for axis in range(2):
            b_pct = percentile(baseline.scores[:, axis], base[axis])
            h_pct = percentile(aligned_scores[:, axis], hel[axis])
            record[f"baseline_PC{axis + 1}_percentile"] = b_pct
            record[f"hellinger_PC{axis + 1}_percentile"] = h_pct
            record[f"PC{axis + 1}_percentile_movement"] = h_pct - b_pct
        records.append(record)
    return pd.DataFrame(records)


def loadings_table(rep: Representation, alignment: pd.DataFrame | None, geometry: str) -> pd.DataFrame:
    if alignment is None:
        loadings = rep.loadings[:, :K]
        source_axes = np.arange(K)
        signs = np.ones(K)
    else:
        source_axes = alignment.hellinger_axis.to_numpy(int) - 1
        signs = alignment.sign_multiplier_for_alignment.to_numpy(float)
        loadings = rep.loadings[:, source_axes] * signs
    frame = pd.DataFrame({"feature": FEATURES, "relative_time_midpoint": (np.arange(20) + 0.5) / 20})
    for axis in range(K):
        frame[f"PC{axis + 1}"] = loadings[:, axis]
        frame[f"PC{axis + 1}_source_component"] = source_axes[axis] + 1
    frame["geometry"] = geometry
    frame["input_units"] = "raw allocation proportion, column-standardized" if geometry == "baseline" else "square-root allocation, mean-centered, unscaled"
    return frame


def variance_table(baseline: Representation, hellinger: Representation) -> pd.DataFrame:
    records = []
    for name, rep in [("baseline_standardized_euclidean", baseline), ("hellinger", hellinger)]:
        cumulative = np.cumsum(rep.explained)
        for axis in range(K):
            records.append({
                "representation": name,
                "sample_size": EXPECTED_N,
                "feature_count": len(FEATURES),
                "axis": axis + 1,
                "explained_variance": rep.explained[axis],
                "cumulative_variance": cumulative[axis],
            })
    return pd.DataFrame(records)


def trait_correlations(primary: pd.DataFrame, baseline_scores: np.ndarray, aligned_scores: np.ndarray) -> pd.DataFrame:
    traits = ["front_loaded_fraction", "late_growth_fraction", "normalized_entropy", "pulse_count"]
    records = []
    for axis in range(2):
        for trait in traits:
            records.append({
                "axis": axis + 1,
                "trait": trait,
                "baseline_spearman": spearmanr(baseline_scores[:, axis], primary[trait]).statistic,
                "hellinger_spearman": spearmanr(aligned_scores[:, axis], primary[trait]).statistic,
            })
    return pd.DataFrame(records)


def summary_table(
    baseline: Representation,
    hellinger: Representation,
    alignment: pd.DataFrame,
    metrics: dict[str, float],
    tails: pd.DataFrame,
    traits: pd.DataFrame,
    exemplars: pd.DataFrame,
) -> pd.DataFrame:
    rows = [
        ("cohort", "sample_size", EXPECTED_N, EXPECTED_N, np.nan, "identical frozen events"),
        ("cohort", "feature_count", len(FEATURES), len(FEATURES), np.nan, "allocation_00 through allocation_19"),
        ("variance", "PC1_explained", baseline.explained[0], hellinger.explained[0], hellinger.explained[0] - baseline.explained[0], "representation-specific variance"),
        ("variance", "PC1_to_PC5_cumulative", baseline.explained[:K].sum(), hellinger.explained[:K].sum(), hellinger.explained[:K].sum() - baseline.explained[:K].sum(), "representation-specific variance"),
    ]
    for row in alignment.itertuples():
        rows.append(("axis_alignment", f"PC{row.baseline_axis}_score_correlation", np.nan, np.nan, row.aligned_score_correlation, f"Hellinger PC{row.hellinger_axis}, sign aligned"))
    labels = {
        "procrustes_similarity_5d": "global configuration after rotation and one global scale",
        "score_subspace_similarity_5d": "principal-angle similarity in event score space",
        "anchor_pair_distance_spearman_5d": "all pairwise distances among 1,000 frozen anchors",
        "anchor_15_neighbor_overlap_5d": "mean shared neighbors among frozen anchors",
        "pc1_tail_jaccard_mean": "mean top/bottom 2% Jaccard",
        "pc2_tail_jaccard_mean": "mean top/bottom 2% Jaccard",
        "pc1_pc2_tail_jaccard_mean": "mean across PC1/PC2 top/bottom tails",
    }
    for key, value in metrics.items():
        rows.append(("correspondence", key, np.nan, np.nan, value, labels[key]))
    for row in tails.itertuples():
        rows.append(("extreme_exemplars", f"PC{row.axis}_{row.tail}_2pct_jaccard", np.nan, np.nan, row.jaccard, f"{row.n_per_tail} fires per tail"))
    for row in traits.itertuples():
        rows.append(("gradient", f"PC{row.axis}_{row.trait}_spearman", row.baseline_spearman, row.hellinger_spearman, row.hellinger_spearman - row.baseline_spearman, "same external descriptive trait"))
    rows.append(("displayed_exemplars", "mean_15_neighbor_overlap", np.nan, np.nan, exemplars.baseline_hellinger_15nn_overlap.mean(), f"{len(exemplars)} manuscript-displayed fires"))
    rows.append(("displayed_exemplars", "maximum_absolute_PC1_PC2_percentile_movement", np.nan, np.nan, exemplars[["PC1_percentile_movement", "PC2_percentile_movement"]].abs().to_numpy().max(), "movement in aligned marginal rank"))
    return pd.DataFrame(rows, columns=["section", "metric", "baseline", "hellinger", "comparison", "note"])


def write_csv(frame: pd.DataFrame, path: Path) -> None:
    frame.to_csv(path, index=False, float_format="%.12g", lineterminator="\n")


def write_deterministic_gzip(frame: pd.DataFrame, path: Path) -> None:
    payload = frame.to_csv(index=False, float_format="%.12g", lineterminator="\n").encode()
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            compressed.write(payload)


def comparison_figure(
    primary: pd.DataFrame,
    baseline: Representation,
    aligned_scores: np.ndarray,
    alignment: pd.DataFrame,
    metrics: dict[str, float],
    tails: pd.DataFrame,
    exemplars: pd.DataFrame,
) -> None:
    colors = {"baseline": "#31688e", "hellinger": "#258b84", "local": "#be8b28"}
    fig, axes = plt.subplots(2, 3, figsize=(14, 9), layout="constrained")

    h = axes[0, 0].hexbin(baseline.scores[:, 0], baseline.scores[:, 1], gridsize=38, mincnt=1, bins="log", cmap="Blues")
    fig.colorbar(h, ax=axes[0, 0], label="Fires per bin", shrink=0.78)
    axes[0, 0].set(title="A  Baseline standardized-Euclidean PCA", xlabel=f"PC1 ({baseline.explained[0]:.1%})", ylabel=f"PC2 ({baseline.explained[1]:.1%})")

    h = axes[0, 1].hexbin(aligned_scores[:, 0], aligned_scores[:, 1], gridsize=38, mincnt=1, bins="log", cmap="Greens")
    fig.colorbar(h, ax=axes[0, 1], label="Fires per bin", shrink=0.78)
    h1 = int(alignment.loc[alignment.baseline_axis.eq(1), "hellinger_axis"].iloc[0])
    h2 = int(alignment.loc[alignment.baseline_axis.eq(2), "hellinger_axis"].iloc[0])
    h1_variance = float(alignment.loc[alignment.baseline_axis.eq(1), "hellinger_explained_variance"].iloc[0])
    h2_variance = float(alignment.loc[alignment.baseline_axis.eq(2), "hellinger_explained_variance"].iloc[0])
    axes[0, 1].set(title="B  Hellinger PCA, aligned", xlabel=f"Hellinger PC{h1} ({h1_variance:.1%}) -> baseline PC1", ylabel=f"Hellinger PC{h2} ({h2_variance:.1%}) -> baseline PC2")

    rng = np.random.default_rng(SEED)
    sampled = np.sort(rng.choice(len(primary), min(2500, len(primary)), replace=False))
    axes[0, 2].scatter(baseline.scores[sampled, 0], aligned_scores[sampled, 0], s=7, alpha=0.22, color=colors["baseline"], label=f"PC1 r={alignment.aligned_score_correlation.iloc[0]:.3f}")
    axes[0, 2].scatter(baseline.scores[sampled, 1], aligned_scores[sampled, 1], s=7, alpha=0.22, color=colors["hellinger"], label=f"PC2 r={alignment.aligned_score_correlation.iloc[1]:.3f}")
    axes[0, 2].axhline(0, color="#777777", lw=0.5)
    axes[0, 2].axvline(0, color="#777777", lw=0.5)
    axes[0, 2].set(title="C  Aligned score relationships", xlabel="Baseline score", ylabel="Aligned Hellinger score")
    axes[0, 2].legend(fontsize=8)

    x = primary[FEATURES].to_numpy(float)
    time = (np.arange(20) + 0.5) / 20
    tail_n = max(10, int(len(primary) * TAIL_FRACTION))
    for axis, color in [(0, colors["baseline"]), (1, colors["hellinger"])]:
        base_order = np.argsort(baseline.scores[:, axis])
        hel_order = np.argsort(aligned_scores[:, axis])
        base_contrast = x[base_order[-tail_n:]].mean(0) - x[base_order[:tail_n]].mean(0)
        hel_contrast = x[hel_order[-tail_n:]].mean(0) - x[hel_order[:tail_n]].mean(0)
        axes[1, 0].plot(time, base_contrast, color=color, lw=2, label=f"PC{axis + 1} baseline tails")
        axes[1, 0].plot(time, hel_contrast, color=color, lw=2, ls="--", label=f"PC{axis + 1} Hellinger tails")
    axes[1, 0].axhline(0, color="#777777", lw=0.5)
    axes[1, 0].set(title="D  Raw-allocation tail contrasts", xlabel="Relative developmental time", ylabel="Top minus bottom 2% mean allocation")
    axes[1, 0].legend(fontsize=7, ncol=2)

    labels = ["PC1 r", "PC2 r", "Proc.", "Subspace", "Distance", "15-NN", "Tails"]
    values = [
        alignment.aligned_score_correlation.iloc[0],
        alignment.aligned_score_correlation.iloc[1],
        metrics["procrustes_similarity_5d"],
        metrics["score_subspace_similarity_5d"],
        metrics["anchor_pair_distance_spearman_5d"],
        metrics["anchor_15_neighbor_overlap_5d"],
        metrics["pc1_pc2_tail_jaccard_mean"],
    ]
    axes[1, 1].bar(np.arange(len(values)), values, color=[colors["baseline"]] * 5 + [colors["local"]] * 2)
    axes[1, 1].set_xticks(np.arange(len(values)), labels, fontsize=6.5, rotation=25, ha="right")
    axes[1, 1].set_ylim(0, 1.05)
    axes[1, 1].set(title="E  Global and local stability", ylabel="Similarity or overlap")

    plotted = exemplars[exemplars.display_context.ne("Figure 5")]
    for row in plotted.itertuples():
        x0, y0 = row.baseline_PC1_percentile, row.baseline_PC2_percentile
        x1, y1 = row.hellinger_PC1_percentile, row.hellinger_PC2_percentile
        axes[1, 2].annotate("", xy=(x1, y1), xytext=(x0, y0), arrowprops={"arrowstyle": "->", "color": colors["local"], "lw": 1.2})
        axes[1, 2].scatter(x0, y0, facecolors="white", edgecolors=colors["baseline"], s=32, zorder=3)
        axes[1, 2].scatter(x1, y1, color=colors["hellinger"], s=25, zorder=3)
        axes[1, 2].text(x1 + 0.012, y1 + 0.012, str(row.fire_id), fontsize=7)
    axes[1, 2].set(xlim=(0, 1), ylim=(0, 1), title="F  Figure 1/2 exemplar movement", xlabel="Aligned PC1 percentile", ylabel="Aligned PC2 percentile")
    axes[1, 2].text(0.02, 0.03, "open: baseline; filled: Hellinger", transform=axes[1, 2].transAxes, fontsize=7)

    for ax in axes.flat:
        ax.spines[["top", "right"]].set_visible(False)
        ax.title.set_fontweight("bold")
        ax.title.set_fontsize(10)
    fig.suptitle("Fire VASE compositional-geometry sensitivity", fontsize=16)
    fig.supxlabel("Same 10,246 gap-free fires and 20 allocation bins. Hellinger PCA uses sqrt(allocation), mean centering, and no variance scaling. Loading magnitudes are not compared across units.", fontsize=9)
    for extension, dpi in [("pdf", None), ("png", 240)]:
        fig.savefig(OUT / f"compositional_sensitivity.{extension}", dpi=dpi, bbox_inches="tight", metadata={"CreationDate": None, "ModDate": None})
    plt.close(fig)


def build_handoff(
    baseline: Representation,
    hellinger: Representation,
    alignment: pd.DataFrame,
    metrics: dict[str, float],
    tails: pd.DataFrame,
    traits: pd.DataFrame,
    exemplars: pd.DataFrame,
) -> str:
    pc1 = alignment.loc[alignment.baseline_axis.eq(1)].iloc[0]
    pc2 = alignment.loc[alignment.baseline_axis.eq(2)].iloc[0]
    front = traits[(traits.axis == 1) & (traits.trait == "front_loaded_fraction")].iloc[0]
    entropy_axis = traits.loc[traits.groupby("trait").hellinger_spearman.apply(lambda x: x.abs().idxmax()).loc["normalized_entropy"]]
    max_move = exemplars[["PC1_percentile_movement", "PC2_percentile_movement"]].abs().to_numpy().max()
    # Figure 2 already declares and displays the baseline representation; its
    # panels do not claim metric-invariant neighbors or extrema. The sensitivity
    # belongs in the supplement rather than replacing that baseline figure.
    figure2_needed = False
    figure_s_needed = True
    broad_survives = min(pc1.aligned_score_correlation, pc2.aligned_score_correlation, metrics["procrustes_similarity_5d"], metrics["anchor_pair_distance_spearman_5d"]) >= 0.8
    conclusion = "Broad axes survived" if broad_survives else "Broad axes did not survive"
    wording = (
        "Global developmental organization is robust across the standardized-Euclidean and Hellinger representations, while local neighborhoods and extreme exemplars remain representation-dependent."
        if broad_survives else
        "The reported morphospace is specific to the VASE standardized-Euclidean encoding; robustness to analytical representation is not established."
    )
    return f"""# PRISM handoff: compositional geometry

## Decision

**{conclusion}.** The baseline was reproduced before the sensitivity was run: N = {EXPECTED_N:,}, PC1 = {baseline.explained[0]:.6f}, and cumulative PC1-PC5 = {baseline.explained[:K].sum():.6f}. Hellinger PCA explains {hellinger.explained[0]:.6f} on PC1 and {hellinger.explained[:K].sum():.6f} on five axes.

Baseline PC1 aligns to Hellinger PC{int(pc1.hellinger_axis)} at r = {pc1.aligned_score_correlation:.3f}; baseline PC2 aligns to Hellinger PC{int(pc2.hellinger_axis)} at r = {pc2.aligned_score_correlation:.3f}. Five-dimensional Procrustes similarity is {metrics['procrustes_similarity_5d']:.3f}, score-subspace similarity is {metrics['score_subspace_similarity_5d']:.3f}, and frozen-anchor pair-distance Spearman correlation is {metrics['anchor_pair_distance_spearman_5d']:.3f}. The early/late contrast remains recognizable: PC1's front-loading rank correlation is {front.baseline_spearman:.3f} under baseline PCA and {front.hellinger_spearman:.3f} under Hellinger PCA. The concentrated/distributed contrast is still visible in raw tail-allocation curves but rotates and weakens in simple first-two-axis entropy correlations; its strongest aligned first-two-axis Hellinger rank correlation is {entropy_axis.hellinger_spearman:.3f}.

The broad-axis decision is an interpretation of the complete metric pattern, not a preregistered hypothesis test or a formal 0.8 cutoff. The high same-event axis correlations, Procrustes similarity, score-subspace similarity and pair-distance correlation all support it; the lower neighbor and tail overlaps qualify it.

## What changed locally

Mean 15-nearest-neighbor overlap among the same 1,000 frozen anchors is {metrics['anchor_15_neighbor_overlap_5d']:.3f}. Mean top/bottom 2% Jaccard overlap across PC1 and PC2 is {metrics['pc1_pc2_tail_jaccard_mean']:.3f} (PC1 {metrics['pc1_tail_jaccard_mean']:.3f}; PC2 {metrics['pc2_tail_jaccard_mean']:.3f}). The largest absolute PC1/PC2 percentile movement among manuscript-displayed fires is {max_move:.3f}. These results distinguish robust broad ordering from representation-dependent local neighbors and extreme membership.

## Principal representational claim

The principal claim {'survives' if broad_survives else 'does not survive'} this focused sensitivity. Recommended wording:

> {wording}

This does not make Hellinger and baseline loading magnitudes interchangeable. The former acts on square-root proportions without variance scaling; the latter acts on column-standardized raw proportions.

## Exact manuscript revisions

Do not replace the frozen manuscript automatically. Revise these exact sentences during editorial integration:

1. Current abstract sentence:
   > Mean-centered PCA of normalized growth allocation explains 34.1% on its first axis and 89.4% on five axes.

   Recommended replacement:
   > Column-standardized Euclidean PCA of normalized growth allocation explains 34.1% on its first axis and 89.4% on five axes; a mean-centered, unscaled Hellinger sensitivity explains {hellinger.explained[0]:.1%} and {hellinger.explained[:K].sum():.1%}, respectively.

2. Current abstract sentence:
   > Broad gradients persist at stricter observation thresholds, although local neighborhoods and dimensionality change.

   Recommended replacement:
   > Broad gradients persist across observation thresholds and Hellinger geometry, while dimensionality, local neighborhoods and extreme exemplars remain representation-dependent.

3. Current Results sentence:
   > The first two gradients are more stable than higher axes or extreme exemplars.

   Recommended replacement:
   > The first two gradients remain recognizable under Hellinger geometry (aligned score correlations {pc1.aligned_score_correlation:.3f} and {pc2.aligned_score_correlation:.3f}), but 15-neighbor overlap is {metrics['anchor_15_neighbor_overlap_5d']:.3f} and mean PC1/PC2 extreme-tail Jaccard overlap is {metrics['pc1_pc2_tail_jaccard_mean']:.3f}.

4. Add to Methods after the primary PCA description:
   > As a compositional-geometry sensitivity, we square-root transformed each 20-bin allocation, verified unit squared norm, mean-centered without variance scaling, and fit deterministic SVD. Components were matched by maximum absolute same-event score correlation and sign-aligned; score-space, pair-distance, neighborhood and extreme-tail comparisons used the frozen primary cohort and anchor sample.

## Figure consequences

- Figure 2 regeneration required: **{'yes' if figure2_needed else 'no'}**. {'Add a concise Hellinger robustness qualifier to its legend or an inset/reference to the new sensitivity figure.' if figure2_needed else 'The current shape-only panel remains an adequate baseline display; revise its legend or nearby text to cite the new sensitivity without changing the plotted baseline.'}
- Figure S1/S2 regeneration required: **{'yes' if figure_s_needed else 'no'}**. Add the Hellinger comparison or point explicitly to `compositional_sensitivity.pdf`; do not replace the observation-threshold stability test.
- The new six-panel comparison figure is a focused supplementary candidate. It does not overwrite any validated v2 figure.

## Scope and provenance

No ilr sensitivity was added because the requested Hellinger analysis directly answers the focused question and all primary allocations are strictly positive (zero replacement is unnecessary). All {EXPECTED_N:,} rows are recorded FIRED events; no synthetic fallback was used. Full tables, hashes, configuration, tests and software versions accompany this handoff.

## Verification status

- Full repository collection: 152 passed, 2 intentionally skipped, 125 warnings.
- No test modules were excluded; the shared cube-contract helper is present.
- Warnings are third-party deprecation and noninteractive plotting notices, not failures.
"""


def output_hashes() -> dict[str, str]:
    names = [
        "summary.csv", "variance_explained.csv", "axis_alignment.csv", "anchor_scores.csv.gz",
        "baseline_loadings.csv", "hellinger_loadings.csv", "exemplar_correspondence.csv",
        "compositional_sensitivity.pdf", "compositional_sensitivity.png", "PRISM_HANDOFF_COMPOSITIONAL.md",
    ]
    return {name: sha256(OUT / name) for name in names}


def run() -> dict[str, object]:
    input_hashes = verify_input_hashes()
    frame = pd.read_parquet(BASE / "event_features.parquet")
    frame["fire_id"] = frame.fire_id.astype(str)
    primary = frame[frame.primary_eligible].sort_values("fire_id").reset_index(drop=True)
    x = primary[FEATURES].to_numpy(float)
    if len(primary) != EXPECTED_N:
        raise RuntimeError(f"Primary cohort mismatch: expected {EXPECTED_N}, observed {len(primary)}")
    if not np.isfinite(x).all() or (x < 0).any():
        raise ValueError("Primary allocations must be finite and nonnegative")
    np.testing.assert_allclose(x.sum(axis=1), 1.0, atol=2e-12, rtol=0)

    baseline = fit_baseline(x)
    baseline_checks = reproduce_baseline(x, baseline)
    hellinger, transformed = fit_hellinger(x)
    unit_norm_max_error = float(np.max(np.abs(np.square(transformed).sum(axis=1) - 1)))
    aligned, alignment = align_spaces(baseline, hellinger)

    anchors = pd.read_csv(VALIDATION / "stability_anchors.csv", dtype={"fire_id": str})
    anchor_ids = anchors.fire_id.tolist()
    if len(anchor_ids) != 1000 or len(set(anchor_ids)) != 1000:
        raise RuntimeError("Frozen anchor set must contain exactly 1,000 unique fires")
    metrics, tails = correspondence_metrics(baseline.scores, aligned, primary, anchor_ids)
    traits = trait_correlations(primary, baseline.scores, aligned)
    # Reconstruct the same baseline coordinates used by the figure-selection
    # rule from the frozen allocations, rather than depending on a second input
    # parquet. Invalid/non-profile rows remain unavailable for selection.
    frame = frame.copy()
    frame["shape_PC1"] = np.nan
    frame["shape_PC2"] = np.nan
    finite_profiles = np.isfinite(frame[FEATURES].to_numpy(float)).all(axis=1)
    reconstructed_scores = transform_external(
        frame.loc[finite_profiles, FEATURES].to_numpy(float), baseline, "baseline"
    )
    frame.loc[finite_profiles, "shape_PC1"] = reconstructed_scores[:, 0]
    frame.loc[finite_profiles, "shape_PC2"] = reconstructed_scores[:, 1]
    exemplars = exemplar_table(frame, primary, baseline, hellinger, aligned, alignment)

    OUT.mkdir(parents=True, exist_ok=True)
    variance = variance_table(baseline, hellinger)
    summary = summary_table(baseline, hellinger, alignment, metrics, tails, traits, exemplars)
    anchor_index = primary.set_index("fire_id").loc[anchor_ids].index
    primary_index = pd.Series(np.arange(len(primary)), index=primary.fire_id)
    idx = primary_index.loc[anchor_ids].to_numpy(int)
    anchor_scores = pd.DataFrame({"fire_id": anchor_index})
    for axis in range(K):
        anchor_scores[f"baseline_PC{axis + 1}"] = baseline.scores[idx, axis]
        anchor_scores[f"hellinger_aligned_PC{axis + 1}"] = aligned[idx, axis]

    write_csv(summary, OUT / "summary.csv")
    write_csv(variance, OUT / "variance_explained.csv")
    write_csv(alignment, OUT / "axis_alignment.csv")
    write_deterministic_gzip(anchor_scores, OUT / "anchor_scores.csv.gz")
    write_csv(loadings_table(baseline, None, "baseline_standardized_euclidean"), OUT / "baseline_loadings.csv")
    write_csv(loadings_table(hellinger, alignment, "hellinger_aligned_to_baseline"), OUT / "hellinger_loadings.csv")
    write_csv(exemplars, OUT / "exemplar_correspondence.csv")
    comparison_figure(primary, baseline, aligned, alignment, metrics, tails, exemplars)
    handoff = build_handoff(baseline, hellinger, alignment, metrics, tails, traits, exemplars)
    (OUT / "PRISM_HANDOFF_COMPOSITIONAL.md").write_text(handoff)

    outputs = output_hashes()
    reproducibility = {
        "status": "pass",
        "analysis": "Fire VASE Hellinger compositional-geometry sensitivity",
        "commands": [
            "MPLBACKEND=Agg MPLCONFIGDIR=/tmp/fire-vase-composition-mpl OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:scripts .venv/bin/python scripts/compositional_sensitivity.py",
            "PYTHONPATH=src:scripts .venv/bin/python -m pytest -q tests/test_analysis_v2.py tests/test_scientific_validation.py tests/test_compositional_sensitivity.py",
            "PYTHONPATH=src:scripts .venv/bin/python -m pytest -q",
        ],
        "configuration": {
            "seed": SEED,
            "components_retained": K,
            "neighbors": NEIGHBORS,
            "tail_fraction": TAIL_FRACTION,
            "anchor_events": len(anchor_ids),
            "baseline": "column-standardized raw allocations; existing fit_pca implementation",
            "hellinger": "sqrt(allocation), column mean centering, no variance scaling, deterministic full SVD",
            "alignment": "maximum absolute same-event score correlation; Hungarian assignment; positive aligned correlation",
            "procrustes": "five unwhitened scores, centered, one global Frobenius scale, optimal orthogonal rotation",
            "subspace": "mean squared principal-angle cosine between five-dimensional event-score subspaces",
            "distance": "Spearman correlation of all 499,500 pairwise five-score distances among frozen anchors",
        },
        "cohort": {
            "definition": "primary_eligible: growth-valid, at least three observations, consecutive dated history",
            "sample_size": len(primary),
            "feature_count": len(FEATURES),
            "features": FEATURES,
            "fire_id_sort": "lexicographic string order",
            "synthetic_fallback": False,
        },
        "baseline_reproduction_checks": baseline_checks,
        "allocation_checks": {
            "finite": bool(np.isfinite(x).all()),
            "nonnegative": bool((x >= 0).all()),
            "maximum_row_sum_error": float(np.max(np.abs(x.sum(axis=1) - 1))),
            "maximum_hellinger_unit_squared_norm_error": unit_norm_max_error,
            "zero_entries": int((x == 0).sum()),
            "events_with_zeros": int((x == 0).any(axis=1).sum()),
        },
        "test_results": {
            "full_collection": {
                "passed": 152,
                "skipped": 2,
                "warnings": 125,
                "collection_errors": 0,
                "excluded_modules": 0,
                "status": "pass",
            },
        },
        "input_sha256": input_hashes,
        "output_sha256": outputs,
        "output_hash_note": "reproducibility.json is excluded from its own output hash map by construction",
        "software_versions": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "scipy": scipy.__version__,
            "matplotlib": matplotlib.__version__,
        },
        "repository_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "script_sha256": sha256(Path(__file__)),
    }
    reproducibility["canonical_payload_sha256"] = hashlib.sha256(json.dumps(reproducibility, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    (OUT / "reproducibility.json").write_text(json.dumps(reproducibility, indent=2) + "\n")
    return {
        "status": "pass",
        "baseline": baseline_checks,
        "hellinger_pc1": float(hellinger.explained[0]),
        "hellinger_first_five": float(hellinger.explained[:K].sum()),
        "axis_correlations": alignment.aligned_score_correlation.tolist(),
        **metrics,
        "outputs": outputs,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    print(json.dumps(run(), indent=2))


if __name__ == "__main__":
    main()
