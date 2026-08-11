# Data Boundary

Fire VASE treats the VASE as a scientific data object first and a figure second.
The repository tracks code, schemas, documentation, selected derived tables,
publication figures, and small manifests.

## Tracked Here

- pipeline configs and schema contracts;
- manuscript drafts, reviews, and citation audits;
- figure-generation scripts and selected rendered figures;
- small derived CSVs used in the manuscript record;
- manifests that identify release artifacts or summarize generated products.

## Kept Outside Git

These belong in local scratch storage, shared object storage, or an archived
data release:

- FIRED downloads and local source caches;
- gridMET caches;
- full lakehouse tables such as Parquet or GeoParquet;
- Zarr, NetCDF, GLB, TIFF, and bulk rendered asset directories;
- rerun-specific scratch outputs and checkpoints.

Default ignored roots include `artifacts/`, `scratch/`, `lakehouse/`, `tmp/`,
and `manifests/runs/`.

## Provenance Expectations

When adding new data products, document:

- source and access method;
- format and schema;
- license, citation, and reuse constraints;
- whether the artifact is source data, a derived table, or a rendered view;
- the script or command that generated it.

## Whole Data Lake Handoff

Use the data-lake packager to inventory or materialize the full handoff:

```bash
python scripts/prepare_data_lake.py --mode manifest
```

This writes `data_lake/fire-vase-data-lake-v0.1/` with `manifest.json`,
`file_manifest.csv`, `checksums.sha256`, and a generated README. In manifest
mode, it does not copy the 37 GB gridMET/FIRED cache; it records where the lake
currently lives and what should be shared.

To create a full local handoff directory without duplicating bytes when source
and destination are on the same filesystem:

```bash
python scripts/prepare_data_lake.py --mode hardlink --checksum
```

To create an independent copy for an external drive or cloud upload:

```bash
python scripts/prepare_data_lake.py --mode copy --checksum
```

The release config lives at `config/data_release.yml`. The current full lake
definition includes:

- `artifacts/fire-vase-gridmet-real/`: FIRED GeoPackage cache, candidate events,
  and gridMET NetCDF cache;
- `scratch/fire_vase_run_full/`: full Fire VASE reports and Parquet lakehouse
  tables;
- `scratch/fire_vase_developmental_morphology/`: developmental morphospace,
  stage, coupling, and matched-pair tables;
- repository-side derived outputs, figures, schemas, configs, and manuscript
  artifacts.
