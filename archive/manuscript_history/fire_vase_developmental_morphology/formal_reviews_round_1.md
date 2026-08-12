# Formal Reviews - Round 1

Manuscript reviewed:
`output/pdf/fire_vase_developmental_morphology_manuscript.pdf`

Title:
**Wildfire Occupies a Continuous Developmental Morphospace**

Review date:
2026-07-22

## Reviewer 1 - Conceptual Framing and Theory

### Summary

This manuscript proposes that wildfire development can be represented as a
developmental morphology. The Fire VASE converts daily fire progression into a
geometric object and places those objects into a common morphospace. The central
idea is strong and potentially important: wildfires are usually compared through
outcomes, while this paper compares whole developmental histories.

### Major Comments

1. **The representational gap should be stated with precision.** The manuscript
   says wildfire lacks a compact representation of an entire fire. This is
   compelling, but the field already has event perimeters, progression maps,
   time series, and simulation objects. The distinctive claim is that wildfire
   lacks a compact, comparable, whole-history developmental coordinate system.
   The introduction should repeatedly distinguish "event representation" from
   "developmental morphology."

2. **The word morphospace needs a fuller conceptual bridge.** The manuscript
   invokes morphospace but does not yet explain why a morphospace is a useful
   scientific object. Add a paragraph explaining that a morphospace makes three
   things possible: estimating constraint, selecting representative forms, and
   evaluating external drivers relative to intrinsic geometry.

3. **The theory should not sound like climate skepticism.** The developmental
   control profile is striking, but the paper must avoid suggesting climate is
   unimportant. The stronger theory is that climate has a state-dependent
   meaning. A weather condition matters differently depending on the current
   geometry of the fire.

4. **The paper needs an explicit hypothesis test.** The central test should be:
   if development is arbitrary, VASEs should occupy an unstructured space; if
   constrained, they should occupy a low-dimensional and repeatedly populated
   morphospace. This should appear near the end of the introduction and again at
   the opening of Results.

### Minor Comments

- The title is excellent.
- The abstract is strong but should mention that categories are landmarks, not
  classes.
- Use "developmental state" consistently.

### Recommendation

Major revision. The concept is strong enough for a compelling paper, but the
theoretical framing needs to be made explicit and guarded against overclaiming.

## Reviewer 2 - Wildfire Science, Data, and Interpretation

### Summary

The manuscript uses FIRED-style event products and daily gridMET attribution to
construct and analyze Fire VASEs for 278,569 fires. The scale of the analysis is
impressive, and the representation could help organize fire progression records
in a new way. However, the current draft needs a clearer treatment of data
limitations and of what climate variables mean in this version.

### Major Comments

1. **Clarify the data products and time span.** The manuscript should state that
   VASEs are built from FIRED daily/event records spanning 2000-2021 in the
   current repository workflow. It should also state that climate-complete
   records are fewer than total records because gridMET centroid extraction
   returns missing values for some fires.

2. **Centroid climate should be treated as a first-pass proxy.** Daily gridMET
   centroid climate is useful and honest for an initial continental analysis,
   but it is not the active fire edge. The manuscript should say this more
   clearly in Methods and Discussion, and it should explain why the climate
   result should be interpreted as a baseline rather than as the final estimate
   of weather-fire coupling.

3. **Fast fire growth literature should be used more directly.** Fast daily
   growth and early maximum growth motivate the developmental framing. The paper
   should connect these findings to the VASE representation: if daily timing
   matters, then whole-fire developmental geometry matters.

4. **The prevalence of short fires is a result and a caveat.** The median fire
   duration is one day, which is not a problem, but it shapes the morphospace.
   The manuscript should describe this explicitly and frame sensitivity analysis
   as a required next step.

### Minor Comments

- Define VPD at first use.
- Add units for temperature, VPD, and wind in Methods.
- The figures should be described as preliminary manuscript figures generated
  from the current atlas.

### Recommendation

Major revision. The data basis is strong, but the manuscript should more clearly
state what is observed, what is modeled, and what is provisional.

## Reviewer 3 - Methods, Statistics, and Evidence

### Summary

The manuscript presents a geometry-first PCA morphospace, medoid
representatives, directional coupling estimates, matched comparisons, and a
stage-wise developmental control profile. These are appropriate first analyses,
but the statistical claims need more careful language and better connection to
the figures.

### Major Comments

1. **Explain the feature construction.** The manuscript should specify which
   geometry features define the morphospace. At minimum, describe scale, time,
   pulse, taper, entropy, velocity, acceleration, and interpolated profiles.

2. **PCA is acceptable, but interpretability should be stronger.** The current
   manuscript reports explained variance but not what the axes represent. Add a
   sentence interpreting PC1 as dominated by growth-profile structure and PC2/PC3
   as involving taper, peak growth, late growth, pulse/reactivation, and
   timing. Avoid pretending these are final mechanistic axes.

3. **Use "linear baseline" everywhere for R2 results.** The current R2 results
   are useful, but they are not mutual information and not causal estimates.
   Every coupling claim should be framed as a linear information proxy.

4. **Matched comparisons need quantification.** The figure is useful, but the
   paper should say that matched pairs are currently illustrative and should be
   expanded into distributional tests before submission.

5. **The Methods section is too short.** It needs enough detail for the reader
   to understand reproducibility: inputs, VASE construction, morphospace
   features, medoid selection, climate attribution, coupling models, and
   developmental stages.

### Minor Comments

- The first figure plate should be labeled as morphospace and representatives,
  not as the complete concept figure. A true Figure 1 concept diagram is still
  needed for submission.
- Add a "Limitations and next analyses" paragraph.
- Add a data/code availability note.

### Recommendation

Major revision. The analyses are promising, but the paper needs a fuller Methods
section and more disciplined statistical language.

## Editorial Synthesis

The manuscript should be revised toward a short paper rather than an extended
abstract. The revision should:

1. Preserve the strong opening claim from the user draft.
2. Define the representational gap precisely.
3. Explain why morphospace is a scientific object.
4. Make the hypothesis test explicit.
5. Expand Methods enough to support the figures.
6. Use linear-baseline language for all R2 results.
7. Emphasize that climate is important but state-dependent.
8. Treat centroid climate, short fires, and missing climate rows as limitations.
9. Add a data/code availability note.
10. Keep the manuscript tight: about 10-12 formatted pages with figures.
