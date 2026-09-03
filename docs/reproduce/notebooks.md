# Jupyter notebook index

<p class="fire-page-deck">All four notebooks remain in their original repository paths. They serve different roles: canonical reproduction, validation, implementation demonstration, and optional 3-D exploration.</p>

<div class="fire-notebook-card fire-notebook-card--primary" markdown>
<span>Canonical reproduction</span>

## `reproduce_fire_vase_pipeline.ipynb`

**Purpose:** Walk through environment setup, data-lake acquisition or rebuild,
manuscript analysis, figure rendering, whole-pipeline checks, and release
refresh.

**Inputs:** Repository environment; shared v0.1 data lake or local FIRED and
gridMET source caches; project configuration.

**Outputs:** Current analysis products, manuscript figures, validation and
reproducibility reports, and optionally a refreshed shareable data-lake package.

**Place in the analysis:** Primary notebook companion to the full reproduction
vignette. The current quantitative generation is v2; historical stages remain
explicitly labeled.

[Open on GitHub](https://github.com/CU-ESIIL/fire_vase/blob/main/notebooks/reproduce_fire_vase_pipeline.ipynb){ .md-button .md-button--primary .fire-button }
[Read the web vignette](../vignette-reproduce-pipeline.md){ .md-button .fire-button }
</div>

<div class="fire-notebook-card" markdown>
<span>Scientific and software validation</span>

## `validate_fire_vase_pipeline.ipynb`

**Purpose:** Run one inspectable section per production validation module and
the separate expected-failure contrast.

**Inputs:** Materialized FIRED/gridMET data lake, validation configuration, and
the installed repository environment. The independent external-source section
requires network access.

**Outputs:** Module-level PNG, CSV, HTML, and JSON evidence plus the collated
suite report.

**Place in the analysis:** First-class validation notebook. It checks pipe and
stream behavior, cube/HTML integrity, 2-D and 3-D geometry, climate attribution,
external sources, and deliberate corruptions.

[Open on GitHub](https://github.com/CU-ESIIL/fire_vase/blob/main/notebooks/validate_fire_vase_pipeline.ipynb){ .md-button .md-button--primary .fire-button }
[Read the validation overview](../validation/index.md){ .md-button .fire-button }
</div>

<div class="fire-notebook-card" markdown>
<span>Implementation demonstration</span>

## `06_vase_volume_basic.ipynb`

**Purpose:** Demonstrate basic VASE masking and viewer overlays using both verb
and pipe/grammar APIs.

**Inputs:** A small synthetic xarray cube constructed in the notebook and a
two-section `VaseDefinition`; no external research data required.

**Outputs:** Baseline and masked cube views plus a VASE-outline overlay.

**Place in the analysis:** Reusable implementation example, not a source of
manuscript statistics or figures.

[Open on GitHub](https://github.com/CU-ESIIL/fire_vase/blob/main/notebooks/06_vase_volume_basic.ipynb){ .md-button .fire-button }
</div>

<div class="fire-notebook-card" markdown>
<span>Optional 3-D exploration</span>

## `07_vase_volume_3d_viz.ipynb`

**Purpose:** Show point extraction and optional scientific 3-D visualization
with PyVista.

**Inputs:** A small synthetic xarray cube and `VaseDefinition` created in the
notebook; PyVista is optional.

**Outputs:** Extracted point arrays and, when the optional dependency is
available, an interactive 3-D scatter view.

**Place in the analysis:** Exploratory visualization example, not a canonical
paper or validation workflow.

[Open on GitHub](https://github.com/CU-ESIIL/fire_vase/blob/main/notebooks/07_vase_volume_3d_viz.ipynb){ .md-button .fire-button }
</div>

## Preservation and execution notes

- Notebook paths are unchanged; no notebook was deleted, merged, or replaced
  with prose.
- The notebook index groups assets conceptually without moving them.
- Canonical commands also appear as scripts so automated reproduction does not
  depend on interactive execution.
- Large real-data inputs remain outside Git and are resolved through the
  documented data-lake path.

<nav class="fire-next">
<a href="../"><small>Back</small><strong>Reproduce Fire VASE</strong></a>
<a href="../../code-map/"><small>Next</small><strong>Inspect the implementation →</strong></a>
</nav>
