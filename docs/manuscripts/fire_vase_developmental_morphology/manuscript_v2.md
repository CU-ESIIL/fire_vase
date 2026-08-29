# The Developmental Morphospace of Wildfire

Research manuscript draft | Second-generation methodological reanalysis | 28 August 2026

Ty Tuff, Ph.D. | Environmental Data Science Innovation & Impact Lab (ESIIL), Cooperative Institute for Research in Environmental Sciences (CIRES), University of Colorado Boulder, Boulder, Colorado, USA. ORCID: 0000-0001-5249-5197. Correspondence: ty.tuff@colorado.edu.

## One-sentence summary

Fire VASE makes the ordered allocation of observed wildfire growth a comparable developmental response, with weather as an external layer for testing associations.

## Abstract

Fire VASE converts dated growth observations into developmental morphology. We reanalyzed 278,569 FIRED events without defining their shape coordinates by weather, final size, duration, or observation count. The primary analysis contains 10,246 events with at least three consecutive daily observations; shorter and gappy histories remain explicit separate populations. Mean-centered PCA of normalized growth allocation explains 34.1% on its first axis and 89.4% on five axes. Broad gradients persist at stricter observation thresholds, although local neighborhoods and dimensionality change. Histories are more front-loaded and less episodic than permutations of the same observed increments; low dimensionality alone is not uniquely biological. In 9,212 complete primary fires, weather associations are weak and response-dependent. Exact calendar-day models show strong recent-state predictability and small additional weather skill, including qualified VPD-state interaction support. Unique caliper-matched pairs show mismatch compatible with conditional null expectations. Morphology is the primary contribution; weather is an external demonstration, and matched cases motivate hypotheses rather than causal attribution.

## Introduction

Final area and duration describe endpoints, not the allocation of growth over a fire's observed history. FIRED reconstructs fire events and their daily burned footprints from satellite burned-area records [1,2]. Fire VASE encodes these dated increments as a developmental object: elapsed time orders rings, and ring radius represents the square root of normalized cumulative area. The representation is retrospective. An observation gap is not a documented pause or a zero-growth day.

The scientific distinction is between a representation and an explanation. Shared morphological coordinates allow histories to be compared without weather entering the coordinate construction. Daily gridMET conditions [3] are the first external layer projected onto that representation. Associations do not establish which environmental or management process generated a trajectory.

## Results

### Corrected semantics and observation support

The pilot trait labeled peak growth was catalog area divided by catalog duration for all 278,569 events. Replacing it with the largest observed daily increment changes 108,214 event values. That is an observed daily peak, not an instantaneous or hourly maximum. Reconstructed and catalog totals differ by at most 6.5e-16 in relative magnitude in these cached events. Normalizing entropy to the sum of observed increments fixes the implementation, but changes no current entropy value within numerical tolerance.

Of 626,102 cached observations, 196,611 adjacent pairs are exactly one calendar day apart and 150,922 span longer gaps. Missing and duplicate dates number 0 and 0. There are 161,073 one-observation events, 47,950 two-observation events and 59,300 gappy events with at least three observations. Only 10,246 events satisfy the primary consecutive-history criterion. This restriction favors short, continuously observed histories; it is a scientific scope limit, not a claim to represent every wildfire.

The old neighborhood branch assigned 17,837 fires to a multi-pulse label without the branch's nominal three detected pulses. The new rules require actual local maxima. Labels are interpretive landmarks and never inputs to PCA or discovered natural classes (Figures 1-2).

### A shared coordinate system, without a universal restricted-wedge claim

The primary 20-bin space explains 34.1%, 28.2%, and 14.5% on its first three axes. Its first-five-axis fraction is 89.4%, compared with 96.3% in the older mixed-scale, median-centered SVD. These numbers refer to different feature definitions and cohorts, not interchangeable estimates. Mean-centering the unchanged legacy feature space alone lowers its first-axis fraction from 81.0% to 72.9%. The v2 effective dimension (inverse squared variance-share sum) is 4.39.

