# Vase Volumes: Streaming 3-D Subsets

Vases describe analytic volumes in `(time, y, x)` by lofting time-stamped polygons across the cube. They pair naturally with the streaming viewer so you can mask voxels, visualize outlines, and keep data lazy.

## Concepts

- Cubes live in `(time, y, x [, band])`.
- A `VaseSection` stores a time stamp and a polygon in `(x, y)` space.
- A `VaseDefinition` is an ordered list of sections plus an interpolation rule (`nearest` or `linear`). Lofting/interpolating those polygons through time defines a 3-D hull.
- `attrs["vase"]` carries the definition so viewers and stats can auto-detect it.

## Core API

- `cubedynamics.vase.VaseSection(time, polygon)`
- `cubedynamics.vase.VaseDefinition(sections, interp="nearest")`
- `v.vase_extract(cube, vase, fill_value=np.nan, ...)` masks outside the vase and attaches `attrs["vase"] = vase`.
- `CubePlot.stat_vase(vase)` injects the mask into the grammar; `CubePlot.geom_vase_outline(...)` tints faces where the vase touches.
- `v.plot()` detects `attrs["vase"]` and overlays the outline automatically.

## Quick vase plot with `v.vase()`

Once you have a `VaseDefinition` on a cube (via `attrs["vase"]` or the `vase=` argument), you can produce a vase-focused 3-D view in one step:

```python
from cubedynamics import pipe, verbs as v

# Attach vase definition (or pass `vase=` directly)
ndvi.attrs["vase"] = vase_def

# Vase-focused plot with optional viewer tweaks
pipe(ndvi) | v.vase(elev=45, azim=35)
```

## Example: NDVI inside a vase

```python
import numpy as np
import shapely.geometry as geom
from cubedynamics import pipe, verbs as v
from cubedynamics.plotting import CubePlot
from cubedynamics.vase import VaseSection, VaseDefinition

cube = ndvi  # DataArray (time, y, x)

t0, t1 = cube.time.values[[0, -1]]
y_center = float(cube.y.mean())
x_center = float(cube.x.mean())
radius = 0.2 * min(float(cube.x.max()-cube.x.min()),
                  float(cube.y.max()-cube.y.min()))

poly_t0 = geom.Point(x_center, y_center).buffer(radius)
poly_t1 = geom.Point(x_center, y_center).buffer(1.5 * radius)

sections = [VaseSection(time=t0, polygon=poly_t0),
            VaseSection(time=t1, polygon=poly_t1)]
vase = VaseDefinition(sections=sections, interp="nearest")

# Mask outside the vase and persist the definition
vase_cube = v.vase_extract(cube, vase)
assert "vase" in vase_cube.attrs

# High-level viewer (adds vase outline automatically)
pipe(vase_cube) | v.plot(title="NDVI inside vase")

# Grammar-of-graphics control
p = (CubePlot(cube)
     .stat_vase(vase)
     .geom_cube()
     .geom_vase_outline(color="limegreen", alpha=0.6))
p
```

## Demo: stacked-polygon vase

For quick experiments, you can use the built-in demo helper to construct a
time-varying vase made of stacked polygons:

```python
import cubedynamics as cd
from cubedynamics import pipe, verbs as v

ndvi = cd.ndvi(
    lat=40.0,
    lon=-105.25,
    start="2023-01-01",
    end="2024-12-31",
)

# Build a simple tapered vase over time
vase_def = cd.demo.stacked_polygon_vase(ndvi, n_sections=4, shrink=0.1)

# Vase-focused 3D plot
pipe(ndvi) | v.vase(vase=vase_def)
```

This uses only geometric information from the cube (its spatial extent and time
axis) to create a time-varying polygon tube. Later, you can replace
``cd.demo.stacked_polygon_vase(...)`` with a data-driven vase constructed from
your own polygons or AOI definitions.

## Quick demo with `v.vase_demo()`

For a one-liner demo, you can let CubeDynamics build a stacked-polygon vase
for you and plot it in one go:

```python
import cubedynamics as cd
from cubedynamics import pipe, verbs as v

ndvi = cd.ndvi(
    lat=40.0,
    lon=-105.25,
    start="2023-01-01",
    end="2024-12-31",
)

pipe(ndvi) | v.vase_demo(n_sections=4, shrink=0.1)
```

This uses ``cd.demo.stacked_polygon_vase(...)`` under the hood to construct a
simple geometric vase volume, then passes it into ``v.vase()`` to render the
vase-focused 3D cube plot.

## Streaming-first behavior

`v.vase_extract` and `CubePlot.stat_vase` iterate over time slices using coordinates only, so they work with dask-backed cubes and `VirtualCube` streams without ever calling `.values` on the full array. The streaming renderer reuses those masks to tint faces slice by slice.

## Tips

- Use `fill_value=np.nan` (default) to clearly mask voxels outside the vase.
- Keep polygons compact relative to the domain for crisp outlines with `tight_axes=True`.
- For advanced 3-D analysis, `cubedynamics.vase_viz` offers PyVista/Trimesh helpers that reuse the same mask.
