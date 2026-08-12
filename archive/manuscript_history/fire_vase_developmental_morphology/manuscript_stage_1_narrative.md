# Fire VASE Developmental Morphology Manuscript - Stage 1 Narrative Draft

Working title:
**Wildfire Has a Developmental Morphology**

Short title:
**Fire VASE Morphospace**

Status:
Stage 1 narrative scaffold with citation map and figure plan. This is not yet a
submission-ready manuscript. It is the argument spine we will revise against the
literature and then tighten around the figures.

## Central Claim

Wildfire is usually analyzed as an event outcome: area burned, duration, rate of
spread, severity, exposure, or cost. Those outcomes matter, but they flatten the
developmental structure of a fire. A fire does not merely become large or small.
It passes through a sequence of geometric states: ignition, emergence, expansion,
burst, taper, reactivation, and quiescence. The Fire VASE representation turns
that sequence into a developmental object.

The claim of this manuscript is that wildfire development occupies a structured
morphospace. Individual fires do not trace arbitrary histories. They fall into a
constrained landscape of recurring developmental forms, and those forms retain
information about climate while also becoming state-dependent. Climate matters,
but not as a simple external controller. The evolving geometry of the fire is
itself a state variable.

## Intended Contribution

This manuscript should introduce Fire VASE as a scientific representation, not
as a visualization technique. The argument is:

1. Remote-sensing fire records now support event-scale and daily progression
   analysis across hundreds of thousands of fires.
2. Existing fire-climate work has shown strong links among warming, fuel drying,
   vapor pressure deficit, wind, and burned area, but most analyses still treat
   fire development as an input-output problem.
3. Fire VASE transforms daily fire progression into a comparable developmental
   geometry.
4. A geometry-first morphospace reveals the developmental landscape of wildfire.
5. Climate can then be mapped onto that landscape to ask directional questions:
   how much morphology is recoverable from climate, how much climate is retained
   in morphology, and when geometry becomes more informative than climate.

## Draft Abstract

Wildfires are commonly summarized by final size, duration, severity, or rate of
spread. These summaries obscure the developmental structure of fire: the sequence
of geometric states through which a fire grows, pauses, reactivates, and ends.
Here we introduce the Fire VASE, a representation that converts daily wildfire
progression into a developmental object whose width encodes cumulative burned
area through time and whose rings retain event and climate histories. Using
278,569 FIRED events from 2000-2021 and daily gridMET climate attribution for
237,235 climate-complete fires, we construct a continuous geometry-first
morphospace of wildfire development. The first five geometry axes explain 96.3%
of VASE-feature variance, indicating that wildfire development is highly
structured rather than arbitrarily distributed. Representative medoids summarize
the morphospace as a field guide of recurring developmental forms, including
single-flash, persistent, front-loaded, late-surge, and multi-pulse trajectories.
Climate is then evaluated after geometric events are defined. In a first-pass
linear information analysis, climate explains a modest fraction of morphology
(`P(morphology | climate)`, mean held-out R2 = 0.191), while morphology retains
little linear information about climate (`P(climate | morphology)`, mean
held-out R2 = 0.020). Across developmental stages, geometry-only models carry
far more information about final morphospace position than climate-only models.
These results support a developmental view of wildfire: climate helps shape the
developmental landscape, but fire geometry becomes an informative state variable
in its own right.

## Introduction - Narrative Draft

Wildfire science has become increasingly powerful at explaining why fires are
becoming more frequent, larger, faster, and more destructive. Satellite-derived
event datasets now describe fire occurrence and progression at continental
scales, and climate analyses have shown that warming, fuel drying, vapor
pressure deficit, wind, and precipitation shape fire activity across much of the
western United States. Yet the dominant analytical grammar still treats fire as
an event with outcomes: final area, duration, spread rate, severity, emissions,
or exposure. These outcomes are indispensable, but they ask what the fire became
rather than how the fire developed.

