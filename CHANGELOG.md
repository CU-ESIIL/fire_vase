# Changelog

## 2026-08-25

- Added a modular real-data validation suite for CubeDynamics pipe/direct
  equivalence, chunk-preserving GridMET access, FIRED simplification and
  time-hull sensitivity, centroid/date table reproduction, fractional
  polygon-pixel climate overlap, and independent NCAR GridMET mirror checks.
- Added per-module PNG/CSV/JSON QA artifacts and a rendered, visually verified
  collated validation PDF.
- Added a runnable validation notebook and a multi-page website validation
  section with one vignette-style page per scientific boundary.
- Documented the accepted 0-125 m simplification range separately from 500 m
  and 1000 m stress tests, and retained centroid climate as the explicit
  lakehouse baseline while exposing fractional overlap as sensitivity analysis.

## 2026-08-12

- Expanded the climate-revision manuscript methods with reproducible data-lake,
  VASE construction, climate attribution, modeling, and figure-generation
  details, then refreshed the Google Docs-ready DOCX.
- Expanded the root and manuscript-figure README guides with linked data-lake
  rebuild steps, CubeDynamics/Fire VASE pipeline scripts, and figure
  reproduction entry points.
- Added `scripts/check_reproducibility.py` to verify data-lake checksums,
  derived-stat byte identity, and figure pixel reproducibility.
- Reorganized the documentation website as manuscript supplementary material
  with focused pages for data-lake, figure, and methods reproduction.
- Added collaborator-facing code maps and expanded inline documentation for the
  data-lake, reproducibility, and manuscript-figure orchestration scripts.
- Added an end-to-end website vignette for reproducing the data lake, analysis
  products, manuscript figures, and final reproducibility checks as one
  pipeline.
- Added a runnable Jupyter notebook companion for the end-to-end reproduction
  vignette.
- Redesigned the website homepage with stronger Fire VASE branding, hierarchy,
  and reproduction pathways.
- Added a Python-generated transparent VPD-colored Fire VASE hero asset and
  generation script.
- Added an expanded, periodically regenerable AI transparency report with
  prompt-basis statistics, repository artifact inventories, vetting summaries,
  test summaries, and charts.
- Added current manuscript figure galleries to the website figure reproduction
  page so readers can see the rendered outputs as well as the code.
- Archived legacy CubeDynamics docs, superseded manuscript review/history
  materials, and ad hoc visual checks outside the public supplement docs tree.
- Added a `--full-population` lakehouse-build option and aligned the data
  release rebuild workflow with the full data-lake paths.

## 2026-08-11

- Added `manuscript_figures/` with numbered scripts that render manuscript
  figures from a Fire VASE data-lake package into the same folder.
- Added data-lake path overrides for the shared figure helpers and declared
  `pyarrow` so Parquet-based figure inputs work in the locked environment.
- Added a Zotero-importable manuscript bibliography in `bibliography/`.
- Regenerated the Google Docs-ready manuscript DOCX and sanitized title styling
  for upload/import into Google Docs.

## 2026-07-23

- Migrated Fire VASE research material from `CU-ESIIL/cubedynamics` at commit
  `0f2538d393abde5d1ff503e2c5dd73d01562b53e`.
- Added project documentation for the repository split, data boundary, examples,
  and publication-facing MkDocs navigation.
- Added transitional packaging and tests so the copied research code can be
  installed and smoke-tested before a later namespace cleanup.
- Added a full data-lake handoff workflow in `config/data_release.yml` and
  `scripts/prepare_data_lake.py` for manifest, hardlink, or copy exports.
