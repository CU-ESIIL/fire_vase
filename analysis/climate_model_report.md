# Climate Model Report

Models are exploratory regularized linear baselines. They are descriptive/predictive association tests, not causal estimates.

## Predictor sets

- Core event means: mean maximum temperature, mean minimum temperature, mean VPD, maximum VPD, and mean wind speed.
- Moisture and humidity: precipitation, maximum and minimum relative humidity, specific humidity, and 100-hour and 1000-hour fuel moisture.
- Fire danger and energy: energy release component, burning index, reference evapotranspiration, potential evapotranspiration, and solar radiation.
- Comprehensive event means: the union of core climate, moisture/humidity, and fire-danger/energy means.
- Region-season anomalies: observed value minus region-month fire-season median from the current fire population; not a true local climatological normal.
- Extreme days: fraction of daily slices above high-temperature, high-VPD, windy, wet-day, dry-fuel, or high-ERC thresholds where available.
- Time-resolved exposure: early, middle, and late means for core and selected expanded climate variables plus extreme-day fractions.

## Blocked performance

| predictor_set | block | median_r2 | min_r2 | max_r2 | n |
| --- | --- | --- | --- | --- | --- |
| comprehensive event means | random_fire | 0.0034 | 0.0015 | 0.0247 | 237235.0000 |
| comprehensive event means | region_block | -0.0029 | -0.0056 | 0.0109 | 237235.0000 |
| comprehensive event means | region_year_hash | 0.0028 | 0.0012 | 0.0231 | 237235.0000 |
| comprehensive event means | year_block | 0.0028 | 0.0012 | 0.0232 | 237235.0000 |
| core event means | random_fire | 0.3628 | 0.1572 | 0.5596 | 237235.0000 |
| core event means | region_block | 0.3448 | 0.1459 | 0.5312 | 237235.0000 |
| core event means | region_year_hash | 0.3620 | 0.1567 | 0.5587 | 237235.0000 |
| core event means | year_block | 0.3609 | 0.1560 | 0.5570 | 237235.0000 |
| extreme days | random_fire | 0.0005 | 0.0001 | 0.0220 | 237235.0000 |
| extreme days | region_block | -0.0023 | -0.0048 | 0.0074 | 237235.0000 |
| extreme days | region_year_hash | 0.0003 | -0.0001 | 0.0211 | 237235.0000 |
| extreme days | year_block | 0.0004 | 0.0000 | 0.0214 | 237235.0000 |
| fire danger and energy | random_fire | 0.0007 | 0.0005 | 0.0177 | 237235.0000 |
| fire danger and energy | region_block | -0.0019 | -0.0034 | 0.0084 | 237235.0000 |
| fire danger and energy | region_year_hash | 0.0004 | 0.0004 | 0.0163 | 237235.0000 |
| fire danger and energy | year_block | 0.0005 | 0.0004 | 0.0169 | 237235.0000 |
| moisture and humidity | random_fire | 0.0018 | 0.0004 | 0.0167 | 237235.0000 |
| moisture and humidity | region_block | -0.0019 | -0.0042 | 0.0056 | 237235.0000 |
| moisture and humidity | region_year_hash | 0.0015 | 0.0003 | 0.0156 | 237235.0000 |
| moisture and humidity | year_block | 0.0016 | 0.0003 | 0.0159 | 237235.0000 |
| region-season anomalies | random_fire | 0.0030 | 0.0012 | 0.0149 | 237235.0000 |
| region-season anomalies | region_block | -0.0002 | -0.0008 | 0.0013 | 237235.0000 |
| region-season anomalies | region_year_hash | 0.0027 | 0.0010 | 0.0138 | 237235.0000 |
| region-season anomalies | year_block | 0.0028 | 0.0010 | 0.0137 | 237235.0000 |
| time-resolved exposure | random_fire | 0.0229 | 0.0032 | 0.1115 | 63840.0000 |
| time-resolved exposure | region_block | 0.0173 | 0.0016 | 0.0935 | 63840.0000 |
| time-resolved exposure | region_year_hash | 0.0217 | 0.0031 | 0.1088 | 63840.0000 |
| time-resolved exposure | year_block | 0.0223 | 0.0029 | 0.1089 | 63840.0000 |

Best transferable event-level representation by median conservative blocked R2: **core event means** (0.349).
Anomalies outperform raw event means: **False**.
Comprehensive event means outperform core event means: **False**.
Temporally resolved exposure outperforms event means: **False**.

Interpretation: climate associations are real enough to shift developmental-neighborhood prevalence and response gradients, but held-out transfer is weak. The manuscript should say climate redistributes developmental opportunity, not that climate uniquely predicts form.
