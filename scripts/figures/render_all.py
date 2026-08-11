#!/usr/bin/env python3
"""Render the complete Fire VASE main-figure suite and documentation."""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from make_figure_1 import build as build_figure_1
from make_figure_2 import build as build_figure_2
from make_figure_3 import build as build_figure_3
from make_figure_4 import build as build_figure_4
from make_figure_5 import build as build_figure_5
from make_supplementary_figures import build as build_supplement, save_supplement
from morphospace import DATA_DIR, TABLE_DIR, load_data
from statistics import compute_validation_bundle
from style import DERIVED_STATS_DIR, MAIN_FIGURE_DIR, ROOT, SUPPLEMENT_DIR, file_sha256, save_figure


MANUSCRIPT_VALUES = {
    "n_fires": 278569,
    "n_slices": 626102,
    "n_climate_complete_fires": 237235,
    "cumvar_pc1_5": 0.963,
    "pc1": 0.810,
    "pc2": 0.066,
    "pc3": 0.035,
    "pc4": 0.033,
    "pc5": 0.018,
}


def _git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return "unavailable"


def _package_versions() -> dict[str, str]:
    versions = {
        "python": platform.python_version(),
        "matplotlib": matplotlib.__version__,
        "numpy": np.__version__,
        "pandas": pd.__version__,
    }
    for name in ["scipy", "pyarrow"]:
        try:
            versions[name] = importlib.import_module(name).__version__
        except Exception:
            versions[name] = "unavailable"
    return versions