Bootstrap five-dimensional subspace overlap has median 0.999 and 2.5-97.5 percentiles 0.998-1.000. Axis/loadings and region/year checks are exported separately. Restricting to at least ten consecutive observations leaves 438 fires and reduces five-axis coverage to 66.6%; interpolation at 10 or 40 bins also changes compression. Thus dimensionality is not independent of temporal support or resolution.

The second-pass >=7-observation fit contains 1,171 fires and explains 74.2% on five axes. When refitted spaces are evaluated on the same 1,000 primary-event anchors, its pairwise-distance rank correlation with the primary fit is 0.969, but 15-neighbor overlap is only 71.8%. The first two gradients are more stable than higher axes or extreme exemplars. Excluding endpoints does not make morphology independent of them: primary PC1 has rank correlations -0.308 with final area, -0.185 with duration/count and -0.332 with observed daily peak; PC2 correlations with area and duration/count are 0.259 and 0.256. Continuous coordinates provide a representation; the absence of discrete latent fire classes has not been tested.

In the separately recorded 4,000-fire second-pass null sample, observed five-axis coverage is 0.896. Corresponding means are 0.855 after shuffling observed increments, 0.902 for uniform-simplex allocations and 0.909 for more even allocations. All nulls preserve each fire's count and reconstructed total; shuffling also preserves its full increment multiset. Real mean first-half allocation is 0.541, versus 0.500 under shuffling; pulse counts are 1.249 versus 1.413, and reactivation counts 0.038 versus 0.120. Entropy is unchanged by shuffling, as required. Observed ordering contains structure, but compression alone does not establish biological restriction. The second-pass sample is not mixed with the earlier v2 null sample (Figure S2).

### Weather is an external, response-dependent association

All primary event-model comparisons use the same 9,212 complete fires. Core event means exclude maximum VPD; explicit nested additions include maximum VPD in both core and comprehensive sets. Means, the 90th VPD quantile and fixed-threshold exceedance fractions are distinguished from record-length-dependent extremes. Duration and count are adjustment variables only; their inclusion cannot be used to claim prediction of duration itself.

Region-held-out R-squared values are shown below; other blocks, penalties, intervals, and every response remain in machine-readable tables. No cross-response median is the primary result.

| response | comprehensive_means | comprehensive_plus_max | core_means | core_plus_max |
| --- | --- | --- | --- | --- |
| front_loaded_fraction | 0.031 | 0.038 | 0.014 | 0.022 |
| late_growth_fraction | 0.037 | 0.054 | 0.023 | 0.038 |
| normalized_entropy | 0.096 | 0.111 | 0.054 | 0.074 |
| peak_timing | 0.001 | -0.000 | 0.002 | 0.001 |
| pulse_count | -0.001 | 0.015 | 0.001 | 0.019 |
| reactivation_count | -0.001 | 0.019 | -0.001 | 0.022 |
| shape_PC1_fold | 0.014 | 0.022 | -0.001 | 0.007 |

The low regional recoverability of fold-trained shape PC1 (0.007 for core plus maximum VPD) contrasts with the old 0.349 median across heterogeneous outcomes. Increased model size does not have a uniform benefit or cost across responses. Fixed-duration and fixed-count strata, length-only versus length-plus-maximum VPD models, and the broader gappy cohort test exposure opportunity explicitly. Maximum VPD is not retained as a deterministic explanation of shape (Figure 3).