This distinction matters. Two fires can have similar final area and duration
while following different developmental histories: one may spread in a single
early burst and then plateau; another may remain narrow and persistent; another
may appear quiescent before reactivating. Conversely, similar developmental
forms can arise under different climate histories. If wildfire is analyzed only
through final outcomes, these cases collapse into the same statistical endpoint.
If it is analyzed as a developmental object, they become different trajectories
through a shared morphospace.

We introduce the Fire VASE to make this developmental structure explicit. A Fire
VASE represents a fire as a time-ordered geometry: each ring corresponds to an
observed developmental slice, width encodes cumulative burned area, and ring
attributes retain daily growth and climate information. The representation is
analogous to morphospace approaches in biology, where shape variation is treated
as a structured landscape rather than a set of predefined classes. In this
manuscript, categories such as "single flash" or "late surge" are not the
analysis. They are labels placed within a continuous developmental space.

The scientific question is therefore not whether climate controls wildfire in a
single global sense. Instead, we ask how wildfire morphology and climate are
coupled through development. Does climate predict where a fire falls in
morphospace? Does morphology retain information about the climate history that
produced it? At what developmental stages does climate add new information, and
when does the evolving geometry of the fire become more informative than climate
alone?

## Citation-Grounded Framing

### Data and representation

FIRED provides the event-delineation foundation for this analysis. Balch et al.
introduced FIRED as an open algorithm and database derived from MODIS burned
area products, designed to define fire events as spatiotemporal objects rather
than isolated burned pixels (Balch et al. 2020). Mahood et al. extended this
event-delineation logic into country-level fire perimeter datasets for
2001-2021, including daily and event-level products suitable for reconstructing
fire progression (Mahood et al. 2022). Our analysis builds directly on this
event object logic, but shifts the target from event delineation to event
development.

gridMET supplies the daily meteorological context. Abatzoglou developed gridMET
as a high-resolution gridded surface meteorological dataset for ecological
applications and modeling (Abatzoglou 2013). In this manuscript, daily gridMET
maximum temperature, minimum temperature, vapor pressure deficit, and wind speed
are attached to Fire VASE slices after the VASE geometry is defined.

### Fire-climate controls

The fire-climate literature establishes why climate must be attached to Fire
VASEs, but also why it should not replace geometry. Abatzoglou and Williams
showed that anthropogenic climate change has increased fuel aridity and
contributed to western US forest fire activity (Abatzoglou and Williams 2016).
Williams et al. showed that warming-driven drying has strongly influenced
California wildfire activity, with wind and delayed precipitation particularly
important in fall fire regimes (Williams et al. 2019). Recent work also shows
that VPD calculations are sensitive to temporal averaging and temperature
inputs, which supports our choice to work with daily data rather than monthly
climate summaries (He et al. 2025).

At daily progression scales, fast growth matters. Balch et al. showed that fast
fires are disproportionately destructive and that maximum daily growth usually
occurs early in an event (Balch et al. 2024). That result motivates a
developmental analysis: if the timing of maximum growth is structured, then a
fire's geometry through time contains information that is lost in final-area
summaries.

### Geometry, barriers, and state dependence

Fire development is not driven by climate alone. Weather, fuels, and topography
can also impede spread and shape boundaries (Holsinger et al. 2016), while
topographic controls can vary with scale and affect fire spread through barriers,
microclimates, wind channeling, and convective pre-heating (Povak et al. 2018).
These studies make a key point for the VASE argument: observed fire geometry is
not merely an outcome to be explained after the fact. It is an integrated trace
of prior climate, fuels, terrain, suppression, and internal fire dynamics.

### Morphospace logic

Morphospace methods provide the conceptual bridge. Geometric morphometrics uses
quantitative shape coordinates to study form, variation, constraint, and
developmental change (Bookstein 1991; Mitteroecker and Gunz 2009). Morphospace
approaches have been used to ask whether biological forms occupy all possible
regions of shape space or are constrained to particular landscapes. Fire VASE
adapts this logic to wildfire development: each fire becomes a point in a
geometry-first developmental morphospace, and representative medoids become the
equivalent of a field guide to recurring forms.

## Methods - Draft Skeleton

### Fire VASE construction

