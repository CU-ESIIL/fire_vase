# Fire VASE Developmental Morphology Manuscript - Stage 2

Working title:
**Wildfire Occupies a Continuous Developmental Morphospace**

One-sentence summary:
Representing complete wildfire histories as developmental objects reveals that
fire occupies a continuous, low-dimensional morphospace that provides a common
coordinate system for comparing fire development.

Status:
Citation-revised narrative draft. This version incorporates the user's opening
framing and modifies it against the literature: existing fire datasets and
models describe perimeters, spread, and event outcomes; the gap is a compact
whole-history developmental representation that makes fires comparable as
objects.

## Core Thesis

Wildfire science can now measure fires with extraordinary detail. Satellite
products delineate events and daily progression; climate analyses explain
changes in fire activity; spread models simulate fire behavior under weather,
fuels, and topography. Yet the field still lacks a compact representation of an
entire fire history as a comparable developmental object.

The Fire VASE fills that representational gap. It converts each observed fire
history into a geometric object, places that object into a common developmental
morphospace, and then evaluates climate relative to the geometry rather than
using climate to define the geometry. The resulting morphospace is not merely a
visualization. It is a coordinate system for asking whether wildfire development
is structured, how representative forms organize the population, and when
environmental forcing is informative relative to the evolving state of the fire.

## Revised Abstract

Wildfire is typically represented as expanding perimeters, burned footprints, or
time series of mapped polygons. These representations describe where fires have
been, but they do not provide a compact description of how whole fires develop.
Consequently, comparisons among fires often require reducing each event to final
area, duration, or maximum growth rate, discarding much of the developmental
history. Here we introduce the Fire VASE, a developmental representation that
compresses the observed history of an individual fire into a single geometric
object. Successive developmental slices are stacked through time, with width
encoding cumulative burned area and ring attributes retaining growth and climate
history. Applying this representation to 278,569 FIRED events from 2000-2021
reveals that wildfire occupies a strongly structured, low-dimensional
developmental morphospace: five geometry-only principal components explain
96.3% of observed VASE-feature variation, and the first component alone explains
81.0%. Representative medoids summarize large neighborhoods of the population
without imposing discrete classes. We then project daily gridMET climate onto
this geometry-first coordinate system for 237,235 climate-complete fires. In a
first-pass linear information analysis, climate explains a modest fraction of
morphology (`P(morphology | climate)`, mean held-out R2 = 0.191), while
morphology retains little linear information about average climate
(`P(climate | morphology)`, mean held-out R2 = 0.020). Across developmental
stages, geometry-only models carry far more information about final morphospace
position than climate-only models. These results support a developmental view of
wildfire: climate helps shape the conditions under which fires develop, but
evolving fire geometry is itself an informative state variable. Fire VASE
therefore functions as a scientific instrument for comparing whole-fire
development and for investigating how climate, fuels, topography, and
suppression interact through developmental time.

## Introduction Draft

Wildfire science has become extraordinarily successful at measuring fire.
Satellite observations now delineate fire events from burned-area products,
daily perimeter records reconstruct progression through time, and operational
models combine weather, fuels, and topography to estimate spread. These advances
have transformed fire from an episodic disturbance observed after the fact into
a spatially and temporally resolved phenomenon.

Yet one representational problem remains unresolved. We still lack a compact
description of an entire fire.

Most fires are represented as sequences: a perimeter on one date, another
perimeter later, accumulated burned area, daily growth, changing weather, and
eventual termination. Each fire therefore exists as a developmental history.
Those histories are rich, but they are difficult to compare. One fire may burn
for a single observed day while another persists for two months. One may expand
rapidly and plateau; another may remain narrow and persistent; another may
reactivate after apparent quiescence. To compare many fires, analyses commonly
collapse these histories into summary statistics such as final area, duration,
or maximum daily growth rate. These summaries are useful, but they discard the
developmental structure of the fire itself.

Many scientific fields have solved analogous problems by creating common
representational spaces. Developmental biology compares trajectories rather than
isolated observations. Evolutionary biology and paleontology compare organismal
form within morphospaces, where complex geometries become points in a shared
coordinate system. This shift makes it possible to ask whether observed forms
occupy all possible regions of shape space or are constrained to particular
developmental landscapes.

Wildfire has no direct equivalent. Fire datasets define events, fire behavior
models simulate spread, and fire-climate studies explain variation in burned
area and activity. But these frameworks do not, by themselves, create a compact
morphology of the whole fire history. This absence limits the questions we can
ask. Which fires develop similarly? Do fire histories form continuous
trajectories or discrete types? How many representative developmental forms are
needed to summarize a continental fire archive? When during development does
climate matter most? When does the geometry of the fire become more informative
than the weather that accompanied it?

