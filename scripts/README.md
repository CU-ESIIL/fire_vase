# Fire VASE Script Map

This folder contains the code used to build, analyze, package, and verify the
Fire VASE manuscript data products. Most collaborators should start with the
data-lake and figure commands rather than running every script manually.

## Data Lake And Reproducibility

| Script | Purpose | Typical command |
|---|---|---|
| `prepare_data_lake.py` | Inventories or materializes the shareable data-lake package from `config/data_release.yml`. | `uv run python scripts/prepare_data_lake.py --mode manifest --checksum` |
| `check_reproducibility.py` | Verifies data-lake checksums, derived-stat identity, and figure pixel reproducibility. | `uv run python scripts/check_reproducibility.py` |
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

## Recommended Starting Points

- Recreate or verify the shared data lake:
  `uv run python scripts/check_reproducibility.py`
- Rebuild the package manifest:
  `uv run python scripts/prepare_data_lake.py --mode manifest --checksum`
- Recreate all manuscript figures:
  `uv run python manuscript_figures/00_run_all.py --data-lake data_lake/fire-vase-data-lake-v0.1`