Each FIRED event is treated as a developmental object. For each event, daily
growth area is ordered through time. Cumulative burned area is transformed into a
normalized VASE width, so each fire can be compared by developmental shape
rather than absolute size alone. Daily rings retain observed development, and
climate is attached as slice metadata rather than used to define the geometry.

### Geometry-only developmental events

Developmental events are detected from geometry only:

- first observed development
- emergence at 5% cumulative area
- first major burst
- peak expansion
- secondary burst where present
- slowdown after peak where present
- final meaningful expansion
- geometric quiescence

Climate is evaluated only after these events have been defined.

### Continuous morphospace

Each fire is represented by developmental features derived from VASE geometry:
final area, duration, peak daily growth, observation count, pulse count,
reactivation count, timing of peak expansion, front-loaded growth fraction, late
growth fraction, terminal taper, growth entropy, developmental velocity,
developmental acceleration, slenderness, and interpolated width and growth
profiles. Principal component analysis is fit to geometry-only features. The
resulting axes define the developmental morphospace.

### Representative field guide

Thirty-six real medoid VASEs are selected by farthest-point coverage in PC1-PC3
morphospace. Each medoid represents nearby fires and includes neighboring fire
IDs, developmental traits, climate histories, and VASE geometry. These
representatives summarize the archive without rendering hundreds of thousands of
fires.

### Climate coupling

Climate is attached to each VASE slice from daily gridMET using event-centroid
nearest-grid-cell extraction. First-pass coupling is estimated in two directions:

- `P(morphology | climate)`: how much final morphospace position is recoverable
  from climate summaries?
- `P(climate | morphology)`: how much climate information is retained in
  morphology?

Stage-wise models compare climate-only, geometry-only, and geometry-plus-climate
predictors across early, expansion, mature, and terminal stages. These are
interpreted as linear information proxies, not optimized predictive models.

## Results - Draft Skeleton

### Result 1: Wildfire development occupies a structured morphospace

The Fire VASE morphospace is not diffuse. Across 278,569 FIRED events, the first
five geometry-only principal components explain 96.3% of VASE-feature variance.
PC1 alone explains 81.0%, reflecting a strong dominant axis in developmental
geometry. The space is highly constrained, with a dense population of
short-duration and single-slice fires and structured arms corresponding to
longer, pulsed, front-loaded, or tapering forms.

Interpretation:
Wildfire development appears to have a strong low-dimensional structure. This is
the first quantitative support for the idea that wildfire has a developmental
morphology.

### Result 2: Representative medoids summarize the archive

Thirty-six medoid VASEs sampled across PC1-PC3 provide a field guide to the
developmental landscape. The representatives include single-flash forms,
front-loaded tapering forms, long persistent forms, and multi-pulse forms. They
are not predefined categories. They are actual fires selected from the
morphospace.

Interpretation:
The archive can be summarized by representative developmental forms without
reducing the analysis to a small set of rigid labels.

### Result 3: Climate maps onto morphospace, but asymmetrically

Daily gridMET climate was available for 237,235 fires. In the first-pass linear
coupling analysis, climate explained a modest amount of geometry:
`P(morphology | climate)` mean held-out R2 = 0.191. The inverse relationship was
weaker: `P(climate | morphology)` mean held-out R2 = 0.020.

Interpretation:
Climate helps place fires in developmental morphospace, but morphology is not a
simple climate recorder. Similar forms can arise under different climate
histories, and similar climate histories can lead to different developmental
forms.

### Result 4: Geometry becomes more informative than climate through development

Stage-wise models show that geometry-only predictors carry far more information
about final morphospace position than climate-only predictors. Geometry-plus-
climate models add little over geometry-only models in this first-pass linear
baseline.

Interpretation:
Fire development is not a simple climate-response curve. The current geometry of
the fire is a strong state variable.

### Result 5: Matched pairs reveal developmental resilience

Matched comparisons identify fires with similar VASE morphology but different
climate histories, and fires with similar climate histories but different
morphologies. These pairs are the clearest route to testing whether fire
development is tightly constrained by environment or partially independent of
it.

Interpretation:
The next draft should elevate matched pairs from examples to evidence. They can
become the bridge between morphospace description and developmental theory.

