# Validation

The Fire VASE validation suite checks the scientific handoffs that are hardest
to infer from a final table or figure: CubeDynamics pipe execution, lazy
GridMET access, complete HTML cube serialization, FIRED polygon-to-hull
construction and 3-D averaging alternatives, climate date selection,
polygon/grid alignment, and agreement with upstream representations.

All six modules run on the same real FIRED event (`20657`) by default. Each
module writes its own PNG, CSV, and `result.json`; the runner also writes a
suite manifest and a [collated QA PDF](../assets/validation/fire_vase_validation_report.pdf).

| Module | Default result | What is independently recomputed |
|---|---:|---|
| Pipe and stream | PASS | Direct and pipe-style z-score graphs over the same lazy GridMET cube |
| Data cube and HTML | PASS | Every source coordinate, time plane, HTML face, interior raster, and corner landmark |
| Geometry and hull | PASS | Simplified FIRED polygons, directional support profiles, and hull metrics |
| 3-D hull decisions | PASS | Raw polygons through final mesh, plus 1-, 3-, 7-day and cumulative alternatives |
| Climate attribution | PASS | NetCDF values at the event centroid and fractional polygon/pixel overlaps |
| External source | PASS | Raw packed values from the NCAR GridMET mirror and FIRED daily/event geometry agreement |

## Run The Complete Suite

Restore the materialized data lake under
`data_lake/fire-vase-data-lake-v0.1/files`, install the project environment,
then run:

```bash
uv run python scripts/run_validation.py
```

That command is fully offline. It validates the packaged GridMET cache and all
FIRED/lakehouse products, but records the independent NCAR mirror check as not
requested. Add `--external` when network access is available:

```bash
uv run python scripts/run_validation.py --external
```

To refresh the plots embedded in this website and the collated PDF:

```bash
uv run python scripts/run_validation.py --external --publish-docs
```

The selected fire, climate variable, simplification range, hull resolution,
and acceptance thresholds are declared in
[`config/validation.yml`](https://github.com/CU-ESIIL/fire_vase/blob/main/config/validation.yml).

## Run One Check

Every module has an isolated output directory and can be rerun alone:

```bash
uv run python scripts/run_validation.py --modules pipeline --no-pdf
uv run python scripts/run_validation.py --modules cube --no-pdf
uv run python scripts/run_validation.py --modules geometry --no-pdf
uv run python scripts/run_validation.py --modules hull3d --no-pdf
uv run python scripts/run_validation.py --modules climate --no-pdf
uv run python scripts/run_validation.py --modules external --external --no-pdf
```

The companion
[validation notebook](https://github.com/CU-ESIIL/fire_vase/blob/main/notebooks/validate_fire_vase_pipeline.ipynb)
contains one executable section per module, so a reviewer can run a single QA
plot without rebuilding the full report.

For evidence that the validators reject plausible errors, see the
[expected-failure contrast](contrast.md). It uses a passing cube control, three
deliberately corrupted cubes, and a real FIRED polygon event that exceeds the
simplification threshold. These expected failures are reported separately and
are not counted among the six production-module results above.

## Read The Checks

- [Pipe grammar and streaming backend](pipeline.md)
- [Data cube and HTML axis integrity](cube.md)
- [FIRED geometry and hull sensitivity](geometry.md)
- [Three-dimensional hull construction and averaging](hull3d.md)
- [GridMET time and spatial attribution](climate.md)
- [External and upstream-source checks](external.md)
- [Expected-failure contrast and negative controls](contrast.md)

!!! note "Validation scope"

    These checks validate a real, deliberately inspectable sample and the
    documented data contracts. They complement, rather than replace, full-table
    schema/checksum checks and broader population-level statistical validation.
