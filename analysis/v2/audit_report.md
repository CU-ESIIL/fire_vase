# Fire VASE v2 audit

Legacy values were reproduced to <1e-15 in archived event/state model tables and all five legacy figures were regenerated before corrections. Reproduction is not methodological validation.

| Issue | Finding | Correction/evidence | Old | New | Scientific consequence |
| --- | --- | --- | --- | --- | --- |
| Peak versus mean | Confirmed | 108214 changed peaks | Catalog area/duration called peak | Maximum observed daily increment | Scale-free PCA unaffected by absolute units; legacy mixed-space claims replaced |
| Entropy probabilities | Implementation confirmed; current values unchanged | Normalize by observed increment sum | Catalog-based denominator | 0 changed within tolerance | Incomplete-reconstruction failure mode fixed; observed entropy values survive |
| Pulse branch | Confirmed | 17837 count-only assignments | Count >=6 could imply multi-pulse | Actual prominent local maxima; branch table exported | Natural-class interpretation removed |
| Date transitions | Confirmed | 150922 longer gaps | 313726 modeled adjacent rows | Exact calendar transitions; shared AR cohort | Old next-day interpretation removed |
| PCA centering and scale | Confirmed | Mean-centered profile-only PCA | PC1 .810; first five .963 | PC1 0.341496; first five 0.894436 | Compression survives, universal restricted wedge does not |
| Weather predictor/cohort comparison | Confirmed | Nested sets; one cohort; fixed-length sensitivities | Median .349348 | Response-specific; PC1 region/core+max 0.006641 | Median headline withdrawn; heterogeneous associations remain |
| Final-geometry state leakage | Confirmed | Day-t growth-centroid extraction; same-row exposure comparison | Final-event centroid; no calendar-gap filter | 87944 shared AR transitions | Prospective covariate design, but operational availability unresolved |
| Adversarial matching | Confirmed | Greedy disjoint nearest pairs with calipers and conditional permutations | Maximum other-space discordance among neighbors | Weather matched 0.805471; morphology matched 0.682805 | Representative mismatch survives only as a diagnostic; no causal mechanism inferred |

## Important remaining limitations

- The primary population is only 10,246 consecutive histories, 9,212 weather-complete. Intermittent observations are not zero growth and are analyzed only under explicitly separate assumptions.
- Normalized-profile geometry and observation count themselves induce dimensionality; null conclusions are model-dependent. No universal wedge claim survives.
- Weather uncertainty intervals resample fixed held-out errors, not the complete training/fitting process. Four main CONUS region clusters and small state/season subsets limit precision.
- Day-specific geometry is available and used; FIRED's retrospective reconstruction and gridMET daily timing still prevent an operational-availability claim.
- Matching is a declared greedy disjoint procedure, not optimal allocation. Conditional permutations contain sparse/singleton strata. No two-by-two display or causal attribution is claimed.
- Complete model grids include duration as an external outcome, but configurations containing duration as a predictor are marked excluded_known_outcome and cannot count as predictive skill.

## Evidence and commands

Inputs and outputs are indexed by run_manifest.json, input_hashes.json, day_t_weather_manifest.json and publication_manifest.json. Code, configuration, seeds, rows and exclusions accompany the statistics. Execute the normal pipeline:

```sh
PYTHONPATH=src:scripts OPENBLAS_NUM_THREADS=1 MPLCONFIGDIR=/tmp/fire-vase-v2-mpl .venv/bin/python manuscript_figures/00_run_all.py --generation v2 --data-lake data_lake/fire-vase-data-lake-v0.1
.venv/bin/python -m pytest tests/test_analysis_v2.py -q
```

The original source tables and prior manuscript/figures remain unchanged. The old standalone analysis scripts are explicitly legacy; only the v2 normal pipeline produces current conclusions. No external data were downloaded for analysis.
