# FIRED (Fire Event Reconstruction and Discussion)

### What this dataset is
FIRED provides event-level and per-day fire perimeter polygons for the conterminous United States and Alaska from November 2001 to March 2021. Daily footprints track fire growth through time, while event tables summarize ignition, containment, and size.

## Manuscript Use

The manuscript workflow uses FIRED event and daily perimeter records as the
source fire-history product. The reproducible data-lake pipeline reads local
FIRED GeoPackage caches, converts daily event histories into Fire VASE
lakehouse tables, and then builds developmental morphology products.

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
Balch, J. K., Iglesias, V., Braswell, A., Rossi, M. W., Joseph, M. B., Mahood, A., Arkle, R. S., & Boer, M. M. (2020). FIRED: A global fire event database. *Scientific Data*, 7, 164. https://doi.org/10.1038/s41597-020-0524-5

---
Back to [Data Boundary](../data.md)
Next recommended page: [Reproduce the Data Lake](../reproduce-data-lake.md)
