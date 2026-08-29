# Fire VASE Script Map

## Current v2 workflow

`fire_vase_v2.py` computes corrected, real-data statistics under `analysis/v2/`.
`fire_vase_v2_inputs.py` audits original FIRED attributes and constructs day-t
newly burned-area centroid weather. Core tested methods live in
`src/cubedynamics/analysis_v2.py`; `figures/make_figures_v2.py` draws saved
statistics and `fire_vase_v2_manuscript.py` writes the manuscript and audit.

Run `manuscript_figures/00_run_all.py --generation v2` for the full workflow.
The full workflow also runs `validate_fire_vase_science.py` for the bounded
second-pass tests. `finalize_fire_vase_science.py` generates the correction audit,
claim matrix, result comparison and Prism handoff from saved tables under
`analysis/scientific_validation/`. `verify_fire_vase_science.py --snapshot PATH`
and `--compare PATH` verify invariant checks, deterministic regeneration and
the final artifact hashes. Use `MPLBACKEND=Agg` for headless tests and rendering.
The developmental and climate-revision scripts listed below are historical v1
implementations; they are not the corrected scientific pipeline. Use
`reproduce_v1_comparison.py` to reproduce them without overwriting current work.

This folder contains the code used to build, analyze, package, and verify the
Fire VASE manuscript data products. Most collaborators should start with the
data-lake and figure commands rather than running every script manually.

## Data Lake And Reproducibility

| Script | Purpose | Typical command |
|---|---|---|
| `prepare_data_lake.py` | Inventories or materializes the shareable data-lake package from `config/data_release.yml`. | `uv run python scripts/prepare_data_lake.py --mode manifest --checksum` |
| `check_reproducibility.py` | Verifies data-lake checksums, derived-stat identity, and figure pixel reproducibility. | `uv run python scripts/check_reproducibility.py` |
| `run_validation.py` | Runs modular pipe, complete HTML-cube, 2-D/3-D hull, climate-attribution, and external-source QA and collates one PDF report. | `uv run python scripts/run_validation.py --external` |
| `run_validation_contrast.py` | Runs deliberate cube corruptions plus a real FIRED geometry threshold failure and builds the separate expected-FAIL contrast report. | `uv run python scripts/run_validation_contrast.py --publish-docs` |
| `cyverse_upload_data_lake.sh` | Uploads a local data-lake package to the shared CyVerse destination with `gocmd`. | `bash scripts/cyverse_upload_data_lake.sh` |

## Dataset Construction

| Script | Purpose |
|---|---|
| `cache_gridmet_years.py` | Builds the local gridMET cache used for climate attribution. |
| `fire_vase_lakehouse_pilot.py` | Builds the Fire VASE lakehouse tables from the configured fire catalog. Use `--full-population` for the manuscript-scale run. |
| `fire_vase_build_climate_tables.py` | Builds centroid/day-level climate exposure tables. |
| `fire_vase_build_perimeter_climate_tables.py` | Builds active-area, cumulative-perimeter, and perimeter-extension climate exposure tables. |
| `fire_vase_developmental_morphology_analysis.py` | Builds developmental morphology, morphospace, stage, coupling, and matched-pair products. |

## Manuscript Analysis And Figures

| Script | Purpose |
|---|---|
| `fire_vase_climate_revision.py` | Recreates the climate-revision analysis products used by the manuscript. |
| `fire_vase_manuscript_claim_audit.py` | Produces claim-audit and null-model tables used by figure validation. |
| `figures/render_all.py` | Renders the checked-in reference figure set under `figures/main/`. |
| `figures/morphospace.py` | Loads and prepares morphospace data shared by figure builders. |
| `figures/statistics.py` | Computes validation, bootstrap, null-model, and summary tables for figures. |
| `figures/style.py` | Defines shared colors, typography, paths, and figure export behavior. |
| `figures/make_figure_*.py` | Build functions for individual manuscript figures. |
| `figures/make_supplementary_figures.py` | Build functions for supplementary validation figures. |

The collaboration-friendly numbered figure entry points live in
`../manuscript_figures/`.

## Manuscript And Report Rendering

| Script | Purpose |
|---|---|
| `build_fire_vase_google_docs_docx.py` | Converts the Markdown manuscript into a Google Docs-ready DOCX. |
| `fire_vase_science_manuscript_pdf.py` | Renders the Science-style manuscript PDF. |
| `fire_vase_morphology_atlas_pdf.py` | Renders morphology atlas PDFs. |
| `fire_vase_population_atlas_pdf.py` | Renders population summary atlas PDFs. |

## Maintenance

| Script | Purpose |
|---|---|
| `check_repository_size.py` | Checks for large generated artifacts before committing. |
| `generate_hero_vase.py` | Regenerates the transparent VPD-colored homepage hero from the data lake. |
| `generate_ai_transparency_report.py` | Regenerates the expanded AI transparency report, charts, and summary tables from repository evidence. |

## Recommended Starting Points

- Recreate or verify the shared data lake:
  `uv run python scripts/check_reproducibility.py`
- Rebuild the package manifest:
  `uv run python scripts/prepare_data_lake.py --mode manifest --checksum`
- Recreate all manuscript figures:
  `uv run python manuscript_figures/00_run_all.py --data-lake data_lake/fire-vase-data-lake-v0.1`
- Run the complete scientific validation suite:
  `uv run python scripts/run_validation.py --external`
