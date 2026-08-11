# Fire VASE Lakehouse Architecture

The fire VASE lakehouse separates science products from rendered views. A VASE
is a versioned data object made from fire-time geometry and environmental
attribution; a panel, mesh, SVG, PDF, or PNG is an asset derived from that data.

## Product Classes

- Immutable source observations: raw fire records and upstream provenance.
- Canonical fire time and geometry: normalized daily or hourly fire-time rows
  with validated geometry keys.
- Derived traits and events: reusable tables for cohort selection, event
  alignment, and summary products.
- VASE slices: ring-level geometry and climate attribution for each fire-time
  slice.
- VASE climate exposures: companion zone-level climate summaries for each
  fire-time slice, including daily active burned polygons, cumulative burned
  area, and exterior perimeter-extension buffers.
- Rendered assets: GLB, PNG, SVG, HTML, or PDF views registered back to the
  VASE cache key.
- Population summaries: cohort, medoid, and event-aligned quantile products.

## Core Tables

Schemas live in `schemas/*.schema.json` for:

- `fire_observations_raw`
- `fire_time`
- `fire_geometry`
- `fire_traits`
- `fire_events`
- `vase_slices`
- `vase_climate_exposures`
- `vase_assets`
- `processing_manifest`
- `processing_runs`
- `fire_catalog`
- `processing_failures`
- `cohort_summaries`

## Versioning

Component versions are independent: source, geometry, climate, events, traits,
VASE, and render. Cache keys are content-addressed from the fire identity,
component versions, and upstream keys. A climate version update invalidates
climate, events, traits, VASE, and render outputs while preserving source and
geometry products. Event-only updates invalidate events, traits, VASE, and
render outputs.

## Partitioning

Tables are partitioned by `year`, `region`, `spatial_bucket`, and
`processing_version`. They are not partitioned by `fire_id`, which keeps cohort
queries and compaction practical.

## Repository Boundary

Git stores code, schemas, config templates, documentation, small fixtures, and
small curated release manifests. Bulk outputs stay in ignored roots such as
`scratch/`, `artifacts/`, `lakehouse/`, `manifests/runs/`, or external object
storage. Use `scripts/check_repository_size.py` before committing generated
work.

## Pilot

Run a real-data pilot from the configured catalog:

```bash
python scripts/fire_vase_lakehouse_pilot.py \
  --config config/fire_vase_pipeline.yml \
  --output-root ./scratch/fire_vase_run \
  --sample-size 1000
```

The pilot never pads with synthetic fires. If the source catalog contains fewer
than the requested count, it writes all available rows and records the shortfall
in `pilot_report.json`.

## Perimeter Climate Exposure

The original manuscript-scale climate table,
`scratch/fire_vase_run_full/tables/vase_slices.parquet`, is intentionally kept
as the daily centroid baseline. Richer attribution is written to a separate
companion table so downstream figures can compare centroid, active-area, full
cumulative-perimeter, and exterior exposure-zone summaries without breaking
existing analyses.

Run a small real-data smoke test:

```bash
python scripts/fire_vase_build_perimeter_climate_tables.py \
  --max-fires 25 \
  --extension-distances-m 5000 \
  --table-root scratch/fire_vase_run_full/perimeter_smoke_tables \
  --report scratch/fire_vase_run_full/perimeter_climate_build_report_smoke.json
```

Run the full standard cached gridMET variables over all FIRED daily geometries:

```bash
python scripts/fire_vase_build_perimeter_climate_tables.py
```

The table records `climate_sample_method` for every exposure row. Small fires
can be smaller than a gridMET cell; when no grid-cell center falls inside an
exposure zone, the script uses the nearest grid cell to a representative point
and labels the row `fallback_nearest_cell_to_zone`.

The standard cached variables are maximum temperature, minimum temperature,
VPD, and wind speed. To cache the expanded gridMET climate and fire-weather
variables before running the perimeter table with optional variables:

```bash
python scripts/cache_gridmet_years.py --preset comprehensive --keep-going
python scripts/fire_vase_build_perimeter_climate_tables.py --include-optional-variables
```

Optional gridMET variables currently wired into the schema and config include
precipitation, maximum and minimum relative humidity, specific humidity, 100-hr
and 1000-hr dead fuel moisture, energy release component, burning index,
reference and potential evapotranspiration, and solar radiation. Topography,
vegetation, suppression, ignition cause, and local-normal anomalies remain
separate data-integration steps because they do not come from the daily
gridMET cache.
