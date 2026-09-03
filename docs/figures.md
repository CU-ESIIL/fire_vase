# Walk through the evidence

<p class="fire-page-deck">The five current manuscript figures form one argument: encode the observed history, compare developmental form, add weather as an external layer, condition on recent state, and use mismatches to choose the next measurements.</p>

<div class="fire-story-rail" markdown>
<a href="#figure-1-how-fire-vase-represents-development"><span>01</span><strong>Represent</strong><small>What the VASE encodes</small></a>
<a href="#figure-2-developmental-gradients"><span>02</span><strong>Compare</strong><small>How histories vary</small></a>
<a href="#figure-3-weather-and-form"><span>03</span><strong>Associate</strong><small>How weather maps onto shape</small></a>
<a href="#figure-4-state-before-weather"><span>04</span><strong>Predict</strong><small>What adds next-day skill</small></a>
<a href="#figure-5-matched-mismatches"><span>05</span><strong>Question</strong><small>What to measure next</small></a>
</div>

## Figure 1: How Fire VASE represents development

<p class="fire-figure-takeaway">One endpoint can conceal many ordered histories. Fire VASE makes the allocation of observed growth through time visible and comparable.</p>

![Four verified dated FIRED histories above the Fire VASE forms that encode their cumulative observed growth. Gray bands identify unobserved dates rather than zero growth.](assets/figures/v2/Figure_1.png)

<details class="fire-read-figure" open>
<summary>How to read this figure</summary>
<div markdown>

- **Panels:** Each column is one real fire. Bars show daily growth share; the
  line shows cumulative share; the VASE below is the same history rendered as
  widening rings.
- **Axes and objects:** Calendar time runs left to right in the charts and
  relative developmental time runs upward in each VASE. Width is the square
  root of cumulative reconstructed-area share.
- **Look here:** Compare the early jump in Fire 159684 with the steadier
  accumulation in Fire 378845 and the longer, episodic record in Fire 220764.
- **Comparison:** Similar endpoints do not imply similar ordered development.
- **Supported conclusion:** The representation preserves ordering and exposes
  observation gaps; it does not identify a causal mechanism.

</div>
</details>

<div class="fire-evidence-trail" markdown><span>Trace this figure</span>
<div><b>Story</b><a href="approach/">What Fire VASE does</a></div>
<div><b>Analysis</b><code>vase_slices.parquet</code> + <code>event_analysis.parquet</code></div>
<div><b>Reproduce</b><a href="https://github.com/CU-ESIIL/fire_vase/blob/main/manuscript_figures/01_figure_1.py">Figure script</a> · <a href="reproduce/notebooks/">Notebook index</a></div>
<div><b>Validate</b><a href="validation/#could-climate-attribution-be-wrong">Source/date attribution</a></div>
<div><b>Manuscript</b><a href="manuscripts/fire_vase_developmental_morphology/manuscript_v2.md#corrected-semantics-and-observation-support">Observation support</a></div>
</div>

??? info "Formal manuscript caption"

    Four verified FIRED events connect observed daily area increments,
    cumulative area, and VASE rings. Gray bands are unobserved dates, not
    zero-growth days; the VASE records normalized allocation through time
    rather than geographic shape.

## Figure 2: Fire histories occupy broad developmental gradients

<p class="fire-figure-takeaway">Adequately observed fires fill a continuous shape space. The leading directions describe when growth is allocated—not discrete fire types.</p>

![The primary shape-only morphospace for 10,246 consecutive histories, with axis loadings, observation-support counts, and example Fire VASEs.](assets/figures/v2/Figure_2.png)

<details class="fire-read-figure" open>
<summary>How to read this figure</summary>
<div markdown>

- **Panels:** A maps where fires fall; B shows which relative-time bins define
  PC1 and PC2; C shows how many archive fires meet each observation category;
  D gives real example VASEs.
- **Axes:** PC1 explains 34.1% and primarily contrasts earlier with later
  allocation. PC2 explains 28.2% and contrasts middle-concentrated with more
  endpoint-weighted allocation.
- **Look here:** The points spread continuously across the horizontal gradient
  instead of separating into isolated clusters.
- **Comparison:** Read the loadings and VASE examples together; neither the
  point cloud nor a label alone supplies the interpretation.
