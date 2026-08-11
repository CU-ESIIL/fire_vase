# Null Model Report

Random seed: `20260722`. Sample size per replicate: `6000` fires. Replicates per null: `12`.

## Interpretation

The easy feature-permutation null confirms that the engineered VASE features have strong covariance. More defensible nulls are stricter because they preserve duration, final size, monotonic cumulative growth, zero-growth frequency, or duration-specific empirical profiles. The key manuscript decision is whether observed fires are clearly more compact than these stricter alternatives.

If the observed-minus-null five-PC variance is small or if synthetic support overlaps the observed support, the paper should use "low-dimensional coordinate system" rather than "restricted subset of plausible trajectories."

## Null Hierarchy

| observed_cumvar_pc1_5 | observed_participation_ratio | observed_logdet_cov_pc1_5 | null_model | preserves | destroys | reps | cumvar_pc1_5_mean | cumvar_pc1_5_lo | cumvar_pc1_5_hi | participation_ratio_mean | dimension95_median | synthetic_logdet_cov_pc1_5_mean | synthetic_to_observed_median_mean | observed_to_synthetic_median_mean | observed_minus_null_cumvar | synthetic_minus_observed_logdet |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0.9632 | 1.5002 | 5.4077 | dirichlet duration and final area | final area and observation count; monotonic cumulative growth | empirical pulse/timing structure and daily-growth marginal distribution | 12 | 0.9445 | 0.9433 | 0.9455 | 1.6112 | 6.0000 | 6.3799 | 0.0000 | 0.0000 | 0.0187 | 0.9722 |
| 0.9632 | 1.5002 | 5.4077 | duration-bin empirical increments | duration-bin empirical daily-growth profiles and final area | fire-specific growth order and cross-feature pairing | 12 | 0.9470 | 0.9461 | 0.9481 | 1.5148 | 6.0000 | 4.4884 | 0.0000 | 0.0000 | 0.0162 | -0.9193 |
| 0.9632 | 1.5002 | 5.4077 | duration-bin mean profile | duration-bin average growth profile with weak noise | fire-specific pulse heterogeneity | 12 | 0.9687 | 0.9676 | 0.9696 | 1.3576 | 4.0000 | 2.5363 | 0.0000 | 0.0000 | -0.0055 | -2.8714 |
| 0.9632 | 1.5002 | 5.4077 | independent feature permutation | marginal distribution of each engineered feature | all covariance and developmental ordering | 12 | 0.4251 | 0.4242 | 0.4259 | 7.8641 | 33.0000 | -0.0034 | 3.0863 | 1.2657 | 0.5380 | -5.4111 |
| 0.9632 | 1.5002 | 5.4077 | shuffled daily growth order within fire | final area, duration, observed daily increments | temporal order of each fire's observed growth increments | 12 | 0.9496 | 0.9490 | 0.9501 | 1.5106 | 6.0000 | 5.7234 | 0.0000 | 0.0000 | 0.0136 | 0.3157 |
| 0.9632 | 1.5002 | 5.4077 | zero-preserving dirichlet | final area, observation count, and number of zero-growth days | empirical timing and increment sizes beyond zero frequency | 12 | 0.9445 | 0.9434 | 0.9451 | 1.6146 | 6.0000 | 6.4051 | 0.0000 | 0.0000 | 0.0187 | 0.9974 |

## Replicate Table

Full replicate results are written to `analysis/claim_audit_stats/null_model_replicates.csv`.
