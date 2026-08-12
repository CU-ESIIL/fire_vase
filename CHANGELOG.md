# Changelog

## 2026-08-12

- Expanded the climate-revision manuscript methods with reproducible data-lake,
  VASE construction, climate attribution, modeling, and figure-generation
  details, then refreshed the Google Docs-ready DOCX.
- Expanded the root and manuscript-figure README guides with linked data-lake
  rebuild steps, CubeDynamics/Fire VASE pipeline scripts, and figure
  reproduction entry points.
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