def _write_legends(stats) -> None:
    text = f"""# Main Figure Legends

## Figure 1. Whole-fire histories can be organized in a common developmental coordinate system.

(A) Fire VASE converts each real FIRED event into a comparable developmental object by mapping event time from bottom to top and normalized cumulative burned area to ring width. The examples pair each daily cumulative-area history with its VASE glyph; labels give the descriptive shape name, duration in days, and final burned area in square kilometers. (B) Geometry-only morphospace for {stats.observed['n_fires']:,} fires. The gray density field shows all events along the first two developmental gradients, darker tones indicate higher fire density, and red points identify high-occupancy real representative fires used as atlas landmarks. Axes report the variance explained by the underlying geometry-only principal components. (C) Scree plot and cumulative explained variance for the first ten developmental axes; vertical intervals mark stratified bootstrap variation for the first five axes. (D) Simple null comparisons place the observed five-axis variance against feature-wise and within-fire growth-timing permutation nulls. (E) Duration sensitivity repeats the PCA after excluding increasingly short fires. The low-dimensional result is strongest for the full population and weakens for longer-duration subsets.

Alt text: A multi-panel scientific figure showing real fire histories transformed into vase-shaped glyphs, a dense low-dimensional morphospace, PCA variance curves, null-model separation, and duration sensitivity.

## Figure 2. Wildfire occupies a continuous atlas of recurring developmental forms.

(A) The 18 highest-occupancy real representative Fire VASEs are placed over the full geometry-only density field. Each representative is an observed fire, not an idealized or synthetic glyph; leader lines connect displaced glyphs to true coordinates along the first two developmental gradients. (B) Representative-fire occupancy ranks landmarks by the number of fires closest to each representative in the first three developmental gradients, showing that some developmental neighborhoods are common whereas others are rare. (C) Coverage improves as the number of representative fires increases, quantified by median and 90th-percentile distance to the nearest representative. (D) Real-fire transects through gradients 1, 2, and 3 show gradual morphological change along the axes. (E) Local neighborhood purity compares observed label agreement with a class-frequency reference, supporting the interpretation of shape names as soft landmarks within a continuous morphospace rather than sharply separated classes.

Alt text: A morphospace atlas with many small Fire VASE glyphs, occupancy bars, medoid coverage curves, transects of changing glyph shape, and an overlap metric.

## Figure 3. PC1 is a robust but partly redundant developmental profile axis.

(A) Variance explained by PC1 under feature ablations: the full current feature set, features with scale and duration removed, normalized profile features only, growth-share profiles only, interpolated profile features removed, and fires lasting at least 10 days. (B) Cumulative variance in the first five axes for the same ablations. (C) A null hierarchy compares observed five-axis variance with developmental universes that preserve progressively more trivial structure. Feature permutation breaks all covariance; stricter nulls preserve final area, duration, zero-growth frequency, observed growth increments, or duration-bin mean profiles. (D) Support diagnostics compare null covariance volume and null-to-observed distance in the observed PC1-PC5 coordinate space; numbered labels follow the top-to-bottom null order in panel C. The figure supports a reproducible low-dimensional coordinate system but cautions against claiming that observed fires occupy a restricted subset of all plausible trajectories.

Alt text: Four quantitative panels showing PC1 sensitivity, first-five-axis variance, a hierarchy of null developmental models, and support-overlap diagnostics.

## Figure 4. Climate aligns with developmental geometry but does not uniquely determine it.

(A) Median maximum vapor pressure deficit (VPD, kPa) is projected onto the geometry-first morphospace for {stats.observed['n_climate_complete_fires']:,} climate-complete fires using daily centroid gridMET attribution. The axes remain the geometry-only developmental gradients from Figure 1, so climate does not define the coordinate system. (B) Additional climate surfaces show average daily high temperature in degrees C, average VPD in kPa, and average wind speed in m/s in the same coordinate system. (C) Held-out linear association models compare shape recovered from climate and climate recovered from shape under random and region-blocked validation; error bars summarize fold variation. (D) Matched real-fire examples show similar shape under contrasting climate and similar climate under contrasting shape. (E) Population-level nearest-neighbor matching compares climate and morphology distances. Climate associations are interpreted as alignment and recoverability, not causation.

Alt text: Climate-colored morphospace maps, predictive performance bars with intervals, matched Fire VASE pairs, and population matching summaries.

## Supplementary Figure 2. Fixed-day partial histories provide a leakage-audited developmental benchmark.

(A) A real fire is truncated at fixed observed-day stages to illustrate the prediction task. For each stage, the partial VASE contains only information available by that day, while the adjacent final VASE shows the complete event. (B) Region-blocked prediction accuracy for final shape compares trivial stage summaries, climate-only predictors, geometry-only predictors, and geometry-plus-climate predictors. Values near or below zero mean that the fixed-day linear model does not generalize beyond the held-out mean under blocked validation. (C) Incremental climate value is shown as the accuracy gain from adding climate beyond geometry-only prediction. (D) Observed versus predicted final main shape score for held-out day-4 region-blocked predictions illustrates the conservative benchmark. (E) Leakage audit explains why older fractional-stage variables normalized by final area or counted future pulses are excluded; only fixed-day safe predictors are used in this figure.

Alt text: Partial and complete Fire VASE glyphs, held-out prediction performance by observed day, climate increment bars, observed-predicted scatter, and a leakage audit.
"""
    (MAIN_FIGURE_DIR / "figure_legends.md").write_text(text, encoding="utf-8")


def _fmt_interval(series: pd.Series) -> str:
    vals = series.dropna().to_numpy(float)
    if vals.size == 0:
        return "NA"
    return f"{np.mean(vals):.3f} [{np.quantile(vals, 0.025):.3f}, {np.quantile(vals, 0.975):.3f}]"


