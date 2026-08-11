# Fire / VASE Status Audit

This audit tracks the current FIRED, fire time-hull, and VASE implementation in the runtime package under `src/cubedynamics/`.

## Canonical runtime modules

- `src/cubedynamics/fire_time_hull.py`
  - `TemporalSupport`
  - `GRIDMET_SUPPORT`
  - `load_fired_conus_ak()`
  - `pick_event_with_joint_support()`
  - `FireEventDaily`
  - `FireHull`
  - `TimeHull` (compatibility alias to `FireHull`)
  - `ClimateCube`
  - `HullClimateSummary`
  - `build_fire_event_daily()`
  - `build_fire_event()` (deprecated compatibility wrapper)
  - `compute_time_hull_geometry()`
  - `sample_inside_outside()`
  - `build_inside_outside_climate_samples()`
  - `time_hull_to_vase()`
  - `load_climate_cube_for_event()`
  - `plot_climate_filled_hull()`
  - `plot_inside_outside_hist()`
  - `compute_derivative_hull()`
  - `plot_derivative_hull()`

- `src/cubedynamics/verbs/fire.py`
  - `fire_plot()`
  - `fire_derivative()`
  - Current high-level fire workflow entry point used by `cubedynamics.verbs.fire_plot`

- `src/cubedynamics/verbs/__init__.py`
  - `extract()`
  - legacy/high-level `fire_plot()` wrapper definitions, later overridden by `from .fire import fire_plot, fire_derivative`
  - `fire_panel()`
  - `vase()`
  - `vase_demo()`
  - `vase_extract()`
  - `vase_mask()`

- `src/cubedynamics/vase.py`
  - `VaseSection`
  - `VaseDefinition`
  - `VasePanel`
  - `build_vase_panels()`
  - `build_vase_mask()`
  - `extract_vase_from_attrs()`

- `src/cubedynamics/vase_viz.py`
  - `extract_vase_points()`
  - `vase_scatter_plot()`
  - `vase_to_mesh()`
  - `vase_scatter_with_hull()`

## Internal / compatibility wrappers

- `src/cubedynamics/ops_fire/time_hull.py`
  - deprecated forwarding wrappers to `cubedynamics.fire_time_hull`
- `src/cubedynamics/ops_fire/fired_io.py`
  - deprecated FIRED IO forwarding wrappers
- `src/cubedynamics/ops_fire/climate_hull_extract.py`
  - deprecated climate extraction forwarding wrappers
- `src/cubedynamics/ops_fire/fired_api.py`
  - `fired_event()` convenience entry point for loading and selecting a FIRED event

## Examples and notebooks

- `examples/fire_plot_demo.py`
  - standalone demo script with local FIRED loading and event selection
- `examples/fire_time_hull_gridmet_demo.py`
  - cube-first `v.fire_plot(...)` and `v.fire_panel(...)` examples
- `notebooks/06_vase_volume_basic.ipynb`
  - generic vase masking and plotting workflow
- `notebooks/07_vase_volume_3d_viz.ipynb`
  - optional scientific 3-D vase visualization helpers

## Tests

- `tests/test_fire_hull_api.py`
  - `FireEventDaily.example()`, `to_hull()`, `metrics()`, `to_mesh()`, `to_cube()`, `attach_environment()`, `plot()`
- `tests/test_fire_hull_viewer_scalars.py`
  - scalar-to-geometry mapping, z/slice diagnostics, climate projection ordering
- `tests/test_fire_plot_cube_first.py`
  - cube-first `fire_plot()` behavior
- `tests/test_fire_plot_loader_calls.py`
  - loader/frequency/provenance behavior for fire workflows
- `tests/test_time_hull_geometry.py`
  - synthetic geometry construction for `compute_time_hull_geometry()`
- `tests/test_fire_time_hull_loader.py`
  - FIRED cache/download loader behavior
- `tests/test_climate_hull_extract.py`
  - climate sampling inside/outside event footprints
- `tests/test_verbs_fire_extract.py`
  - `v.extract()` attaches `fire_time_hull`, `fire_climate_summary`, and `vase`
- `tests/test_verbs_vase.py`
  - vase verbs and masking
- `tests/test_vase.py`
  - `VaseDefinition`, panels, masking
