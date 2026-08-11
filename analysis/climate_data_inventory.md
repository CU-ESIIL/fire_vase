# Climate Data Inventory

Generated: 2026-07-23T01:49:24.448582+00:00

## Population-wide daily centroid climate

Source: gridMET cached NetCDF files; variables are tmmx, tmmn, vpd, vs, pr, rmax, rmin, sph, fm100, fm1000, erc, bi, etr, pet, srad.
Spatial resolution: gridMET native 4-km grid.
Temporal resolution: daily. The processing manifest labels the component `gridmet-hourly-v0`, but the available table is daily and every slice has one daily value per variable.
Exposure basis: event centroid / nearest grid-cell extraction for each daily VASE slice.
Absolute or anomaly: absolute values in the source table; this revision also derives a region-month fire-season anomaly diagnostic from the observed fire population. It is not a true local climatological normal.
Date range: 2000-11-02 to 2021-05-01.
Fires with complete climate values: 237,235 of 278,569. Slice rows with climate values: 550,961 of 626,102.
Missingness pattern: 41,334 fires have missing cached climate values, reported as outside gridMET coverage or missing grid value in `processing_failures_climate.parquet`.

| Variable | Units | Non-null slice rows | Summary types in revision | Used in manuscript |
| --- | --- | --- | --- | --- |
| Maximum temperature | degrees C | 550,961 | daily slice, event mean, daily min/max, early/middle/late means, region-month anomaly, hot-day fraction | yes |
| Minimum temperature | degrees C | 550,961 | daily slice, event mean, daily min/max, early/middle/late means, region-month anomaly | yes |
| VPD | kPa | 550,961 | daily slice, event mean, daily min/max, early/middle/late means, region-month anomaly, high-VPD-day fraction | yes |
| Wind speed | m s-1 | 550,961 | daily slice, event mean, daily min/max, early/middle/late means, region-month anomaly, windy-day fraction | yes |
| Precipitation | mm d-1 | 550,961 | daily slice, event mean, daily min/max, early/middle/late means, region-month anomaly, wet-day fraction | yes |
| Maximum relative humidity | % | 550,961 | daily slice, event mean, daily min/max, early/middle/late means, region-month anomaly | yes |
| Minimum relative humidity | % | 550,961 | daily slice, event mean, daily min/max, early/middle/late means, region-month anomaly | yes |
| Specific humidity | kg kg-1 | 550,961 | daily slice, event mean, daily min/max, early/middle/late means, region-month anomaly | yes |
| 100-hour fuel moisture | % | 550,961 | daily slice, event mean, daily min/max, early/middle/late means, region-month anomaly | yes |
| 1000-hour fuel moisture | % | 550,961 | daily slice, event mean, daily min/max, early/middle/late means, region-month anomaly, dry-fuel-day fraction | yes |
| Energy release component | index | 550,961 | daily slice, event mean, daily min/max, early/middle/late means, region-month anomaly, high-ERC-day fraction | yes |
| Burning index | index | 550,961 | daily slice, event mean, daily min/max, early/middle/late means, region-month anomaly | yes |
| Reference evapotranspiration | mm d-1 | 550,961 | daily slice, event mean, daily min/max, early/middle/late means, region-month anomaly | yes |
| Potential evapotranspiration | mm d-1 | 550,961 | daily slice, event mean, daily min/max, early/middle/late means, region-month anomaly | yes |
| Solar radiation | W m-2 | 550,961 | daily slice, event mean, daily min/max, early/middle/late means, region-month anomaly | yes |

## Perimeter, active-burned-area, and perimeter-extension pilot

Source: `scratch/fire_vase_run_full/tables/vase_climate_exposures.parquet`, produced by `scratch/fire_vase_run_full/perimeter_climate_build_comprehensive_report.json`.
Fire count: 100. Rows: 1,095. Climate-available rows: 795.
Exposure bases present: active_burned_area, cumulative_burned_area, perimeter_extension.
Extension distances: 5000.0, 10000.0, 25000.0 m.
Variables are summarized by zone as mean/min/max/std where present, plus sampled cell count and exposure area.
Status: useful as a methods/perimeter-exposure product. If its fire count is lower than the centroid table, it remains a coverage limitation rather than the main inferential basis.

| exposure_zone | rows | fires | climate_available |
| --- | --- | --- | --- |
| active_burned_area | 219 | 100 | 0.726 |
| cumulative_burned_area | 219 | 100 | 0.726 |
| perimeter_extension | 657 | 100 | 0.726 |

## Variables still not available as population-wide analysis products

Wind direction, gusts, soil moisture, topography, vegetation, suppression, ignition cause, and true local seasonal normals were not found in the current population-wide Fire VASE tables. The current anomaly diagnostic is a region-month fire-population contrast, not a climatological normal.

## Current manuscript use

The new manuscript uses population-wide daily centroid gridMET temperature, VPD, wind, precipitation, relative humidity, specific humidity, fuel moisture, fire-danger indices, evapotranspiration, PET, and solar radiation; derived extreme-day fractions; early/middle/late exposure summaries; and a clearly labeled region-month anomaly diagnostic. Perimeter and active-burned-area climate are described according to the coverage actually present in the perimeter exposure table.