def _write_validation(stats) -> None:
    boot = stats.pca_bootstrap
    null = stats.pca_null[stats.pca_null["null_model"] != "observed"]
    duration_min = stats.duration_sensitivity["cumvar_pc1_5"].min()
    ablation_min = stats.ablation["cumvar_pc1_5"].min()
    climate_blocked = stats.climate_cv[stats.climate_cv["fold_kind"].isin(["region", "year_block"])]
    stage_blocked = stats.safe_stage_prediction[stats.safe_stage_prediction["fold_kind"].isin(["region", "year_block"])]
    rows = [
        ["Five PCs explain most geometry variance", "Geometry-only PCA", "all fires", stats.observed["n_fires"], "deterministic SVD plus bootstrap", f"{stats.observed['cumvar_pc1_5']:.3f}", _fmt_interval(boot["cumvar_pc1_5"]), "feature/temporal nulls", f"null max mean {null.groupby('null_model')['cumvar_pc1_5'].mean().max():.3f}", "not used as primary", "strongly supported", "Figure 1C-D"],
        ["Low-dimensional result is stable", "Stratified bootstrap PCA", "duration-area-year-region strata", stats.observed["n_fires"], f"{stats.observed['bootstrap_replicates']} repeated subsamples", f"subspace overlap {boot['subspace_overlap'].median():.3f}", _fmt_interval(boot["subspace_overlap"]), "NA", "high loading cosine", "NA", "supported", "Figure 1D"],
        ["Not explained entirely by one-day fires", "Duration sensitivity", "duration thresholds", int(stats.duration_sensitivity["n"].min()), "repeat PCA by threshold", f"minimum PC1-PC5 {duration_min:.3f}", "see CSV", "all-fire PCA", "small-to-moderate change", "NA", "supported but needs fuller supplement", "Figure 1E"],
        ["Not explained entirely by feature redundancy", "Feature ablation", "feature sets", stats.observed["n_fires"], "repeat PCA after exclusions", f"minimum PC1-PC5 {ablation_min:.3f}", "see CSV", "all-feature PCA", "constraint persists in reduced sets", "NA", "supported provisionally", "Supplementary Figure 1D"],
        ["Medoids represent occupied regions", "Coverage curve", "all fires", stats.observed["n_fires"], "nearest medoid in PC1-PC3", f"36-medoid p90 distance {stats.medoid_coverage.iloc[-1]['p90_nearest_distance']:.3f}", "see CSV", "fewer medoids", "distance declines with k", "NA", "supported", "Figure 2B-C"],
        ["Named forms overlap continuously", "Nearest-neighbor label purity", "25k sample", 25000, "15-neighbor local purity", f"{stats.category_overlap.iloc[0]['value']:.3f}", "NA", f"class-frequency reference {stats.category_overlap.iloc[0]['null_or_reference']:.3f}", "overlap remains high", "NA", "supports landmarks-not-classes", "Figure 2E"],
        ["Climate predicts some morphology axes", "Held-out OLS", "climate-complete fires", stats.observed["n_climate_complete_fires"], "random, region-blocked, year-blocked CV", _fmt_interval(climate_blocked[climate_blocked["model"] == "climate predicts morphology"]["r2"]), "fold intervals", "blocked folds", "blocked R2 lower/more conservative", "NA", "partially supported", "Figure 4C"],
        ["Morphology and climate are not equivalent", "Matched-neighborhood analysis", "35k climate-complete sample", 35000, "nearest-neighbor matching in one space, distance in the other", "see matched_population.csv", "NA", "random matches", "non-equivalence visible", "NA", "supported provisionally", "Figure 4D-E"],
        ["Fixed-day geometry provides a leakage-audited benchmark", "Fixed-day prediction", "eligible fires by observed day", int(stage_blocked["n_test"].sum()) if not stage_blocked.empty else 0, "region/year blocked held-out OLS", _fmt_interval(stage_blocked[stage_blocked["model"] == "geometry only"]["r2"]), "fold intervals", "trivial stage summary and climate-only baselines", "blocked performance is weak and sometimes negative", "NA", "provisional; replaces older leaky stage claim", "Figure 5B-D"],
        ["Climate adds incremental information after geometry", "Delta R2", "fixed-day safe stages", int(stage_blocked["n_test"].sum()) if not stage_blocked.empty else 0, "region/year blocked held-out OLS", "see safe_stage_prediction.csv", "fold intervals", "geometry-only model", "small and stage-dependent", "NA", "provisional", "Figure 5C"],
    ]
    header = ["claim", "analysis", "data subset", "n", "validation design", "observed statistic", "confidence interval", "null or baseline", "effect size", "p-value", "conclusion", "figure panel"]
    lines = ["# Statistical Validation\n", "| " + " | ".join(header) + " |", "| " + " | ".join(["---"] * len(header)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(v).replace("|", "/") for v in row) + " |")
    lines.append("\n## Leakage Audit\n")
    lines.append(_markdown_table(stats.leakage_audit))
    lines.append("\n## Unavailable Or Deferred Analyses\n")
    lines.append("- Full 500-replicate bootstrap is implemented by increasing `--bootstrap-reps`, but the default local run uses fewer replicates for turnaround.")
    lines.append("- UMAP, diffusion maps, PHATE, nonlinear model comparisons, and datashader density rendering are deferred because the required optional dependencies are not installed.")
    lines.append("- Public archival data/code links and DOI-complete references remain placeholders.")
    (MAIN_FIGURE_DIR / "statistical_validation.md").write_text("\n".join(lines), encoding="utf-8")