Precipitation associations also change after adjustment. In the 9,212 complete primary fires, its raw rank correlation with detected pulses is 0.070 and its partial rank correlation is 0.025 after duration, count, area, region, month and year adjustment; the conditional region-resampling interval (-0.005, 0.064) includes zero. Mean VPD versus late allocation remains weakly associated after controls (partial rank -0.069). The broader gappy-inclusive cohort is supplementary, not the primary daily-history association. Maximum VPD correlates with primary duration at 0.207 versus 0.120 for mean VPD. Its regional increment above core means for entropy is 0.020 R-squared, falling to 0.005 after length controls; for fold PC1 the corresponding increments are 0.008 and 0.0005. This attenuation is consistent with observational opportunity, not proof that all maximum-VPD signal is mechanical. Weather completeness is exactly geographic here: all 237,235 complete fires are CONUS, while 41,279 Alaska and 55 Hawaii events are incomplete. Complete histories have greater mean duration (3.34 versus 2.35 days) and observation count (2.32 versus 1.82). These are selected, descriptive associations, not causal effects.

### Subsequent growth is evaluated against known developmental state

The state analysis uses exactly dated one-day transitions and an autoregressive baseline containing current growth, previous-calendar-day growth, cumulative observed area and elapsed time. The common cohort contains 87,944 transitions from 31,700 fires. Requiring the previous calendar day for every comparator removes first observations and transitions following gaps equally from all models. Day-t weather is sampled at that day's newly burned-area centroid, not a final-fire centroid. Daily polygons are projected before centroid calculation and points outside the weather grid are excluded.

| kind | predictor_set | r2 | delta_r2 |
| --- | --- | --- | --- |
| year_block | autoregressive | 0.458 | 0.000 |
| year_block | state_plus_weather | 0.463 | 0.005 |
| year_block | state_weather_interactions | 0.473 | 0.015 |
| region_block | autoregressive | 0.448 | 0.000 |
| region_block | state_plus_weather | 0.453 | 0.005 |
| region_block | state_weather_interactions | 0.466 | 0.018 |
| spatiotemporal | autoregressive | 0.448 | 0.000 |
| spatiotemporal | state_plus_weather | 0.452 | 0.005 |
| spatiotemporal | state_weather_interactions | 0.466 | 0.018 |

Incremental rather than total skill is the relevant weather comparison. Fire-, year- and region-resampling intervals and region, season, area and observation-quality sensitivity estimates accompany Figure 4. These intervals condition on fitted held-out predictions and do not include model-refitting or remote-sensing error. Interactions are statistical associations. End-of-day weather and reconstructed burned area should not be called information demonstrably available to a real-time system; satellite latency, retrospective FIRED event delineation and daily time-zone alignment remain unresolved.

The two VPD products were then isolated from the six temperature/wind products. Adding VPD-by-current and VPD-by-prior growth above the other interaction terms improves held-out R-squared by 0.006-0.012 across the four blocks; the regional increment is 0.0118 (conditional fire-bootstrap interval 0.0097-0.0138). In the full-sample ridge model, current/prior product coefficients are 0.217 and -0.118 per kPa times log(1 + km2), with fire-cluster standard errors 0.0127 and 0.0105. These coefficients vary across region, size and partial edge years; small-fire subsets can have poor absolute prediction despite a positive increment. Joint quantile-cell support and the central VPD range (1st-99th percentile: 0.19-3.48 kPa) are reported without extrapolated response surfaces. The VPD interaction is supported with caveats, not a universal growth-response curve (Figure S3).

### Representative convergence and divergence

Weather-space matching assigns unique acceptable partners to 80.5% of eligible complete primary fires; morphology-space matching assigns 68.3%. The fraction with standardized other-space distance greater than one is 49.7% among weather matches and 39.5% among morphology matches. This is an explicitly chosen diagnostic threshold, not a natural class boundary. Conditional permutation distributions and candidate-neighbor/metric sensitivity quantify how much mismatch is expected under nuisance-matched allocation.

The conditional permutation mean mismatch fractions are 50.4% for weather matches and 40.2% for morphology matches. The observed fractions are compatible with these permutation distributions; the diagnostic does not establish excess mismatch beyond the declared reference. The displayed examples are nearest the median population mismatch, not maxima among a selected neighborhood. They are independent matched pairs, not a two-by-two arrangement asserting both row and column matches. The full pair table prints event IDs, dates, area, duration, count, region, season, predictor values, standardized distances, and calipers. Fuel continuity, terrain, active-edge heterogeneity, ignition context and suppression histories are plausible hypotheses, not explanations established by this diagnostic (Figure 5).

