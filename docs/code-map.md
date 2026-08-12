# Code Map

This page summarizes the code a collaborator is most likely to need when
recreating the Fire VASE data lake, manuscript analyses, or figures.

## Start Here

- Reproduce the full data lake:
  [Reproduce the Data Lake](reproduce-data-lake.md)
- Reproduce manuscript figures:
  [Reproduce the Figures](reproduce-figures.md)
- Read script-level summaries:
  [scripts/README.md](https://github.com/CU-ESIIL/fire_vase/blob/main/scripts/README.md)

## Data Lake Scripts

- [prepare_data_lake.py](https://github.com/CU-ESIIL/fire_vase/blob/main/scripts/prepare_data_lake.py):
  inventories, checksums, hardlinks, or copies the full handoff package.
- [check_reproducibility.py](https://github.com/CU-ESIIL/fire_vase/blob/main/scripts/check_reproducibility.py):
  checks data-lake hashes, derived statistics, and figure pixel identity.
- [generate_hero_vase.py](https://github.com/CU-ESIIL/fire_vase/blob/main/scripts/generate_hero_vase.py):
  regenerates the transparent VPD-colored homepage hero from the data lake.
- [generate_ai_transparency_report.py](https://github.com/CU-ESIIL/fire_vase/blob/main/scripts/generate_ai_transparency_report.py):
  regenerates the expanded AI transparency report and usage charts from repository evidence.
- [config/data_release.yml](https://github.com/CU-ESIIL/fire_vase/blob/main/config/data_release.yml):
  declares what belongs in the public data-lake release.

## Dataset Construction Scripts

- [cache_gridmet_years.py](https://github.com/CU-ESIIL/fire_vase/blob/main/scripts/cache_gridmet_years.py):
  downloads or refreshes the gridMET cache used for climate attribution.
- [fire_vase_lakehouse_pilot.py](https://github.com/CU-ESIIL/fire_vase/blob/main/scripts/fire_vase_lakehouse_pilot.py):
  builds the manuscript lakehouse tables from FIRED inputs.
- [fire_vase_build_climate_tables.py](https://github.com/CU-ESIIL/fire_vase/blob/main/scripts/fire_vase_build_climate_tables.py):
  builds centroid climate attribution tables.
- [fire_vase_build_perimeter_climate_tables.py](https://github.com/CU-ESIIL/fire_vase/blob/main/scripts/fire_vase_build_perimeter_climate_tables.py):
  builds active-area and perimeter-zone climate attribution tables.
- [fire_vase_developmental_morphology_analysis.py](https://github.com/CU-ESIIL/fire_vase/blob/main/scripts/fire_vase_developmental_morphology_analysis.py):
  builds developmental morphology and morphospace products.

## Figure Scripts

The easiest entry points are the numbered wrappers in
[manuscript_figures](https://github.com/CU-ESIIL/fire_vase/tree/main/manuscript_figures).
They all share
[_figure_runner.py](https://github.com/CU-ESIIL/fire_vase/blob/main/manuscript_figures/_figure_runner.py),
which resolves data-lake paths and handles cached validation tables.

The shared figure-building code lives in
[scripts/figures](https://github.com/CU-ESIIL/fire_vase/tree/main/scripts/figures).
Those modules contain the actual Matplotlib figure logic.

## Manuscript Artifacts

- [build_fire_vase_google_docs_docx.py](https://github.com/CU-ESIIL/fire_vase/blob/main/scripts/build_fire_vase_google_docs_docx.py):
  builds the Google Docs-ready manuscript file.
- [manuscript_climate_revision_science_style.md](manuscripts/fire_vase_developmental_morphology/manuscript_climate_revision_science_style.md):
  current manuscript text used for the Google Docs handoff.
