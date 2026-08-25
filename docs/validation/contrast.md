# Expected-Failure Contrast

A validator is only persuasive if it rejects plausible mistakes. This
contrast run keeps the six-module production validation report unchanged and
builds a separate report from one clean control, three deliberately corrupted
data cubes, and one real FIRED geometry counterexample.

[Download the expected-failure contrast report](../assets/validation/fire_vase_validation_contrast_report.pdf)

## Cube Negative Controls

The clean event `20657` cube passes the complete source-to-HTML audit. The
same audit is then run after changing only one data contract at a time:

1. reverse latitude values while leaving latitude labels unchanged;
2. swap two time planes while leaving timestamps unchanged; and
3. remove the middle day.

All three are rejected. The latitude reversal disagrees with all 61 decoded
HTML rasters, the time scramble disagrees with 25 rasters, and the dropped day
creates a two-day timestamp gap and a cube-shape mismatch. This demonstrates
that monotonic coordinate labels alone cannot conceal reversed or scrambled
values.

![Cube negative controls](../assets/validation/contrast_cube.png)

## A Real Geometry Failure

The geometry scan also found a naturally difficult FIRED event rather than
manufacturing a broken polygon. Event `72016` contains seven valid daily
polygons, but simplifying them at the operational 125 m tolerance changes the
cumulative union area by **26.86%**. That exceeds the declared 10% acceptance
threshold, so the module correctly reports `FAIL`. At 1000 m, the area change
reaches 51.03%.

This is a sensitivity counterexample, not evidence that the main production
sample failed. It shows why the tolerance is tested for every selected event
instead of assumed safe from geometric validity alone.

![Real FIRED geometry failure](../assets/validation/contrast_geometry.png)

## Reproduce The Contrast

Run the contrast separately from the production suite:

```bash
uv run python scripts/run_validation_contrast.py --publish-docs
```

The command exits successfully only when the clean cube passes, every injected
cube corruption is detected, and the selected real FIRED geometry case fails
the declared threshold. It writes modular CSV, JSON, and PNG evidence under
`output/validation/contrast/` and the collated report under `output/pdf/`.

The negative controls are implemented in
[`src/cubedynamics/validation/contrast.py`](https://github.com/CU-ESIIL/fire_vase/blob/main/src/cubedynamics/validation/contrast.py),
so reviewers can add another corruption without changing the production
validators.