The ten-neighbor candidate graph contains acceptable edges for 91.2% of weather-space fires and 81.3% of morphology-space fires; these are search-limited coverage fractions, not exhaustive existence over every possible partner. Changing the RMS caliper from 0.25 to 1 changes paired coverage from 59.8% to 85.7% and from 54.0% to 77.9%, respectively. Paired absolute differences, area balance and distance distributions are exported. Matching coverage and mismatch are design-dependent diagnostics, not ecological prevalence estimates.

## Methods

### Data provenance and exclusions

All observations come from the materialized v0.1 FIRED/gridMET data lake; no synthetic fallback is permitted. Every cached daily increment is joined by event ID and date to the original daily GeoPackage and must agree within 1e-9 km2. Catalog areas must match the original event GeoPackage. The raw daily file contains 627,033 rows, 931 more than the lakehouse; unmatched rows and their catalog membership are enumerated in source_row_exclusions.csv. Cached dates span 2 November 2000 to 1 May 2021, despite the source filename. Missing dates, duplicate dates, nonfinite or negative increments, zero reconstructed totals and calendar gaps are explicitly checked. None is imputed as zero. Source and weather-cache hashes, code versions and output hashes are recorded.

### Growth and shape coordinates

For nonnegative daily increments g_i, reconstructed area is S = sum(g_i), distinct from catalog area A. Growth probabilities are p_i = g_i/S. Shannon entropy is -sum(p_i log p_i), with zero-probability terms omitted; normalized entropy divides by log(n) for n > 1. A positive one-slice history has entropy zero and no internal shape information. Zero-total or incomplete growth is undefined, not assigned high or low entropy.

In the primary consecutive cohort, each daily increment occupies one equal-width relative-time interval. Linear interpolation of cumulative mass at 21 fixed edges followed by differencing produces 20 nonnegative bin masses summing to one. It does not create additional observations. Gappy histories appear only in the explicitly observation-time sensitivity; their missing calendar days are not reconstructed. The primary PCA uses only these allocation bins. Catalog area, duration, count, absolute peak, mean growth and slenderness are excluded. Shape-oriented traits are projected afterward and provide a separate trait-only sensitivity, avoiding duplicated profile/trait weighting in the primary space.

PCA subtracts training means, divides by training standard deviations, and eigendecomposes the covariance matrix. Near-constant columns receive scale one. Loadings use a deterministic sign convention. Bootstrap comparisons optimally align five loading axes and also report subspace overlap; individual axes can rotate when eigenvalues are close. Nulls retain each sampled event's observation count and relative-time support: within-fire permutations preserve increments; symmetric Dirichlet allocations with concentration 1 and 10 test two alternative allocation universes. They are simulation controls, never presented as observed fires. Hull fill is convex-hull area after clipping scores to their 1st-99th percentile rectangle and rescaling to a unit box; occupancy is the fraction of a 20-by-20 score grid occupied. Neither is a formal proof of biological constraint. Empirical tails use (1 + exceedances)/(1 + replicates); multiple metrics are descriptive and not multiplicity-adjusted.

### Landmarks and pulses

Rules are evaluated in exported priority order. Invalid growth, one observation, two observations and gappy/undated histories are classified first. On eligible histories, at least two local maxima with prominence >= 20% of the observed peak define the multiple-detected-pulses landmark. Endpoints are eligible by padding the series with zeros; a flat plateau counts once. Reactivation requires a return above 25% of peak after at least two consecutively observed subthreshold days. Late peak requires normalized peak-bin midpoint >= 2/3; front-loaded taper requires >= 75% area by relative time 0.5 and final/peak growth <= 0.35. All others are distributed growth. These thresholds are declared interpretive rules, not validated ecological classes.

