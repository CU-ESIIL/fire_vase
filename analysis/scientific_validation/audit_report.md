# Second-pass scientific audit

Candidate baseline: `18c923cb0c82bf9f66567b62a3491ac30a28c369`. The preceding v2 closeout reproduced 60 numerical/publication artifact hashes in a saved-statistics render replay and reviewed all 12 manuscript pages. Targeted second-pass numerical replay validates primary event models at the prespecified penalty, three principal state models across all four blocks, the PCA, and exact matching IDs/order. See replay JSON files. This is not a blind rerun of archived/gappy/penalty grids.

## Correction audit

Statuses assess how completely the **preceding pass** implemented each correction. The last column distinguishes second-pass additions. All statuses use the requested vocabulary.

| issue | previous implementation | new implementation | status | evidence file | tests | scientific consequence |
| --- | --- | --- | --- | --- | --- | --- |
| Mean mislabeled as peak | Catalog area/duration called peak | Separate mean_catalog growth attribute; old label retired | CORRECTLY IMPLEMENTED | analysis/v2/event_semantic_audit.csv.gz | test_peak_is_not_mean | All 278569 old peaks equal the catalog mean; 108214 observed peaks differ. |
| True peak | No direct daily maximum | Maximum observed dated increment | CORRECTLY IMPLEMENTED | analysis/v2/semantic_summary.json | test_peak_is_not_mean | Observed daily maximum only, never instantaneous/hourly peak. |
| Entropy | Catalog denominator could fail if reconstruction incomplete | Normalize to actual increment sum; undefined zero/missing totals | CORRECTLY IMPLEMENTED | analysis/v2/semantic_summary.json | entropy and invalid-growth tests | Current entropy unchanged; defensive correction is material. |
| Area totals | Reconstruction equality assumed | Source join and per-event discrepancy audit | CORRECTLY IMPLEMENTED | analysis/v2/input_audit.json | source join assertions | Maximum relative discrepancy 6.46e-16; 931 orphan source rows remain documented exclusions. |
| Pulse and landmark logic | Observation count could trigger multi-pulse | Actual prominence-based peaks; ordered interpretive rules | CORRECTLY IMPLEMENTED | analysis/v2/neighborhood_rules.csv | test_pulses_require_detected_maxima_not_observation_count | Labels are not natural classes; gappy pulse traits remain sequence-based sensitivity only. |
| Exact dates | Adjacent rows interpreted as next day | One-calendar-day response before completeness filtering | CORRECTLY IMPLEMENTED | analysis/scientific_validation/population_audit.json | calendar and duplicate-date tests | 150922 longer gaps are not next-day transitions. Second pass also invalidates ambiguous duplicate prior-day state; no current rows affected. |
| Shape-only PCA | Mixed-scale median-centered SVD | Mean-centered standardized 20 normalized allocation masses | CORRECTLY IMPLEMENTED | analysis/v2/pca_loadings.csv | mass conservation and PCA replay | PC1 34.1%, five axes 89.4%, not the legacy 81.0/96.3%. |
| Endpoint removal | Area/duration/count/growth entered axes | Only allocation bins enter primary PCA | CORRECTLY IMPLEMENTED | analysis/scientific_validation/endpoint_projections.csv | verify_fire_vase_v2.py | Exclusion is not independence; moderate external associations persist. |
| Observation-count handling | Single-slice events mixed with rich histories | Primary >=3 consecutive; 1/2/gappy strata separate | CORRECTLY IMPLEMENTED | analysis/scientific_validation/observation_counts.csv | actual population assertions | Second pass adds >=2/3/5/7 common-anchor stability; local structure less stable than broad gradients. |
| Null histories | No adequate constraint baseline | Permutation and two Dirichlet nulls with fixed counts | PARTIALLY IMPLEMENTED | analysis/scientific_validation/null_history_comparison.csv | test_nulls_preserve_real_total_and_observation_count | v2 checked PCA geometry only; second pass adds actual-total conservation, trait/distance/landmark distributions. |
| Predictor nesting | Different sets mixed maximum VPD inclusion | Explicit core/full/maximum/length/quantile sets | CORRECTLY IMPLEMENTED | analysis/v2/event_predictors.csv | predictor nesting test | Effects are response-specific, not a cross-response median. |
| Common cohorts and folds | Feature and cohort changes confounded | Union-complete cohort, training-only preprocessing and fold PCA | CORRECTLY IMPLEMENTED | analysis/scientific_validation/event_fold_replay.csv | targeted alpha=1 numerical replay | 9212 fires, identical cohort and folds. Fold-PCs are local statistical targets, not guaranteed identical biological axes. |
| Maximum VPD opportunity | Extreme exposure interpreted without record-length control | Nested length controls and fixed-length strata | CORRECTLY IMPLEMENTED | analysis/scientific_validation/maximum_vpd_increment.csv | same-cohort model replay | Most extra max-VPD shape skill attenuates with opportunity controls; attenuation does not prove purely mechanical causation. |
| Geographic/seasonal/year confounding | Bivariate relations emphasized | v2 partial ranks control length, area, region, month but omit year | PARTIALLY IMPLEMENTED | analysis/scientific_validation/adjusted_weather_associations.csv | test_partial_rank_projects_both_outcomes_off_same_nuisance | Second pass adds categorical year and primary-cohort results; broad rain-pulse story weakens. |
| Weather selection | Complete fires treated as broadly representative | Region/year/size/morphology inclusion table | PARTIALLY IMPLEMENTED | analysis/scientific_validation/weather_selection_traits.csv | population census | Second pass adds explicit observation count and standardized differences; selection exactly excludes Alaska/Hawaii here. |
| State estimand | Adjacent-observation next growth | log1p exact next-calendar-day km2; common t-1,t,t+1 cohort | CORRECTLY IMPLEMENTED | analysis/scientific_validation/state_population.csv | state cohort hash/date assertions | 87944 transitions from 31700 fires, not all 196611 eligible transitions. |
| Spatial look-ahead | Final-event centroid exposure | Day-t newly burned-area centroid from raw geometry | CORRECTLY IMPLEMENTED | analysis/v2/day_t_weather_manifest.json | test_no_final_geometry_or_future_geometry_in_prospective_models | Removes final-geometry pathway, not retrospective reconstruction or timing limitations. |
| Autoregression | Weather totals without strong state comparator | Current/prior growth, cumulative area and elapsed time baseline | CORRECTLY IMPLEMENTED | analysis/scientific_validation/state_incremental_skill.csv | state replay | Most total skill is state-only; additive weather increment is about .005 R2. |
| VPD x state uncertainty/support | Visually emphasized interaction | v2 validates eight weather products jointly, not VPD specifically | PARTIALLY IMPLEMENTED | analysis/scientific_validation/vpd_incremental_robustness.csv | coefficient fixture and held-out ablations | Second pass isolates two VPD products; qualified positive average increment, heterogeneous coefficients. |
| Mismatch matching | Most-discordant neighbor selected | Outcome-blind greedy disjoint kNN graph with calipers | CORRECTLY IMPLEMENTED | analysis/scientific_validation/matching_balance.csv | exact pair replay and uniqueness assertions | Null-compatible mismatch; good-match existence is only within candidate graph. |
| Matching sensitivity | No representative prevalence design | v2 k/metric sensitivity, but no caliper variation | PARTIALLY IMPLEMENTED | analysis/scientific_validation/matching_caliper_sensitivity.csv | actual caliper/ID assertions | Second pass adds .25/.5/.75/1 sensitivity; paired fraction is design-dependent, not ecological prevalence. |
| Figure redesign | Legacy climate-centered panels | Five morphology-first figures | PARTIALLY IMPLEMENTED | analysis/scientific_validation/figure_claim_audit.csv | PDF/PNG visual QA | Second pass simplifies Figures 2/3, moves diagnostics to S2 and adds VPD-specific S3. |
| Manuscript numbers | Legacy headlines and overclaims | Versioned generated manuscript with corrected evidence | CORRECTLY IMPLEMENTED | docs/manuscripts/fire_vase_developmental_morphology/manuscript_v2.md | source/table checks and PDF QA | Second pass inserts stability/null/adjustment/interaction qualifications; archival values remain explicitly retired. |
| Tests and reproducibility | Legacy numerical reproduction alone | Invariant tests, numerical replays, deterministic rendering, and restored shared test contracts | CORRECTLY IMPLEMENTED | analysis/submission_freeze/test_report.md | full repository pytest command | Full collection passes: 152 passed, 2 skipped, 0 collection errors; no modules excluded. |
| Configuration integrity | Some declared thresholds silently ignored | Actual fixed defaults happen to match recorded settings | PARTIALLY IMPLEMENTED | scripts/fire_vase_v2.py | test_fixed_protocol_rejects_silent_threshold_override | Second pass rejects unsupported overrides. No current numerical value changes. |

