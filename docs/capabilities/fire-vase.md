# Fire VASE / FireHull

CubeDynamics treats FIRED fire events as spatiotemporal objects, not just a list of polygons or a one-off plot. The fire/VASE workflow turns daily perimeters into a time-stacked hull that can participate in the same cube-centered grammar used elsewhere in the library.

## Core objects

### `FireEventDaily`

`FireEventDaily` is the canonical daily fire event object.

It stores:

- `event_id`
- `gdf` with daily perimeter geometry
- `t0` / `t1`
- `centroid_lat` / `centroid_lon`

Useful entry points:

```python
from cubedynamics.fire_time_hull import FireEventDaily

event = FireEventDaily.example()
event = FireEventDaily.from_fired(fired_daily, event_id=12345)
```

### `FireHull`

`FireHull` is the canonical fire-time hull / VASE object.

It stores triangulated geometry and time metadata:

- `verts_km`
- `tris`
- `t_days_vert`
- `t_norm_vert`
- `metrics`

It exposes object methods aligned with CubeDynamics design principles:

```python
hull = event.to_hull()
hull.metrics()
hull.to_mesh()
hull.to_cube(template_cube)
hull.attach_environment(cube, variables=["vpd"])
hull.plot(color="vpd")
```

`TimeHull` remains available as a compatibility alias, but `FireHull` is the preferred public name going forward.

## Minimal runnable example

```python
from cubedynamics.fire_time_hull import FireEventDaily

event = FireEventDaily.example()
hull = event.to_hull(n_ring_samples=24, n_theta=16)

print(hull.metrics())
mesh = hull.to_mesh()
print(mesh["verts_km"].shape, mesh["tris"].shape)
```

For a complete lightweight example that does not require live FIRED downloads, see [Synthetic fire/VASE recipe](../recipes/fire_vase_synthetic.md).

## Interactive example

This embedded Plotly VASE uses a real FIRED event paired with streamed gridMET
maximum temperature. Rotate the hull to inspect how the event footprint changes
through time and how daily temperature bands are painted across the surface.

<div class="interactive-embed">
  <iframe
    src="/fire_vase/assets/figures/fire_vase_gridmet_interactive.html"
    title="Interactive fire VASE with gridMET temperature"
    loading="lazy"
  ></iframe>
  <p class="interactive-embed__fallback">
    If the interactive VASE doesn’t load,
    <a href="/fire_vase/assets/figures/fire_vase_gridmet_interactive.html" target="_blank" rel="noopener">open it in a new tab</a>.
  </p>
</div>

Recreate the embedded output locally:

```bash
python examples/real_fire_vase_gridmet_smoke.py \
  --output-dir artifacts/fire-vase-gridmet-real \
  --variable tmmx \
  --diagnostic-variables tmmx tmmn vpd

cp artifacts/fire-vase-gridmet-real/real_fire_vase_gridmet_interactive.html \
  docs/assets/figures/fire_vase_gridmet_interactive.html

cp artifacts/fire-vase-gridmet-real/real_fire_vase_gridmet_diagnostic.png \
  docs/assets/figures/fire_vase_gridmet_diagnostic.png
```

The first command downloads/caches FIRED event layers under the artifact
directory and streams the gridMET climate cube for the selected event window.
It also writes `real_fire_vase_gridmet_diagnostic.png`, a static panel with
VASE projections, climate traces, inside/outside samples, and hull metrics.
The second command is only needed when refreshing the website copy.

## Prescribed-burn VASE panel example

The multi-event VASE panel uses the same single-event fire VASE workflow, then
lays the successful prescribed burns into a shared Plotly scene grid. This
sample is synthetic so the website can be rebuilt without downloading FIRED or
gridMET data, but it exercises the public `v.fire_vase_panel(...)` verb.

<div class="interactive-embed">
  <iframe
    src="/fire_vase/assets/figures/fire_vase_panel_sample.html"
    title="Prescribed-burn VASE panel sample"
    loading="lazy"
  ></iframe>
  <p class="interactive-embed__fallback">
    If the VASE panel doesn’t load,
    <a href="/fire_vase/assets/figures/fire_vase_panel_sample.html" target="_blank" rel="noopener">open it in a new tab</a>.
  </p>
