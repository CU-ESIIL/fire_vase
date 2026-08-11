# Fire VASE observed-cessation exploratory report

Rerun from the repository root:

```bash
env MPLCONFIGDIR=/private/tmp/mplconfig .venv/bin/python examples/fire_vase_death_exploratory_report.py
```

The workflow uses cached FIRED candidate events under
`artifacts/fire-vase-gridmet-real/fired-cache/` and cached real gridMET tmmx
NetCDF files under `artifacts/fire-vase-gridmet-real/gridmet-cache/`.

Terminology: "fire death" is shorthand only. The report analyzes observed
cessation of detectable spatial growth, not independently verified physical
extinction.
