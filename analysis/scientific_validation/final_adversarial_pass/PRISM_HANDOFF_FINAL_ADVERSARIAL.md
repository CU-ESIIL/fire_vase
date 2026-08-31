# PRISM handoff: final adversarial pass

## Bottom line

The low-dimensional *existence* of a five-axis geometry is distinguishable from the temporal-shuffle reference by the prespecified cumulative-variance comparison (observed 0.896; shuffle 95% interval 0.851-0.860). This does not erase the observed ordering result: front loading differs from shuffled histories at >=3, >=5, and >=7 observations by 0.042, 0.086, and 0.111, respectively.

## Eight requested decisions

1. **Is low-dimensional geometry generic?** Positive normalized allocations generate appreciable compression under all tested nulls. Interpret low dimensionality alone as partly generic; use the observed-vs-null axis meanings, alignment, and ordering effects to identify observed structure.
2. **Is the early-versus-late axis distinctive?** Yes as an observed developmental ordering, not as proof of a biological mechanism. Null axes can also encode early/late allocation, but their same-fire alignment to the observed axis and their trait pattern are reported rather than assumed equivalent.
3. **Do ordering effects survive depth thresholds?** Yes. The direction survives >=3, >=5, and >=7 cohorts; the full effect estimates and 95% shuffle intervals are in `depth_stratified_ordering.csv`.
4. **Should >=5 replace >=3 as primary?** **No**. The >=3 cohort remains the declared observation-supported primary population; >=5 is a stronger-support sensitivity, not a post-hoc replacement.
5. **Are depth spaces stable?** Broad distances remain stable (frozen-anchor rho >=5 0.987; >=7 0.969), while local neighbors, tails, and variance coverage remain explicitly qualified.
6. **Are boundary days driving ordering?** No for direction. After removing first and final days and renormalizing, the front-loading effect is 0.082 for original >=5 histories and 0.110 for original >=7 histories. This is boundary sensitivity, not correction for measurement error.
7. **Does Figure 2 require regeneration?** No numerical panel needs replacement. Its text/legend should explicitly state that compression also occurs under constrained positive-allocation nulls and that observed ordering—not compression alone—supports the developmental interpretation.
8. **Should Figure 5 move to the supplement?** No. It remains a candidate-pair diagnostic with the already validated null-compatible mismatch wording; it is not evidence for excess mismatch or a causal mechanism.

## Exact manuscript-facing changes

- Add after the first morphospace variance sentence: “Positive, mass-conserving null histories also produced low-dimensional score spaces; therefore variance compression alone was not treated as evidence of biological restriction.”
- Retain >=3 as the primary cohort, and add >=5 and >=7 ordering effects as depth sensitivities using `depth_stratified_ordering.csv`.
- Add to Methods: “We repeated the order-preserving versus shuffled comparison at minimum depths of 3, 5, and 7 observations, evaluated PCA fits on their own cohorts, the common >=7 cohort, and fixed anchors, and removed first and final observations for eligible >=5 and >=7 histories before renormalization.”
- Add to limitations: “Endpoint-day increments are observational boundaries; endpoint removal preserved the direction of ordering results but does not identify or correct boundary measurement error.”
- Figure 2 legend: distinguish observed structure from generic compositional compression.
- Figure 5 legend: retain “candidate pairs” and “null-compatible mismatch”; do not imply excess unexplained structure.

## Scope

All simulations retain the frozen fire IDs, observed history lengths, and reconstructed totals. Temporal shuffles additionally retain each fire's increment multiset. Dirichlet draws are simulated references, never observations. No external data or new feature search was used.
