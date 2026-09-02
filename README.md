# Fire VASE

Fire VASE changes the response being explained. It turns the ordered
accumulation of observed wildfire growth into standardized morphology so fires
can be compared by how they develop—not only by final area, duration, or peak
growth.

The central scientific sequence is:

1. preserve the observed growth pathway in a common developmental geometry;
2. describe continuous gradients in timing, concentration, persistence, and
   recurrence rather than asserting discrete fire types;
3. project weather and later process-specific data onto that response; and
4. use state dependence and explanatory mismatches to generate testable next
   questions without turning associations into causal claims.

Read the [manuscript narrative](docs/manuscript.md), the assembled
[submission manuscript](output/submission/fire_vase_manuscript_submission.pdf),
and [submission SI](output/submission/fire_vase_supplementary_submission.pdf).
The supplied editorial sources are preserved as
[`main-22.pdf`](docs/manuscripts/fire_vase_developmental_morphology/main-22.pdf)
and [`supplementary-4.pdf`](docs/manuscripts/fire_vase_developmental_morphology/supplementary-4.pdf).
The [submission freeze](analysis/submission_freeze/README.md) controls current
claims, hashes, checks, and remaining human items.

## Current evidence: v2 (2026-08-28)

The manuscript's representational argument survives the corrected analysis,
with narrower inference. Broad developmental gradients and nonrandom temporal
ordering are supported; exact local neighborhoods are less stable, weather
associations are weak and heterogeneous, and mismatch remains diagnostic rather
than mechanistic. The corrected, versioned analysis is in
[`analysis/v2/`](analysis/v2/), with an [audit](analysis/v2/audit_report.md),
[manuscript](docs/manuscripts/fire_vase_developmental_morphology/manuscript_v2.md),
[PDF](output/pdf/fire_vase_v2_manuscript.pdf), and [figures](figures/v2/).
The older 0.349 weather-model headline is withdrawn. Legacy generations and their
reproduction remain in [`archive/comparison_v1/`](archive/comparison_v1/).

The [second-pass scientific validation](analysis/scientific_validation/final_report.md)
freezes the evidence, with a [claim matrix](analysis/scientific_validation/final_claim_matrix.md)
and [Prism handoff](analysis/scientific_validation/PRISM_HANDOFF.md). Broad shape
gradients and nonrandom ordering survive; event-weather prediction is weak and
heterogeneous, and matched mismatch is compatible with the declared null.
The [final adversarial pass](analysis/scientific_validation/final_adversarial_pass/PRISM_HANDOFF_FINAL_ADVERSARIAL.md)
shows that compression alone is partly generic while ordering survives stricter
depth and endpoint-day removal.

```sh
PYTHONPATH=src:scripts OPENBLAS_NUM_THREADS=1 MPLCONFIGDIR=/tmp/fire-vase-v2-mpl .venv/bin/python manuscript_figures/00_run_all.py --generation v2 --data-lake data_lake/fire-vase-data-lake-v0.1
```

This is now the numbered pipeline's default. It writes statistics first, then
five PDF/PNG/SVG main figures, four supplements and manuscript PDF. The full run
includes the second-pass validation; use `--render-only` only after both statistics
sets exist. `--generation legacy` explicitly selects the older
pipeline. [V2 methods and reproduction](docs/reanalysis-v2.md) explain the source
audits, strict cohort, day-specific spatial exposure and remaining limitations.

