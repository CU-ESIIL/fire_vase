# V2 figure legends

## Figure 1

From daily growth to morphology. Four verified FIRED events connect observed daily area increments (blue bars), their reconstructed cumulative sum (gold), and VASE rings. Horizontal dates and vertical ring spacing use elapsed calendar time. The fourth event intentionally exposes observation gaps: shaded dates are unobserved, not zero-growth days. Radius is the square root of normalized cumulative area; catalog area is an external annotation, not the profile denominator. Source IDs, dates, counts, and areas appear in the panel and event audit table.

## Figure 2

The developmental morphospace. (A) Occupancy of 10,246 histories with at least three consecutive dated observations, projected from 20 normalized growth-allocation bins. (B) Signed PCA loadings locate the relative-time contrasts defining the axes. (C) One- and two-observation events and gappy multi-observation events remain separate. (D) Ordinary mean-centered, standardized PCA explains 89.4% on five axes. (E) The same 4,000 real-event counts and durations support observed and randomized-allocation comparisons, with 100 realizations per null. Representative glyphs are real events, not inferred natural classes. Null results depend on the allocation model; they do not establish a unique physical wedge.

## Figure 3

How weather maps onto morphology. (A-B) Median event-mean VPD and precipitation in occupied shape-space bins (at least five fires per bin); weather never defines the axes. (C) Unadjusted and partial rank associations for precipitation, after duration, observation count, catalog area, region and month adjustment in the broader complete multi-observation cohort. Region-resampling intervals hold the nuisance fit fixed. (D) Separate held-out R-squared values for individual responses, using core means plus maximum VPD on the identical 9,212-event primary population. Bars are fire-resampling intervals for fixed held-out predictions. Region/year resampling, all nested predictor comparisons, every response and penalty are in the supplementary tables; Figure S1 shows the full regional comparison. Negative values are retained. PCA response preprocessing is fitted inside each training fold.

## Figure 4

Developmental state and subsequent growth. The response is log(1 + next calendar-day area in km2), for 87,944 transitions from 31,700 fires sharing complete t-1, t and t+1 growth and day-t weather. (A) Mean, persistence, autoregressive state, weather-only, additive and interaction models. (B) Paired incremental R-squared above autoregressive state is the main comparison. (C) Active-day and final-centroid exposure comparisons use the same rows. (D) Seasonal checks use region-held-out predictions and fire-cluster uncertainty. Daily newly burned-area centroids use no final-event geometry. These are end-of-day covariates from retrospectively reconstructed observations, not an operational forecast or causal estimate. All fire slices remain together; spatiotemporal folds exclude both the test region and test year block from training.

## Figure 5

Convergent and divergent pathways. (A) Fraction assigned a unique nearest-neighbor partner under RMS standardized distance <= 0.5, exact region, season, duration and observation count, and catalog-area ratio <= 2. Each fire is used at most once in each matching analysis. (B) The fraction with other-space distance > 1 is compared with 100 conditional permutations within region, season, duration, count and log2-area strata. This threshold is a descriptive diagnostic, not a biological boundary. (C-D) Two independent examples nearest the median mismatch; no adversarial maximum is selected and no two-by-two match is claimed. Full dates, areas, counts, standardized distances, calipers, variables and IDs are in matched_examples.csv. Missing mechanistic covariates make these hypothesis-generating diagnostics, not causal evidence.