### Weather, prediction and uncertainty

Daily gridMET variables comprise maximum/minimum temperature, VPD, wind speed, precipitation, relative/specific humidity, 100/1000-hour fuel-moisture indices, energy release component, burning index, reference/potential evapotranspiration and solar radiation. The latter indices are modeled products, not direct measurements of local fuel loads. Event means use all observed dates and require complete values for every variable on every observed row. VPD exceedance is > 2 kPa; wet fraction is precipitation > 0.1 mm/day. Quantiles and fractions do not monotonically increase by construction with record length, but still have record-length-dependent sampling uncertainty. No event-sample anomaly is called climatology.

Ridge models use penalties 0.01, 1 and 100 on standardized predictors with an unpenalized intercept. Penalty 1 is prespecified, not chosen by test performance; all penalties are reported. Training-only scaling is mandatory. When predicting shape PCs, the PCA is refitted inside each training fold, scores are scaled by training score standard deviation, and pooled evaluation subtracts each held-out fold's observed score mean from both target and prediction to prevent arbitrary fold offsets inflating the denominator. Axis sign conventions are local; fold-level values and loading variation are authoritative. Outcomes already present as predictors are explicitly excluded from predictive reporting.

Validation leaves out each coarse geographic region, contiguous five-year blocks beginning in 2000 (last block 2020-2021), or each region-by-year-block intersection. For the crossed scheme, training excludes the entire test region AND the entire test year block, a stricter transfer task than hashing region-year identifiers. All rows of a fire share its ignition-year block. Random-fire hashing is diagnostic only. Models share a complete cohort determined by the union of requested predictors and outcomes. Held-out R-squared uses all valid predictions and retains negatives; the reference mean is trained, not calculated from test outcomes. Paired fire/year/region cluster resampling of fixed out-of-fold errors uses 200 draws; few regional clusters limit precision. No causal interpretation follows from predictive improvement.

### Second-pass validation

Unchanged 20-bin PCA fits are compared across bootstrap resamples, years, regions and >=2, >=3, >=5 and >=7 consecutive observations. All fits project the same seeded 1,000 primary-event anchors. Assignment/sign-aligned score correlations and loading cosines, five-dimensional subspace overlap, orthogonal Procrustes similarity, rank correlation of sampled pair distances, 15-neighbor overlap and top/bottom 2% exemplar-tail Jaccard distinguish global from local stability. Scores are not whitened; Procrustes permits rotation and one global scale. These are common-anchor comparisons, not independent external generalization tests.

The second-pass null sample stores all 4,000 event IDs and reconstructed totals. Temporal shuffling preserves each full increment multiset; Dirichlet concentrations 1 and 10 generate alternative positive allocations with the same count and total. In addition to PCA metrics, tests compare fixed-reference standardized profile-distance quantiles, trait means/quantiles and landmark occupancy over 100 replicates. Empirical tails are descriptive, with resolution 1/101 and no multiplicity adjustment. Year-adjusted partial ranks project both ranked variables off the same nuisance matrix; uncertainty resamples fixed residuals. Collinear primary duration and count are handled by least-squares projection, not interpreted as two separately identified effects.

VPD validation removes or adds its two product terms while retaining the common state cohort, core weather, folds and prespecified ridge penalty. Paired fixed-prediction bootstrap intervals test held-out increments. Original-unit descriptive coefficients use fire-cluster sandwich covariance conditional on the design/penalty; regional, year, season, size and training-fold refits test heterogeneity. VPD-by-current/prior-state decile bins report transition and distinct-fire counts, merging tied cut points. This support check does not license extrapolation into unobserved conditional combinations.

### Matching and reproducibility

