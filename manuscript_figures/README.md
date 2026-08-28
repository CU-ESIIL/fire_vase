# Manuscript Figure Reproduction

The default is now the corrected **v2** generation. Run
`00_run_all.py --generation v2 --data-lake data_lake/fire-vase-data-lake-v0.1`
from the repository root using the Python environment. Statistics are computed
before figures, which are written to `figures/v2/`; the manuscript goes to
`docs/manuscripts/fire_vase_developmental_morphology/manuscript_v2.md` and
`output/pdf/fire_vase_v2_manuscript.pdf`. Individual numbered entry points also
ensure the entire consistent v2 bundle exists. Add `--render-only` to avoid
recomputing existing statistics.

The historical instructions below describe `--generation legacy`, which reads
the immutable v0.1 tables and writes to this folder. Those figures and claims
are comparison artifacts, not current scientific results.

This folder contains numbered scripts for regenerating the Fire VASE manuscript
figures from a Fire VASE data-lake package. Each script reads from the data lake
and writes its figure outputs back into this folder as PDF, PNG, and SVG.

For the full repository-level data-lake rebuild guide, see the root
[`README.md`](../README.md#data-lake-reproduction).

## Data Lake

By default, the scripts look for the local package:

```bash
data_lake/fire-vase-data-lake-v0.1
```

You can also point at a downloaded CyVerse package, its `files/` directory, or a restored repository root:

```bash
uv run python manuscript_figures/01_figure_1.py --data-lake /path/to/fire-vase-data-lake-v0.1
```

The expected data-lake layout is:

```text
fire-vase-data-lake-v0.1/
  files/
    scratch/fire_vase_developmental_morphology/
    scratch/fire_vase_run_full/tables/
    repository/analysis/claim_audit_stats/
    repository/figures/main/derived_stats/
```

The scripts also accept the `files/` directory itself or a restored repository
root containing `scratch/fire_vase_developmental_morphology/` and
`scratch/fire_vase_run_full/tables/`.

## Setup

From the repository root, install the locked project environment or use `uv run`
directly:

```bash
python -m pip install -e ".[dev]"
```

The wrappers call shared plotting and analysis code from
[`../scripts/figures/`](../scripts/figures/), including
[`morphospace.py`](../scripts/figures/morphospace.py),
[`statistics.py`](../scripts/figures/statistics.py), and the individual
`make_figure_*.py` builders.

## Run Everything

From the repository root:

```bash
uv run python manuscript_figures/00_run_all.py
```

With an explicit data-lake path:

```bash
uv run python manuscript_figures/00_run_all.py \
  --data-lake /path/to/fire-vase-data-lake-v0.1
```

## Run One Figure

```bash
uv run python manuscript_figures/01_figure_1.py
uv run python manuscript_figures/02_figure_2.py
uv run python manuscript_figures/03_figure_3.py
uv run python manuscript_figures/04_figure_4.py
uv run python manuscript_figures/05_figure_5.py
uv run python manuscript_figures/06_supplementary_figure_1.py
```

## Script Map

| Output | Wrapper | Shared figure builder |
|---|---|---|
| Figure 1 | [`01_figure_1.py`](01_figure_1.py) | [`../scripts/figures/make_figure_1.py`](../scripts/figures/make_figure_1.py) |
| Figure 2 | [`02_figure_2.py`](02_figure_2.py) | [`../scripts/figures/make_figure_2.py`](../scripts/figures/make_figure_2.py) |
| Figure 3 | [`03_figure_3.py`](03_figure_3.py) | [`../scripts/figures/make_figure_3.py`](../scripts/figures/make_figure_3.py) |
| Figure 4 | [`04_figure_4.py`](04_figure_4.py) | [`../scripts/figures/make_figure_4.py`](../scripts/figures/make_figure_4.py) |
| Figure 5 | [`05_figure_5.py`](05_figure_5.py) | [`../scripts/figures/make_figure_5.py`](../scripts/figures/make_figure_5.py) |
| Supplementary Figure 1 | [`06_supplementary_figure_1.py`](06_supplementary_figure_1.py) | [`../scripts/figures/make_supplementary_figures.py`](../scripts/figures/make_supplementary_figures.py) |
| All figures | [`00_run_all.py`](00_run_all.py) | [`_figure_runner.py`](_figure_runner.py) |

## Validation Cache

The first run seeds `manuscript_figures/derived_stats/` from the data lake cache so collaborators can render figures without recomputing the expensive validation tables. To recompute the validation tables from the raw data-lake tables, run:

```bash
uv run python manuscript_figures/00_run_all.py --force-validation
```

Use `--bootstrap-reps` and `--sample-size` to control the heavier validation settings when recomputing.

Example smaller validation rerun for testing:

```bash
uv run python manuscript_figures/00_run_all.py \
  --data-lake /path/to/fire-vase-data-lake-v0.1 \
  --force-validation \
  --bootstrap-reps 20 \
  --sample-size 5000
```

## Outputs

The scripts write these files into this folder:

- `Figure_1.pdf`, `Figure_1.png`, `Figure_1.svg`
- `Figure_2.pdf`, `Figure_2.png`, `Figure_2.svg`
- `Figure_3.pdf`, `Figure_3.png`, `Figure_3.svg`
- `Figure_4.pdf`, `Figure_4.png`, `Figure_4.svg`
- `Figure_5.pdf`, `Figure_5.png`, `Figure_5.svg`
- `Supplementary_Figure_1_validation.pdf`, `Supplementary_Figure_1_validation.png`, `Supplementary_Figure_1_validation.svg`

Generated figure files and `derived_stats/` are ignored by Git in this folder so
collaborators can rerun figures without polluting commits.

## Troubleshooting

- If a script cannot find inputs, pass `--data-lake` explicitly and make sure
  the path contains either `files/scratch/...` or `scratch/...`.
- If validation recomputation is slow, omit `--force-validation` so the wrapper
  seeds cached validation tables from the data lake.
- If a figure imports but cannot write outputs, run from the repository root so
  relative paths resolve cleanly.

The scripts depend on the repository Python environment and the shared plotting
code in `scripts/figures/`. `uv run` uses the locked project environment; an
already activated equivalent environment also works.