def _write_dictionary(data) -> None:
    rows = []
    for name, frame in data.items():
        if isinstance(frame, pd.DataFrame):
            for col in frame.columns:
                rows.append({"table": name, "column": col, "dtype": str(frame[col].dtype), "description": _describe_column(col)})
    out = pd.DataFrame(rows)
    lines = ["# Figure Data Dictionary\n", _markdown_table(out)]
    (MAIN_FIGURE_DIR / "figure_data_dictionary.md").write_text("\n".join(lines), encoding="utf-8")


def _markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "_No rows._"
    cols = list(frame.columns)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in frame.iterrows():
        lines.append("| " + " | ".join(str(row[col]).replace("|", "/").replace("\n", " ") for col in cols) + " |")
    return "\n".join(lines)


def _describe_column(col: str) -> str:
    if col.startswith("morph_pc"):
        return "Geometry-only Fire VASE morphospace coordinate."
    if col.startswith("width_p"):
        return "Interpolated normalized cumulative-width profile feature."
    if col.startswith("growth_p"):
        return "Interpolated daily-growth fraction profile feature."
    if "temperature" in col or "tmax" in col or "tmin" in col:
        return "gridMET centroid temperature in degrees C."
    if "vpd" in col:
        return "gridMET centroid vapor pressure deficit in kPa."
    if "wind" in col:
        return "gridMET centroid wind speed or wind-presence summary."
    if col == "shape_label":
        return "Rule-based descriptive landmark label, not a discovered natural class."
    if col == "fire_id":
        return "FIRED event identifier represented as a string."
    return "Derived Fire VASE analysis field used by the figure suite."


def _write_readme(args) -> None:
    text = f"""# Fire VASE Main Figure Suite

This directory contains a publication-oriented four-figure suite for the manuscript **Fire VASE Provides a Low-Dimensional Coordinate System for Wildfire Development**.

## Regenerate

Run from the repository root:

```bash
.venv/bin/python scripts/figures/render_all.py
```

Use `--force-validation` to recompute cached validation tables. Use `--bootstrap-reps 500` for a heavier Science-review validation run.

## Inputs

- `scratch/fire_vase_developmental_morphology/developmental_morphospace_features.parquet`
- `scratch/fire_vase_developmental_morphology/developmental_morphospace_medoids.parquet`
- `scratch/fire_vase_developmental_morphology/developmental_morphospace_loadings.csv`
- `scratch/fire_vase_developmental_morphology/developmental_stage_table.parquet`
- `scratch/fire_vase_developmental_morphology/developmental_climate_coupling.parquet`
- `scratch/fire_vase_developmental_morphology/developmental_matched_pairs.parquet`
- `scratch/fire_vase_run_full/tables/vase_slices.parquet`
- `scratch/fire_vase_run_full/tables/fire_traits.parquet`

## Outputs

Each main figure is exported as PDF, PNG, and SVG: `Figure_1` through `Figure_4`.
Fixed-day prediction is exported as `figures/supplement/Supplementary_Figure_2_prediction.*`.
Supplementary validation output is also written under `figures/supplement/`.

## Statistical Analyses

The pipeline performs geometry-only PCA recomputation, stratified bootstrap PCA stability, feature-permutation and within-fire growth-profile nulls, duration sensitivity, feature ablation, audited PC1 robustness, defensible null-developmental-universe summaries, medoid coverage, neighborhood label-overlap analysis, random/blocked climate association, matched-neighborhood diagnostics, and a leakage-audited fixed-day stage prediction analysis.

## Runtime

The default run uses `{args.bootstrap_reps}` bootstrap replicates and caches validation tables under `figures/main/derived_stats/`. Increase `--bootstrap-reps` for a final slow run.

## Style

Typography, palette, figure dimensions, and output resolution are controlled in `scripts/figures/style.py`.

## Robust Conclusions

- Fire VASE provides a shared, reproducible, low-dimensional coordinate system for whole-fire histories.
- The result persists under many feature ablations but weakens for longer-duration fire subsets.
- Medoids are real observed fires and provide a compact atlas of occupied regions.
- Climate aligns with morphology but does not uniquely determine developmental form.

## Conservative Conclusions

- The current data do not yet justify the stronger claim that observed fires occupy a restricted subset of all plausible developmental trajectories after accounting for monotonicity, size, duration, and feature redundancy.
- Climate analysis should remain a proof of concept until perimeter/active-area climate exposure and local anomalies are integrated.
- Stage-wise prediction is retained as a supplementary leakage audit, not a main affirmative result.
"""
    (MAIN_FIGURE_DIR / "README.md").write_text(text, encoding="utf-8")


