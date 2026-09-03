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
