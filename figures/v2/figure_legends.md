# V2 figure legends

## Figure 1

From daily growth to morphology. Four verified FIRED events connect observed daily area increments (blue bars), their reconstructed cumulative sum (gold), and VASE rings. Horizontal dates and vertical ring spacing use elapsed calendar time. The fourth event intentionally exposes observation gaps: shaded dates are unobserved, not zero-growth days. Radius is the square root of normalized cumulative area; catalog area is an external annotation, not the profile denominator. Source IDs, dates, counts, and areas appear in the panel and event audit table.

## Figure 2

The developmental morphospace. (A) Occupancy of 10,246 histories with at least three consecutive dated observations, projected from 20 normalized growth-allocation bins. (B) Signed loadings identify the first two relative-time contrasts; five axes explain 89.4%. (C) One- and two-observation events and gappy multi-observation events remain explicit parts of the population narrative, not primary training histories. (D) Real representative glyphs, not inferred natural classes. Observation-threshold, null and endpoint-projection tests are in Figure S2 and machine-readable tables. Neither continuous coordinates nor visual occupancy proves the absence of latent classes or a unique physical wedge.

## Figure 3

How weather maps onto morphology. (A) Median event-mean VPD in occupied shape-space bins containing at least five fires; weather never defines the axes. (B) Separate held-out R-squared values for individual responses, using core means plus maximum VPD on the identical 9,212-event primary population. Bars are fire-resampling intervals conditional on fitted held-out predictions. Region/year resampling, all nested predictor comparisons, every response and penalty remain supplementary. Figure S2 shows associations after duration, count, area, region, month and year controls. Negative values are retained. PCA response preprocessing is fitted inside each training fold, so PC targets are fold-local rather than a guaranteed common biological axis.

## Figure 4

Developmental state and subsequent growth. The response is log(1 + next calendar-day area in km2), for 87,944 transitions from 31,700 fires sharing complete t-1, t and t+1 growth and day-t weather. (A) Mean, persistence, autoregressive state, weather-only, additive and interaction models. (B) Paired incremental R-squared above autoregressive state is the main comparison. (C) Active-day and final-centroid exposure comparisons use the same rows. (D) Seasonal checks use region-held-out predictions and fire-cluster uncertainty. Daily newly burned-area centroids use no final-event geometry. These are end-of-day covariates from retrospectively reconstructed observations, not an operational forecast or causal estimate. All fire slices remain together; spatiotemporal folds exclude both the test region and test year block from training.

## Figure 5

Convergent and divergent pathways. (A) Fraction assigned a unique nearest-neighbor partner under RMS standardized distance <= 0.5, exact region, season, duration and observation count, and catalog-area ratio <= 2. Each fire is used at most once in each matching analysis. (B) The fraction with other-space distance > 1 is compared with 100 conditional permutations within region, season, duration, count and log2-area strata. This threshold is a descriptive diagnostic, not a biological boundary. (C-D) Two independent examples nearest the median mismatch; no adversarial maximum is selected and no two-by-two match is claimed. Full dates, areas, counts, standardized distances, calipers, variables and IDs are in matched_examples.csv. Missing mechanistic covariates make these hypothesis-generating diagnostics, not causal evidence.

## Figure S1

Full regional model grid, feature/cohort sensitivity, bootstrap axes, weather completeness, neighbor/metric matching sensitivity and ridge penalties. Complete numerical tables accompany each panel.

## Figure S2

Second-pass scientific validation. (A) Refitted >=2/3/5/7 spaces are evaluated on identical 1,000 primary anchors; five-PC distances, 15-neighbor overlap and extreme-tail exemplar Jaccard distinguish broad from local stability. (B) All three nulls use the same recorded 4,000 fires and 100 realizations; low dimensionality alone is not uniquely biological. (C) Temporal shuffling preserves each observed increment multiset, count and total, but changes front-loading, pulses and reactivation. (D) Endpoint attributes excluded from PCA still correlate with its axes. (E) Primary-cohort partial ranks adjust duration, count, area, region, month and year; intervals resample regions conditional on nuisance fits. (F) Unique pairing depends on the declared caliper.

## Figure S3

VPD-specific interaction validation on 87,944 transitions from 31,700 fires. (A-B) Observed VPD-by-current/prior-state quantile-cell counts; tied growth values merge bins. Crosses would indicate fewer than 100 transitions or 30 distinct fires; no cell fails these coarse thresholds. Dense cells do not establish support at every tail or nuisance combination. (C) Original-unit product coefficients from the full interaction model and regional refits, with fire-cluster sandwich intervals conditional on design and penalty. (D) Paired held-out ablations compare two VPD products against additive weather and against the six other interaction products. Average improvement is positive, but size/region/edge-year heterogeneity rules out a universal response curve. These are associations, not causal effects.