def _write_manifest(outputs: dict, data, stats) -> None:
    files = []
    for path in list(MAIN_FIGURE_DIR.glob("Figure_*.*")) + list(SUPPLEMENT_DIR.glob("Supplementary_Figure_*.*")):
        files.append({"path": path.as_posix(), "sha256": file_sha256(path), "bytes": path.stat().st_size})
    discrepancies = []
    observed = stats.observed
    comparisons = {
        "n_fires": observed["n_fires"],
        "n_slices": observed["n_slices"],
        "n_climate_complete_fires": observed["n_climate_complete_fires"],
        "cumvar_pc1_5": observed["cumvar_pc1_5"],
        "pc1": observed["pc_explained_variance"][0],
        "pc2": observed["pc_explained_variance"][1],
        "pc3": observed["pc_explained_variance"][2],
        "pc4": observed["pc_explained_variance"][3],
        "pc5": observed["pc_explained_variance"][4],
    }
    for key, value in comparisons.items():
        manuscript = MANUSCRIPT_VALUES[key]
        diff = float(value - manuscript) if isinstance(value, float) else int(value) - int(manuscript)
        if abs(diff) > (0.0015 if isinstance(value, float) else 0):
            discrepancies.append({"metric": key, "manuscript_value": manuscript, "recomputed_value": value, "difference": diff})
    manifest = {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "git_commit": _git_commit(),
        "random_seed": 20260722,
        "data_files": [p.as_posix() for p in DATA_DIR.glob("*")] + [p.as_posix() for p in TABLE_DIR.glob("*.parquet")],
        "environment": _package_versions(),
        "outputs": outputs,
        "checksums": files,
        "validation_cache": DERIVED_STATS_DIR.as_posix(),
        "manuscript_value_discrepancies": discrepancies,
    }
    (MAIN_FIGURE_DIR / "figure_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def render(args: argparse.Namespace) -> dict:
    data = load_data()
    stats = compute_validation_bundle(data, reps=args.bootstrap_reps, sample_size=args.sample_size, force=args.force_validation)
    outputs = {}
    for name, builder in [
        ("Figure_1", build_figure_1),
        ("Figure_2", build_figure_2),
        ("Figure_3", build_figure_3),
        ("Figure_4", build_figure_4),
    ]:
        fig = builder(data, stats)
        outputs[name] = save_figure(fig, name)
        plt.close(fig)
    pred = build_figure_5(data, stats)
    outputs["Supplementary_Figure_2_prediction"] = save_supplement(pred, "Supplementary_Figure_2_prediction")
    plt.close(pred)
    supp = build_supplement(data, stats)
    outputs["Supplementary_Figure_1_validation"] = save_supplement(supp, "Supplementary_Figure_1_validation")
    plt.close(supp)
    _write_legends(stats)
    _write_validation(stats)
    _write_dictionary(data)
    _write_readme(args)
    _write_manifest(outputs, data, stats)
    return outputs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bootstrap-reps", type=int, default=160)
    parser.add_argument("--sample-size", type=int, default=25000)
    parser.add_argument("--force-validation", action="store_true")
    args = parser.parse_args()
    print(json.dumps(render(args), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
