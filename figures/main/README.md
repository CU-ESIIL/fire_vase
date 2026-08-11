# Fire VASE Main Figure Suite

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

The default run uses `60` bootstrap replicates and caches validation tables under `figures/main/derived_stats/`. Increase `--bootstrap-reps` for a final slow run.

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
