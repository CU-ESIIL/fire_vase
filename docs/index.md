# Fire VASE

Fire VASE is the research workspace for treating fire events as developmental
space-time objects. It collects the manuscript, analysis scripts, schemas,
figures, and tracked derived outputs that were previously embedded in the
`cubedynamics` package repository.

[Read the Migration Note](migration.md){ .md-button .md-button--primary }
[View Manuscripts](manuscripts/fire_vase_developmental_morphology/manuscript_climate_revision_science_style.md){ .md-button }

<div class="grid cards" markdown>

- **Research Corpus**

  ---

  Manuscript drafts, citation audits, formal reviews, analysis notes, and
  figure legends live with the code that generated them.

- **Lakehouse Contract**

  ---

  Schemas, configs, and the data-lake exporter define source fire records,
  canonical fire time, VASE slices, climate exposures, traits, manifests, and
  derived assets.

- **Publication Outputs**

  ---

  Selected figures, PDFs, derived CSVs, and manifests are tracked as current
  publication artifacts; bulk data products remain external or ignored.

</div>

## Repository Roles

`cubedynamics` remains the reusable package for generic cube operations and the
public fire hull/VASE API. This repository is the project-specific research
home for the fire VASE publication pipeline.

The first migration preserved source paths and imports so the current scripts
remain traceable. Later cleanup can move project-specific pieces into a native
`fire_vase` package namespace once the copied content has settled.
