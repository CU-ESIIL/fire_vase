# Statistical Validation

| claim | analysis | data subset | n | validation design | observed statistic | confidence interval | null or baseline | effect size | p-value | conclusion | figure panel |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Five PCs explain most geometry variance | Geometry-only PCA | all fires | 278569 | deterministic SVD plus bootstrap | 0.963 | 0.963 [0.962, 0.964] | feature/temporal nulls | null max mean 0.957 | not used as primary | strongly supported | Figure 1C-D |
| Low-dimensional result is stable | Stratified bootstrap PCA | duration-area-year-region strata | 278569 | 60 repeated subsamples | subspace overlap 1.000 | 1.000 [0.999, 1.000] | NA | high loading cosine | NA | supported | Figure 1D |
| Not explained entirely by one-day fires | Duration sensitivity | duration thresholds | 19528 | repeat PCA by threshold | minimum PC1-PC5 0.785 | see CSV | all-fire PCA | small-to-moderate change | NA | supported but needs fuller supplement | Figure 1E |
| Not explained entirely by feature redundancy | Feature ablation | feature sets | 278569 | repeat PCA after exclusions | minimum PC1-PC5 0.945 | see CSV | all-feature PCA | constraint persists in reduced sets | NA | supported provisionally | Supplementary Figure 1D |
| Medoids represent occupied regions | Coverage curve | all fires | 278569 | nearest medoid in PC1-PC3 | 36-medoid p90 distance 1.783 | see CSV | fewer medoids | distance declines with k | NA | supported | Figure 2B-C |
| Named forms overlap continuously | Nearest-neighbor label purity | 25k sample | 25000 | 15-neighbor local purity | 0.953 | NA | class-frequency reference 0.374 | overlap remains high | NA | supports landmarks-not-classes | Figure 2E |
| Climate predicts some morphology axes | Held-out OLS | climate-complete fires | 237235 | random, region-blocked, year-blocked CV | 0.184 [-0.001, 0.543] | fold intervals | blocked folds | blocked R2 lower/more conservative | NA | partially supported | Figure 4C |
| Morphology and climate are not equivalent | Matched-neighborhood analysis | 35k climate-complete sample | 35000 | nearest-neighbor matching in one space, distance in the other | see matched_population.csv | NA | random matches | non-equivalence visible | NA | supported provisionally | Figure 4D-E |
| Fixed-day geometry provides a leakage-audited benchmark | Fixed-day prediction | eligible fires by observed day | 10156236 | region/year blocked held-out OLS | 0.006 [-0.092, 0.109] | fold intervals | trivial stage summary and climate-only baselines | blocked performance is weak and sometimes negative | NA | provisional; replaces older leaky stage claim | Figure 5B-D |
| Climate adds incremental information after geometry | Delta R2 | fixed-day safe stages | 10156236 | region/year blocked held-out OLS | see safe_stage_prediction.csv | fold intervals | geometry-only model | small and stage-dependent | NA | provisional | Figure 5C |

## Leakage Audit

| feature_source | status | reason | action |
| --- | --- | --- | --- |
| developmental_stage_table.stage_growth_fraction | leakage risk | Computed as growth divided by final event area, unavailable at early prediction time. | Excluded from safe fixed-day prediction models. |
| developmental_stage_table.stage_width_mean | leakage risk | Uses normalized VASE width based on final cumulative area. | Excluded from safe fixed-day prediction models. |
| developmental_stage_table.pulse_count | leakage risk | Full-event pulse count can include future pulses. | Excluded from safe fixed-day prediction models. |
| fixed-day safe stage predictors | audited | Use only cumulative area, growth, active days, and climate observed up to day 1, 2, 4, or 8. | Used for Figure 5. |

## Unavailable Or Deferred Analyses

- Full 500-replicate bootstrap is implemented by increasing `--bootstrap-reps`, but the default local run uses fewer replicates for turnaround.
- UMAP, diffusion maps, PHATE, nonlinear model comparisons, and datashader density rendering are deferred because the required optional dependencies are not installed.
- Public archival data/code links and DOI-complete references remain placeholders.