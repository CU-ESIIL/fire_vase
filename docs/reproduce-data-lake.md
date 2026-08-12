# Reproduce the Data Lake

The Fire VASE data lake is the manuscript-scale handoff package. It contains
the source fire and climate caches, Parquet lakehouse tables, developmental
morphology outputs, schemas, figures, manuscripts, and release manifests needed
to reproduce the analysis.

## Get the Shared Data Lake

The current shared folder is:

[CyVerse Fire_Vase](https://de.cyverse.org/data/ds/iplant/home/shared/esiil/Fire_Vase?type=folder&resourceId=ce3e72e4-95d1-11f1-852a-90e2ba675364)

Expected local package path:

```text
data_lake/fire-vase-data-lake-v0.1
```

After downloading or syncing the package, verify every file against the release
checksums:

```bash
uv run python scripts/check_reproducibility.py
```

This reads the full package, so it can take several minutes.

## Inspect Or Package A Local Lake

The release definition is
[`config/data_release.yml`](https://github.com/CU-ESIIL/fire_vase/blob/main/config/data_release.yml).

Create or refresh the manifest and checksums:

```bash
uv run python scripts/prepare_data_lake.py --mode manifest --checksum
```

Create a materialized handoff directory with hardlinks:

```bash
uv run python scripts/prepare_data_lake.py --mode hardlink --checksum
```

Create an independent copy for upload or external transfer:

```bash
uv run python scripts/prepare_data_lake.py --mode copy --checksum
```

The packager writes:

- `manifest.json`
- `file_manifest.csv`
- `checksums.sha256`
- `README.md`
- `files/`, for `hardlink` and `copy` modes

## Rebuild From Source

Use this path when you want to recreate the lakehouse rather than start from
the shared data lake.

1. Install the repository.

   ```bash
   uv sync
   ```

2. Cache the gridMET variables used by the manuscript.

   ```bash
   uv run python scripts/cache_gridmet_years.py --preset comprehensive --keep-going
   ```

3. Build the full Fire VASE lakehouse tables.

   ```bash
   uv run python scripts/fire_vase_lakehouse_pilot.py \
     --config config/fire_vase_pipeline.yml \
     --output-root scratch/fire_vase_run_full \
     --full-population
   ```

4. Build centroid and perimeter climate attribution tables.

   ```bash
   uv run python scripts/fire_vase_build_climate_tables.py \
     --include-optional-variables \
     --table-root scratch/fire_vase_run_full/tables

   uv run python scripts/fire_vase_build_perimeter_climate_tables.py \
     --include-optional-variables
   ```

5. Build developmental morphology and climate-coupling products.

   ```bash
   uv run python scripts/fire_vase_developmental_morphology_analysis.py \
     --table-root scratch/fire_vase_run_full/tables \
     --data-output-dir scratch/fire_vase_developmental_morphology
   ```

6. Regenerate the climate-revision analysis products and manuscript figures.

   ```bash
   uv run python scripts/fire_vase_climate_revision.py
   ```

7. Refresh the data-lake package metadata.

   ```bash
   uv run python scripts/prepare_data_lake.py --mode manifest --checksum
   ```

## Main Code Links

- [Data release config](https://github.com/CU-ESIIL/fire_vase/blob/main/config/data_release.yml)
- [Data-lake packager](https://github.com/CU-ESIIL/fire_vase/blob/main/scripts/prepare_data_lake.py)
- [Reproducibility checker](https://github.com/CU-ESIIL/fire_vase/blob/main/scripts/check_reproducibility.py)
- [Lakehouse builder](https://github.com/CU-ESIIL/fire_vase/blob/main/scripts/fire_vase_lakehouse_pilot.py)
- [Climate table builder](https://github.com/CU-ESIIL/fire_vase/blob/main/scripts/fire_vase_build_climate_tables.py)
- [Perimeter climate builder](https://github.com/CU-ESIIL/fire_vase/blob/main/scripts/fire_vase_build_perimeter_climate_tables.py)
- [Developmental morphology analysis](https://github.com/CU-ESIIL/fire_vase/blob/main/scripts/fire_vase_developmental_morphology_analysis.py)
