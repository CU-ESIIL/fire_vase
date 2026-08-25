# FIRED Geometry And Hull Sensitivity

The geometry module makes the polygon-to-hull steps visible:

1. Select all daily FIRED polygons for one event.
2. Reproject them to the CONUS Albers equal-area CRS (EPSG:5070).
3. Simplify each daily polygon while preserving topology.
4. Sample each exterior at equal arc-length steps.
5. Calculate directional support radii around the centered polygon.
6. Join adjacent daily support profiles with a triangulated ruled surface.

The operational simplification range is 0–125 m. The 500 m and 1000 m values
are intentional stress tests that show when boundary detail and area begin to
be discarded too aggressively.

```python
from cubedynamics.validation import ValidationPaths
from cubedynamics.validation.geometry import run_geometry_validation

paths = ValidationPaths.discover()
result = run_geometry_validation(
    paths,
    fire_id=20657,
    tolerances_m=(0, 125, 500, 1000),
    operational_max_tolerance_m=125,
    n_theta=96,
)
```

![FIRED simplification and hull sensitivity](../assets/validation/geometry.png)

At 125 m, the sampled event changes cumulative area by only 0.254%. The two
aggressive stress tests visibly change area by much more. The angular support
panel shows the precise averaging performed by the hull: concavities and
high-frequency boundary teeth are reduced to a directional support function,
then the transition between daily profiles is linear along each hull wall.

The module writes both `polygon_simplification_metrics.csv` and
`hull_sensitivity_metrics.csv`, so tolerance and angular-resolution decisions
can be reviewed numerically as well as visually.

Continue to the [three-dimensional hull audit](hull3d.md) to see these stages
stacked in time and compare alternative temporal averaging decisions.
