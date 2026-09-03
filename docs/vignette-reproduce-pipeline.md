# Vignette: Reproduce The Fire VASE Pipeline

The [manuscript narrative](manuscript.md) defines the scientific sequence:
construct comparable developmental histories first, then test candidate
explanations against them. For current quantitative results, follow
[Corrected Evidence](reanalysis-v2.md).
After obtaining the real v0.1 data package, the numbered pipeline defaults to v2
and writes `analysis/v2/`, `figures/v2/` and the versioned manuscript. The original
developmental/climate-revision stages and identity checks below are historical
and should be selected explicitly as legacy, not used to support current claims.

This vignette walks through the complete manuscript-support workflow: set up
the repository, obtain or rebuild the data lake, regenerate analysis products,
render the manuscript figures, and run reproducibility checks.

Use the shared data lake when you want to reproduce the analysis and figures
quickly. Rebuild from source when you need to audit or recreate the full data
lake itself.

Runnable notebook:
[notebooks/reproduce_fire_vase_pipeline.ipynb](https://github.com/CU-ESIIL/fire_vase/blob/main/notebooks/reproduce_fire_vase_pipeline.ipynb)

## 1. Set Up The Repository

Clone the manuscript repository and install the locked Python environment:

```bash
git clone https://github.com/CU-ESIIL/fire_vase.git
cd fire_vase
uv sync
```

The reusable VASE implementation is preserved through the repository's Python
environment and migrated `cubedynamics` code paths. The manuscript-specific
workflow lives in this repository.

## 2. Choose A Data-Lake Starting Point

### Option A: Use The Shared Data Lake

Download or sync the data lake from:

[CyVerse Fire_Vase](https://de.cyverse.org/data/ds/iplant/home/shared/esiil/Fire_Vase?type=folder&resourceId=ce3e72e4-95d1-11f1-852a-90e2ba675364)

Place it at:

```text
data_lake/fire-vase-data-lake-v0.1
```

Verify the downloaded lake before running analyses:

```bash
uv run python scripts/check_reproducibility.py \
  --json-output analysis/reproducibility_check_latest.json
```

The `data_lake.status` field in the JSON report should be `pass`.

### Option B: Rebuild The Lake From Source Caches

Use this route when source FIRED and gridMET caches are available locally and
you want to recreate the manuscript-scale lakehouse.

Cache the manuscript gridMET variables:

```bash
uv run python scripts/cache_gridmet_years.py \
  --preset comprehensive \
  --keep-going
```

Build the full Fire VASE lakehouse:

```bash
uv run python scripts/fire_vase_lakehouse_pilot.py \
  --config config/fire_vase_pipeline.yml \
  --output-root scratch/fire_vase_run_full \
  --full-population
```

Build climate attribution tables:

```bash
uv run python scripts/fire_vase_build_climate_tables.py \
  --include-optional-variables \
  --table-root scratch/fire_vase_run_full/tables

uv run python scripts/fire_vase_build_perimeter_climate_tables.py \
  --include-optional-variables
```

Build developmental morphology products:

```bash
uv run python scripts/fire_vase_developmental_morphology_analysis.py \
  --table-root scratch/fire_vase_run_full/tables \
  --data-output-dir scratch/fire_vase_developmental_morphology
```

Package the rebuilt lake:

```bash
uv run python scripts/prepare_data_lake.py \
  --mode manifest \
  --checksum
```

The package metadata is written to:

```text
data_lake/fire-vase-data-lake-v0.1/
```

For a materialized handoff, rerun the packager with `--mode hardlink` or
`--mode copy`.

## 3. Regenerate Current Analysis Products

The canonical v2 analysis and figure orchestrator is the numbered manuscript
runner. It requires real lakehouse inputs and has no synthetic fallback:

```bash
PYTHONPATH=src:scripts OPENBLAS_NUM_THREADS=1 \
MPLCONFIGDIR=/tmp/fire-vase-v2-mpl \
.venv/bin/python manuscript_figures/00_run_all.py \
  --generation v2 \
  --data-lake data_lake/fire-vase-data-lake-v0.1
```

This refreshes the current `analysis/v2/` products and validated v2 figures.
The fixed configuration is `config/analysis_v2.json` with seed `20260828`.

Then regenerate and verify the bounded scientific-validation layer:

```bash
PYTHONPATH=src:scripts MPLBACKEND=Agg \
MPLCONFIGDIR=/tmp/fire-vase-v2-mpl OPENBLAS_NUM_THREADS=1 \
.venv/bin/python scripts/validate_fire_vase_science.py

PYTHONPATH=src:scripts MPLBACKEND=Agg \
MPLCONFIGDIR=/tmp/fire-vase-v2-mpl OPENBLAS_NUM_THREADS=1 \
.venv/bin/python scripts/verify_fire_vase_science.py
```

The climate-revision and claim-audit scripts remain preserved historical
workflows. Run them only when reproducing the superseded generation; they do
not control current quantitative claims.

## 4. Regenerate Manuscript Figures

The collaboration-friendly figure pipeline is in `manuscript_figures/`. Run the
full figure set against the data lake:

```bash
uv run python manuscript_figures/00_run_all.py \
  --generation v2 \
  --data-lake data_lake/fire-vase-data-lake-v0.1
```

The command writes PDF, PNG, and SVG files into:

```text
manuscript_figures/
```

To regenerate one figure:

```bash
uv run python manuscript_figures/03_figure_3.py \
  --generation v2 \
  --data-lake data_lake/fire-vase-data-lake-v0.1
```

To recompute validation tables instead of using cached tables from the data
lake:

```bash
uv run python manuscript_figures/00_run_all.py \
  --generation v2 \
  --data-lake data_lake/fire-vase-data-lake-v0.1 \
  --force-validation
```

## 5. Check The Whole Pipeline

Run the scientific validation modules for pipe execution, complete HTML-cube
serialization, 2-D and 3-D hull construction/averaging decisions, climate
attribution, and source agreement:

```bash
uv run python scripts/run_validation.py --external
```

See the [validation vignette](validation/index.md) or open
[notebooks/validate_fire_vase_pipeline.ipynb](https://github.com/CU-ESIIL/fire_vase/blob/main/notebooks/validate_fire_vase_pipeline.ipynb)
to rerun one QA plot at a time.

Then run the full artifact-level reproducibility checker:

```bash
uv run python scripts/check_reproducibility.py \
  --json-output analysis/reproducibility_check_latest.json
```

Read the report as three checks:

- `data_lake.status`: every file in the lake matches `checksums.sha256`.
- `derived_stats.status`: regenerated figure statistics match references by
  byte hash.
- `figures.pixel_status`: regenerated manuscript PNGs are visually identical to
  checked-in reference figures.

If you only want to check regenerated figures and derived statistics after the
data lake has already been verified:

```bash
uv run python scripts/check_reproducibility.py \
  --skip-data-lake \
  --json-output analysis/reproducibility_check_latest.json
```

## 6. Refresh The Shareable Data-Lake Package

After intentional changes to scripts, figures, manuscripts, or derived tables,
refresh the package manifest and checksums:

```bash
uv run python scripts/prepare_data_lake.py \
  --mode manifest \
  --checksum
```

For an upload-ready local package:

```bash
uv run python scripts/prepare_data_lake.py \
  --mode copy \
  --checksum
```

The release inventory is controlled by
[`config/data_release.yml`](https://github.com/CU-ESIIL/fire_vase/blob/main/config/data_release.yml).

## Code Used In This Vignette

- [Data release config](https://github.com/CU-ESIIL/fire_vase/blob/main/config/data_release.yml)
- [Data-lake packager](https://github.com/CU-ESIIL/fire_vase/blob/main/scripts/prepare_data_lake.py)
- [Reproducibility checker](https://github.com/CU-ESIIL/fire_vase/blob/main/scripts/check_reproducibility.py)
- [Scientific validation runner](https://github.com/CU-ESIIL/fire_vase/blob/main/scripts/run_validation.py)
- [Lakehouse builder](https://github.com/CU-ESIIL/fire_vase/blob/main/scripts/fire_vase_lakehouse_pilot.py)
- [Climate table builder](https://github.com/CU-ESIIL/fire_vase/blob/main/scripts/fire_vase_build_climate_tables.py)
- [Perimeter climate builder](https://github.com/CU-ESIIL/fire_vase/blob/main/scripts/fire_vase_build_perimeter_climate_tables.py)
- [Developmental morphology analysis](https://github.com/CU-ESIIL/fire_vase/blob/main/scripts/fire_vase_developmental_morphology_analysis.py)
- [Manuscript figure wrappers](https://github.com/CU-ESIIL/fire_vase/tree/main/manuscript_figures)
- [Script map](https://github.com/CU-ESIIL/fire_vase/blob/main/scripts/README.md)
