# Reproduce Fire VASE

<p class="fire-page-deck">Everything required to inspect, rerun, validate, or extend this research is available here—from source-data contracts and notebooks to frozen claims and figure hashes.</p>

<div class="fire-repro-grid" markdown>
<div markdown><span>I want the data</span>

## Download, inspect, or rebuild

Use the shared v0.1 data lake for the shortest path. Source documentation,
schemas, release inventory, checksums, exclusions, and a full rebuild route are
kept alongside it.

[Data and data lake →](../reproduce-data-lake.md)
</div>
<div markdown><span>I want to reproduce the paper</span>

## Run the canonical v2 workflow

Install the locked environment, materialize the data lake, regenerate the v2
analysis and figures, run scientific validation, and compare output hashes.

[Full reproduction vignette →](../vignette-reproduce-pipeline.md)
</div>
<div markdown><span>I want the notebooks</span>

## Open all four Jupyter assets

The canonical reproduction notebook and validation notebook sit beside two
implementation-focused VASE volume notebooks. Their roles, inputs, outputs,
and status are indexed explicitly.

[Notebook index →](notebooks.md)
</div>
<div markdown><span>I want the implementation</span>

## Trace code to evidence

Inspect package code, analysis scripts, numbered figure entry points, schemas,
tests, configuration, and validation modules.

[Code map →](../code-map.md)
</div>
<div markdown><span>I want the figures</span>

## Render or audit every figure

Browse the current main figures, supplementary diagnostics, adversarial checks,
and preserved historical generation—with the commands that rebuild them.

[Figure workflow →](../reproduce-figures.md)
</div>
<div markdown><span>I want provenance</span>

## Follow claims and corrections

Review input/output hashes, correction history, scientific-validation records,
AI transparency, citation audit, manuscript sources, and the project migration
record.

[Provenance map →](#provenance-and-project-record)
</div>
</div>

## Quick start: reproduce the current paper

**Requirements:** Git, `uv`, Python 3.9 or newer, and the materialized Fire VASE
v0.1 data lake at `data_lake/fire-vase-data-lake-v0.1`. External validation
also requires network access.

```bash
git clone https://github.com/CU-ESIIL/fire_vase.git
cd fire_vase
uv sync

PYTHONPATH=src:scripts OPENBLAS_NUM_THREADS=1 \
MPLCONFIGDIR=/tmp/fire-vase-v2-mpl \
.venv/bin/python manuscript_figures/00_run_all.py \
  --generation v2 \
  --data-lake data_lake/fire-vase-data-lake-v0.1

PYTHONPATH=src:scripts MPLBACKEND=Agg \
MPLCONFIGDIR=/tmp/fire-vase-v2-mpl OPENBLAS_NUM_THREADS=1 \
.venv/bin/python scripts/validate_fire_vase_science.py

PYTHONPATH=src:scripts:. .venv/bin/pytest -q
```

The configuration is `config/analysis_v2.json` with seed `20260828`. Required
real inputs must exist; there is no synthetic fallback. After successful
statistics generation, `--render-only` can rebuild figures without recomputing
the tables.

<div class="fire-claim-boundary" markdown>
**Canonical versus historical.** `manuscript_figures/00_run_all.py --generation
v2` is the current paper workflow. Climate-revision scripts and v1 comparison
outputs remain available for provenance, but they do not control current
quantitative claims.
</div>

## Reproduction map

| Stage | Primary entry point | Inputs | Outputs |
|---|---|---|---|
| Environment | `uv sync` | `pyproject.toml`, `uv.lock` | `.venv/` |
| Data verification | `scripts/check_reproducibility.py` | v0.1 data lake, checksums | JSON status report |
| Current analysis + figures | `manuscript_figures/00_run_all.py --generation v2` | data lake, `config/analysis_v2.json` | `analysis/v2/`, current figure assets |
| Scientific challenge suite | `scripts/validate_fire_vase_science.py` | frozen v2 tables | `analysis/scientific_validation/` |
| Real-data QA modules | `scripts/run_validation.py` | FIRED/gridMET materialization | module results, plots, suite manifest, PDF |
| Tests | `pytest -q` | source and fixtures | full repository pass/fail report |
| Artifact identity | `scripts/check_reproducibility.py` | data, statistics, reference figures | checksums and pixel comparisons |

## Data, schemas, and licensing

- [Shared data lake and rebuild instructions](../reproduce-data-lake.md)
- [What is tracked and what stays external](../data.md)
- [FIRED source note and citation guidance](../datasets/fired.md)
- [Machine-readable schemas](https://github.com/CU-ESIIL/fire_vase/tree/main/schemas)
- [Release inventory](https://github.com/CU-ESIIL/fire_vase/blob/main/config/data_release.yml)

The analysis does not relicense FIRED or gridMET. Upstream reuse and citation
requirements remain attached to each source package; access method, exclusions,
hashes, and derived-product boundaries are recorded in the data-lake and v2
manifests.

## Provenance and project record

- [Current technical manuscript](../manuscripts/fire_vase_developmental_morphology/manuscript_v2.md)
- [Correction and reanalysis history](../reanalysis-v2.md)
- [AI transparency statement](../manuscripts/fire_vase_developmental_morphology/ai_transparency_statement.md)
- [Expanded AI evidence report](../manuscripts/fire_vase_developmental_morphology/ai_transparency_report.md)
- [Citation audit](../manuscripts/fire_vase_developmental_morphology/final_citation_check_2026-07-23.md)
- [Repository migration note](../migration.md)
- [GitHub source repository](https://github.com/CU-ESIIL/fire_vase)

<nav class="fire-next">
<a href="../validation/"><small>Previous</small><strong>How the evidence was challenged</strong></a>
<a href="notebooks/"><small>Next</small><strong>Choose a notebook →</strong></a>
</nav>
