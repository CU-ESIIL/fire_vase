# FIRED (Fire Event Reconstruction and Discussion)

### What this dataset is
FIRED provides event-level and per-day fire perimeter polygons for the conterminous United States and Alaska from November 2001 to March 2021. Daily footprints track fire growth through time, while event tables summarize ignition, containment, and size.

## Quickstart

### Get the stream (CubeDynamics grammar)

```python
import cubedynamics as cd
from cubedynamics import pipe, verbs as v

fired_evt = cd.fired_event(event_id=21281)
clim = cd.gridmet(
    lat=fired_evt.centroid_lat,
    lon=fired_evt.centroid_lon,
    start=str(fired_evt.t0.date()),
    end=str(fired_evt.t1.date()),
    variable="tmmx",
)

pipe(clim) | v.extract(fired_event=fired_evt) | v.fire_plot(fired_event=fired_evt)
```

### Preview plot

![FIRED preview](../assets/datasets/fired-preview.png)

!!! note
    Image placeholder — after running the code below locally, save a screenshot to `docs/assets/datasets/fired-preview.png`.

### Regenerate this plot

1. Execute the Quickstart code to load the FIRED event and matching gridMET slice.
2. Collect the viewer returned from the pipe for export:

    ```python
    viewer = (
        pipe(clim) | v.extract(fired_event=fired_evt) | v.fire_plot(fired_event=fired_evt)
    ).unwrap()
    viewer.save("docs/assets/datasets/fired-preview.html")
    ```

3. Open `docs/assets/datasets/fired-preview.html` in a browser and save a 1200×700 px PNG screenshot to `docs/assets/datasets/fired-preview.png`.

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

See also: [Fire event vase + climate merge (fire_plot)](../recipes/fire_event_vase_hull.md)

---
Back to [Data Boundary](../data.md)
Next recommended page: [Fire event vase + climate merge](../recipes/fire_event_vase_hull.md)
