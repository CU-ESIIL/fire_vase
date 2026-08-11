# Formal Reviews Round 2

Date: 2026-07-22

## Reviewer 1: Conceptual Framing And Novelty

The manuscript is substantially more credible after the leakage audit, but the caution now slightly buries the central contribution. The main claim should not be that Fire VASE predicts future fire shape. The stronger and more defensible claim is that Fire VASE creates a reusable developmental coordinate system for comparing hundreds of thousands of real fire histories. The Discussion should make this representation-first contribution explicit and explain why it matters for future climate, fuels, suppression, and topography analyses.

Recommended edits:
- State earlier that the discovery is the existence of a reproducible developmental coordinate system, not the labels or the predictive model.
- Make clear that caveats refine the scope of the claim rather than invalidate it.
- Add a short forward-looking paragraph explaining what hypotheses the morphospace enables.

## Reviewer 2: Quantitative Validation And Leakage

The manuscript now acknowledges the most important validation concerns, especially the temporal null and leakage in the older fractional-stage table. The Results should make the validation hierarchy easier to read: strong evidence from PCA concentration and bootstrap stability; partial evidence from feature-wise nulls and duration sensitivity; provisional evidence from climate coupling and fixed-day prediction. The Methods should also define the fixed-day benchmark in plainer language.

Recommended edits:
- Avoid any phrase implying strong early prediction from Figure 5.
- State that blocked validation is the conservative benchmark.
- Explain why within-fire permutation remaining high points to profile redundancy and monotone cumulative-area structure.

## Reviewer 3: Figure Readability

The new figure suite is much stronger than the earlier atlas pages, but some labels still read as internal variable names. A Science reader should not have to decode "PC1", "R2 proxy", "nearest-medoid distance", or "C->M". Plain-language axis labels should be used in the figures, while technical names can remain in the legends and methods.

Recommended edits:
- Rename morphospace axes as developmental gradients in figures.
- Replace medoid jargon with representative-fire language where possible.
- Replace bare R2 axis labels with prediction accuracy or adjusted fit language.
- Inspect every rendered main figure after changes to catch label overlap.

## Revision Response

Implemented in this round:
- Revised the manuscript generator to emphasize the representation-first contribution and the validation hierarchy.
- Kept Figure 5 as a leakage-audited benchmark with weak blocked performance, not an affirmative early-prediction result.
- Updated main figure scripts to use plain-language axis labels and more readable panel text.
- Updated figure legends in the figure-suite generator and regenerated both figures and manuscript.