Matching uses core event means in weather space or 20 allocation bins in morphology space, standardized across the declared complete primary matching cohort. Candidate edges are the k nearest neighbors within exact region, season, duration and count strata. Edges exceeding an area ratio of two or RMS z-distance 0.5 are rejected. Remaining edges are sorted by match distance and ID order, and selected greedily without reusing either member; mismatch outcomes do not influence selection. This is disjoint nearest-neighbor graph matching, not globally optimal matching. Both the fraction with an eligible candidate and the fraction actually paired are exported. Sensitivities use k = 1, 5, 10 and 20 and Euclidean/RMS versus cityblock/mean-absolute standardized distance. Nulls permute the other-space vectors within exact nuisance strata plus floor(log2(area)); singleton strata cannot randomize and constrain the reference. Models and matching remain observational.

## Limitations and conclusions

Fire VASE supplies a transparent representation and a shared coordinate system, not a universal set of fire types. Dimensionality depends on observation support, resolution and the normalized-curve constraints themselves. The strict primary cohort is small relative to the source population and does not establish transfer to long or intermittently observed fires. Weather is a useful external layer, but the earlier 0.349 median was not a defensible general headline. Duration, count and maxima must remain disentangled, especially for pulse and reactivation opportunity.

Day-specific geometry removes one identifiable spatial look-ahead pathway, but this does not establish operational availability of reconstructed fire histories or causal weather effects. Nearest-cell daily exposures miss spatial heterogeneity, directional winds and active-edge conditions. GridMET nominal days use Mountain Standard Time; FIRED dates and satellite burn-date uncertainty may not align perfectly. Fuel load/continuity, terrain and slope, ignition, suppression and independent operational validation are not included. Source land-cover labels alone cannot substitute for those mechanisms. Matched mismatches generate questions for those next layers; they are not unexplained residuals that by themselves prove contingency or causal control.

## Supplementary inventory

Figure S1 covers complete regional model grids, alternative feature/cohort spaces, bootstrap axes, missingness, matching sensitivity and penalty sensitivity. Figure S2 covers second-pass observation-count robustness, null histories, endpoint projections, year-adjusted associations and caliper sensitivity. Figure S3 covers VPD-specific support, coefficient heterogeneity and held-out ablation. Machine-readable tables include PCA loadings/variance, all bootstrap loadings, year/region stability, null realizations/tests, every landmark rule and branch count, every event's semantic audit, source-row exclusions, weather inclusion/exclusion, predictor dictionaries, complete model grids and folds, all preprocessing parameters, cluster intervals, fixed-length strata, gappy-cohort sensitivity, legacy-outcome cohort comparisons, spatial-exposure/state-subgroup sensitivities, complete unique pairs, representative examples, matching nulls and output manifests. The scientific-validation folder adds the correction audit, claim matrix, scientific story and Prism handoff. Large row-level tables are compressed CSV or regenerable Parquet; the latter remain local and ignored by Git.

## References and reuse

[1] Balch et al. (2020). FIRED (Fire Events Delineation): An Open, Flexible Algorithm and Database of US Fire Events Derived from the MODIS Burned Area Product (2001-2019). Remote Sensing 12, 3498. https://doi.org/10.3390/rs12213498

[2] Country-level fire perimeter datasets (2001-2021). Scientific Data (2022). https://doi.org/10.1038/s41597-022-01572-3

[3] Climatology Lab. gridMET product documentation. https://www.climatologylab.org/gridmet.html (accessed 28 August 2026). Daily meteorological data, approximately 4-km resolution; gridMET is public-domain/CC0 as described by the provider. Upstream FIRED reuse and citation requirements remain attached to the source package; this reanalysis does not relicense the data.

## AI assistance and verification

Codex assisted with code, methodological auditing, statistical regeneration, tests, figures and manuscript drafting in this repository. Results were computed from the identified real inputs. Human scientific review remains necessary, especially for estimand choice, remote-sensing uncertainty and ecological interpretation. The audit and verification records disclose limitations rather than substituting computational reproduction for scientific validation.
