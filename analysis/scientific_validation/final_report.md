# Final scientific validation report

1. Repository baseline SHA: `18c923cb0c82bf9f66567b62a3491ac30a28c369`; subsequent working-tree code and output hashes are in the freeze manifest.
2. Previous pass reproduced: 60-file render replay; PCA, primary alpha=1 event/state models, cohorts/folds and unique pair IDs reproduced. Historical v1 event/state tables reproduced to <1e-15 in the preceding pass. No claim of rerunning every archived sensitivity.
3. Remaining implementation errors: no known numerical error affecting these data. Two guard defects corrected (ignored fixed-protocol overrides and ambiguous duplicate prior state). Pre-existing full-test collection gap remains. Event-year/month are fire-level, not observation-level seasonal effects.
4. Primary population: 10246 valid >=3 consecutive histories; 9212 complete primary weather fires. Matching uses the same 9212; state analysis is a different explicitly identified transition cohort.
5. Observation distribution: 161073 one-slice, 47950 two-slice, 69546 >=3, 30538 >=5, 15036 >=7. Consecutive >=3/5/7 counts: 10246/2887/1171. Threshold rows overlap; do not sum them.
6. Exact-day transitions: 196611 of 347533 adjacent pairs; 81940 two-day and 68982 longer gaps. Common AR cohort: 87944 transitions, 31700 fires. Missing/duplicate dates and observed zero increments: zero.
7. Morphospace: mean-centered standardized PCA of 20 mass-conserving normalized growth-allocation bins; five-axis geometry, not a new feature search.
8. Excluded inputs: final area, duration, observation count, absolute peak/mean growth, slenderness and weather. They are external attributes only.
9. Observation-threshold stability: >=7 PC1/2 common-anchor correlations 0.985/0.997, distance rho 0.969; local neighbors 0.718, exemplar-tail overlap 0.606. Five-axis coverage falls to 74.2%. Full bootstrap/year/region results are in `morphospace_stability.csv`.
10. Null result: observed first-half allocation 0.541 versus shuffle 0.500; pulses 1.249 versus 1.413; reactivation 0.038 versus 0.120. Ordering differs; compression alone is not uniquely biological.
11. Endpoint relationship: PC1 Spearman area -.308, duration/count -.185, true peak -.332; PC2 area .259, duration/count .256. Excluded variables remain moderately associated with shape.
12. Strongest adjusted associations: mean VPD versus late allocation rho -0.069; mean VPD/front loading +.050, precipitation/late allocation +.041. Primary precipitation/pulses falls from 0.070 to 0.025, with region interval crossing zero. All are small; no causal claim.
13. Per-response weather performance: table below uses core means + maximum VPD; all nested sets and fire/year/region intervals are in `weather_response_validation.csv`. Stronger response skill lies in roughness/taper/entropy than peak timing or fold PCs. The latter are training-fold-local targets.
14. Weather selection: 237235 complete CONUS events; all 41279 Alaska and 55 Hawaii events incomplete. Complete mean duration 3.34 vs 2.35 days and mean count 2.32 vs 1.82; standardized entropy difference .309. Geography and observation process restrict generality.
15. State-only performance: pooled AR R2 .448 regional and crossed space-time; .458 random/year. Small-fire absolute performance is weaker and can be negative.
16. Incremental weather: additive about .005 R2; all weather-state products .015-.018 over AR. Table below and `state_incremental_skill.csv` contain all blocks and paired uncertainty.
17. VPD x state: SUPPORTED WITH CAVEATS. VPD products add .006-.012 over the other interaction products; global current/prior coefficients 0.217/-0.118. Blocked average increments are positive, but region/size and edge-year coefficient heterogeneity precludes a universal curve.
18. Matching: 9212 eligible; 3710 weather pairs (80.5% paired), 3145 morphology pairs (68.3% paired). Candidate-graph coverage 91.2%/81.3%. Caliper .25-1 changes paired coverage to 59.8-85.7% / 54.0-77.9%.
19. Mismatch/null: observed >1 fractions .497 vs null .504 and .395 vs .402, within conditional permutation ranges. No excess mismatch detected. Not an ecological prevalence estimate.
20. Strongest conclusion: broad shape geometry and nonrandom ordering among adequately observed histories; representation precedes environmental explanation.
21. Most important negative result: low dimensionality does not establish biological restriction; measured event weather has weak heterogeneous shape skill, and mismatch is null-compatible.
22. Largest limitation: observation-process selection and timing uncertainty; only 3.68% of catalog events enter primary shape training. Missing mechanistic covariates and retrospective exposure further limit environmental interpretation.
23. Main figures changed: Figures 2 and 3 simplified; Figures 1, 4 and 5 retain their main analytical design. New S2 holds stability/null/adjustment/caliper checks; S3 holds VPD support/coefficients/ablation. Full figure-to-claim audit accompanies them.
24. Claims changed: strengthen ordering evidence and bounded VPD incremental support; qualify local neighborhood/long-history stability; weaken rain/pulses and broad weather predictability; remove excess mismatch, biological wedge and untested absence-of-types claims.
25. Prism handoff: `analysis/scientific_validation/PRISM_HANDOFF.md`.
26. Final manuscript PDF: `output/pdf/fire_vase_v2_manuscript.pdf`; source: `docs/manuscripts/fire_vase_developmental_morphology/manuscript_v2.md`.

## Individual weather responses

