# Fire VASE

Fire VASE is the research repository for the fire developmental morphology and
fire-climate VASE work that began inside
[`CU-ESIIL/cubedynamics`](https://github.com/CU-ESIIL/cubedynamics).

This repo is now the home for the publication-facing material: analysis scripts,
lakehouse schemas, manuscript drafts, figure generation, rendered figures, and
small derived tables. `cubedynamics` remains the reusable package home for the
generic fire hull/VASE API and examples.

## What Was Migrated

The initial migration copied VASE-related material from `cubedynamics` `main` at
commit `0f2538d393abde5d1ff503e2c5dd73d01562b53e`.

Key copied areas:

- `src/cubedynamics/`: transitional copy of the runtime code needed by the
  current scripts and tests.
- `scripts/`: fire VASE lakehouse, climate, manuscript, atlas, and figure
  generation scripts.
- `schemas/` and `config/`: table schemas and pipeline configuration templates.
- `analysis/`, `figures/`, `output/`, and `outputs/`: tracked analysis notes,
  publication figures, rendered manuscripts, and small derived outputs.
- `docs/manuscripts/`: manuscript drafts, citation audits, formal reviews, and
  transparency notes.
- `examples/`, `notebooks/`, and `tests/`: VASE examples and smoke tests copied
  from the source project.

## Data Boundary

Large source data and runtime products are not expected to live in Git. Keep
FIRED downloads, gridMET caches, lakehouse tables, Zarr stores, GeoParquet
products, and ad hoc run directories under ignored roots such as `artifacts/`,
`scratch/`, `lakehouse/`, and `tmp/`.

Small derived CSVs, manifests, manuscript figures, and publication PDFs may be
tracked when they are part of the scholarly record.

## Local Setup

```bash
python -m pip install -e ".[dev]"
pytest tests/test_fire_vase_lakehouse.py
mkdocs serve
```

The installed package currently exposes the transitional CubeDynamics runtime
under `src/cubedynamics/`. That preserves the original fire VASE import paths
while this research repository is split out from the general-purpose
[`CU-ESIIL/cubedynamics`](https://github.com/CU-ESIIL/cubedynamics) package.

## Data Lake Reproduction

There are two supported collaborator workflows:

1. Use an existing Fire VASE data-lake package when you only need to reproduce
   manuscript figures or inspect the derived tables.
2. Rebuild the data lake from source FIRED and gridMET caches when you need to
   audit or extend the full processing pipeline.

The release definition lives in
[`config/data_release.yml`](config/data_release.yml). It records the expected
data-lake layout, upstream inputs, generated tables, derived outputs, schemas,
and the command order for a full rebuild.

### Use Or Package An Existing Data Lake

Start with a complete manifest:

```bash
python scripts/prepare_data_lake.py --mode manifest
```

This writes a handoff inventory under `data_lake/` for the whole Fire VASE lake:
FIRED caches, gridMET NetCDF caches, full Parquet lakehouse tables,
developmental morphology tables, derived outputs, schemas, figures, and
manuscript artifacts.

To materialize a handoff directory without duplicating bytes on the same
filesystem:

```bash
python scripts/prepare_data_lake.py --mode hardlink --checksum
```

Use `--mode copy --checksum` when preparing an independent folder for an
external drive or cloud upload. The lake itself is ignored by Git; the manifest,
checksums, and restore map are the reproducibility contract.

Packager code:
[`scripts/prepare_data_lake.py`](scripts/prepare_data_lake.py)

Data boundary guide:
[`docs/data.md`](docs/data.md)

FIRED source notes:
[`docs/datasets/fired.md`](docs/datasets/fired.md)

### Rebuild The Lake With CubeDynamics/Fire VASE Code

This is the heavy path. It rebuilds the lakehouse from FIRED caches and cached
gridMET files, then regenerates the morphology and climate-revision products.
It may download many NetCDF files and write large ignored directories under
`artifacts/` and `scratch/`.

1. Install the repository environment.

   ```bash
   python -m pip install -e ".[dev]"
   ```

2. Put the FIRED event and daily perimeter GeoPackages where the pipeline
   expects them, or update
   [`config/fire_vase_pipeline.yml`](config/fire_vase_pipeline.yml).

   ```text
   artifacts/fire-vase-gridmet-real/fired-cache/
     fired_conus-ak_events_nov2001-march2021.gpkg
     fired_conus-ak_daily_nov2001-march2021.gpkg
   ```

3. Cache gridMET variables.

   ```bash
   python scripts/cache_gridmet_years.py --preset comprehensive --keep-going
   ```

   Code:
   [`scripts/cache_gridmet_years.py`](scripts/cache_gridmet_years.py)

4. Build the base Fire VASE lakehouse tables.

   ```bash
   python scripts/fire_vase_lakehouse_pilot.py \
     --config config/fire_vase_pipeline.yml \
     --output-root scratch/fire_vase_run_full \
     --full-population
   ```

   Code:
   [`scripts/fire_vase_lakehouse_pilot.py`](scripts/fire_vase_lakehouse_pilot.py)

   Note: the script does not fabricate rows. Use `--sample-size N` instead of
   `--full-population` when you want a smaller pilot run.

5. Attach daily centroid gridMET climate to VASE slices.

   ```bash
   python scripts/fire_vase_build_climate_tables.py \
     --include-optional-variables \
     --table-root scratch/fire_vase_run_full/tables
   ```

   Code:
   [`scripts/fire_vase_build_climate_tables.py`](scripts/fire_vase_build_climate_tables.py)

6. Build perimeter and active-area climate exposure products.

   ```bash
   python scripts/fire_vase_build_perimeter_climate_tables.py \
     --include-optional-variables \
     --table-root scratch/fire_vase_run_full/tables
   ```

   Code:
   [`scripts/fire_vase_build_perimeter_climate_tables.py`](scripts/fire_vase_build_perimeter_climate_tables.py)

7. Build developmental morphology tables.

   ```bash
   python scripts/fire_vase_developmental_morphology_analysis.py \
     --table-root scratch/fire_vase_run_full/tables \
     --data-output-dir scratch/fire_vase_developmental_morphology
   ```

   Code:
   [`scripts/fire_vase_developmental_morphology_analysis.py`](scripts/fire_vase_developmental_morphology_analysis.py)

8. Regenerate climate-revision analysis products, figures, and manuscript
   source outputs.

   ```bash
   python scripts/fire_vase_climate_revision.py
   ```

   Code:
   [`scripts/fire_vase_climate_revision.py`](scripts/fire_vase_climate_revision.py)

After a rebuild, run the packager again to create a shareable data-lake manifest
or materialized handoff directory.

```bash
python scripts/prepare_data_lake.py --mode manifest
```

## Figure Reproduction

The easiest figure workflow starts from an existing data-lake package. The
figure guide is in
[`manuscript_figures/README.md`](manuscript_figures/README.md).

Run every manuscript figure:

```bash
uv run python manuscript_figures/00_run_all.py \
  --data-lake data_lake/fire-vase-data-lake-v0.1
```

Run one figure:

```bash
uv run python manuscript_figures/03_figure_3.py \
  --data-lake data_lake/fire-vase-data-lake-v0.1
```

Figure entry points:

- [`manuscript_figures/00_run_all.py`](manuscript_figures/00_run_all.py)
- [`manuscript_figures/01_figure_1.py`](manuscript_figures/01_figure_1.py)
- [`manuscript_figures/02_figure_2.py`](manuscript_figures/02_figure_2.py)
- [`manuscript_figures/03_figure_3.py`](manuscript_figures/03_figure_3.py)
- [`manuscript_figures/04_figure_4.py`](manuscript_figures/04_figure_4.py)
- [`manuscript_figures/05_figure_5.py`](manuscript_figures/05_figure_5.py)
- [`manuscript_figures/06_supplementary_figure_1.py`](manuscript_figures/06_supplementary_figure_1.py)

Shared figure implementation lives in
[`scripts/figures/`](scripts/figures/). The wrapper scripts set data-lake paths
and write PDF, PNG, and SVG outputs back into `manuscript_figures/`.

## Reproducibility Checks

After regenerating the figures, compare the outputs against the checked-in
reference figures and derived statistics:

```bash
uv run python scripts/check_reproducibility.py --skip-data-lake
```

The checker reports byte-level differences for PDF, PNG, and SVG files, and a
pixel-level comparison for PNG figures. Byte-identical figure files are stricter
than visual reproduction because PDF/SVG metadata can change across plotting
environments.

To verify the materialized data lake itself, run the full SHA-256 pass:

```bash
uv run python scripts/check_reproducibility.py
```

This reads every data-lake file listed in `checksums.sha256`, so it can take
several minutes on the full package. To save a machine-readable report:

```bash
uv run python scripts/check_reproducibility.py \
  --json-output analysis/reproducibility_check_latest.json
```

The website builds from `docs/` and is configured for GitHub Pages at:

```text
https://cu-esiil.github.io/fire_vase/
```

## Near-Term Cleanup

The copied code intentionally preserves old `cubedynamics` import paths so the
research scripts still run. A later pass should either:

- keep `cubedynamics` as an explicit dependency and move project-specific code
  into `src/fire_vase/`, or
- retain the transitional runtime copy here only for reproducibility.

That refactor should be separate from this migration so collaborators can review
the copied research content first.
