# What Fire VASE does

<p class="fire-page-deck">Fire VASE turns dated observations of wildfire growth into a common developmental response—then asks what might explain the differences.</p>

<div class="fire-stage-map" markdown>
<div><span>01</span><strong>Observe</strong><small>Dated polygons</small></div>
<b>→</b>
<div><span>02</span><strong>Order</strong><small>Daily increments</small></div>
<b>→</b>
<div><span>03</span><strong>Standardize</strong><small>Relative time</small></div>
<b>→</b>
<div><span>04</span><strong>Represent</strong><small>Fire VASE</small></div>
<b>→</b>
<div><span>05</span><strong>Compare</strong><small>Morphospace</small></div>
<b>→</b>
<div><span>06</span><strong>Explain</strong><small>External layers</small></div>
<b>→</b>
<div><span>07</span><strong>Challenge</strong><small>Failure tests</small></div>
</div>

<div class="fire-answer" markdown>
<span>Short answer</span>

The analysis reconstructs each fire’s observed sequence, expresses cumulative
growth on comparable relative-time coordinates, and compares those histories
without using weather or endpoints to define the primary shape space. Weather
and recent fire state enter only afterward as candidate explanatory layers.
</div>

## Seven stages, with technical routes

<div class="fire-method-steps" markdown>
<div markdown><span>01 · Observe</span>

### Start with dated fire polygons

FIRED event and daily records identify where and when satellite observations
attribute newly burned area to a reconstructed fire. The full reanalysis begins
with **278,569 events** and **626,102 cached observations**.

[Source-data details](datasets/fired.md)
</div>
<div markdown><span>02 · Order</span>

### Reconstruct the observed history

Daily increments are ordered by date and audited for gaps, duplicates,
nonfinite values, and agreement with source geometry. An observation gap stays
a gap; it is never silently converted into a no-growth day.

[Data boundary](data.md)
</div>
<div markdown><span>03 · Standardize</span>

### Put histories on comparable coordinates

For the primary cohort, each increment occupies an equal-width relative-time
interval. Interpolating cumulative mass at 21 fixed edges produces 20
nonnegative growth-allocation bins that sum to one. This aligns histories; it
does not create new observations.

[Detailed methods](methods.md)
</div>
<div markdown><span>04 · Represent</span>

### Construct the Fire VASE

Time runs upward. Each observed slice adds a ring; its radius is proportional
to the square root of normalized cumulative burned area. A VASE is a
retrospective developmental record—not a geographic perimeter, spread
direction, mechanistic model, or natural fire type.

[Implementation map](code-map.md)
</div>
<div markdown><span>05 · Compare</span>

### Build a developmental morphospace

Mean-centered, standardized PCA compares the 20 allocation bins for **10,246
fires with at least three consecutive daily observations**. Final area,
duration, observation count, absolute peak growth, and weather are excluded
from the primary coordinate construction.

[Developmental pathways](findings/developmental-pathways.md)
</div>
<div markdown><span>06 · Explain</span>

### Add external layers afterward

Event-level weather models use **9,212 complete primary fires**. A separate
state analysis uses **87,944 exact next-day transitions from 31,700 fires** to
ask what weather adds beyond known recent growth, cumulative area, and elapsed
time.

[Weather and recent state](findings/weather-and-state.md)
</div>
<div markdown><span>07 · Challenge</span>

### Test the claim’s weak points

Observation thresholds, temporal shuffles, alternative allocation nulls,
compositional geometry, blocked transfer, spatial attribution, matching
choices, deliberate corruptions, and software tests probe where the result is
stable and where it is conditional.

[How we tried to break Fire VASE](validation/index.md)
</div>
</div>

<section class="fire-figure" markdown>

![Four observed histories become four Fire VASE representations.](assets/figures/v2/Figure_1.png)

<div class="fire-figure__caption" markdown>
<strong>Read from top to bottom.</strong> Bars show each observed daily share;
the line shows cumulative reconstructed area; the lower glyph preserves that
ordered accumulation. Fire 100001 includes unobserved dates, shown as gray
bands, and is therefore not part of the consecutive-history primary
morphospace. [Full caption and figure provenance](reproduce-figures.md#figure-1-from-dated-growth-observations-to-developmental-morphology)
</div>
</section>

<details class="fire-read-figure" open>
<summary>How to read this figure</summary>
<div markdown>

- **Panels:** Each column follows one observed fire from dated increments to a
  cumulative curve and then to its VASE.
- **Look here:** Fire 100001 contains gray bands. Those dates are unobserved,
  not days of confirmed zero growth.
- **Comparison:** Compare where the cumulative line widens rapidly across the
  four fires; the VASE retains the same ordering visually.
- **Supported conclusion:** Fire VASE standardizes an observed developmental
  record. It does not reconstruct spread direction or a continuous fire front.

</div>
</details>

## What was measured—and what was not

| Layer | Quantity | Interpretation boundary |
|---|---|---|
| Observations | Dated FIRED area increments | Retrospective satellite-derived record, not continuous flame-front telemetry |
| Development | Normalized allocation through relative time | Comparable history, not absolute size or spread direction |
| Morphospace | PCA of 20 allocation bins | Continuous coordinates; labels are landmarks, not established classes |
| Weather | Daily gridMET conditions, roughly 4-km resolution | External association; not local fuel load, causal effect, or operational forecast |
| Recent state | Current/prior growth, cumulative area, elapsed time | Strong retrospective predictor; availability in real time is not established |
| Matching | Unique, caliper-constrained pairs | Hypothesis-generating cases; mismatch is design-dependent, not prevalence |

??? info "Technical details"

    The [technical manuscript](manuscripts/fire_vase_developmental_morphology/manuscript_v2.md)
    defines the equations, folds, resampling, matching rules, and claim
    boundaries. The [second-generation analysis record](reanalysis-v2.md)
    traces corrections and frozen outputs.

<nav class="fire-next">
<a href="../"><small>Back</small><strong>Overview</strong></a>
<a href="../findings/"><small>Next question</small><strong>What did Fire VASE find? →</strong></a>
</nav>