## Observation-time semantics

There are 347,533 adjacent observed pairs: 196,611 one-day, 81,940 two-day and 68,982 longer than two days. Missing dates, duplicates and zero-growth observations are all zero in these inputs. Missing days are never inserted as zero. The 931 raw daily rows not linked to the event catalog remain exclusions, not silently added events.

| Quantity | Time basis | Permitted interpretation |
| --- | --- | --- |
| Pulse and reactivation counts | Observation sequence; consecutive daily only in primary | Low observed increments, not documented suppression or dormancy; gappy counts sensitivity-only |
| First/second differences | Fixed 20-bin normalized relative-time density | Dimensionless roughness, not km2/day velocity or acceleration |
| Next growth | Exact t to t+1 calendar day; AR also requires t-1 | Subsequent observed daily increment, conditioned on an observed transition |
| Duration | Catalog hours / 24; calendar span retained separately | Endpoint attribute, never PCA input |
| Allocation interpolation | Relative calendar time for consecutive histories; index time for gappy sensitivity | Mass-conserving rebinning, not additional observations |
| State weather | Day-t newly burned polygon centroid | Forward-dated response with retrospectively reconstructed end-of-day exposure; no final geometry |

One/two-observation and gappy events remain in the data narrative and separate sensitivity PCA fits. They do not define primary axes and are not silently projected as fully observed multi-day forms. This pass explicitly projects excluded endpoint attributes onto primary scores, not excluded events into the primary cohort.

