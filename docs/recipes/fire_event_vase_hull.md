# Fire event vase + climate merge (fire_plot)

FIRED daily fire perimeters and gridMET climate grids span the same era but rarely meet in a unified analysis space. FIRED tracks perimeter geometry day by day, while gridMET provides gridded meteorology over CONUS. CubeDynamics stitches these together so that fire progression, space–time geometry, and climate context can be explored in one object.

`v.fire_plot` packages this workflow. It chooses a FIRED event that fits gridMET temporal support, builds a space–time “vase” from the daily polygons, summarizes that vase as a triangulated hull, samples gridMET into the event window, and returns an interactive Plotly visualization plus metrics. The result is an event-centric cube you can visualize and quantify without writing glue code.

## Concepts
### Vase (space–time event volume)
Daily polygons are extruded through time to form a 3-D volume—a “vase.” Two knobs control how finely the perimeter is discretized:

- **`n_ring_samples`**: number of radial samples along the boundary (and interior rings, if present).
- **`n_theta`**: angular resolution controlling mesh smoothness.

A well-sampled vase makes it possible to fill and merge gridded climate data into an event-defined space–time region, enabling event-centric statistics and visualization.

### Hull (geometric summary)
The hull is a compact triangulated surface summarizing the vase. In runtime code
the canonical object is `FireHull` (`TimeHull` remains a compatibility alias).
Key arrays include:

- **`verts_km`** (`N×3`): vertices in kilometers (x, y, time/day).
- **`tris`** (`M×3` indices): triangle connectivity over the vertices.

Hull metrics (scale, duration, volume, surface) make it easy to summarize, compare, and render fire events.

### Stream alignment (FIRED × gridMET)
gridMET has fixed temporal support. To ensure the fire window (plus buffer) sits inside that support, use **`GRIDMET_SUPPORT`** and **`pick_event_with_joint_support`**. They enforce that the chosen FIRED event can be paired with the requested climate buffer before running `fire_plot`.

## Quickstart
Cube-first usage is recommended: load your climate cube (gridMET, PRISM, Sentinel-2 NDVI, etc.) however you prefer, then pipe it into `v.fire_plot(fired_event=...)`.
```python
from cubedynamics import verbs as v
from cubedynamics.fire_time_hull import (
    load_fired_conus_ak,
    GRIDMET_SUPPORT,
    pick_event_with_joint_support,
)

# 1) FIRED daily (downloads & caches if enabled)
fired_daily = load_fired_conus_ak(which="daily", prefer="gpkg", download=True)

# 2) Choose an event that fits GRIDMET temporal support
event_id = pick_event_with_joint_support(
    fired_daily,
    climate_support=GRIDMET_SUPPORT,
    time_buffer_days=14,
    min_days=64,
)

# 3) Run fire_plot (returns hull + cube + summary + fig)
results = v.fire_plot(
    fired_daily=fired_daily,
    event_id=event_id,
    climate_variable="vpd",    # or "tmmx"
    freq="D",                   # daily by default; avoid empty monthly windows
    allow_synthetic=False,      # fail loudly instead of using demo data
    time_buffer_days=1,
    n_ring_samples=200,
    n_theta=296,
    show_hist=False,
    save_prefix=None,
)

# Optional: show interactive Plotly hull in notebook
results["fig_hull"].show(renderer="iframe")

hull = results["hull"]
summary = results["summary"]
cube = results["cube"]

print("Event:", results["event"].event_id)
print("Hull verts:", hull.verts_km.shape, "tris:", hull.tris.shape)
print("Cube:", getattr(cube, "da", None).shape if hasattr(cube, "da") else type(cube))
```

!!! tip "Daily by default"
    `fire_plot` requests daily gridMET/PRISM data for event windows. Explicitly pass
    `freq="D"` to emphasize daily sampling or a different frequency if needed.

## Prescribed-burn panels

Use `v.fire_vase_panel` when the analysis target is a group of prescribed burns
rather than one event. It selects prescribed events from a FIRED event table,
runs the same per-event VASE workflow used by `fire_plot`, and returns a Plotly
subplot figure plus records, individual results, and failures.

```python
panel = (
    pipe(gridmet_cube)
    | v.fire_vase_panel(
        fired_daily=fired_daily,
        fired_events=fired_events,
        prescribed_column="fire_type",
        prescribed_values=("prescribed", "rx", "planned"),
        max_events=12,
        climate_variable="tmmx",
    )
).unwrap()

panel["fig_panel"].show(renderer="iframe")
```

For full-list runs where each burn needs its own AOI/time climate pull, pass a
`climate_loader(event)` callback or use `load_climate=True` so each event can be
loaded independently.

## Current viewer status

