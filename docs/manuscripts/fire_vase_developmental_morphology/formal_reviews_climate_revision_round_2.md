# Formal Reviews: Climate Revision Round 2

Date: 2026-07-22

Object reviewed:
`output/pdf/fire_vase_climate_revision_science_style_manuscript.pdf`

## Editor's Decision Letter

The revised manuscript is substantially clearer than the previous climate
draft. The five-figure narrative now has a recognizable arc: Fire VASE first
establishes why fire life histories matter, then defines the developmental
space, projects climate onto it, evaluates state dependence, and closes with
the limits of centroid climate explanation. I am returning the manuscript for
revision rather than rejection because the central idea is novel and visually
compelling, but the paper still needs tighter inferential guardrails and a
more explicit statement of what is new.

Please revise around three issues. First, distinguish the descriptive
coordinate-system contribution from the climate-attribution contribution.
Second, avoid implying that expanded climate variables are unimportant simply
because they do not improve blocked linear prediction over core event means.
Third, describe the state-dependent analysis as an autoregressive and
associational baseline, not as evidence of mechanism.

## Reviewer 1: Fire Science And Climate Attribution

This manuscript introduces a useful way to visualize and quantify fire
development. The strongest parts are Figs. 1, 2, and 5, which make the
representational problem and inferential boundary unusually clear. I am less
comfortable with how the climate analysis is described. The text sometimes
moves quickly from "climate shifts prevalence" to "climate organizes
opportunity." That is an acceptable framing, but only if it is repeatedly tied
to the actual climate product: daily centroid gridMET exposure. Centroid
exposure is not active-edge exposure, and in wind-driven fires the centroid can
be a poor proxy for the relevant growth environment.

Required revisions:

- State earlier that the paper has two separable contributions: a
  developmental representation and a bounded climate projection.
- Make clear that comprehensive climate not improving blocked prediction over
  core means does not imply humidity, fuel moisture, precipitation, or fire
  danger are irrelevant. It may reflect collinearity, coarse event summaries,
  daily time scale, centroid attribution, and linear baselines.
- Clarify that Fig. 5's matched examples are matched on a limited centroid
  climate summary, not full climate trajectories or active-edge weather.
- Keep perimeter and active-edge climate in the manuscript as a next-step
  priority, not as completed main evidence.

## Reviewer 2: Statistical And Developmental Morphology

The representation is promising, but the manuscript should say more precisely
what the models are and are not doing. The current draft reports R2 values
without enough context for a reader to know whether the value comes from
random, year, region, or region-year blocking. The Methods are also too terse
about standardization, ridge fitting, and why state variables improve
next-day growth. State predictors include current growth and acceleration, so
their performance is partly autoregressive. That is not a flaw, but it changes
the interpretation.

Required revisions:

- Define conservative blocked validation in the Results or Methods and say
  that the reported R2 values summarize year, region, and region-year transfer
  tests rather than random-fire splits alone.
- Describe predictors as standardized inside training folds before ridge
  fitting.
- Clarify that state-model gains show that current fire state contains useful
  near-term information; they do not identify causal state-dependent climate
  effects.
- Avoid calling the neighborhoods "types" except to reject that interpretation.
  "Landmarks" or "neighborhoods along gradients" is more accurate.

## Reviewer 3: Science Readership, Narrative, And Figures

The manuscript is now much closer to a Science-style story, but it still buries
the novelty. A general reader needs one crisp sentence near the end of the
Introduction explaining what the paper contributes. The figures are coherent,
but the legends should also help the reader understand why each figure exists.
The title works. The abstract is within range and clear.

Required revisions:

- Add a "what this paper contributes" sentence before the Results.
- Make the transition from Fig. 2 to Fig. 3 more explicit: the developmental
  space is constructed from fire histories first, then climate is projected
  afterward.
- In the Discussion, end with a stronger but still scholarly synthesis rather
  than a list of caveats.
- Keep placeholders for author metadata, but do not let placeholder language
  distract from the argument.

## Revision Response Implemented

- Revised the Introduction to separate the representation claim from the
  climate-projection claim and to state the contribution before the Results.
- Revised the climate Results to distinguish interpretation from transferable
  prediction and to explain why expanded climate variables may not improve
  blocked linear prediction despite being scientifically relevant.
- Revised the state Results and Methods to describe state predictors as
  autoregressive, leakage-safe associational baselines.
- Revised the Fig. 5 Results and legend language to say matched examples use
  limited centroid summaries rather than full trajectories or active-edge
  weather.
- Revised the Discussion so the final paragraph synthesizes the contribution
  instead of ending only with limitations.