## Figure Plan

### Figure 1 - Fire VASE concept

Purpose:
Introduce the representation. Show daily perimeter sequence transformed into a
VASE, with rings as developmental slices and climate attached afterward.

Current status:
Need a clean conceptual figure. Existing VASE renderings can supply the visual
grammar, but this figure should be simpler than the atlas.

### Figure 2 - Developmental morphospace

Purpose:
Show all fires as points in PC1-PC2 morphospace, with medoid VASEs overlaid.

Current source:
`output/pdf/fire_vase_developmental_morphology_atlas.pdf`, Figure 2.

### Figure 3 - Morphological field guide

Purpose:
Show 20-40 representative medoids, each with traits, climate, represented count,
and neighbors.

Current source:
`scratch/fire_vase_developmental_morphology/developmental_morphospace_medoids.parquet`
and field-guide pages in the developmental morphology atlas.

### Figure 4 - Climate mapped onto morphospace

Purpose:
Color the morphospace by mean maximum temperature, VPD, and wind speed.

Current source:
`scratch/fire_vase_developmental_morphology/developmental_morphospace_features.parquet`
and atlas Figure 4.

### Figure 5 - Matched comparisons

Purpose:
Show same morphology with different climate and same climate with different
morphology.

Current source:
`scratch/fire_vase_developmental_morphology/developmental_matched_pairs.parquet`.

### Figure 6 - Developmental control profile

Purpose:
The central theory figure. Show how predictive information shifts across
developmental stages for climate-only, geometry-only, and geometry-plus-climate
models.

Current source:
`scratch/fire_vase_developmental_morphology/developmental_control_profile.parquet`
and atlas Figure 6.

## Discussion - Argument to Develop

The Fire VASE results suggest that wildfire development has a morphology in the
same broad sense that biological structures have morphologies: form varies, but
not arbitrarily. Fires occupy a constrained developmental landscape. Some of
that structure is climate-related, but much of it is carried by the geometry of
the fire itself.

This does not mean climate is unimportant. On the contrary, climate defines the
environmental envelope in which fire development occurs. But the central result
is that climate should be interpreted relative to developmental state. A hot,
dry, windy day may not have the same meaning for a newly emerging fire, a
front-loaded plateau, a persistent narrow fire, or a late-reactivating fire. The
same climate forcing can be developmentally different depending on the geometry
that receives it.

The manuscript should therefore avoid two traps:

1. It should not claim that climate "does not matter" because geometry-only
   models perform well.
2. It should not claim that climate "controls fire" because climate explains
   some morphospace variation.

The stronger claim is subtler: wildfire development is a coupled system in
which climate forcing and evolving geometry interact, and Fire VASE gives us a
way to measure that interaction.

## Current Evidence From This Repository

Data basis:

- Full FIRED event table: 278,569 events.
- VASE slice table: 626,102 daily slices.
- Climate-complete fires: 237,235.
- Climate variables currently attached: daily maximum temperature, daily minimum
  temperature, VPD, wind speed, and wind-present indicator.
- Climate extraction method: event-centroid nearest gridMET cell.
- Climate temporal resolution: daily.

Current analytical outputs:

- `scratch/fire_vase_developmental_morphology/developmental_morphospace_features.parquet`
- `scratch/fire_vase_developmental_morphology/developmental_morphospace_medoids.parquet`
- `scratch/fire_vase_developmental_morphology/developmental_geometry_events.parquet`
- `scratch/fire_vase_developmental_morphology/developmental_stage_table.parquet`
- `scratch/fire_vase_developmental_morphology/developmental_climate_coupling.parquet`
- `scratch/fire_vase_developmental_morphology/developmental_control_profile.parquet`
- `scratch/fire_vase_developmental_morphology/developmental_matched_pairs.parquet`
- `output/pdf/fire_vase_developmental_morphology_atlas.pdf`

## Known Caveats To Handle Honestly

- Current climate attribution is centroid-based. It does not yet estimate
  climate over advancing boundary, newly burned area, or active fire edge.
