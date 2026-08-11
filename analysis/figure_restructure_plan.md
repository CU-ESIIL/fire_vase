# Figure Restructure Plan

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
