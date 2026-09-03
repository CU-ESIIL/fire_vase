# The Developmental Morphospace of Wildfire

Fire VASE changes the response being explained. Instead of reducing a wildfire
to final area, duration, or peak growth, it treats the ordered accumulation of
burned area as an observed developmental history that can be compared across
events.

The current manuscript's central claim is precise: Fire VASE makes the ordered
allocation of observed wildfire growth a robust, comparable developmental
response. Its broad geometry persists across the tested observation-depth,
temporal-order, and compositional-geometry comparisons. The method creates a
shared response for asking why adequately observed fires follow different
growth pathways; it does not claim that endpoint summaries, weather, or local
neighborhood labels uniquely determine those pathways.

[Read the assembled manuscript](https://github.com/CU-ESIIL/fire_vase/blob/main/output/submission/fire_vase_manuscript_submission.pdf){ .md-button .md-button--primary .fire-button }
[Read the assembled SI](https://github.com/CU-ESIIL/fire_vase/blob/main/output/submission/fire_vase_supplementary_submission.pdf){ .md-button .fire-button }
[Browse every figure](reproduce-figures.md){ .md-button .fire-button }
[Read the guided figure walkthrough](figures.md){ .md-button .fire-button }
[See how AI was used](ai-accountability.md){ .md-button .fire-button }
[Inspect the corrected v2 evidence](reanalysis-v2.md){ .md-button .fire-button }

## The argument

### The pathway matters, not only the endpoint

Two fires can reach similar final areas over similar durations through very
different sequences: an early run followed by little change, persistent steady
growth, a late surge, or repeated growth and quiescence. Fire VASE preserves
those distinctions in a common geometry.

Relative developmental time runs upward through a VASE. Each observed slice
adds a ring, and normalized cumulative burned area controls its width. The
result is not a geographic perimeter or a fire-spread direction. It is a
standardized record of when observed growth accumulated.

### Developmental histories form a continuum

The manuscript describes gradients in the timing, concentration, persistence,
and recurrence of observed growth. Named neighborhoods such as late surge,
front-loaded plateau, or multi-pulse complex are interpretive landmarks, not
discovered natural fire types. Intermediate and mixed pathways are part of the
result.

The current 20-bin shape-only coordinate system uses 10,246 histories with at
least three observations and no intervening calendar-day gaps. Its first axis
explains 34.1% of standardized variance and the first five explain 89.4%.
Positive, mass-conserving reference histories also compress, so compression by
itself is not treated as evidence of biological restriction. The observed
ordering and the meaning and stability of the broad axes carry the stronger
developmental evidence.

### Weather is an explanatory layer, not the definition

The developmental representation is constructed before weather is added.
Weather is the first demonstration of a broader explanatory architecture in
which fuels, terrain, active-edge conditions, ignition context, suppression,
and the spatial geometry of progression can all be tested against the same
developmental response.

The current evidence supports a restrained interpretation: weather associations
are distributional and response-dependent. They do not uniquely specify an
individual history, establish a universal growth response, or identify a
causal mechanism.

### State and mismatch generate better questions

Recent fire state explains substantially more subsequent observed growth than
weather alone. Qualified weather-state interactions indicate that an exposure
can have a different fitted association in different developmental contexts;
they remain retrospective associations rather than operational or causal
estimates.

Across 87,944 exact next-calendar-day transitions, the region-held-out
autoregressive state baseline has R² about 0.448. Weather adds about 0.005 and
the full set of weather-state interactions adds about 0.018 above that baseline.
These increments are informative but small relative to recent-state
predictability.

Likewise, fires that are close in weather space but distant in developmental
space—and the reverse—are useful candidate comparisons. They show where the
present representation is insufficient and where fuels, terrain, suppression,
active-edge exposure, or observation error should be tested. They do not, by
themselves, establish excess mismatch or its ecological prevalence.

## Evidence boundary

The manuscript PDF articulates the project-level scientific argument across the
full FIRED archive, then reports each result for its explicitly defined
observation-supported cohort. The [corrected v2 analysis](reanalysis-v2.md) is
the repository authority for quantitative claims. It uses consecutively
observed histories, a shape-only coordinate system, exact calendar-day
transitions, day-specific newly burned-area exposure, and explicit null and
stability tests. Its results narrow—but preserve—the central contribution:
broad developmental gradients are useful and reproducible, while weather
effects are weak, heterogeneous, and non-causal.

!!! note "Submission document status"

    The supplied `main-22.pdf` and `supplementary-4.pdf` are the latest preserved
    editorial source exports. Their figure markers are provenance notes, not
    website instructions. The assembled PDFs replace those markers with
    validated assets and add full-size figure pages. Current claims, sources,
    and remaining human submission items are frozen in
    `analysis/submission_freeze/`.

## Immediate research focus

The next step is not another endpoint model. It is to test the same
developmental response against more process-specific, independently validated
layers—especially active-edge fuel continuity and terrain aligned to dated
observed growth—while improving observation-depth and burn-date uncertainty.