- **Supported conclusion:** Broad developmental gradients are reproducible.
  Natural fire classes and a universal restricted wedge were not established.

</div>
</details>

<div class="fire-challenge" markdown><strong>Challenge this result</strong> If
the gradients vanished when more observations or another compositional metric
were required, short-history or geometry choices could explain the pattern.
[See those tests →](validation/#does-the-result-depend-on-observation-depth)
</div>

<div class="fire-evidence-trail" markdown><span>Trace this figure</span>
<div><b>Story</b><a href="findings/developmental-pathways/">Developmental pathways</a></div>
<div><b>Figure</b>Figure 2 · N = 10,246</div>
<div><b>Analysis</b>PCA variance, loadings, scores, and sensitivity tables in <code>analysis/v2/</code></div>
<div><b>Reproduce</b><a href="https://github.com/CU-ESIIL/fire_vase/blob/main/manuscript_figures/02_figure_2.py">Figure script</a> · <a href="reproduce/notebooks/">Canonical notebook</a></div>
<div><b>Validate</b><a href="validation/#could-the-geometry-be-an-artifact">Observation depth + geometry</a></div>
<div><b>Manuscript</b><a href="manuscripts/fire_vase_developmental_morphology/manuscript_v2.md#a-shared-coordinate-system-without-a-universal-restricted-wedge-claim">Shared coordinate system</a></div>
</div>

??? info "Formal manuscript caption"

    A shape-only coordinate system is fitted from 20 normalized
    growth-allocation bins for 10,246 gap-free histories. The broad gradients
    are reproducible, while exact neighbors, extreme examples, and
    low-dimensional compression require supplementary qualifications.

## Figure 3: Measured weather maps weakly and unevenly onto form

<p class="fire-figure-takeaway">Weather is added after the developmental axes are built. Its held-out relationship with morphology is small and depends on the response being predicted.</p>

![Mean vapor pressure deficit projected onto the developmental morphospace beside held-out prediction scores for several developmental responses in 9,212 weather-complete primary fires.](assets/figures/v2/Figure_3.png)

<details class="fire-read-figure" open>
<summary>How to read this figure</summary>
<div markdown>

- **Panels:** A colors occupied regions of the already-fitted shape space by
  median event-mean VPD. B shows held-out R² for several developmental
  responses under region, year-block, and strict space-time tests.
- **Axes and colors:** Position is developmental shape; color is added weather,
  not an input to those axes. In B, farther right means more predictive skill.
- **Look here:** Panel A does not show a clean weather gradient across shape,
  and Panel B varies strongly by response; peak timing and fold-fitted shape PC1
  are barely recovered regionally.
- **Comparison:** Compare outcomes and holdout schemes instead of searching for
  one cross-response headline.
- **Supported conclusion:** Weather associations are weak and heterogeneous in
  this cohort and model. The figure does not show that weather is unimportant.

</div>
</details>

<div class="fire-evidence-trail" markdown><span>Trace this figure</span>
<div><b>Story</b><a href="findings/weather-and-state/">Weather and recent state</a></div>
<div><b>Figure</b>Figure 3 · N = 9,212 complete primary fires</div>
<div><b>Analysis</b>Common-cohort event predictors, folds, performance, and uncertainty</div>
<div><b>Reproduce</b><a href="https://github.com/CU-ESIIL/fire_vase/blob/main/manuscript_figures/03_figure_3.py">Figure script</a> · <a href="reproduce/notebooks/">Canonical notebook</a></div>
<div><b>Validate</b><a href="validation/#could-climate-attribution-be-wrong">Attribution + external-source checks</a></div>
<div><b>Manuscript</b><a href="manuscripts/fire_vase_developmental_morphology/manuscript_v2.md#weather-is-an-external-response-dependent-association">Weather association</a></div>
</div>

??? info "Formal manuscript caption"

    Weather is projected after the axes are fitted. Held-out skill is small and
    response-dependent across the same 9,212 weather-complete primary fires.

## Figure 4: Recent state carries most next-day predictive information

<p class="fire-figure-takeaway">Measured weather adds a reproducible but small increment after current and previous growth, cumulative area, and elapsed time are known.</p>

![Held-out next-calendar-day growth predictions comparing recent fire state, measured weather, their interactions, spatial attribution, and seasons across 87,944 transitions.](assets/figures/v2/Figure_4.png)

<details class="fire-read-figure" open>
<summary>How to read this figure</summary>
<div markdown>

- **Panels:** A compares total held-out skill; B isolates increments above the
  same state baseline; C changes exposure geometry; D checks seasons.
- **Axes:** In A, R² is total predictive performance. In B-D, ΔR² is only the
  extra skill gained after recent state is already included.
- **Look here:** State sits near R² 0.45, while weather-only points sit much
  closer to zero. Adding weather moves the state model only slightly.
- **Comparison:** The defensible weather comparison is incremental skill above
  state—not total R² from the interaction model.
- **Supported conclusion:** Recent state predicts the next observed increment
  much better than these weather variables add on top. This is not a causal or
  operational forecast.

</div>
</details>

<div class="fire-evidence-trail" markdown><span>Trace this figure</span>
<div><b>Claim</b>Region-held-out state R² 0.448; weather ΔR² 0.005; interactions ΔR² 0.018</div>
<div><b>Analysis</b>87,944 exact transitions from 31,700 fires; paired blocked comparisons</div>
<div><b>Reproduce</b><a href="https://github.com/CU-ESIIL/fire_vase/blob/main/manuscript_figures/04_figure_4.py">Figure script</a> · <a href="reproduce/notebooks/">Canonical notebook</a></div>
<div><b>Validate</b><a href="validation/#could-climate-attribution-be-wrong">Day-specific attribution</a> · <a href="validation/climate/">Technical audit</a></div>
<div><b>Manuscript</b><a href="manuscripts/fire_vase_developmental_morphology/manuscript_v2.md#subsequent-growth-is-evaluated-against-known-developmental-state">Subsequent growth</a></div>
</div>

??? info "Formal manuscript caption"

    In 87,944 exact next-day transitions, recent fire state provides most
    predictive information; weather adds a small increment and weather-state
    interactions add somewhat more. These are retrospective associations, not
    an operational forecast or causal estimate.

## Figure 5: Matched mismatches define the next questions

<p class="fire-figure-takeaway">Similar weather can accompany different developmental histories, and similar histories can accompany different weather—but observed mismatch is compatible with the conditional null.</p>

![Matching coverage, conditional-permutation references, and representative morphology-matched and weather-matched fire pairs.](assets/figures/v2/Figure_5.png)

<details class="fire-read-figure" open>
<summary>How to read this figure</summary>
<div markdown>

- **Panels:** A reports pair coverage; B compares observed mismatch dots with
  conditional-null boxes; C and D show two independent representative pairs.
- **Axes:** The lower panels show cumulative reconstructed-area fraction across
  relative developmental time. Distance values are standardized diagnostics.
- **Look here:** In B, the observed dots sit within the conditional reference
  distributions. In D, closely weather-matched fires follow visibly different
  histories.
- **Comparison:** Treat C and D as separate pairs, not rows and columns of one
  reciprocal match.
- **Supported conclusion:** These are controlled cases for new measurements.
  They do not establish excess mismatch, prevalence, or an omitted mechanism.

</div>
</details>

<div class="fire-evidence-trail" markdown><span>Trace this figure</span>
<div><b>Story</b><a href="findings/mismatched-fires/">Mismatched fires</a></div>
<div><b>Analysis</b>3,710 weather pairs; 3,145 morphology pairs; conditional permutations</div>
<div><b>Reproduce</b><a href="https://github.com/CU-ESIIL/fire_vase/blob/main/manuscript_figures/05_figure_5.py">Figure script</a> · <a href="reproduce/notebooks/">Canonical notebook</a></div>
<div><b>Validate</b><a href="validation/#does-the-result-depend-on-observation-depth">Caliper sensitivity in Figure S2F</a></div>
<div><b>Manuscript</b><a href="manuscripts/fire_vase_developmental_morphology/manuscript_v2.md#representative-convergence-and-divergence">Convergence and divergence</a></div>
</div>

??? info "Formal manuscript caption"

    Unique, caliper-constrained pairs identify candidate contrasts, but
    observed mismatch is compatible with the conditional reference
    distribution. The examples generate hypotheses; they do not identify
    omitted mechanisms.

<nav class="fire-next">
<a href="findings/"><small>Back</small><strong>Findings</strong></a>
<a href="validation/"><small>Next question</small><strong>Why should I trust what I saw? →</strong></a>
</nav>
