# Corrected v2 outputs

Start with `audit_report.md`, `issue_audit.csv`, and `legacy_dependency_audit.md`.
The scientific methods, units, estimands, thresholds and caveats are in
`docs/manuscripts/fire_vase_developmental_morphology/manuscript_v2.md`.

All CSV/JSON products here are generated from real, hashed v0.1 inputs. The
`null_*` and `matching_permutation` files are explicitly simulated controls,
not synthetic observations or replacements for missing real data. Parquet
files are local regenerable row-level products and are ignored by Git.

## Table families

- `input_audit`, `source_row_exclusions`, `semantic_summary` and compressed
  `event_semantic_audit.csv.gz`: original GeoPackage joins, exclusions, true
  daily peak, mean, probability entropy, area discrepancies and dated support.
- `neighborhood_rules`: priority, exact criterion and assigned fire count for
  every interpretive branch; no natural-class claim.
- `pca_*`, `axis_attribute_projections`, `morphospace_sensitivity`, `null_*`:
  ordinary shape-only PCA, loadings, variance, bootstrap axes and subspaces,
  years/regions/resolutions/cohorts, and duration/count-preserving controls.
- `event_predictors`, `event_performance`, `event_folds`, `event_uncertainty`,
  `event_preprocessing`: identical-cohort weather models. `alpha=1` is primary;
  0.01 and 100 are penalty sensitivities. Known outcomes used as predictors
  have `status=excluded_known_outcome`, never reported perfect skill.
- `event_fixed_length_strata`, `event_gappy_cohort_sensitivity`,
  `legacy_outcome_feature_cohort_comparison`: fixed duration/count and explicit
  feature-versus-cohort comparisons. Legacy outcomes are diagnostics only.
- `weather_inclusion_exclusion`, `adjusted_associations`: population selection
  and raw/partial rank associations. Partial coefficients adjust duration,
  count, area, region and month. Their bootstrap conditions on the nuisance fit.
- `day_t_weather_manifest`, `transition_audit`, `state_*`: exact dated state
  models, day-t geometry provenance, fold definitions, same-row spatial exposure
  comparison, paired increments and season/region/size/quality sensitivities.
- `matched_pairs`, `matched_examples`, `matching_sensitivity`,
  `matching_permutation`: unique partners, actual matching variables/distances,
  calipers, representative examples, good-candidate and assigned coverage, and
  conditional permutation references.
- `run_manifest`, `publication_manifest`, `verification`: provenance and
  reproducibility. `verification.md` describes test scope and pre-existing gaps.

All R² and ΔR² values are unitless. State outcomes are log(1 + km²) of next
calendar-day observed growth. Event log-area/log-duration are external outcomes,
not shape-defining variables. Weather means use degrees Celsius, kPa, m/s,
mm/day, relative humidity/fuel moisture percent, specific humidity kg/kg,
dimensionless danger indices and solar radiation W/m² as named in the columns.
GridMET fuel-moisture products are indices, not observed fuel loads.

Region/year/fire resampling intervals use 200 draws of fixed held-out errors,
not model refits; sparse geographic clusters limit inference. The main cohort
is deliberately restricted and does not stand in for the full population.
