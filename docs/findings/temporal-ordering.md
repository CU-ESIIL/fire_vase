# The order of growth contains information

<p class="fire-eyebrow">Finding 02 · Temporal-order null model</p>
<p class="fire-page-deck">Keeping every observed increment but changing its position changes the developmental signal.</p>

<div class="fire-question" markdown><span>Question</span>

Does Fire VASE retain information about sequence, or does only the total and
multiset of growth increments matter?
</div>

<div class="fire-answer" markdown><span>Answer</span>

Sequence matters. In a separately recorded **4,000-fire** sample, observed
histories are more front-loaded, less pulsed, and less frequently reactivated
than within-fire permutations of exactly the same increments.
</div>

<div class="fire-shuffle" markdown>
<div><span>Observed order</span><strong>large → small → small → large → small</strong></div>
<b>shuffle the same increments</b>
<div><span>Permuted order</span><strong>small → large → small → small → large</strong></div>
</div>

If only total growth mattered, rearranging the same increments would not
systematically change order-sensitive developmental traits. Each permutation
preserves the fire’s observation count, reconstructed total, and full
increment multiset.

<section class="fire-figure" markdown>

![Second-pass validation of observation depth, allocation nulls, temporal order, excluded endpoints, adjusted weather associations, and matching calipers.](../assets/figures/v2/Supplementary_Figure_2.png)

<div class="fire-figure__caption" markdown>
<strong>What to notice.</strong> Panel S2C compares observed trait means with
the 95% range from temporal shuffles. Panel S2B shows an equally important
boundary: other positive, mass-conserving allocation nulls compress as much as
or more than the observed space. Ordering is informative; compression alone
does not prove biological restriction. [Technical caption](../reproduce-figures.md#supplementary-figure-2-second-pass-validation)
</div>
</section>

<div class="fire-stat-row" markdown>
<div><strong>0.541</strong><span>observed mean first-half allocation</span></div>
<div><strong>0.500</strong><span>mean after temporal shuffling</span></div>
<div><strong>1.249 vs 1.413</strong><span>observed vs shuffled detected pulses</span></div>
<div><strong>0.038 vs 0.120</strong><span>observed vs shuffled reactivations</span></div>
</div>

## How well does it hold up?

One hundred replicates compare profile distances, trait distributions, landmark
occupancy, and PCA summaries. Entropy remains unchanged by shuffling—as it
should, because entropy ignores order. That invariant is a useful internal
control on what the permutation changes.

## What this does not show

The result does not prove that morphology is caused by biology, fuels, weather,
suppression, or any other mechanism. The empirical tail tests are descriptive,
have resolution 1/101, and are not multiplicity-adjusted. Positive normalized
curves are constrained objects, so compression cannot carry the argument by
itself.

??? info "Technical details"

    Read the [null-model methods](../manuscripts/fire_vase_developmental_morphology/manuscript_v2.md#growth-and-shape-coordinates)
    and [frozen reanalysis evidence](../reanalysis-v2.md#what-survived-scientific-validation).

<nav class="fire-next">
<a href="../developmental-pathways/"><small>Previous</small><strong>Developmental pathways</strong></a>
<a href="../weather-and-state/"><small>Next question</small><strong>What explains next-day growth? →</strong></a>
</nav>
