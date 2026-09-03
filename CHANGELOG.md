# Changelog

## 2026-09-03

- Reorganized the public MkDocs navigation around Overview, Approach, Findings,
  Validation, and Reproduce while preserving every existing technical page and
  URL.
- Rebuilt the homepage as a short scientific story from question through
  representation, findings, confidence, meaning, and reproducibility.
- Added a seven-stage accessible Approach page and four finding-centered pages
  for developmental pathways, temporal ordering, weather versus recent state,
  and matched-fire diagnostics.
- Reframed the validation landing page around scientific threats while keeping
  all six detailed QA modules and the expected-failure contrast subordinate and
  directly accessible.
- Added a user-intent reproduction landing page and a first-class inventory of
  all four preserved Jupyter notebooks, including purpose, inputs, outputs, and
  status.
- Aligned the reproduction vignette with the canonical v2 runner, added
  reusable narrative components and responsive styles, and recorded the
  non-destructive information-architecture migration plan under `analysis/`.

## 2026-09-02

- Updated the website narrative to match the latest `main-22.pdf` and
  `supplementary-4.pdf` editorial sources, with clearer boundaries around
  developmental geometry, null compression, state predictability, weather,
  and causal inference.
- Rebuilt the figure page as a complete, navigable gallery containing the five
  current main figures, four current supplementary figures, final adversarial
  validation, and all five main plus three supplementary historical figures.
- Preserved the prior supplementary export for provenance while promoting
  `supplementary-4.pdf` as the current source across the website and repository
  handoff documentation.

## 2026-08-31

- Added a Google Docs-ready editable DOCX of the current `main-22.pdf`
  manuscript, with all five submission figures, accessible image descriptions,
  editable captions and equations, and a reproducible conversion script.
- Added the supplied `main-22.pdf` and `supplementary-3.pdf` drafts and assembled
  visually verified submission PDFs with five main and four supplementary
  figures in PDF/PNG/SVG.
- Restored the missing shared xarray test contracts; the full suite now reports
  152 passed and 2 intentionally skipped with no collection exclusions.
- Added the final adversarial null-geometry, observation-depth, and boundary-day
  sensitivity package, including deterministic tables, a six-panel figure, and
  exact manuscript/figure handoff.
- Added a 1,005-row claim-source registry, manuscript/SI consistency audit,
  extended claim matrix, test report, hash manifest, readiness decision, and
  human-only submission checklist under `analysis/submission_freeze/`.
- Removed visible and hidden placeholder/obsolete provenance text from the final
  PDFs while preserving unedited text pages and full-size figures as vector PDF.

## 2026-08-30

- Added the focused pre-submission compositional-geometry sensitivity without
  changing frozen v2 outputs: exact baseline reproduction followed by
  mean-centered, unscaled Hellinger PCA on the same 10,246 primary fires.
- Added aligned score, Procrustes, score-subspace, frozen-anchor distance,
  nearest-neighbor, extreme-tail and displayed-exemplar comparisons, plus a
  six-panel PDF/PNG, deterministic tests, hashes and manuscript/figure handoff.
- The sensitivity supports stable broad developmental geometry while qualifying
  local neighborhoods and extreme exemplars as representation-dependent.
- Recentered the README and documentation website on the manuscript's primary
  contribution: Fire VASE changes the response from wildfire endpoints to
  comparable observed developmental pathways.
- Added a manuscript narrative page and direct access to `main-16.pdf` and
  `supplementary-2.pdf`, while marking the unresolved supplementary placeholders
  as draft material rather than validated findings.
- Reordered the public methods story so morphology is constructed before
  weather is introduced, and aligned the figure, data-lake, FIRED, reproduction,
  code-map, navigation, and v2 evidence pages with the manuscript's
  representation-to-explanation sequence.
- Preserved the corrected v2 analysis as the authority for numerical claims and
  made the distinction between the manuscript framing and validated evidence
  explicit.

## 2026-08-28

- Completed a second-pass scientific validation on the corrected v2 baseline:
  unchanged-feature geometry stability, expanded order/allocation nulls, endpoint
  projections, year-adjusted primary weather associations, VPD-specific held-out
  ablations and coefficient/support checks, and matching balance/caliper tests.
- Added the requested correction audit, old/new headline table, A-M claim matrix,
  scientific story, 26-point final report, Prism handoff and reproducibility freeze
  under `analysis/scientific_validation/`, plus a reconstructed `PROMPT_LOG.md`.
- Simplified main Figures 2/3, added validation supplements S2/S3, and revised
  only evidence-dependent manuscript content. Used the user-supplied remote
  `main-16.pdf` for title/authorship/framing guidance without modifying it.
- Added defensive checks for unsupported fixed-protocol configuration overrides
  and ambiguous duplicate prior-day state. Neither affects current real-data
  estimates. Recorded the pre-existing missing-test-helper collection gap.

- Reproduced the v1 event/state statistics and five figures in an isolated
  comparison archive before introducing corrected versioned results.
- Added v2 source-to-table audits, true observed daily peaks, correctly normalized
  entropy, dated observation support and actual-pulse neighborhood rules.
- Replaced the primary mixed-scale median-centered SVD with mean-centered PCA
  of mass-conserving normalized growth allocation. Added observation/resolution,
  trait/legacy-space, bootstrap, year/region and allocation-null sensitivities.
- Added common-cohort nested weather models, exact calendar-day autoregressive
  models, day-t newly burned-area centroid weather, blocked transfer, conditional
  cluster uncertainty and disjoint caliper-constrained matching with nulls.
- Made the numbered figure pipeline default to v2, with explicit legacy mode.
  Added five versioned main figures, a supplement, manuscript/PDF and audit;
  preserved prior generations and withdrew the 0.349 cross-response headline.
- Renamed the pilot's catalog mean growth quantity and rejected missing/invalid
  raw growth instead of imputing zeros. Added methodological invariant tests.
- Synchronized documentation with the versioned outputs; source data and large
  regenerable Parquet products remain outside Git.

## 2026-08-25

- Added a separate expected-failure contrast report: a clean cube control,
  deterministic latitude-reversal/time-scramble/dropped-day corruptions, and a
  real FIRED event whose 125 m simplification exceeds the operational area
  threshold. Added its modular evidence and website walkthrough without
  changing the six-module production PASS report.
- Added a real-cube HTML integrity audit that verifies canonical dimension
  order, coordinate uniqueness/direction, contiguous daily time, all six shell
  faces, every interior time/x/y plane, corner landmarks, exact decoded RGBA
  pixels, and embedded source/coordinate hashes.
- Added 3-D FIRED hull construction plots showing raw polygons, equal-step
  boundary samples, directional support rings, and the triangulated production
  mesh, plus interactive 1-, 3-, and 7-day averaging and cumulative-envelope
  alternatives with quantitative displacement metrics.
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
