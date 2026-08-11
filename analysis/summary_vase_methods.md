# Summary VASE Methods

Observed VASEs show one fire. Composite VASEs summarize groups of observed fires. Conditional VASEs show empirical or model-derived expected development under a named condition.

## Composite VASE

For each fire, daily slice index is mapped to normalized developmental time from 0 to 1. Normalized VASE width is interpolated onto 41 common time points. The median width at each time point forms the composite VASE. The interquartile range is drawn as a translucent shell. Uncertainty is summarized by fire-level resampling, not slice-level resampling, because daily slices within a fire are not independent.

## Climate-conditioned VASE

This revision uses empirical climate-conditioned composites for low, middle, and high VPD exposure groups. Climate groups are terciles of event-mean daily centroid gridMET VPD among climate-complete fires. The profiles are observed composites, not synthetic fires.

## Probability VASE

The reusable framework can summarize pulse, zero-growth, acceleration, reactivation, or termination probabilities by developmental time. The current main figures avoid overloading one glyph and instead use the simplest probability summary: developmental-neighborhood prevalence across VPD terciles.

## Model-predicted Conditional VASE

The current data support exploratory state-dependent regressions for next-day growth, but blocked interaction performance is not strong enough to justify a main-text model-predicted VASE as a central result. Model-predicted conditional VASEs should be added only after the active-edge/perimeter climate extraction is population-wide and local anomalies are computed from independent normals.
