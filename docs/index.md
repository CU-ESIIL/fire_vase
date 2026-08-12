# Fire VASE Supplement

This site is the supplementary information hub for the Fire VASE manuscript. It
points to the data lake, the code used to build the analysis tables, and the
numbered scripts that regenerate the manuscript figures.

[Reproduce the Data Lake](reproduce-data-lake.md){ .md-button .md-button--primary }
[Reproduce the Figures](reproduce-figures.md){ .md-button }
[Code Map](code-map.md){ .md-button }

<div class="grid cards" markdown>

- **Data Lake**

  ---

  Download or rebuild the FIRED/gridMET caches, Parquet lakehouse tables,
  developmental morphology tables, figures, schemas, and manuscript artifacts.

- **Methods**

  ---

  Follow the manuscript workflow from source fire records through VASE
  construction, climate attribution, developmental morphology, and validation.

- **Figures**

  ---

  Run one command to regenerate the manuscript figure set, or run the numbered
  scripts for individual figures.

</div>

## What To Use

- Data lake handoff:
  [CyVerse Fire_Vase folder](https://de.cyverse.org/data/ds/iplant/home/shared/esiil/Fire_Vase?type=folder&resourceId=ce3e72e4-95d1-11f1-852a-90e2ba675364)
- Source code:
  [CU-ESIIL/fire_vase](https://github.com/CU-ESIIL/fire_vase)
- Script summaries:
  [Code Map](code-map.md)
- Reusable VASE implementation:
  [CU-ESIIL/cubedynamics](https://github.com/CU-ESIIL/cubedynamics)
- Current manuscript draft:
  [Science-style revision](manuscripts/fire_vase_developmental_morphology/manuscript_climate_revision_science_style.md)

Start with the data-lake page if you want to reproduce the dataset. Start with
the figure page if you already have the data lake and want to regenerate the
publication figures.
