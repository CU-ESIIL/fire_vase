# State-Dependent Climate Report

Response: next-day growth, modeled as `log(1 + next daily burned area km2)`.
Climate predictors: core models use daily maximum temperature, minimum temperature, VPD, and wind speed; expanded models add precipitation, humidity, fuel moisture, fire-danger indices, evapotranspiration, PET, and solar radiation where available.
Leakage controls: state predictors use only elapsed day, current growth, current cumulative area, and current acceleration. They do not use final duration, final area fraction, or future VASE coordinates.

| predictor_set | block | r2 | n |
| --- | --- | --- | --- |
| core climate only | random_fire | 0.0477 | 313726.0000 |
| core climate only | region_block | 0.0251 | 313726.0000 |
| core climate only | region_year_hash | 0.0451 | 313726.0000 |
| core climate only | year_block | 0.0451 | 313726.0000 |
| core climate plus state | random_fire | 0.3394 | 313726.0000 |
| core climate plus state | region_block | 0.3206 | 313726.0000 |
| core climate plus state | region_year_hash | 0.3382 | 313726.0000 |
| core climate plus state | year_block | 0.3388 | 313726.0000 |
| core climate-state interaction | random_fire | 0.3544 | 313726.0000 |
| core climate-state interaction | region_block | 0.3426 | 313726.0000 |
| core climate-state interaction | region_year_hash | 0.3535 | 313726.0000 |
| core climate-state interaction | year_block | 0.3533 | 313726.0000 |
| expanded climate only | random_fire | 0.0928 | 313726.0000 |
| expanded climate only | region_block | 0.0793 | 313726.0000 |
| expanded climate only | region_year_hash | 0.0905 | 313726.0000 |
| expanded climate only | year_block | 0.0905 | 313726.0000 |
| expanded climate plus state | random_fire | 0.3466 | 313726.0000 |
| expanded climate plus state | region_block | 0.3301 | 313726.0000 |
| expanded climate plus state | region_year_hash | 0.3454 | 313726.0000 |
| expanded climate plus state | year_block | 0.3459 | 313726.0000 |
| state only | random_fire | 0.3313 | 313726.0000 |
| state only | region_block | 0.3113 | 313726.0000 |
| state only | region_year_hash | 0.3302 | 313726.0000 |
| state only | year_block | 0.3309 | 313726.0000 |

Best conservative state model: **core climate-state interaction** (0.353 median blocked R2).
Climate-state interactions survive blocking by the predeclared +0.01 R2 margin: **True**.

Interpretation: developmental state improves interpretation and near-term prediction relative to climate alone. Interaction terms should be treated as suggestive unless they improve blocked transfer beyond the additive climate-plus-state model.