We developed the Fire VASE to answer these questions. The representation
transforms daily fire development into a single geometric object: cumulative
burned area becomes width, time becomes vertical position, and each slice
retains growth and climate information. The construction is intentionally
geometry-first. No environmental variables are used to define the VASE. Climate
is attached only afterward, allowing us to distinguish developmental morphology
from environmental forcing.

The purpose of this study is therefore not to improve fire prediction directly
or to replace existing fire behavior models. It is to test a more fundamental
hypothesis: wildfire development occupies a continuous, structured morphospace.
If fire histories are arbitrary, then Fire VASE objects should fill
developmental space diffusely. If development is constrained, then independent
fires should repeatedly occupy similar regions despite differences in location,
climate, fuels, and management.

Applying Fire VASE to 278,569 FIRED events reveals a strongly structured
morphospace. This morphospace provides a common coordinate system for comparing
whole-fire development, selecting representative medoids, mapping climate onto
developmental form, and estimating when geometry becomes more informative than
climate alone.

## Citation-Revised Framing

### What the Literature Already Solves

**Event definition.** FIRED establishes fire events as spatiotemporal objects
derived from MODIS burned area products and validates event delineation against
MTBS perimeters (Balch et al. 2020). Country-level perimeter datasets extend
event and daily products across 2001-2021, making progression analysis possible
at large scales (Mahood et al. 2022). This means our manuscript should not claim
that fire lacks event objects. It should claim that fire lacks a compact
whole-history developmental morphology.

**Meteorological forcing.** gridMET provides daily surface meteorology for
ecological modeling at high spatial resolution (Abatzoglou 2013). Fire-climate
studies show that warming, aridity, VPD, and fuel drying strongly influence
western US and California fire activity (Abatzoglou and Williams 2016; Williams
et al. 2019). Recent work on VPD temporal averaging reinforces why daily
meteorological attribution is preferable to coarse monthly summaries when asking
developmental questions (He et al. 2025).

**Daily growth importance.** Fast daily fire growth is ecologically and socially
important. Balch et al. (2024) showed that fast fires account for disproportionate
destruction and that maximum daily growth often occurs early in events. This
supports the Fire VASE premise: developmental timing is scientifically
meaningful and should not be reduced away.

**Environmental constraints beyond climate.** Weather, fuels, and topography can
impede spread and shape boundaries (Holsinger et al. 2016), and topographic
controls vary with scale through barriers, microclimate, wind channeling, and
convective preheating (Povak et al. 2018). This cautions against interpreting
climate as the sole driver of VASE morphology. Geometry integrates many drivers:
weather, fuels, terrain, suppression, and the prior state of the fire.

**Morphospace logic.** Geometric morphometrics provides the conceptual analogue:
complex forms can be represented as coordinates in a shared space, enabling
analysis of variation, constraint, and developmental organization (Bookstein
1991; Mitteroecker and Gunz 2009). Fire VASE adapts that logic to wildfire
development.

### How Citations Modify the Narrative

The original opening line "wildfire lacks a representation of an entire fire" is
powerful but should be refined. The literature does represent entire fires as
events and perimeters. The sharper, defensible claim is:

> Wildfire lacks a compact, comparable, whole-history developmental
> representation.

The original framing says that existing observations describe "where fires have
been." The citation-revised version should add:

> Existing datasets define where and when fires burned; Fire VASE asks what
> developmental form those histories take.

The original abstract says morphology contains more information about wildfire
state than average climate. The citation-revised version should be careful:

> In this first-pass linear baseline, stage-wise geometry carries far more
> information about final morphospace position than stage-wise climate.

That phrasing avoids overclaiming that climate is unimportant.

## Results Narrative To Build Around Figures

### Result 1 - The Morphospace Exists

The first result should be existential: the representation produces a structured
space rather than an arbitrary cloud. Across 278,569 events, PC1-PC5 explain
96.3% of geometry-feature variance. PC1 alone explains 81.0%, indicating a
dominant developmental axis. The median event is short (1 day), but the space
also contains long, structured branches corresponding to multi-day and pulsed
development.

Interpretive line:
The most important result is not any named category. It is that independent fire
histories repeatedly occupy the same developmental space.

Figure support:
Figure 2, morphospace with representative VASE medoids.

### Result 2 - Developmental Forms Are Landmarks, Not Classes

The medoid atlas should be framed as navigation, not classification. Thirty-six
real fires selected by farthest-point coverage in PC1-PC3 represent all 278,569
events. These representatives include recognizable forms such as single-flash,
persistent, late-surge, front-loaded, and multi-pulse fires. But those labels are
landmarks placed within a continuous landscape.