</div>

Recreate the embedded panel locally:

```bash
python examples/fire_vase_panel_demo.py \
  --output docs/assets/figures/fire_vase_panel_sample.html
```

The example script builds synthetic prescribed-burn perimeters and a synthetic
temperature cube, then runs:

```python
from cubedynamics import pipe, verbs as v

panel = (
    pipe(climate_cube)
    | v.fire_vase_panel(
        fired_daily=fired_daily,
        fired_events=fired_events,
        prescribed_column="fire_type",
        prescribed_values=("prescribed burn",),
        climate_variable="tmmx",
        max_events=4,
        columns=2,
        n_ring_samples=32,
        n_theta=32,
    )
).unwrap()

panel["fig_panel"].write_html("fire_vase_panel_sample.html")
panel["records"]
panel["failures"]
```

## Pipe verbs

### `v.fire_plot(...)`

`fire_plot` remains the single-event fire VASE verb. It accepts either an
already-open climate cube through the pipe or a climate-loading configuration
and returns the event, hull, climate cube, summary table, and static/interactive
figures.

```python
from cubedynamics import pipe, verbs as v

result = (
    pipe(gridmet_cube)
    | v.fire_plot(
        fired_event=event,
        climate_variable="tmmx",
        prefer_streaming=True,
    )
).unwrap()
```

### `v.fire_vase_panel(...)`

`fire_vase_panel` is the multi-event verb for prescribed-burn panels. It keeps
`fire_plot` intact for one event, then runs that same VASE construction across a
set of prescribed events and assembles the results into `fig_panel`.

Prescribed events can be supplied directly with `event_ids`, selected from a
known column with `prescribed_column`/`prescribed_values`, or discovered from
text-like FIRED attributes containing prescribed-burn labels.

```python
panel = (
    pipe(gridmet_cube)
    | v.fire_vase_panel(
        fired_daily=fired_daily,
        fired_events=fired_events,
        prescribed_column="fire_type",
        prescribed_values=("prescribed", "rx", "planned"),
        max_events=12,
    )
).unwrap()

panel["fig_panel"]
panel["records"]
panel["failures"]
```

For real runs where each burn needs its own climate pull, pass a
`climate_loader(event)` callback or set `load_climate=True` with the same
climate options used by `fire_plot`.

## Metrics available now

Stable metric names currently include:

- `duration_days`
- `scale_km`
- `footprint_area_peak_km2`
- `footprint_area_final_km2`
- `hull_volume_km2_days`
- `hull_surface_km_day`

Legacy aliases retained for compatibility:

- `days`
- `volume_km2_days`
- `surface_km_day`

These metrics are geometric summaries of the hull. They are not yet a complete ecological or dynamical taxonomy.

## Environmental attribution

The scientific direction is:

```python
hull + environment -> explanatory fire manifold
```

The current first implementation is `FireHull.attach_environment(...)`, which stores per-variable `HullClimateSummary` objects keyed by variable name:

```python
hull_with_env = hull.attach_environment(cube, variables=["vpd"], method="nearest")
fig = hull_with_env.plot(color="vpd")
```

This is intentionally modest but now mesh-aware. It stores:

- the original summary-level `HullClimateSummary`
- per-layer values aligned to hull time slices
- per-vertex values aligned explicitly to the mesh

It does not yet store a fully local `(x, y, t)` field sampled independently at every hull vertex.

## Cube compatibility

`FireHull.to_cube(template_cube)` returns a boolean occupancy cube aligned to a supplied template grid.

Why a template is required:

- CubeDynamics prefers explicit coordinate semantics.
- The hull itself does not yet define a standalone canonical occupancy grid.
- Requiring a template keeps the conversion predictable and composable.

## Current limitations

- The fire-specific interactive hull viewer still uses Plotly.
- `FireHull.to_cube()` requires a template cube.
- `attach_environment()` currently supports `method="nearest"` only.
- Environmental attribution is summary-level, not yet full local hull-element attribution.
- FIRED ingestion, hull geometry, attribution, and rendering are clearer than before, but not fully separated into independent public submodules yet.
