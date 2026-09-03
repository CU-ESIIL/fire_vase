# Similar weather can accompany different histories

<p class="fire-eyebrow">Finding 04 · Matched-pair diagnostics</p>
<p class="fire-page-deck">The mismatches are scientifically useful because they identify cases where the current explanatory layer is insufficient—and where new measurements can be most informative.</p>

<div class="fire-question" markdown><span>Question</span>

When fires are closely matched on weather and declared nuisance variables, do
they necessarily share a developmental history? And do similar histories
necessarily share weather?
</div>

<div class="fire-answer" markdown><span>Answer</span>

No. Unique matched pairs include both convergence and divergence. But the
observed mismatch fractions are compatible with conditional permutation
references, so this analysis does not establish excess mismatch or its
ecological prevalence.
</div>

<section class="fire-figure" markdown>

![Coverage, conditional-null comparisons, and representative morphology- and weather-matched pairs.](../assets/figures/v2/Figure_5.png)

<div class="fire-figure__caption" markdown>
<strong>What to notice.</strong> The weather-matched example reaches the same
endpoint through visibly different allocations. The plotted examples are near
the population median mismatch, not adversarial extremes. They are two
independent pairs—not a two-by-two matching design. [Technical caption](../reproduce-figures.md#figure-5-representative-matched-pair-diagnostics)
</div>
</section>

<div class="fire-stat-row" markdown>
<div><strong>80.5%</strong><span>eligible fires assigned a weather-space partner</span></div>
<div><strong>68.3%</strong><span>eligible fires assigned a morphology-space partner</span></div>
<div><strong>49.7%</strong><span>observed mismatch among weather matches</span></div>
<div><strong>50.4%</strong><span>conditional-permutation mean</span></div>
</div>

## What we measured

Matching starts with **9,212 complete primary fires**. Candidate partners share
region, season, duration, and observation count, differ in area by no more than
a factor of two, and fall within a declared standardized-distance caliper.
Partners cannot be reused. Mismatch outcomes never influence pair selection.

## How well does it hold up?

Coverage changes when the caliper, candidate-neighbor count, or distance metric
changes. At the declared design, morphology-matched mismatch is **39.5%**
compared with a **40.2%** conditional-permutation mean. These agreements make
the pairs useful as representative study candidates while preventing a claim
that observed mismatch is unusually common.

## These mismatches tell us what to measure next

- fuel load and continuity along the active edge
- terrain and slope aligned to dated progression
- directional wind and sub-grid weather heterogeneity
- ignition context and suppression history
- active-edge geometry and independent operational observations
- uncertainty in satellite burn date and event reconstruction

These are hypotheses named in the manuscript, not mechanisms established by
the current pair analysis. Fire VASE supplies the common response against which
those next layers can be tested.

## What this does not show

The matching is observational, greedy rather than globally optimal, constrained
by candidate search and exact nuisance strata, and sensitive to the declared
caliper. A diagnostic threshold of standardized other-space distance greater
than one is not a natural class boundary.

??? info "Technical details"

    See [matching and reproducibility](../manuscripts/fire_vase_developmental_morphology/manuscript_v2.md#matching-and-reproducibility)
    and the [matching outputs](../reanalysis-v2.md#outputs-and-provenance).

<nav class="fire-next">
<a href="../weather-and-state/"><small>Previous</small><strong>Weather and recent state</strong></a>
<a href="../../validation/"><small>Next</small><strong>How strong is the evidence? →</strong></a>
</nav>