Interpretive line:
Categories help humans read the space; they do not define wildfire development.

Figure support:
Figure 3, morphological field guide.

### Result 3 - Climate Is Projected Onto Development

Daily gridMET climate is attached after geometry is defined. This sequencing is
the conceptual core of the paper. It prevents climate from defining the
developmental axes and allows climate to be interpreted relative to morphology.

In current outputs, climate is available for 237,235 fires. A first-pass linear
analysis shows asymmetric coupling: climate predicts morphology more than
morphology predicts mean climate, but neither relationship should be interpreted
as a complete causal model. The strongest climate-to-morphology relationship is
for PC1 (held-out R2 = 0.509), while PC2 and PC3 are weakly explained by climate
(R2 = 0.062 and 0.001). Morphology has little ability to recover mean maximum
temperature, mean minimum temperature, mean VPD, or mean wind, though it retains
some information about maximum VPD (R2 = 0.071).

Interpretive line:
Climate helps place fires along the dominant developmental axis, but it does not
fully determine the morphology of development.

Figure support:
Figure 4, climate mapped onto morphospace; Figure 6 left panel, directional
coupling.

### Result 4 - Geometry Dominates the Developmental Control Profile

The developmental control profile is the central theory figure. Across early,
expansion, mature, and terminal stages, climate-only models explain little of
final morphospace position in the linear baseline:

- early: mean R2 = 0.005
- expansion: mean R2 = 0.014
- mature: mean R2 = 0.004
- terminal: mean R2 = 0.004

Geometry-only models explain far more:

- early: mean R2 = 0.653
- expansion: mean R2 = 0.714
- mature: mean R2 = 0.846
- terminal: mean R2 = 0.733

Adding climate to geometry changes little in this baseline. This should be
interpreted carefully: not that climate is irrelevant, but that once the
geometry of the developing fire is known, daily average centroid climate adds
little linear information about final morphospace position.

Interpretive line:
Wildfire development becomes increasingly state-readable: the shape of the fire
contains information about where development is going.

Figure support:
Figure 6 right panel, developmental control profile.

### Result 5 - Matched Pairs Test Morphological Resilience

Matched pairs make the argument tangible. The analysis identifies fires with
similar morphology but different climate histories, and fires with similar
climate histories but different morphologies. These pairs should become the
paper's clearest demonstration that morphology and climate are coupled but not
equivalent.

Interpretive line:
Developmental morphology is not a one-to-one translation of climate forcing.

Figure support:
Figure 5, matched comparisons.

## Figure Sequence For A Tight Manuscript

1. **Figure 1: Fire VASE concept.**
   Show a perimeter/time-series becoming a VASE. This figure should make the
   reader understand the scientific representation in 20 seconds.

2. **Figure 2: The morphospace exists.**
   All fires in PC1-PC2, with representative medoids overlaid. Caption should
   emphasize that axes are geometry-only.

3. **Figure 3: Field guide to developmental forms.**
   Thirty-six medoids, each with represented count and key traits. This is the
   atlas figure, not a classification figure.

4. **Figure 4: Climate projected onto morphospace.**
   Same geometry-first space colored by temperature, VPD, and wind. Caption
   should explicitly say climate was not used to construct the axes.

5. **Figure 5: Matched comparisons.**
   Same morphology/different climate; same climate/different morphology. This
   figure prevents the paper from sounding like climate determinism.

6. **Figure 6: Developmental control profile.**
   Stage-wise climate-only, geometry-only, and geometry-plus-climate
   information. This should be the manuscript's conceptual payoff.

## Manuscript Structure

### Introduction

Lead with the representational gap:
fire is measured in detail, but whole-fire development is not yet represented in
a common coordinate system.

End with the core question:
does wildfire possess a developmental geometry?

### Results

1. Fire VASE converts whole fire histories into comparable objects.
2. Wildfire occupies a continuous low-dimensional morphospace.
3. Representative medoids form a developmental atlas.
4. Climate maps onto morphospace but does not define it.
5. Geometry-climate coupling is asymmetric.
6. Developmental state becomes more informative than climate in the baseline
   control profile.

### Discussion

Return to the theory:
Fire is not only an externally forced spread process; it is a developing system
whose geometry carries state information. Climate remains essential, but its
meaning depends on developmental state.

## Current Claims And Confidence

High confidence:

- Fire VASE produces a low-dimensional geometry-first morphospace.
- Representative medoids can summarize the archive without plotting all fires.
- Climate can be attached after geometry and mapped onto the morphospace.
- Stage-wise geometry is far more informative than daily centroid climate in the
  current linear baseline.

