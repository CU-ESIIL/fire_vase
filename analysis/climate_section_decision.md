# Climate Section Decision

## Recommendation

**B. Keep one concise climate figure as proof of concept.**

Climate remains useful because it shows that the geometry-first morphospace can carry external covariates. It should not be framed as a central mechanistic discovery until centroid attribution is replaced by active-area/perimeter exposure, richer covariates, local-normal anomalies, and stricter spatial-temporal blocking.

## Reasons

- Current climate attribution is daily centroid gridMET, not active edge, newly burned area, full perimeter, or perimeter extension.
- Region-blocked validation is the conservative reference and is weaker than random validation.
- Climate predicts PC1 partly because PC1 includes scale/profile structure that can be geographically and seasonally patterned.
- The current "coupling" language should be replaced by "held-out linear association" or "recoverability."

## Current Held-Out Climate Results

| model | fold_kind | target | n_folds | mean_r2 | lo_r2 | hi_r2 | n_test_total |
| --- | --- | --- | --- | --- | --- | --- | --- |
| climate predicts morphology | random | morph_pc1 | 5 | 0.5123 | 0.5083 | 0.5158 | 237235 |
| climate predicts morphology | random | morph_pc2 | 5 | 0.0616 | 0.0588 | 0.0655 | 237235 |
| climate predicts morphology | random | morph_pc3 | 5 | 0.0008 | 0.0004 | 0.0011 | 237235 |
| climate predicts morphology | region | morph_pc1 | 4 | 0.4738 | 0.4350 | 0.5307 | 237235 |
| climate predicts morphology | region | morph_pc2 | 4 | 0.0555 | 0.0113 | 0.1034 | 237235 |
| climate predicts morphology | region | morph_pc3 | 4 | 0.0002 | -0.0016 | 0.0011 | 237235 |
| climate predicts morphology | year_block | morph_pc1 | 5 | 0.5110 | 0.4784 | 0.5551 | 237235 |
| climate predicts morphology | year_block | morph_pc2 | 5 | 0.0602 | 0.0451 | 0.0746 | 237235 |
| climate predicts morphology | year_block | morph_pc3 | 5 | 0.0005 | -0.0011 | 0.0013 | 237235 |
| morphology predicts climate | random | max_vpd_kpa | 5 | 0.0715 | 0.0692 | 0.0743 | 237235 |
| morphology predicts climate | random | mean_maximum_temperature_c | 5 | 0.0019 | 0.0014 | 0.0023 | 237235 |
| morphology predicts climate | random | mean_minimum_temperature_c | 5 | 0.0009 | 0.0004 | 0.0012 | 237235 |
| morphology predicts climate | random | mean_vpd_kpa | 5 | 0.0044 | 0.0039 | 0.0050 | 237235 |
| morphology predicts climate | random | mean_wind_speed_m_s | 5 | 0.0006 | 0.0005 | 0.0009 | 237235 |
| morphology predicts climate | random | wind_present_fraction | 0 | NA | NA | NA | 237235 |
| morphology predicts climate | region | max_vpd_kpa | 4 | -0.1687 | -0.6480 | 0.0277 | 237235 |
| morphology predicts climate | region | mean_maximum_temperature_c | 4 | -0.0290 | -0.0432 | -0.0112 | 237235 |
| morphology predicts climate | region | mean_minimum_temperature_c | 4 | -0.1290 | -0.2662 | -0.0500 | 237235 |
| morphology predicts climate | region | mean_vpd_kpa | 4 | -0.2007 | -0.5941 | -0.0342 | 237235 |
| morphology predicts climate | region | mean_wind_speed_m_s | 4 | -0.1380 | -0.2995 | -0.0097 | 237235 |
| morphology predicts climate | region | wind_present_fraction | 0 | NA | NA | NA | 237235 |
| morphology predicts climate | year_block | max_vpd_kpa | 5 | 0.0470 | -0.0219 | 0.1000 | 237235 |
| morphology predicts climate | year_block | mean_maximum_temperature_c | 5 | -0.0167 | -0.0400 | 0.0013 | 237235 |
| morphology predicts climate | year_block | mean_minimum_temperature_c | 5 | -0.0074 | -0.0176 | 0.0002 | 237235 |
| morphology predicts climate | year_block | mean_vpd_kpa | 5 | -0.0251 | -0.0843 | 0.0019 | 237235 |
| morphology predicts climate | year_block | mean_wind_speed_m_s | 5 | -0.0004 | -0.0029 | 0.0008 | 237235 |
| morphology predicts climate | year_block | wind_present_fraction | 0 | NA | NA | NA | 237235 |
