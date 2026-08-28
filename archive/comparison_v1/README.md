# V1 comparison archive

Historical outputs here are retained for comparison, not endorsed results.
`reference/` is an unchanged copy of the pre-v2 climate-revision generation.
`recomputed_stats/` and `recomputed_figures/` rerun that implementation against
the real materialized data package. `reproduction_summary.json` reports numeric
agreement and `hashes.json` identifies the artifacts. Regenerate with:

```sh
PYTHONPATH=scripts/figures:scripts:src .venv/bin/python scripts/reproduce_v1_comparison.py
```

These files intentionally preserve the old peak/mean, date-transition,
median-centered SVD, cohort and matching defects for auditability.
