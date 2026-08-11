# Synthetic FireHull Recipe

This recipe shows the intended fire/VASE workflow without live FIRED downloads.

```python
import numpy as np
import pandas as pd
import xarray as xr

from cubedynamics.fire_time_hull import FireEventDaily

event = FireEventDaily.example()
hull = event.to_hull(n_ring_samples=24, n_theta=16)

times = pd.date_range("2020-07-01", periods=3, freq="D")
y = np.linspace(39.95, 40.30, 8)
x = np.linspace(-105.15, -104.80, 8)
data = np.stack(
    [
        np.full((len(y), len(x)), 2.0),
        np.full((len(y), len(x)), 6.0),
        np.full((len(y), len(x)), 11.0),
    ],
    axis=0,
)
cube = xr.DataArray(
    data,
    coords={"time": times, "y": y, "x": x},
    dims=("time", "y", "x"),
    name="vpd",
    attrs={"epsg": 4326},
)

hull_with_env = hull.attach_environment(cube, variables=["vpd"])
mask = hull.to_cube(cube)
fig = hull_with_env.plot(color="vpd")

print(hull.metrics())
print(mask.shape)
fig.show()
```

What this demonstrates:

- `FireEventDaily.example()` provides a tiny synthetic event
- `event.to_hull()` creates a canonical `FireHull`
- `attach_environment()` adds the first environmental attribution layer
- `to_cube(template)` returns a boolean occupancy cube aligned to the input grid
- `plot(color="vpd")` uses the attached environmental summary

Current limitation:

- `attach_environment()` currently stores per-day attribution summaries, not a full local environmental field on each hull element.
