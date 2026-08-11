# Changelog

## 2026-07-23

- Migrated Fire VASE research material from `CU-ESIIL/cubedynamics` at commit
  `0f2538d393abde5d1ff503e2c5dd73d01562b53e`.
- Added project documentation for the repository split, data boundary, examples,
  and publication-facing MkDocs navigation.
- Added transitional packaging and tests so the copied research code can be
  installed and smoke-tested before a later namespace cleanup.
- Added a full data-lake handoff workflow in `config/data_release.yml` and
  `scripts/prepare_data_lake.py` for manifest, hardlink, or copy exports.
