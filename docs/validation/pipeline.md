# Pipe Grammar And Streaming Backend

This module opens a small `(time, lat, lon)` view from the packaged annual
GridMET NetCDF without loading the full year. It applies the same CubeDynamics
z-score verb two ways:

```python
from cubedynamics import pipe
from cubedynamics import verbs as v

direct = v.zscore(dim="time")(cube)
piped = (pipe(cube) | v.zscore(dim="time")).unwrap()
residual = direct - piped
```

Only the small QA subset is computed. The module records chunk metadata before
and after the verb, verifies that a no-op `pipe(cube).unwrap()` returns the same
object, and requires a zero maximum absolute residual.

```python
from cubedynamics.validation import ValidationPaths
from cubedynamics.validation.pipeline import run_pipeline_validation

paths = ValidationPaths.discover()
result = run_pipeline_validation(paths, fire_id=20657, variable="tmmx")
result.metrics
```

![Pipe grammar and backend equivalence](../assets/validation/pipeline.png)

For this published run, the sampled cube has 38 daily steps over 10 by 13
GridMET cells. Direct and pipe graphs were identical (`max |residual| = 0`),
and both remained Dask-backed until the comparison was requested.

The backend shown here is the one used to build the lake tables: chunked annual
GridMET NetCDF. The separate external module then checks its raw packed values
against the NCAR/GDEX mirror.
