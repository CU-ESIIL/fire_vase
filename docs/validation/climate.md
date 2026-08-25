# GridMET Time And Polygon Attribution

The climate module audits two different questions.

## Is The Correct Day In The Table?

For every FIRED observation date in the sampled event, the module independently
selects the nearest GridMET cell at the equal-area event centroid, applies the
same Kelvin-to-Celsius conversion used by the lake builder, and compares the
result with `vase_slices.parquet`.

The published sample has 29 FIRED/table rows. The date sets are identical,
every date is present in GridMET, and the maximum absolute value residual is
zero.

## How Is A Polygon Assigned Climate?

Three inspectable methods are calculated for every daily polygon:

- nearest cell to the daily polygon centroid;
- mean of cells whose centers fall inside the polygon;
- mean weighted by the equal-area square meters of every GridMET cell that
  overlaps the polygon.

```python
from cubedynamics.validation import ValidationPaths
from cubedynamics.validation.climate import run_climate_validation

paths = ValidationPaths.discover()
result = run_climate_validation(paths, fire_id=20657, variable="tmmx")
```

![GridMET time and spatial attribution](../assets/validation/climate.png)

The current lakehouse contract remains
`event_centroid_nearest_grid_cell`. Fractional overlap is reported as an
explicit sensitivity analysis; it is never substituted silently. For this
event, daily polygons overlap between 1 and 15 GridMET cells, and the largest
absolute difference between overlap-weighted and centroid temperature is
1.64 °C. That difference is exactly why both methods are made reviewable.
