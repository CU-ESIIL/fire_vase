# Vase Volumes & Arbitrary 3-D Subsets

> This page is kept for backward compatibility. See the updated [Vase Volumes guide](../vase_volumes.md) for the latest streaming-first examples and API notes.

Vase volumes let you describe arbitrary 3-D regions inside a cube using time-stamped 2-D polygons. A `VaseDefinition` lists cross-sections through `(x, y)`; lofting them across the cube's time dimension produces a 3-D hull. `build_vase_mask` converts that hull into a boolean mask over the cube grid so you can extract, visualize, and share just the voxels you care about.

## Concept: time-stamped polygons become 3-D hulls

- Cubes live in `(time, y, x)` (and optional `band`).
- A `VaseDefinition` is a set of `(time, polygon)` pairs defined in `(x, y)` space.
- Lofting/interpolating those polygons through time defines a 3-D "vase volume".
- `build_vase_mask` uses cube coordinates only—no full `.values`—to mark voxels that fall inside the vase at each time slice.

## Defining a vase

```python
from cubedynamics.vase import VaseDefinition, VaseSection
from shapely.geometry import Point

sections = []
for year, radius in [("2018-01-01", 1.0), ("2020-01-01", 1.5), ("2022-01-01", 1.2)]:
    poly = Point(0, 0).buffer(radius)
    sections.append(VaseSection(time=year, polygon=poly))

vase = VaseDefinition(sections, interp="nearest")
```

## Building a mask and extracting a cube

```python
import xarray as xr
from cubedynamics.vase import build_vase_mask

mask = build_vase_mask(cube, vase, time_dim="time", y_dim="y", x_dim="x")
vase_cube = cube.where(mask)
```

The mask matches the cube's `(time, y, x)` dimensions and carries a helpful `"vase_mask"` name and description attribute.

## Using verbs: `v.vase_mask` and `v.vase_extract`

```python
from cubedynamics import pipe, verbs as v

mask = pipe(cube) | v.vase_mask(vase)
vase_cube = pipe(cube) | v.vase_extract(vase)
```

`v.vase_mask` returns the boolean mask; `v.vase_extract` applies it so values outside the vase become `NaN`. Both verbs stream over time slices, keeping dask-backed cubes lazy.

## Using the grammar: `stat_vase` + `geom_vase_outline`

```python
from cubedynamics.plotting import CubePlot

p = (CubePlot(cube)
     .stat_vase(vase)
     .geom_cube()
     .geom_vase_outline(color="limegreen", alpha=0.6)
     # add scales, coord_cube, theme, captions, facets, ...
)

p  # in a notebook
```

- `stat_vase` uses `build_vase_mask` and stores both the masked cube and the mask.
- `geom_vase_outline` tells the viewer to tint cube faces wherever the vase touches each slice.
- This sits naturally inside the grammar: **Data → StatVase → GeomCube + GeomVaseOutline → Scales → CoordCube → Theme**.

See the current [Fire VASE capability page](../capabilities/fire-vase.md) for the
project-level VASE workflow and examples.

## Streaming-first behavior

`build_vase_mask` iterates over time using coordinate arrays only—no eager `.values`—so it works on `VirtualCube`, dask-backed cubes, and large archives. The mask slices are reused by the viewer to tint faces without extra full-volume loads.

## Scientific 3-D visualization helpers

The cube viewer handles quick overlays; for research-grade 3-D work, `cubedynamics.vase_viz` offers optional PyVista/Trimesh helpers:

- `extract_vase_points(cube, mask, ...)` gathers coordinates/values for voxels inside the vase.
- `vase_scatter_plot(cube, mask, ...)` renders a 3-D scatter plot with PyVista.
- `vase_to_mesh(vase, ...)` (optional) sweeps polygons into a mesh when `trimesh` is available.
- `vase_scatter_with_hull(...)` combines scatter points with a translucent hull when both PyVista and Trimesh are installed.

These tools use the **same mask** as the grammar/cube viewer but are intentionally heavier and optional.

## Keep the simple path

Nothing changes for quicklooks: `pipe(cube) | v.plot()` remains the default. Vase volumes are an **advanced** layer you can add when you need arbitrary 3-D subsets:

```python
pipe(cube) | v.vase_extract(vase) | v.plot()
# or
CubePlot(cube).stat_vase(vase).geom_cube().geom_vase_outline()
```