- The climate table does not yet include humidity, precipitation, fuel moisture,
  or anomalies.
- The current coupling models are linear baselines. They support interpretation
  but are not optimized predictive models.
- Many fires are single-slice or short-duration events. This is a finding, but
  it can dominate PC1. We may need a sensitivity analysis separating
  single-flash events from multi-day developmental fires.
- FIRED is derived from satellite burned-area products, so daily progression is
  constrained by detection timing, product resolution, and event-delineation
  assumptions.

## Citation Set - Stage 1

Balch, J. K., St. Denis, L. A., Mahood, A. L., Mietkiewicz, N. P., Williams, T.
M., McGlinchy, J., & Cook, M. C. (2020). FIRED (Fire Events Delineation): An
open, flexible algorithm and database of US fire events derived from the MODIS
burned area product (2001-2019). *Remote Sensing*, 12(21), 3498.
https://doi.org/10.3390/rs12213498

Mahood, A. L., Lindrooth, E. J., Cook, M. C., et al. (2022). Country-level fire
perimeter datasets (2001-2021). *Scientific Data*, 9, 458.
https://doi.org/10.1038/s41597-022-01572-3

Abatzoglou, J. T. (2013). Development of gridded surface meteorological data
for ecological applications and modelling. *International Journal of
Climatology*, 33, 121-131. https://doi.org/10.1002/joc.3413

Abatzoglou, J. T., & Williams, A. P. (2016). Impact of anthropogenic climate
change on wildfire across western US forests. *Proceedings of the National
Academy of Sciences*, 113, 11770-11775.
https://doi.org/10.1073/pnas.1607171113

Williams, A. P., Abatzoglou, J. T., Gershunov, A., Guzman-Morales, J., Bishop,
D. A., Balch, J. K., & Lettenmaier, D. P. (2019). Observed impacts of
anthropogenic climate change on wildfire in California. *Earth's Future*, 7,
892-910. https://doi.org/10.1029/2019EF001210

He, Q., Williams, A. P., Johnston, M. R., Juang, C. S., & Wang, B. (2025).
Influence of time-averaging of climate data on estimates of atmospheric vapor
pressure deficit and inferred relationships with wildfire area in the western
United States. *Geophysical Research Letters*, 52, e2024GL113708.
https://doi.org/10.1029/2024GL113708

Balch, J. K., Iglesias, V., Mahood, A. L., Cook, M. C., Amaral, C., Decastro,
A., Leyk, S., McIntosh, T. L., Nagy, R. C., St. Denis, L., Tuff, T., Verleye,
E., Williams, A. P., & Kolden, C. A. (2024). The fastest growing and most
destructive fires in the U.S. (2001-2020). *Science*, 386, 425-431.
https://doi.org/10.1126/science.adk5737

Holsinger, L. M., Parks, S. A., & Miller, C. (2016). Weather, fuels, and
topography impede wildland fire spread in western US landscapes. *Forest Ecology
and Management*, 380, 59-69. https://doi.org/10.1016/j.foreco.2016.08.035

Povak, N. A., Kane, V. R., Collins, B. M., Lydersen, J. M., & Kane, J. T.
(2018). Evidence for scale-dependent topographic controls on wildfire spread.
*Ecosphere*, 9, e02443. https://doi.org/10.1002/ecs2.2443

Bookstein, F. L. (1991). *Morphometric Tools for Landmark Data: Geometry and
Biology*. Cambridge University Press. https://doi.org/10.1017/CBO9780511573064

Mitteroecker, P., & Gunz, P. (2009). Advances in geometric morphometrics.
*Evolutionary Biology*, 36, 235-247. https://doi.org/10.1007/s11692-009-9055-x

## Next Stage

Stage 2 should turn this into a tighter manuscript outline with paragraph-level
topic sentences and citation placement. The next draft should also decide the
target journal style and whether the first submission should emphasize:

1. A new representation and theory of wildfire development.
2. A methods-forward morphospace and atlas contribution.
3. A climate-coupling analysis with Fire VASE as the organizing framework.

My current recommendation is option 1, with option 2 as the methodological
engine and option 3 as the empirical test.
