# FIRED (Fire Events Delineation)

### What this dataset is
FIRED provides event-level and per-day fire perimeter polygons for the conterminous United States and Alaska from November 2001 to March 2021. Daily footprints track fire growth through time, while event tables summarize ignition, containment, and size.

## Manuscript Use

The manuscript workflow uses FIRED event and daily perimeter records as the
source fire-history product. The reproducible data-lake pipeline reads local
FIRED GeoPackage caches, converts daily event histories into Fire VASE
lakehouse tables, and then builds developmental morphology products. In the
manuscript argument, this ordered history—not the final perimeter alone—is the
response to be compared and ultimately explained.

See the [full reproduction vignette](../vignette-reproduce-pipeline.md) for the
end-to-end command order.

## Preview Plot

![FIRED preview](../assets/datasets/fired-preview.png)

### Who collects it and why
FIRED was assembled by Balch, Iglesias, and collaborators to provide a consistent, research-grade record of wildland fire events for studying drivers, impacts, and fire–climate interactions. Its coverage and methodological transparency make it a common reference for fire science in North America.

### How CubeDynamics accesses it
FIRED layers are pulled from a CU Scholar ZIP archive, extracted on-the-fly, and cached locally in a user directory. Functions load the requested layer (events or daily perimeters), reproject to EPSG:4326, and return GeoDataFrames ready to intersect with climate cubes. Users can opt into automatic downloads or rely on pre-populated cache files for offline analysis.

### Important variables and dimensions
| Field | Meaning | Units |
|-----|--------|------|
| id | FIRED event identifier | unitless |
| date | Observation date for daily perimeters | ISO date |
| geometry | Polygon footprint in EPSG:4326 | degrees |
| area_ha (if present) | Burned area for the polygon | hectares |

### Citation
Balch et al. (2020). FIRED (Fire Events Delineation): An Open, Flexible Algorithm
and Database of US Fire Events Derived from the MODIS Burned Area Product
(2001-2019). *Remote Sensing*, 12, 3498.
[Original FIRED article](https://doi.org/10.3390/rs12213498).

The v2 source audit identifies actual cached dates from 2 November 2000 to
1 May 2021; do not infer exact coverage from the GeoPackage filename. Daily
records are not always consecutive calendar days. See the
[corrected analysis](../reanalysis-v2.md).

---
Back to [Data Boundary](../data.md)
Next recommended page: [Reproduce the Data Lake](../reproduce-data-lake.md)
