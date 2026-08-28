# Methods Notes

The [v2 methods and audit](reanalysis-v2.md) and
[current manuscript](manuscripts/fire_vase_developmental_morphology/manuscript_v2.md)
supersede the original analysis below. Current shape-only PCA, dated transitions,
nested same-cohort models and matched pairs are generated in `analysis/v2/`.
Historical lakehouse tables remain read-only source inputs, not corrected traits.

These notes connect the manuscript methods to the scripts and data products
needed for reproduction.

## Workflow Overview

1. FIRED event and daily perimeter records define the fire population.
2. gridMET daily climate variables are cached for the manuscript domain and
   period.
3. Fire time is normalized into daily event trajectories.
4. VASE slices are built from daily fire geometry and cumulative fire growth.
5. Climate exposures are attributed to centroid, active-area, cumulative
   perimeter, and perimeter-extension zones.
6. Developmental morphology tables summarize growth, timing, shape, and
   event-stage behavior.
7. Validation and null-model tables support the manuscript figures and claims.

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

## External Data

The manuscript uses FIRED fire records and gridMET daily climate data. See the
[FIRED dataset note](datasets/fired.md) for local cache and citation guidance.

The shared Fire VASE data lake is available through the
[CyVerse Fire_Vase folder](https://de.cyverse.org/data/ds/iplant/home/shared/esiil/Fire_Vase?type=folder&resourceId=ce3e72e4-95d1-11f1-852a-90e2ba675364).
