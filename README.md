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

## Build The Shareable Data Lake

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
