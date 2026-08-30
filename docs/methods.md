# Methods Notes

These notes follow the [manuscript's scientific argument](manuscript.md): first
construct a common response from the ordered history of observed growth, then
project candidate explanations onto it. The [corrected v2 methods and audit](reanalysis-v2.md)
are authoritative for quantitative claims. Current shape-only PCA, dated
transitions, nested same-cohort models, and matched pairs are generated in
`analysis/v2/`. Historical lakehouse tables remain read-only source inputs, not
corrected traits.

These notes connect the manuscript methods to the scripts and data products
needed for reproduction.

## Workflow Overview

1. FIRED event and observation records define the observed fire population.
2. Mapped area increments are ordered and their date support and gaps audited.
3. VASEs encode normalized cumulative area through relative developmental time.
4. Shape coordinates and traits summarize timing, concentration, persistence,
   recurrence, and taper without using weather to define the axes.
5. gridMET weather is attached afterward as a first external explanatory layer;
   the corrected analysis uses day-specific exposure where required.
6. State models and matched comparisons ask when exposure adds information and
   where the present explanation remains insufficient.
7. Stability, null, uncertainty, and provenance checks bound every manuscript
   claim.

## Data Products

Core schemas are stored in
[`schemas/`](https://github.com/CU-ESIIL/fire_vase/tree/main/schemas).

The main lakehouse tables are:

- `fire_catalog.parquet`
- `fire_traits.parquet`
- `vase_slices.parquet`
- `vase_climate_exposures.parquet`
- `processing_manifest.parquet`
- `processing_failures_climate.parquet`

Developmental morphology products are written under:

```text
scratch/fire_vase_developmental_morphology/
```

The figure validation tables are stored under:

```text
figures/main/derived_stats/
analysis/claim_audit_stats/
analysis/climate_revision_stats/
```

## Reproducible Methods Code

- Source/cache preparation:
  [cache_gridmet_years.py](https://github.com/CU-ESIIL/fire_vase/blob/main/scripts/cache_gridmet_years.py)
- Fire VASE lakehouse:
  [fire_vase_lakehouse_pilot.py](https://github.com/CU-ESIIL/fire_vase/blob/main/scripts/fire_vase_lakehouse_pilot.py)
- Climate attribution:
  [fire_vase_build_climate_tables.py](https://github.com/CU-ESIIL/fire_vase/blob/main/scripts/fire_vase_build_climate_tables.py)
  and
  [fire_vase_build_perimeter_climate_tables.py](https://github.com/CU-ESIIL/fire_vase/blob/main/scripts/fire_vase_build_perimeter_climate_tables.py)
- Developmental morphology:
  [fire_vase_developmental_morphology_analysis.py](https://github.com/CU-ESIIL/fire_vase/blob/main/scripts/fire_vase_developmental_morphology_analysis.py)
- Manuscript revision analysis:
  [fire_vase_climate_revision.py](https://github.com/CU-ESIIL/fire_vase/blob/main/scripts/fire_vase_climate_revision.py)
- Manuscript figure rendering:
  [manuscript_figures](https://github.com/CU-ESIIL/fire_vase/tree/main/manuscript_figures)

## Interpretation Boundary

The VASE is a standardized observed history, not a geographic silhouette, a
natural fire type, or a process model. Weather associations are retrospective
and do not establish causal control. Mismatch examples generate testable cases
for additional layers; they do not identify the omitted mechanism or estimate
its ecological prevalence.

## External Data

The manuscript uses FIRED fire records and gridMET daily climate data. See the
[FIRED dataset note](datasets/fired.md) for local cache and citation guidance.

The shared Fire VASE data lake is available through the
[CyVerse Fire_Vase folder](https://de.cyverse.org/data/ds/iplant/home/shared/esiil/Fire_Vase?type=folder&resourceId=ce3e72e4-95d1-11f1-852a-90e2ba675364).
