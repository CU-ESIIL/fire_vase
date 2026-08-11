# Examples

The copied examples are in `examples/` and preserve the source repo paths used
during development.

## Lightweight Examples

- `examples/fire_vase_panel_demo.py`: synthetic prescribed-burn panel.
- `examples/fire_plot_demo.py`: single-event fire plotting workflow.
- `examples/fire_time_hull_gridmet_demo.py`: fire time-hull plus gridMET sketch.
- `examples/real_fire_vase_gridmet_smoke.py`: real FIRED/gridMET smoke workflow.

## Research-Scale Examples

- `examples/fire_vase_developmental_atlas.py`: developmental atlas builder.
- `examples/fire_vase_death_exploratory_report.py`: exploratory terminal report.
- `examples/fire_vase_pdf_panel_demo.py`: static PDF panel generation.

Most research-scale examples expect local caches under `artifacts/` or tables
under `scratch/`. Those directories are intentionally ignored by Git.