## Stability interpretation

| label | n | first_five | subspace_overlap | pair_distance_spearman | neighbor_overlap | exemplar_tail_jaccard |
| --- | --- | --- | --- | --- | --- | --- |
| 2 | 27499 | 0.9247 | 0.9968 | 0.9988 | 0.8461 | 0.6680 |
| 3 | 10246 | 0.8944 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| 5 | 2887 | 0.8243 | 0.9583 | 0.9877 | 0.7702 | 0.4705 |
| 7 | 1171 | 0.7421 | 0.8945 | 0.9689 | 0.7179 | 0.6060 |

All fits use unchanged 20-bin features. Each comparison is evaluated on the same recorded 1000 primary-event anchors and 20000 sampled index pairs (self-pairs removed), using five unwhitened score axes. Assignment/sign alignment tests axes; Procrustes allows rotation and global scale; distance rank and 15-neighbor overlap test geometry; top/bottom 2% anchor-tail Jaccard tests exemplar stability. Repeated/tied profiles can affect neighbor identities. Bootstrap, >=2/3/5/7, region and year results are all exported. Regions/years with fewer than 30 primary events do not define a fit. Higher axes and local identity are less stable than leading gradients.

## Null interpretation

The second-pass seeded 4000-event sample is explicitly stored and differs from the original v2 null sample. Do not mix their observed baselines. Shuffle preserves count, true reconstructed total and the entire increment multiset; both Dirichlet nulls preserve count and total. Entropy is unchanged under shuffle, a useful negative control. Per-replicate trait quantiles, distance quantiles in a fixed primary-standardized metric, landmark proportions, dimensionality and concentration are exported. One hundred replicates give descriptive tail resolution 1/101; these are not multiplicity-adjusted significance declarations. Lower pulse/reactivation counts and higher front loading show nonrandom observed ordering, not a unique ecological cause.

## Weather, state and matching limitations

`weather_response_validation.csv` contains all individual responses, sets, blocks and three resampling units; its wide companion is convenience only. Known duration outcomes in length-predictor models are excluded. Fold PCA is trained without test data; axes are fold-local and metrics must not be interpreted as prediction of a universal PC1. Maximum VPD is more associated with duration than mean VPD; above-core max-VPD increments attenuate sharply with length controls. Fixed-length strata are retained as separate sensitivity tables, not quietly pooled.

