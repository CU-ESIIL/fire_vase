# Website information-architecture migration plan

Date: 2026-09-03

## Safety boundary

This migration changes the MkDocs navigation, adds reader-facing narrative
pages, and updates shared presentation styles. It does not move or delete
notebooks, analysis code, tests, schemas, manuscript sources, generated data,
figures, validation evidence, or provenance records. Existing documentation
paths remain valid.

## Public hierarchy

1. Overview (`docs/index.md`)
2. Approach (`docs/approach.md`)
3. Findings (`docs/findings/`)
4. Validation (`docs/validation/index.md`)
5. Reproduce (`docs/reproduce/index.md`)
6. Paper and Project Record as supporting destinations

## Migration choices

- Preserve existing technical URLs and relabel/re-nest them in `mkdocs.yml`.
- Add narrative wrappers for Approach, Findings, Reproduce, and notebooks.
- Keep `docs/manuscript.md`, `docs/reanalysis-v2.md`, all validation modules,
  data/reproduction guides, and project records at their current paths.
- Reuse the current validated v2 figures without modifying their scientific
  content.
- Use the 28 August 2026 v2 manuscript and frozen validation summaries as the
  numerical and interpretive authority.
- Add directional next-step navigation to the new narrative pages.

## Verification

- Build MkDocs with strict warnings.
- Check internal links and asset references.
- Run targeted tests for site configuration/content and the repository's
  existing reproducibility checks where feasible.
- Inspect desktop and narrow-screen rendering of the primary narrative pages.

## Completion record

- Implemented additively; no existing file was moved or deleted.
- `mkdocs build --strict` completed successfully.
- Generated-site audit checked 40 HTML pages with 0 broken internal file or
  fragment references.
- Desktop (1280 × 720) and narrow (390 × 844) browser checks found no horizontal
  overflow, missing narrative images, or console errors.
- Full repository suite completed with 152 passed and 2 intentionally skipped.
