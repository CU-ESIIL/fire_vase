# Migration From CubeDynamics

This repository was created to pull project-specific Fire VASE research out of
`CU-ESIIL/cubedynamics` while leaving the reusable package API there.

## Source Snapshot

Initial source repository:

- Repository: `CU-ESIIL/cubedynamics`
- Branch: `main`
- Commit: `0f2538d393abde5d1ff503e2c5dd73d01562b53e`
- Migration date: 2026-07-23

## Copied Material

The migration copied the tracked fire/VASE research corpus:

- `analysis/`: claim audits, climate revision summaries, figure restructuring
  notes, method summaries, and small stats tables.
- `config/`: Fire VASE pipeline and storage templates.
- `schemas/`: JSON schemas for source fire records, canonical fire time,
  geometry, traits, events, VASE slices, climate exposures, assets, processing
  runs, processing manifests, failures, and cohort summaries.
- `scripts/`: lakehouse pilots, climate table builders, developmental
  morphology analysis, climate revision, claim audit, atlas/PDF generation, and
  manuscript document builders.
- `scripts/figures/`: publication figure generation helpers.
- `docs/manuscripts/`: manuscript drafts, reviews, citation audits, compliance
  checks, and transparency notes.
- `figures/`, `output/`, `outputs/`: tracked publication figures, rendered
  manuscripts, derived CSVs, and output manifests.
- `examples/`, `notebooks/`, `tests/`: VASE examples and tests from the source
  repo.
- `src/cubedynamics/`: transitional runtime copy so the migrated scripts and
  tests preserve their original import paths.

## What Stayed Conceptually In CubeDynamics

`cubedynamics` should continue to own the general-purpose package surface:

- fire hull/VASE objects and verbs;
- generic cube, streaming, plotting, and event abstractions;
- lightweight examples that demonstrate the reusable API.

This repo should own the project-specific research and publication pipeline:

- manuscript logic and text;
- fire VASE lakehouse schemas and processing contracts;
- data provenance decisions;
- publication figures and reproducible analysis scripts;
- collaboration notes and review history.

## Follow-Up Refactor

The first copy preserved `cubedynamics` import paths for traceability. A later
cleanup should decide whether project-specific modules move to
`src/fire_vase/`, with `cubedynamics` installed as a dependency, or whether this
repository keeps a pinned transitional runtime copy for reproducibility.
