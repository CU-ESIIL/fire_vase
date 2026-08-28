# Legacy dependencies and corrected replacements

This audit records the pre-v2 pathway, not an endorsement of legacy labels.
The exact v1 values and outputs are retained under `archive/comparison_v1/`.

| Issue | Source-code pathway | Affected products | V2 replacement |
| --- | --- | --- | --- |
| Peak mislabeled as mean | `scripts/fire_vase_lakehouse_pilot.py` originally wrote area/duration to `peak_growth_km2_per_hour`; `fire_vase_developmental_morphology_analysis.py::read_tables` multiplied by 24, and `build_features_and_events` used it instead of its locally computed maximum | `fire_traits.parquet`; `developmental_morphospace_features.parquet`; `log_peak_growth_km2_per_day` loading in legacy PCA; every downstream PC response, medoid, morphospace figure, stage prediction and matching distance using those PCs | Pilot writes a catalog mean; `growth_summary` computes observed daily peak. Primary v2 PCA excludes all absolute rates. Both peak and mean are in the per-event audit. |
| Probability denominator | Legacy `build_features_and_events` divided growth by max(catalog area, reconstructed cumulative area) | Entropy and interpolated growth fractions, profile features, PCA and response models | Divide by sum of observed increments; separately report catalog/reconstructed totals. Current totals agree, so entropy is unchanged within tolerance. |
| Count-only multi-pulse branch | Legacy `_assign_category` accepts `pulse_count >= 3 or observation_count >= 6` | Neighborhood prevalence, representative selection and neighborhood-colored figures | Prominent local maxima; complete priority-ordered rules and branch counts in `neighborhood_rules.csv`. |
| Observation index substituted for time | Legacy interpolation/profile functions use `linspace` or `slice_index/max`; state builder shifts after weather filtering | Shape features over gappy histories, stage targets, claimed subsequent-day models | Consecutive primary histories; separate observation-time sensitivity; exact dated responses before weather filtering. |
| Median-centered PCA | Legacy `morphospace.robust_standardize` subtracts medians before SVD | Legacy variance claims and PC-based analyses | Ordinary mean-centered covariance PCA, with fold-specific fits for predictive outcomes. |
| Non-nested meteorological sets | Legacy `run_event_models`: core includes `max_vpd_kpa`, comprehensive does not; independent dropna per fit | The 0.349 cross-response headline and “comprehensive does not improve” conclusion | Explicit nested sets and one cohort, all responses/blocks/penalties exported; duration-as-predictor cannot predict itself. |
| Final-geometry exposure | `fire_vase_build_climate_tables.py::read_events` computes final-event centroids | Legacy daily centroid exposures and prospective-availability wording | `fire_vase_v2_inputs.day_t_weather` computes projected centroids from only day-t burned polygons and samples exact dates within grid bounds. Original exposure remains only a labeled comparison. |
| Adversarial mismatch | Legacy developmental matching chooses `argmax(other_dists)` among nearest candidates; `fire_vase_climate_revision.py::figure_5` also maximizes other-space distance | Matched-pair claims and example displays | Unique caliper-constrained nearest-neighbor graph pairs; examples nearest median mismatch. No two-by-two display. |

Legacy PCA also contained final area, duration, observation count, slenderness,
and redundant width/growth interpolants. V2's primary features are only 20
mass-conserving allocation bins; traits-only, unchanged legacy-space, short,
long and gappy-history sensitivities are separately exported. All figures and
the current manuscript are rebuilt from v2 outputs, not manually relabeled v1 PCs.