`fire_plot` currently returns a fire-event analysis bundle plus a Plotly-based interactive hull figure. This is the supported fire-specific viewer path today. It is not yet rendered through the same custom HTML/CSS/JS viewer backend used by `v.plot()`. The long-term goal is to align fire-event visualization with the cube viewer’s shared space-time conventions so that fire-specific displays and generic cube displays live in the same visual grammar.

Developer note: `If you are working on fire visualization internals, treat event construction, hull generation, climate/event fusion, and rendering as separable layers. The safest near-term improvements are the ones that preserve those boundaries.`

## What you get back
`v.fire_plot` returns a dictionary with:

- `event` (`FireEventDaily`): cleaned FIRED daily perimeters, centroid, and time bounds.
- `hull` (`FireHull`, with `TimeHull` retained as a compatibility alias): triangulated vase geometry with metrics such as `duration_days`, `scale_km`, `hull_volume_km2_days`, and `hull_surface_km_day`.
- `cube` (`ClimateCube`): gridMET DataArray clipped to the event window with any requested buffer.
- `summary` (`HullClimateSummary`): inside/outside pixel samples and per-day means for the event footprint.
- `fig_hull` (`plotly.graph_objects.Figure`): interactive Mesh3d hull colored by mean climate.
- `color_limits` (`tuple[float, float]`): min/max used for the Plotly colorbar.

If `show_hist=True`, a Matplotlib histogram is also drawn (for interactive QA) but is not returned in the dictionary.

## Daily frequency (freq) for GRIDMET / PRISM

`freq` is forwarded to the GRIDMET/PRISM loaders and controls the cube's time index. For fire events, use daily sampling:

```python
results = v.fire_plot(..., freq="D", ...)
```

- **Default**: when `freq` is not supplied, `fire_plot` requests daily GRIDMET/PRISM data (`freq="D"`).
- **Why daily?** Fire events are short; daily timestamps prevent gaps and align with FIRED daily perimeters. The same setting applies if you target PRISM variables.
- **Gotcha**: `freq="MS"` (month start) can yield zero timestamps for short windows (e.g., 2018-07-17 to 2018-07-25), producing an empty cube. Keep `freq="D"` or widen the window when analyzing individual events.

## Parameters and tuning
- **`climate_variable`**: use `"vpd"` (vapor pressure deficit, kPa) to match the prototype or `"tmmx"` (daily max temperature). Other gridMET variables pass through unchanged.
- **`time_buffer_days`**: buffer applied inside `fire_plot` when fetching climate data around the event. This is separate from the selection buffer used in `pick_event_with_joint_support`—you can keep the selection buffer generous (e.g., 14 days) while using a smaller fetch buffer (e.g., 1 day) for plotting.
- **`n_ring_samples` / `n_theta`**: higher values yield smoother hulls at the cost of compute. Start with the defaults (200 / 296); for higher quality rendering, push `n_ring_samples` toward 300–400 and `n_theta` toward 360–512.
- **`show_hist`**: enable when you want to visually compare inside vs. outside pixel distributions for QA.
- **`save_prefix`**: if set, Plotly static export attempts to write `{save_prefix}.png` using Kaleido; leave `None` to skip file output.

## Preview
![Fire vase hull preview](../assets/workflows/fire_event_vase_hull.png)

!!! note
    Image placeholder — after running locally, save a screenshot to `docs/assets/workflows/fire_event_vase_hull.png`.

## Data provenance
Every cube returned by `fire_plot` carries provenance in `cube.da.attrs`:

- `source`: one of `gridmet_streaming`, `gridmet_download`, `prism_streaming`, `prism_download`, or `synthetic`.
- `is_synthetic`: `True` only when a synthetic fallback was generated.
- `freq`: temporal frequency actually used (daily by default for gridMET/PRISM).
- `backend_error`: present only when a fallback occurred (streaming → download or synthetic).

Inspect these fields after running the recipe to confirm that real data were fetched.

## Common pitfalls
!!! warning
    - **Empty time axis**: A short window with `freq="MS"` or `freq="ME"` can return zero timestamps. Use `freq="D"` for event-scale analyses.
    - **Synthetic fallback**: By default `allow_synthetic=False` raises if the backend fails or returns empty/NaN data. Set `allow_synthetic=True` only for demos.
    - **Backend dependencies**: If streaming is unavailable, install the required optional dependencies or point to cached downloads before retrying.

## Troubleshooting
- **FIRED download/cache issues**: check the `load_fired_conus_ak` docstring for cache layout and download guidance; ensure the target file exists or enable `download=True`.
- **No event found for selection**: relax `min_days` or increase `time_buffer_days` in `pick_event_with_joint_support` to widen the search window.
- **Plotly not rendering in notebooks**: set an explicit renderer (e.g., `results["fig_hull"].show(renderer="iframe")` or `"browser"`) and ensure Kaleido is installed only if exporting images.
