# Recent state explains much more than weather alone

<p class="fire-eyebrow">Finding 03 · Held-out subsequent-growth models</p>
<p class="fire-page-deck">Weather matters, but measured weather explains relatively little additional variation in the next observed growth increment compared with recent fire state in these analyses.</p>

<div class="fire-question" markdown><span>Question</span>

For exact next-calendar-day transitions, how much does day-specific weather add
after the fire’s recent developmental state is known?
</div>

<div class="fire-answer" markdown><span>Answer</span>

The region-held-out autoregressive state model explains **44.8%** of variation.
Adding weather raises R² by **0.5 percentage points**; allowing the full set of
weather × state interactions raises it by **1.8 percentage points** above the
same baseline.
</div>

## First ask what weather predicts by itself

<section class="fire-figure" markdown>

![Mean vapor pressure deficit projected onto an already fitted developmental morphospace, beside held-out weather prediction scores for several developmental responses.](../assets/figures/v2/Figure_3.png)

<div class="fire-figure__caption" markdown>
<strong>What to notice.</strong> Weather is projected after the developmental
axes exist. The color field is not a clean shape gradient, and held-out skill
varies by response and blocking scheme. [Technical caption](../reproduce-figures.md#figure-3-weather-associations-with-developmental-form)
</div>
</section>

<details class="fire-read-figure" open>
<summary>How to read Figure 3</summary>
<div markdown>

- **Panels:** A colors the existing morphospace by median event-mean VPD; B
  compares held-out prediction for several developmental responses.
- **Look here:** Peak timing and fold-fitted shape PC1 are barely recovered in
  regional holdout, while other outcomes show somewhat more skill.
- **Supported conclusion:** Weather–morphology associations are weak and
  response-dependent in this cohort. This does not show weather is unimportant.

</div>
</details>

<div class="fire-comparison" markdown>
<div><span>Recent fire state</span><strong>R² 0.448</strong><small>current and prior growth, cumulative area, elapsed time</small></div>
<div><span>+ weather</span><strong>ΔR² 0.005</strong><small>increment above the same state baseline</small></div>
<div><span>+ weather × state</span><strong>ΔR² 0.018</strong><small>full interaction increment above baseline</small></div>
</div>

<section class="fire-figure" markdown>

![Held-out prediction of subsequent calendar-day growth from recent state, weather, and their interactions.](../assets/figures/v2/Figure_4.png)

<div class="fire-figure__caption" markdown>
<strong>What to notice.</strong> The autoregressive state points sit near R²
0.45; weather-only prediction is much lower. The right panels show the smaller
increment that weather contributes above state, including sensitivity to
spatial exposure and season. The common cohort contains **87,944 transitions
from 31,700 fires**. [Technical caption](../reproduce-figures.md#figure-4-developmental-state-and-subsequent-calendar-day-growth)
</div>
</section>

<details class="fire-read-figure" open>
<summary>How to read Figure 4</summary>
<div markdown>

- **Panels:** A compares total held-out R²; B isolates increments above the
  same state baseline; C changes exposure geometry; D checks seasons.
- **Look here:** State is near R² 0.45, while weather-only prediction is much
  lower. Weather moves the state baseline only slightly.
- **Comparison:** The defensible weather comparison is ΔR² above state—not the
  total R² of the interaction model.
- **Supported conclusion:** Recent observed state carries much more next-day
  predictive information than these weather variables add. This is
  retrospective association, not causal or operational prediction.

</div>
</details>

<div class="fire-challenge" markdown><strong>Challenge this result.</strong>
Incorrect dates, static centroids, or region leakage could create artificial
weather skill. [See the date, geometry, external-source, and blocked-fold tests →](../validation/index.md#could-climate-attribution-be-wrong)
</div>

<div class="fire-evidence-trail" markdown><span>Evidence trail</span>
<div><b>Claim</b>State R² 0.448; weather ΔR² 0.005; interactions ΔR² 0.018</div>
<div><b>Figures</b>Figure 3 · N = 9,212; Figure 4 · 87,944 transitions from 31,700 fires</div>
<div><b>Analysis</b>Common cohorts, exact next-day transitions, blocked folds, paired comparisons</div>
<div><b>Reproduce</b><a href="https://github.com/CU-ESIIL/fire_vase/tree/main/manuscript_figures">Figure scripts</a> · <a href="../reproduce/notebooks/">notebooks</a></div>
<div><b>Validate</b><a href="../validation/climate/">Climate attribution audit</a> · <a href="../validation/external/">external source check</a></div>
<div><b>Paper</b><a href="../manuscripts/fire_vase_developmental_morphology/manuscript_v2/#subsequent-growth-is-evaluated-against-known-developmental-state">Current claim</a></div>
</div>

## What we measured

Every comparator uses exact one-day transitions and the same cohort. The
baseline contains current growth, previous-calendar-day growth, cumulative
observed area, and elapsed time. Day-*t* weather is sampled at that day’s newly
burned-area centroid. Models are evaluated by held-out region, year block, and
their stricter intersection.

## How well does it hold up?

| Holdout | State R² | + weather ΔR² | + interactions ΔR² |
|---|---:|---:|---:|
| Region | 0.448 | 0.005 | 0.018 |
| Year block | 0.458 | 0.005 | 0.015 |
| Space + time | 0.448 | 0.005 | 0.018 |

VPD-specific products add **0.006–0.012 R²** above the other interactions
across four blocking schemes; the regional increment is **0.0118** with a
conditional fire-bootstrap interval of **0.0097–0.0138**. Coefficients vary by
region, size, and partial edge years, and small-fire subsets can have poor
absolute prediction despite a positive increment.

## What this does not show

This is not evidence that weather is unimportant. It is evidence that the
measured, roughly 4-km daily weather variables add little *predictive skill*
after recent reconstructed state is known in this cohort and model. The result
is retrospective, non-causal, and not a live forecast. Satellite latency,
event delineation, time-zone alignment, local heterogeneity, directional wind,
active-edge exposure, fuels, terrain, and suppression are not resolved.

??? info "Technical details"

    See [weather, prediction, and uncertainty](../manuscripts/fire_vase_developmental_morphology/manuscript_v2.md#weather-prediction-and-uncertainty)
    and the [state-analysis correction record](../reanalysis-v2.md#what-changed).

<nav class="fire-next">
<a href="../temporal-ordering/"><small>Previous</small><strong>Temporal ordering</strong></a>
<a href="../mismatched-fires/"><small>Next question</small><strong>What remains unexplained? →</strong></a>
</nav>
