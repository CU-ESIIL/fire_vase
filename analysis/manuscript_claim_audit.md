# Fire VASE Manuscript Claim Audit

## Current Claims

- The current manuscript claims a constrained developmental morphospace.
- It also claims a geometry-first coordinate system, recurring developmental neighborhoods, climate alignment without equivalence, and a leakage-audited but weak fixed-day prediction benchmark.

## Evidence Supporting Each Claim

- Shared coordinate system: supported. The pipeline represents 278,569 real FIRED events in one geometry-only feature space with reproducible PCA coordinates.
- Low-dimensional representation: supported for the full observed population. Five PCs explain 0.963 of standardized variance; PC1 explains 0.810.
- Interpretable developmental gradients: partly supported. Top loadings and correlations show PC1 is dominated by cumulative-width and growth-share profile features, with secondary axes carrying duration, taper, pulse, and timing structure.
- Strong developmental constraint relative to plausible alternatives: not yet fully supported. Some nulls remain close to observed once duration, monotonic cumulative growth, and empirical profile structure are preserved.
- Climate as proof of concept: supported as an alignment analysis, not as causation or a main mechanistic explanation.
- Fixed-day prediction: not supported as an affirmative main-text result under blocked validation.

## Evidence Weakening Stronger Claims

- PC1 weakens sharply after removing the many one-day fires. With duration >= 10 days, PC1-PC5 cumulative variance is 0.785.
- Removing scale and duration variables still leaves PC1-PC5 variance at 0.976, but this reflects profile redundancy as much as developmental constraint.
- Profile-only features have very high five-PC variance (0.996); growth-share profiles alone are even higher (0.999), showing that profile encoding itself contributes strong redundancy.
- Within-fire and duration-conditioned nulls are the critical tests. The manuscript should not claim that observed fires occupy a restricted subset of all plausible trajectories unless those nulls show a clear support or volume separation.

## Recommended Final Claim

Highest defensible level: **Level 2 - Wildfire histories occupy a reproducible low-dimensional developmental morphospace.**

Level 3 can be phrased cautiously as a hypothesis or pattern of recurring neighborhoods, but Level 4 is not yet justified.

## Go/No-Go Recommendation For Science

**Go after major revision.** The representation and low-dimensional morphospace are compelling enough for a paper, but the title, abstract, Results headings, and Figure sequence should retreat from strong constraint language unless stronger nulls are made central and survive.

## Unresolved Risks

- Short fires dominate the full-population PCA.
- PC1 is heavily tied to monotone cumulative-profile encoding.
- Climate remains centroid-based in the current manuscript-scale analysis.
- Dynamic/state-space claims are not yet tested.
- Prediction currently distracts from the strongest result.

## Strongest PC1 Correlations In The Full Feature Set

| feature_set | pc1_target | pearson_r |
| --- | --- | --- |
| full current feature set | growth_p05 | 0.9627 |
| full current feature set | log_duration_days | -0.9468 |
| full current feature set | front_loaded_fraction | 0.9436 |
| full current feature set | width_p05 | 0.9207 |
| full current feature set | growth_entropy | -0.9139 |
| full current feature set | log_final_area_km2 | -0.8214 |
| full current feature set | late_growth_fraction | -0.7696 |
| full current feature set | observation_count | -0.7319 |