Fire VASE is the research repository for the fire developmental morphology and
fire-climate VASE work that began inside
[`CU-ESIIL/cubedynamics`](https://github.com/CU-ESIIL/cubedynamics).

This repo is now the home for the publication-facing material: analysis scripts,
lakehouse schemas, manuscript drafts, figure generation, rendered figures, and
small derived tables. `cubedynamics` remains the reusable package home for the
generic fire hull/VASE API and examples.

## Start Here

Use the website vignette or notebook when handing the project to a collaborator:

- Website:
  [Fire VASE supplement](https://cu-esiil.github.io/fire_vase/)
- End-to-end vignette:
  [`docs/vignette-reproduce-pipeline.md`](docs/vignette-reproduce-pipeline.md)
- Runnable notebook:
  [`notebooks/reproduce_fire_vase_pipeline.ipynb`](notebooks/reproduce_fire_vase_pipeline.ipynb)
- Validation vignette:
  [`docs/validation/index.md`](docs/validation/index.md)
- Validation notebook:
  [`notebooks/validate_fire_vase_pipeline.ipynb`](notebooks/validate_fire_vase_pipeline.ipynb)
- Data-lake guide:
  [`docs/reproduce-data-lake.md`](docs/reproduce-data-lake.md)
- Figure guide:
  [`docs/reproduce-figures.md`](docs/reproduce-figures.md)
- Code map:
  [`docs/code-map.md`](docs/code-map.md)

The fastest reproduction path is: install the environment, sync the shared
CyVerse data lake to `data_lake/fire-vase-data-lake-v0.1`, run the
reproducibility checker, and then run the numbered figure scripts.

To audit one real FIRED/GridMET sample through the pipe, complete HTML cube,
2-D and 3-D hull decisions, climate, and external-source boundaries, run:

```bash
uv run python scripts/run_validation.py --external
```

This writes modular CSV/JSON/PNG/HTML evidence under `output/validation/` and
the collated report at `output/pdf/fire_vase_validation_report.pdf`.

To demonstrate that the same checks reject plausible axis, time, and geometry
errors, run the separate expected-failure contrast:

```bash
uv run python scripts/run_validation_contrast.py --publish-docs
```

The walkthrough is documented in
[`docs/validation/contrast.md`](docs/validation/contrast.md).

Shared data lake:
[CyVerse Fire_Vase folder](https://de.cyverse.org/data/ds/iplant/home/shared/esiil/Fire_Vase?type=folder&resourceId=ce3e72e4-95d1-11f1-852a-90e2ba675364)

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
- `docs/manuscripts/`: current manuscript-facing pages and transparency notes.
- `archive/manuscript_history/`: superseded drafts, citation/compliance audits,
  and formal review logs preserved for traceability.
- `examples/`, `notebooks/`, and `tests/`: VASE examples and smoke tests copied
  from the source project.
- `docs/assets/hero-vase-vpd.png` and
  `scripts/generate_hero_vase.py`: reproducible VPD-colored homepage hero asset.
- `docs/manuscripts/.../ai_transparency_report.md` and
  `scripts/generate_ai_transparency_report.py`: expanded AI transparency report
  and regenerable usage-summary charts.

## Data Boundary

Large source data and runtime products are not expected to live in Git. Keep
FIRED downloads, gridMET caches, lakehouse tables, Zarr stores, GeoParquet
products, and ad hoc run directories under ignored roots such as `artifacts/`,
`scratch/`, `lakehouse/`, and `tmp/`.

Small derived CSVs, manifests, manuscript figures, and publication PDFs may be
tracked when they are part of the scholarly record.

## Local Setup

```bash
uv sync
uv run --extra test pytest tests/test_fire_vase_lakehouse.py
uv run --extra docs mkdocs serve
```

The installed package currently exposes the transitional CubeDynamics runtime
under `src/cubedynamics/`. That preserves the original fire VASE import paths
while this research repository is split out from the general-purpose
[`CU-ESIIL/cubedynamics`](https://github.com/CU-ESIIL/cubedynamics) package.

## Vignette And Notebook

The canonical collaboration handoff is the full reproduction vignette:
[`docs/vignette-reproduce-pipeline.md`](docs/vignette-reproduce-pipeline.md).
It walks through repository setup, shared data-lake verification, optional
source rebuild, manuscript analysis products, figure reproduction, final checks,
and data-lake package refresh.

The same workflow is available as a runnable Jupyter notebook:
[`notebooks/reproduce_fire_vase_pipeline.ipynb`](notebooks/reproduce_fire_vase_pipeline.ipynb).
The notebook defaults to the shared-data-lake workflow and keeps expensive
source rebuild steps behind explicit switches.

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

Detailed guide:
[`docs/reproduce-data-lake.md`](docs/reproduce-data-lake.md)

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
[`docs/reproduce-figures.md`](docs/reproduce-figures.md), and the script-level
README is [`manuscript_figures/README.md`](manuscript_figures/README.md).

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

## Website, Manuscript, And Transparency

The website source is `docs/`. It is intentionally organized as manuscript
supplementary information rather than as a package manual. The homepage links
the reproduction vignette, notebook, data-lake guide, figure guide, manuscript
text, and AI transparency materials.

Useful pages:

- Methods notes: [`docs/methods.md`](docs/methods.md)
- Current manuscript:
  [`docs/manuscripts/fire_vase_developmental_morphology/manuscript_climate_revision_science_style.md`](docs/manuscripts/fire_vase_developmental_morphology/manuscript_climate_revision_science_style.md)
- Short AI transparency statement:
  [`docs/manuscripts/fire_vase_developmental_morphology/ai_transparency_statement.md`](docs/manuscripts/fire_vase_developmental_morphology/ai_transparency_statement.md)
- Expanded AI transparency report:
  [`docs/manuscripts/fire_vase_developmental_morphology/ai_transparency_report.md`](docs/manuscripts/fire_vase_developmental_morphology/ai_transparency_report.md)

Regenerate website-derived assets and transparency summaries with:

```bash
uv run python scripts/generate_hero_vase.py
uv run python scripts/generate_ai_transparency_report.py
uv run --extra docs mkdocs build --strict --clean
```

## Near-Term Cleanup

Historical manuscript review logs, superseded drafts, older generic
CubeDynamics docs, and ad hoc visual checks are preserved under `archive/` so
the public supplement website can stay focused on reproduction while the project
record remains intact.

The copied code intentionally preserves old `cubedynamics` import paths so the
research scripts still run. A later pass should either:

- keep `cubedynamics` as an explicit dependency and move project-specific code
  into `src/fire_vase/`, or
- retain the transitional runtime copy here only for reproducibility.

That refactor should be separate from this migration so collaborators can review
the copied research content first.
