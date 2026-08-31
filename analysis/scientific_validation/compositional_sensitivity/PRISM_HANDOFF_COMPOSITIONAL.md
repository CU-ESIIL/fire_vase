# PRISM handoff: compositional geometry

## Decision

**Broad axes survived.** The baseline was reproduced before the sensitivity was run: N = 10,246, PC1 = 0.341496, and cumulative PC1-PC5 = 0.894436. Hellinger PCA explains 0.337908 on PC1 and 0.882819 on five axes.

Baseline PC1 aligns to Hellinger PC1 at r = 0.942; baseline PC2 aligns to Hellinger PC2 at r = 0.938. Five-dimensional Procrustes similarity is 0.985, score-subspace similarity is 0.960, and frozen-anchor pair-distance Spearman correlation is 0.976. The early/late contrast remains recognizable: PC1's front-loading rank correlation is -0.968 under baseline PCA and -0.945 under Hellinger PCA. The concentrated/distributed contrast is still visible in raw tail-allocation curves but rotates and weakens in simple first-two-axis entropy correlations; its strongest aligned first-two-axis Hellinger rank correlation is -0.263.

The broad-axis decision is an interpretation of the complete metric pattern, not a preregistered hypothesis test or a formal 0.8 cutoff. The high same-event axis correlations, Procrustes similarity, score-subspace similarity and pair-distance correlation all support it; the lower neighbor and tail overlaps qualify it.

## What changed locally

Mean 15-nearest-neighbor overlap among the same 1,000 frozen anchors is 0.701. Mean top/bottom 2% Jaccard overlap across PC1 and PC2 is 0.430 (PC1 0.573; PC2 0.287). The largest absolute PC1/PC2 percentile movement among manuscript-displayed fires is 0.278. These results distinguish robust broad ordering from representation-dependent local neighbors and extreme membership.

## Principal representational claim

The principal claim survives this focused sensitivity. Recommended wording:

> Global developmental organization is robust across the standardized-Euclidean and Hellinger representations, while local neighborhoods and extreme exemplars remain representation-dependent.

This does not make Hellinger and baseline loading magnitudes interchangeable. The former acts on square-root proportions without variance scaling; the latter acts on column-standardized raw proportions.

## Exact manuscript revisions

Do not replace the frozen manuscript automatically. Revise these exact sentences during editorial integration:

1. Current abstract sentence:
   > Mean-centered PCA of normalized growth allocation explains 34.1% on its first axis and 89.4% on five axes.

   Recommended replacement:
   > Column-standardized Euclidean PCA of normalized growth allocation explains 34.1% on its first axis and 89.4% on five axes; a mean-centered, unscaled Hellinger sensitivity explains 33.8% and 88.3%, respectively.

2. Current abstract sentence:
   > Broad gradients persist at stricter observation thresholds, although local neighborhoods and dimensionality change.

   Recommended replacement:
   > Broad gradients persist across observation thresholds and Hellinger geometry, while dimensionality, local neighborhoods and extreme exemplars remain representation-dependent.

3. Current Results sentence:
   > The first two gradients are more stable than higher axes or extreme exemplars.

   Recommended replacement:
   > The first two gradients remain recognizable under Hellinger geometry (aligned score correlations 0.942 and 0.938), but 15-neighbor overlap is 0.701 and mean PC1/PC2 extreme-tail Jaccard overlap is 0.430.

4. Add to Methods after the primary PCA description:
   > As a compositional-geometry sensitivity, we square-root transformed each 20-bin allocation, verified unit squared norm, mean-centered without variance scaling, and fit deterministic SVD. Components were matched by maximum absolute same-event score correlation and sign-aligned; score-space, pair-distance, neighborhood and extreme-tail comparisons used the frozen primary cohort and anchor sample.

## Figure consequences

- Figure 2 regeneration required: **no**. The current shape-only panel remains an adequate baseline display; revise its legend or nearby text to cite the new sensitivity without changing the plotted baseline.
- Figure S1/S2 regeneration required: **yes**. Add the Hellinger comparison or point explicitly to `compositional_sensitivity.pdf`; do not replace the observation-threshold stability test.
- The new six-panel comparison figure is a focused supplementary candidate. It does not overwrite any validated v2 figure.

## Scope and provenance

No ilr sensitivity was added because the requested Hellinger analysis directly answers the focused question and all primary allocations are strictly positive (zero replacement is unnecessary). All 10,246 rows are recorded FIRED events; no synthetic fallback was used. Full tables, hashes, configuration, tests and software versions accompany this handoff.

## Verification status

- Full repository collection: 152 passed, 2 intentionally skipped, 125 warnings.
- No test modules were excluded; the shared cube-contract helper is present.
- Warnings are third-party deprecation and noninteractive plotting notices, not failures.