Medium confidence:

- The morphospace should be interpreted as evidence of developmental constraint.
  This is compelling, but should be supported by sensitivity analyses.
- Matched pairs demonstrate morphological resilience. The examples are strong,
  but the manuscript should quantify the distribution, not just show examples.

Low confidence / not yet claimed:

- Climate is unimportant.
- Fire morphology is independent of fuels, topography, suppression, or ignition.
- The current PC axes are the final best morphospace.
- Centroid climate captures the true active-edge forcing.

## Analyses Needed Before Submission

1. Sensitivity analysis separating single-day fires from multi-day fires.
   Because the median event duration is one day, PC1 may partly encode the
   single-flash versus developmental-fire divide.

2. Region/ecoregion overlays.
   The current morphospace should be colored by region or ecoregion to see
   whether developmental neighborhoods are geographically structured.

3. Active-edge or newly burned area climate attribution.
   Centroid gridMET is acceptable for a first pass, but the strongest version of
   the paper should estimate climate over the advancing boundary or newly burned
   daily area.

4. Climate anomalies.
   Absolute temperature and VPD mix geography and seasonality. Anomaly fields
   would better test whether developmental transitions are climate sensitive.

5. Quantified matched-pair distributions.
   The paper should report how often similar morphology arises under different
   climate and how often similar climate produces different morphology.

6. Nonlinear coupling check.
   A modest nonlinear model or mutual-information estimate would make the
   coupling results less dependent on linear assumptions.

## References For Stage 2

Abatzoglou, J. T. (2013). Development of gridded surface meteorological data
for ecological applications and modelling. *International Journal of
Climatology*, 33, 121-131. https://doi.org/10.1002/joc.3413

Abatzoglou, J. T., & Williams, A. P. (2016). Impact of anthropogenic climate
change on wildfire across western US forests. *Proceedings of the National
Academy of Sciences*, 113, 11770-11775.
https://doi.org/10.1073/pnas.1607171113

Balch, J. K., St. Denis, L. A., Mahood, A. L., Mietkiewicz, N. P., Williams, T.
M., McGlinchy, J., & Cook, M. C. (2020). FIRED (Fire Events Delineation): An
open, flexible algorithm and database of US fire events derived from the MODIS
burned area product (2001-2019). *Remote Sensing*, 12, 3498.
https://doi.org/10.3390/rs12213498

Balch, J. K., Iglesias, V., Mahood, A. L., Cook, M. C., Amaral, C., Decastro,
A., Leyk, S., McIntosh, T. L., Nagy, R. C., St. Denis, L., Tuff, T., Verleye,
E., Williams, A. P., & Kolden, C. A. (2024). The fastest growing and most
destructive fires in the U.S. (2001-2020). *Science*, 386, 425-431.
https://doi.org/10.1126/science.adk5737

Bookstein, F. L. (1991). *Morphometric Tools for Landmark Data: Geometry and
Biology*. Cambridge University Press. https://doi.org/10.1017/CBO9780511573064

He, Q., Williams, A. P., Johnston, M. R., Juang, C. S., & Wang, B. (2025).
Influence of time-averaging of climate data on estimates of atmospheric vapor
pressure deficit and inferred relationships with wildfire area in the western
United States. *Geophysical Research Letters*, 52, e2024GL113708.
https://doi.org/10.1029/2024GL113708

Holsinger, L. M., Parks, S. A., & Miller, C. (2016). Weather, fuels, and
topography impede wildland fire spread in western US landscapes. *Forest Ecology
and Management*, 380, 59-69. https://doi.org/10.1016/j.foreco.2016.08.035

Mahood, A. L., Lindrooth, E. J., Cook, M. C., et al. (2022). Country-level fire
perimeter datasets (2001-2021). *Scientific Data*, 9, 458.
https://doi.org/10.1038/s41597-022-01572-3

Mitteroecker, P., & Gunz, P. (2009). Advances in geometric morphometrics.
*Evolutionary Biology*, 36, 235-247. https://doi.org/10.1007/s11692-009-9055-x

Povak, N. A., Kane, V. R., Collins, B. M., Lydersen, J. M., & Kane, J. T.
(2018). Evidence for scale-dependent topographic controls on wildfire spread.
*Ecosphere*, 9, e02443. https://doi.org/10.1002/ecs2.2443

Williams, A. P., Abatzoglou, J. T., Gershunov, A., Guzman-Morales, J., Bishop,
D. A., Balch, J. K., & Lettenmaier, D. P. (2019). Observed impacts of
anthropogenic climate change on wildfire in California. *Earth's Future*, 7,
892-910. https://doi.org/10.1029/2019EF001210