Year-adjusted primary associations replace the gappy-inclusive main association narrative. Exact collinearity of duration/count in primary histories is handled by least-squares projection; it prevents estimating two distinct opportunity effects. Weather completeness is exactly geographic in this materialized input, so missingness is not ignorable. There are no weather data to validate Alaska/Hawaii transfer.

VPD interaction classification: **SUPPORTED WITH CAVEATS**. Full-sample product coefficients use original units and fire-cluster sandwich standard errors conditional on the ridge design/penalty. Per-year/region/season/size and training-fold refits test heterogeneity; VPD-product ablations test incremental held-out performance. Joint support is reported for both current and prior state; quantile bins merge where growth values tie. Central 1-99% VPD range is 0.19-3.48 kPa. A dense coarse cell does not license tail extrapolation or prove conditional positivity after every nuisance variable. Partial 2000/2021 years and small-size refits can change coefficient signs. No fitted response surface is shown.

Matching uses global matching-cohort scales, exact region/season/duration/count, RMS or mean-absolute z-distance, area ratio <=2, and no reuse within an analysis. Balance tables report absolute paired differences, not merely signed means that could cancel. The candidate graph is limited to k neighbors before area filtering; `candidate_fraction` is not exhaustive existence. Singleton permutation strata contain 2.79% of eligible events. Null results condition on declared strata, not a proof of universal independence. Both independent examples verify their own matching-space caliper; no two-by-two assertion remains.

## Figure-to-claim audit

| FIGURE | SCIENTIFIC QUESTION | DATA | ANALYSIS | CLAIM | WHAT THE FIGURE DOES NOT SHOW | DEPENDENCIES | VALIDATION STATUS |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | What does VASE encode? | Four real dated events | Observed increments, cumulative mass and elapsed-time rings | Encoding preserves ordering and makes gaps explicit | No causal mechanism or population prevalence | vase_slices.parquet; event_analysis.parquet; example_ids() | PASS: IDs and dates checked; visual review |
| 2 | What shape structure is represented? | 10246 consecutive >=3 histories | 20-bin PCA; first two loading contrasts; observation census; real glyphs | Shared broad developmental gradients without endpoint inputs | Not independence from endpoints, natural classes, or a biological wedge | pca_variance.csv; pca_loadings.csv; event_analysis.parquet | PASS: numerical PCA replay and threshold stress tests |
| 3 | Does external weather map to shape predictably? | 9212 common complete primary fires | Binned mean VPD and per-response blocked prediction | Weak, heterogeneous association with morphology | No uniform explanatory power, causation, or all-fire generality | event_uncertainty.csv; event_analysis.parquet | PASS: same cohort/folds; simplified to two panels |
| 4 | What does weather add above recent state? | 87944 transitions / 31700 fires | Six comparators; paired deltas; exposure/season checks | Small reproducible improvement above strong AR baseline | Not a VPD-specific curve, uniform subgroup skill, or live forecast | state_uncertainty.csv; state_spatial_exposure_sensitivity.csv; state_subgroup_sensitivity.csv | PASS: exact dates, hashes and numerical replay; VPD specifics in S3 |
| 5 | How much mismatch remains under declared matching? | 9212 eligible fires; 3710 weather and 3145 morphology pairs | Unique caliper pairs; conditional permutations; two independent median examples | Observed mismatch is compatible with this null; pairs are study candidates | No excess mismatch, ecological prevalence, 2x2 matching, or mechanism | matched_pairs.csv; matching_permutation.csv; matched_examples.csv | PASS: exact ID/order reproduction, balance, k/metric/caliper checks |

## Reproducibility and remaining implementation issues

Two safe guard corrections affect no current observations: reject declared fixed-protocol configuration overrides that would otherwise be ignored, and invalidate an ambiguous duplicate prior-day state. The current inputs have no duplicate dates. The shared test contracts are restored and the full repository suite now collects and passes without exclusions. The final reproducibility record distinguishes byte-identical regenerated tables/publications from reused v2 source/statistics hashes. The old v2 run manifest is historical provenance; the new validation/publication freeze supersedes stale publication hashes within it without rewriting history.