| response | random_fire | region_block | spatiotemporal | year_block |
| --- | --- | --- | --- | --- |
| front_loaded_fraction | 0.0376 | 0.0215 | 0.0210 | 0.0356 |
| late_growth_fraction | 0.0516 | 0.0383 | 0.0370 | 0.0500 |
| log_area | 0.2442 | 0.2060 | 0.2005 | 0.2377 |
| log_duration | 0.2173 | 0.1962 | 0.1900 | 0.2111 |
| normalized_entropy | 0.1043 | 0.0744 | 0.0725 | 0.1024 |
| normalized_first_difference | 0.2022 | 0.1755 | 0.1704 | 0.1971 |
| normalized_second_difference | 0.1823 | 0.1606 | 0.1565 | 0.1780 |
| peak_timing | 0.0024 | 0.0005 | 0.0003 | 0.0021 |
| pulse_count | 0.0213 | 0.0191 | 0.0183 | 0.0204 |
| reactivation_count | 0.0270 | 0.0220 | 0.0208 | 0.0247 |
| shape_PC1_fold | 0.0415 | 0.0066 | 0.0029 | 0.0386 |
| shape_PC2_fold | 0.0239 | 0.0142 | 0.0100 | 0.0218 |
| shape_PC3_fold | 0.0082 | 0.0045 | 0.0024 | 0.0080 |
| terminal_taper_fraction | 0.0918 | 0.0803 | 0.0784 | 0.0898 |

## State comparator results

| kind | predictor_set | r2 | delta_r2 |
| --- | --- | --- | --- |
| random_fire | autoregressive | 0.4584 | 0.0000 |
| random_fire | state_plus_weather | 0.4638 | 0.0054 |
| random_fire | state_weather_interactions | 0.4736 | 0.0152 |
| year_block | autoregressive | 0.4582 | 0.0000 |
| year_block | state_plus_weather | 0.4633 | 0.0051 |
| year_block | state_weather_interactions | 0.4729 | 0.0147 |
| region_block | autoregressive | 0.4476 | 0.0000 |
| region_block | state_plus_weather | 0.4527 | 0.0050 |
| region_block | state_weather_interactions | 0.4658 | 0.0181 |
| spatiotemporal | autoregressive | 0.4475 | 0.0000 |
| spatiotemporal | state_plus_weather | 0.4525 | 0.0049 |
| spatiotemporal | state_weather_interactions | 0.4655 | 0.0180 |

## Claims A-M

| claim_id | status | evidence | major_caveat |
| --- | --- | --- | --- |
| A | SUPPORTED | Dated normalized allocations encode internal ordering, including measured front/late growth and pulses. | Information content, not proven extra ecological/causal mechanism. |
| B | SUPPORTED | Only allocation_00 through allocation_19 are fitted; PCA reproduced. | No claim of statistical independence from duration or size. |
| C | SUPPORTED WITH CAVEATS | >=7 distance rho 0.969, neighbor overlap 0.718; first axes stable. | Common primary anchors, not independent external validation; higher axes, exemplars and local neighborhoods change. |
| D | SUPPORTED WITH CAVEATS | Mean front loading 0.541 vs shuffle 0.500; pulses 1.249 vs 1.413. | Ordering-specific evidence; dimensionality also arises under positive-allocation constraints and observation selection. |
| E | NOT YET SUPPORTED | Coordinates are continuous and landmark labels are rules, but absence of natural classes was not tested. | Do not equate a continuous coordinate system with evidence against all latent classes. |
| F | SUPPORTED WITH CAVEATS | Selected responses have weak positive blocked skill; peak timing and fold PCs are poorly recovered. | Model-, response-, population- and blocking-dependent. |
| G | SUPPORTED WITH CAVEATS | Mean VPD/late-growth partial rho -0.069; most associations are small after year/region/month/size/length controls. | Survival does not imply a large or causal relationship; precipitation/pulses is weak. |
| H | SUPPORTED WITH CAVEATS | Measured event weather and tested ridge models leave much shape variation unrecovered; matched pairs differ. | Not proof that every possible weather representation/model is nondeterministic. |
| I | SUPPORTED WITH CAVEATS | Pooled AR R2 .448 in regional/space-time holdouts, .458 in year/random holdouts. | Pooled across 31700 fires; some small-area strata have poor absolute skill. |
| J | SUPPORTED WITH CAVEATS | Additive delta about .005; all-weather products .015-.018 across blocks. | Small conditional improvement; fixed-prediction intervals, four regions, reconstructed end-of-day benchmark. |
| K | SUPPORTED WITH CAVEATS | Two VPD products add .006-.012 over other interactions; region delta 0.0118; dense central quantile cells. | Year edges, region and size coefficients vary; not a universal curve or causal effect. |
| L | NOT SUPPORTED | 49.7% vs null 50.4% (weather matches); 39.5% vs 40.2% (morphology matches). | Declared distance>1 threshold and sparse-stratum reference only; no excess detected. |
| M | SUPPORTED WITH CAVEATS | Two independently validated median-mismatch pairs have explicit IDs and calipers. | Candidates, not extreme cases or evidence identifying the missing mechanism. |

## Verdict

CENTRAL REPRESENTATION ROBUST BUT ENVIRONMENTAL STORY WEAK

This verdict reflects stable representation and temporal-order evidence alongside weak, selected, noncausal event-weather associations. It does not deny the modest reproducible state-weather increment. See `reproducibility.json` for exact verification scope and the full-test collection limitation.
