# Climate Revision Changelog

Generated: 2026-07-23T01:49:47.909965+00:00

## Added or elevated

- Population-wide daily centroid gridMET maximum temperature, minimum temperature, VPD, wind speed, precipitation, relative humidity, specific humidity, fuel moisture, fire-danger indices, evapotranspiration, PET, and solar radiation are now the main climate basis.
- Extreme-day fractions for hot, high-VPD, windy, wet, dry-fuel, and high-ERC days were derived from population daily-slice thresholds.
- Early, middle, and late developmental-time climate summaries were added.
- Region-month fire-season anomaly diagnostics were added and clearly labeled as observed-population diagnostics, not true local normals.
- Leakage-safe state-dependent next-day growth models were added.
- Empirical composite VASEs and difference VASEs were added to the main figure grammar.

## Removed or weakened

- The manuscript no longer treats the low-dimensional coordinate system as the final discovery.
- Claims that climate determines fire form were weakened to probabilistic opportunity language.
- Perimeter, active-edge, and perimeter-extension climate are not used as main evidence unless their coverage approaches the centroid table; the current manuscript labels the perimeter product by actual coverage.
- Wind presence was removed from substantive interpretation because the complete event table has no variation in `wind_present_fraction`.

## Moved to supplement

- Defensive PCA and null-model diagnostics.
- Full feature-ablation and prediction audits.
- Perimeter/active-edge climate extraction appears as a coverage/methods supplement.

## Model summary

- Best transferable event-level climate representation: core event means (0.349 median conservative blocked R2).
- Best state model: core climate-state interaction (0.353 median conservative blocked R2).
- Anomalies outperform raw event means: False.
- Comprehensive event means outperform core event means: False.
- Temporally resolved exposure outperforms event means: False.
- Climate-state interactions survive blocking: True.

## Analyses that could not be completed from current data

- Population-wide active-edge, newly burned area, and perimeter-extension climate attribution.
- True local climate anomalies relative to independent long-term normals.
- Soil moisture, topography, vegetation, suppression, ignition cause, wind direction, or gust analyses.
