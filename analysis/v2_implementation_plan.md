# Second-generation reanalysis plan (2026-08-28)

## Contract and preservation

Use the materialized `data_lake/fire-vase-data-lake-v0.1/files` as read-only
real input. No synthetic fallback. Preserve the existing figure/manuscript
generations unchanged; reproduce legacy calculations and figures under
`archive/comparison_v1/`. Write corrected tables under `analysis/v2/`, figures
under `figures/v2/`, and a versioned manuscript and PDF. Legacy results are
comparison evidence, not current conclusions.

## Implementation order

1. Reproduce legacy PCA, event/state model results and reference figures;
   record differences from cached numbers. Audit FIRED source attributes,
   dates, increments, catalog totals and extraction geometry against Parquet.
2. Normalize growth by reconstructed observed increments, distinguish catalog
   area, calculate actual observed daily peak, remove count-only pulse labels.
   Primary morphology: at least three dated, consecutive observations with
   positive reconstructed growth; keep short and gappy histories separate.
3. Mean-centered, scaled PCA on fixed-resolution relative-calendar-time
   growth allocation only. Treat shape traits, size, duration, count, region
   and weather as projections. Test resolutions, feature choices, strata,
   bootstrap axes and loadings, regional/year transfer, and duration/count
   preserving randomized allocations through the identical PCA pipeline.
4. Compare explicitly nested meteorological predictor sets on one complete
   cohort. Use region, contiguous year and crossed spatiotemporal holdouts,
   fold-trained scaling/PCA, penalty sensitivity, per-response scores and
   fire/year/region clustered uncertainty. Adjust associations for exposure
   opportunity, size, geography and season; quantify missingness.
5. Retain only exact calendar-day transitions before filtering weather.
   Compare mean/persistence/autoregressive/weather/additive/interaction models.
   Audit spatial support and use day-t geometry where feasible; otherwise
   explicitly report retrospective exposure and its limited interpretation.
6. Use caliper-constrained unique nearest-neighbor pairs with declared
   nuisance strata, metric/k sensitivities and constrained permutation
   references. Do not manufacture a two-by-two display if its constraints fail.
7. Write machine-readable statistics before figures; render five main figures
   plus supplement using the repository figure entry point. Generate manuscript
   text from computed values, compile and visually inspect PDF/figures. Add
   tests for all requested invariants and deterministic regeneration; record
   hashes, commands, versions, seeds, counts, exclusions and limitations.

## Early confirmed implementation issues

- Pilot `peak_growth_km2_per_hour` is catalog area / catalog duration.
- Developmental features consume that value despite calculating a true peak.
- Entropy normalizes by max(catalog area, reconstructed area), not necessarily
  by a probability sum; impact must be checked against the actual rows.
- Six observations trigger the old multi-pulse branch without detected pulses.
- Old SVD subtracts feature medians, not means: reported variance is uncentered
  second-moment variance rather than ordinary PCA variance.
- State targets shift rows after weather filtering, without checking dates.
- Weather sampling uses final-event centroids; perimeter exposure cache covers
  only 100 fires. Date gaps are present in the real daily observations.
- The old core weather set includes maximum VPD; the comprehensive set does
  not. Their independent complete-case selection is not a nested comparison.

Definitions, thresholds and conservative scope are declared before rerunning;
results will determine the revised claims, not the legacy narrative.