- `tests/test_vase_viewer.py`
  - viewer overlay behavior for vase metadata
- `tests/test_vase_viz.py`
  - optional PyVista/Trimesh helpers
- `tests/test_demo_vase.py`
  - synthetic demo vase utilities

## Current docs

- `docs/recipes/fire_event_vase_hull.md`
  - current end-to-end fire workflow doc
- `docs/datasets/fired.md`
  - FIRED dataset overview
- `docs/dev/fire_plot_architecture.md`
  - fire plot architecture notes
- `docs/vase_volumes.md`
  - generic vase concept/user guide
- `docs/legacy/vase-volumes.md`
  - archived vase write-up
- `docs/api/verbs.md`
  - user-facing verbs documentation including `fire_plot`
- `AGENTS.md`
  - contributor constraints and renderer guidance for fire/vase work

## What works

- `FireEventDaily` is now the canonical event container in runtime code.
- `FireHull` is now the canonical hull object, with `TimeHull` retained as a compatibility alias.
- `compute_time_hull_geometry()` produces deterministic synthetic meshes and stable metrics for tests.
- `v.fire_plot()` supports both cube-first and legacy fire-first entry paths.
- FIRED loading, joint-support event selection, and climate sampling are centralized in `src/cubedynamics/fire_time_hull.py`.
- The hull can be converted to a `VaseDefinition` via `time_hull_to_vase()`.
- The hull now supports object methods:
  - `FireEventDaily.from_fired()`
  - `FireEventDaily.example()`
  - `FireEventDaily.to_hull()`
  - `FireHull.metrics()`
  - `FireHull.plot()`
  - `FireHull.to_mesh()`
  - `FireHull.to_cube(template)`
  - `FireHull.attach_environment(...)`

## What is fragile

- `src/cubedynamics/verbs/__init__.py` still contains an older fire/vase layer before overriding imports from `src/cubedynamics/verbs/fire.py`.
- The primary fire-specific interactive renderer remains Plotly, while `v.plot()` uses the custom cube viewer.
- `FireHull.to_cube()` currently requires a template cube. Standalone occupancy-grid generation is not implemented yet.
- Environmental attribution now stores explicit per-layer and per-vertex hull-aligned values, but it still derives them from per-day footprint summaries rather than from a fully local `(x, y, t)` sampling model.
- `examples/fire_plot_demo.py` duplicates concepts that are now canonical in `src/cubedynamics/fire_time_hull.py`.

## What is undocumented or under-documented

- The canonical distinction between `FireEventDaily` and `FireHull`
- The stable metrics vocabulary and legacy metric aliases
- The exact status of `TimeHull` as a compatibility alias rather than the preferred public name
- The current scope of `attach_environment(...)`
- The limitation that `FireHull.to_cube()` needs a template grid

## Proposed public API

Public / canonical:

- `cubedynamics.fire_time_hull.FireEventDaily`
- `cubedynamics.fire_time_hull.FireHull`
- `cubedynamics.fire_time_hull.TimeHull` (compatibility alias; document as legacy name)
- `cubedynamics.fire_time_hull.load_fired_conus_ak`
- `cubedynamics.fire_time_hull.pick_event_with_joint_support`
- `cubedynamics.fire_time_hull.compute_time_hull_geometry`
- `cubedynamics.fire_time_hull.plot_climate_filled_hull`
- `cubedynamics.verbs.fire_plot`
- `cubedynamics.verbs.extract`
- `cubedynamics.vase.VaseDefinition`, `VaseSection`, `build_vase_mask`

Internal / less stable:

- `cubedynamics.ops_fire.*`
- `cubedynamics.vase_viz.*`
- lower-level geometry helpers such as `_largest_polygon()`, `_sample_ring_equal_steps()`, `_tri_area()`
- renderer-specific wiring inside `src/cubedynamics/verbs/fire.py`

## Recommended next refactors

- Collapse the remaining legacy fire implementation in `src/cubedynamics/verbs/__init__.py` into clearer adapter functions or remove it behind deprecation windows.
- Move toward a renderer adapter layer so `FireHull.plot()` does not encode backend details directly.
- Extend `attach_environment(...)` from summary-level attribution to explicit local hull-element attribution.
- Add a template-free occupancy cube builder once grid conventions are finalized.
