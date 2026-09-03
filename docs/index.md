<section class="fire-home-hero">
<img class="fire-hero-vase" src="assets/hero-vase-vpd.png" alt="A Fire VASE: a vessel-shaped record whose widening rings encode cumulative observed fire growth through time">
<div class="fire-home-hero__content">
<p class="fire-kicker">Developmental wildfire morphology</p>

<h1>Fires have developmental histories.</h1>

<h2>Final size tells us how big a fire became. Fire VASE captures how it got there.</h2>

<p>Fire VASE turns ordered, dated growth observations into comparable
developmental trajectories. It reconstructs the observed history first, then
tests weather and other possible explanations against that common response.</p>

<p>
<a class="md-button md-button--primary fire-button" href="approach/">See how it works</a>
<a class="md-button fire-button" href="findings/">Explore the findings</a>
<a class="md-button fire-button" href="reproduce/">Reproduce the research</a>
</p>
</div>
</section>

<section class="fire-home-strip" markdown>
<div markdown>
<span>278,569</span>
FIRED events in the reanalyzed source archive
</div>
<div markdown>
<span>10,246</span>
histories with ≥3 consecutive daily observations in the primary morphospace
</div>
<div markdown>
<span>87,944</span>
exact next-calendar-day transitions used in the recent-state analysis
</div>
</section>

<section class="fire-home-intro" markdown>
<p class="fire-kicker">The problem</p>

## The endpoint hides the pathway

Two fires can finish at a similar size after a similar span of time while
allocating growth very differently—early, steadily, late, or in repeated
pulses. Endpoint summaries collapse those sequences. Fire VASE keeps the order
visible so that the developmental pathway itself becomes something scientists
can compare and explain.
</section>

<section class="fire-figure fire-figure--wide" markdown>

![Four dated fire-growth records and the Fire VASE forms they produce.](assets/figures/v2/Figure_1.png)

<div class="fire-figure__caption" markdown>
<strong>What to notice.</strong> The top row records when observed growth was
added; the lower row translates that cumulative sequence into a VASE. Gray
bands are unobserved dates, not zero-growth days. The primary comparative
analysis therefore uses only consecutive histories. **N = 10,246** for the
primary morphospace; the four fires shown here are examples.

[Read the technical figure caption](reproduce-figures.md#figure-1-from-dated-growth-observations-to-developmental-morphology)
</div>
</section>

<section class="fire-home-intro" markdown>
<p class="fire-kicker">The idea</p>

## Reconstruct first. Explain second.

Weather, final area, duration, and observation count do not define the primary
shape coordinates. Fire VASE first standardizes the allocation of observed
growth through relative developmental time. External variables are added only
afterward, making representation and explanation separate, testable steps.
</section>

<div class="fire-flow fire-flow--compact" markdown>
<div><span>01</span><strong>Observed polygons</strong><small>Dated FIRED growth</small></div>
<b>→</b>
<div><span>02</span><strong>Ordered growth</strong><small>History reconstructed</small></div>
<b>→</b>
<div><span>03</span><strong>Standardized trajectory</strong><small>Comparable relative time</small></div>
<b>→</b>
<div><span>04</span><strong>Fire VASE</strong><small>Development made visible</small></div>
</div>

<section class="fire-home-intro" markdown>
<p class="fire-kicker">The findings</p>

## What the evidence supports
</section>

<section class="fire-finding-grid">
<a class="fire-finding-card" href="findings/developmental-pathways/">
<span>01 · Representation</span>
<h2>Fires follow different developmental pathways.</h2>
<p>Broad gradients distinguish earlier from later allocation and concentrated
from more distributed growth. They are continuous coordinates, not established
fire types.</p>
<strong>5 axes · 89.4% <i>of standardized shape variance</i></strong>
</a>

<a class="fire-finding-card" href="findings/temporal-ordering/">
<span>02 · Ordering</span>
<h2>The order of growth contains information.</h2>
<p>Shuffling each fire’s same observed increments changes front-loading,
detected pulses, reactivations, and morphospace coverage.</p>
<strong>0.541 vs 0.500 <i>mean first-half allocation</i></strong>
</a>

<a class="fire-finding-card" href="findings/weather-and-state/">
<span>03 · Prediction</span>
<h2>Recent state explains much more than weather alone.</h2>
<p>Weather matters, but in these held-out analyses it adds little next-day
predictive skill beyond recent observed fire state.</p>
<strong>0.448 R² <i>state baseline</i> · +0.005 <i>weather</i></strong>
</a>

<a class="fire-finding-card" href="findings/mismatched-fires/">
<span>04 · Open questions</span>
<h2>Similar weather can accompany different histories.</h2>
<p>Matched mismatches are study candidates for fuels, terrain, active-edge
conditions, ignition, suppression, and observation uncertainty—not proof of a
missing causal mechanism.</p>
<strong>49.7% vs 50.4% <i>observed vs conditional-null mismatch</i></strong>
</a>
</section>

<section class="fire-dark-band" markdown>
<p class="fire-kicker">Confidence</p>

## We tried to break the result.

The analysis was challenged with stricter observation thresholds, shuffled and
synthetic null histories, alternative compositional geometry, blocked
prediction, day-specific climate attribution, subgroup tests, independent data
checks, deliberate corruptions, and a full software test suite. Broad
developmental gradients and informative ordering persist; exact neighborhoods,
dimensionality, weather associations, and mechanistic interpretation remain
qualified.

<div class="fire-stat-row" markdown>
<div><strong>6 / 6</strong><span>real-data validation modules pass</span></div>
<div><strong>152</strong><span>repository tests pass; 2 intentionally skipped</span></div>
<div><strong>0.969</strong><span>distance-rank agreement at ≥7 observations</span></div>
</div>

[See how Fire VASE was challenged →](validation/index.md){ .md-button .md-button--primary .fire-button }
</section>

<section class="fire-home-intro" markdown>
<p class="fire-kicker">Meaning</p>

## A common response for the next layer of wildfire science

Fire VASE does not replace weather, fire-behavior physics, or endpoint
summaries. It supplies a transparent response against which those explanations
can be tested. The next scientific step is to align dated growth with
process-specific measurements—especially fuel continuity, terrain, active-edge
conditions, ignition context, and suppression—while improving observation-depth
and burn-date uncertainty.
</section>

<section class="fire-home-journey">
<a href="approach/"><span>01</span><div><strong>How can similar fires develop differently?</strong><small>See the idea →</small></div></a>
<a href="approach/"><span>02</span><div><strong>We reconstructed their developmental histories.</strong><small>See the approach →</small></div></a>
<a href="findings/developmental-pathways/"><span>03</span><div><strong>Development occupies broad, reproducible gradients.</strong><small>See what we found →</small></div></a>
<a href="findings/weather-and-state/"><span>04</span><div><strong>Measured weather adds little beyond recent state.</strong><small>See the evidence →</small></div></a>
<a href="validation/"><span>05</span><div><strong>We tested where the result holds—and where it does not.</strong><small>See the validation →</small></div></a>
</section>

<section class="fire-reproduce-cta" markdown>
<p class="fire-kicker">Open evidence</p>

## Inspect every layer

Data, schemas, four Jupyter notebooks, analysis and figure scripts, validation
outputs, tests, provenance records, manuscript sources, and historical
corrections remain available beneath this narrative.

[Reproduce this research →](reproduce/index.md){ .md-button .md-button--primary .fire-button }
[Read the paper](manuscript.md){ .md-button .fire-button }
</section>
