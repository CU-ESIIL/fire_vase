#!/usr/bin/env python3
"""Reproduce the pre-v2 calculation without modifying reference artifacts."""
from pathlib import Path
import hashlib
import json
import shutil
import numpy as np
import pandas as pd
import fire_vase_climate_revision as old

ROOT = Path(__file__).resolve().parents[1]


def main():
    target = ROOT / "archive/comparison_v1"
    target.mkdir(parents=True, exist_ok=True)
    data = ROOT / "data_lake/fire-vase-data-lake-v0.1/files"
    for key in ["FEATURES_PATH", "STAGE_PATH", "MATCHED_PATH", "SLICES_PATH",
                "TRAITS_PATH", "CATALOG_PATH", "EXPOSURES_PATH", "CLIMATE_REPORT_PATH",
                "PERIMETER_REPORT_PATH", "GRIDMET_MANIFEST_PATH"]:
        setattr(old, key, data / getattr(old, key).relative_to(ROOT))
    for key, rel in [("STATS_DIR", "recomputed_stats"), ("MAIN_FIGURE_DIR", "recomputed_figures")]:
        setattr(old, key, target / rel)
        getattr(old, key).mkdir(exist_ok=True)
    originals = [ROOT / "analysis/climate_revision_stats", ROOT / "figures/climate_revision_main"]
    for path in originals:
        if not (target / "reference" / path.name).exists():
            shutil.copytree(path, target / "reference" / path.name)
    source = ROOT / "docs/manuscripts/fire_vase_developmental_morphology/manuscript_climate_revision_science_style.md"
    if not (target / "reference" / source.name).exists():
        shutil.copy2(source, target / "reference" / source.name)
    old.set_style()
    bundle = old.load_data()
    f = old.make_climate_features(bundle)
    print("Recomputing v1 event models", flush=True)
    event = old.run_event_models(f)
    state_df = old.build_state_model_table(bundle)
    print("Recomputing v1 state models", flush=True)
    state = old.run_state_models(state_df)
    from figures.morphospace import fit_pca, geometry_columns
    pca = fit_pca(bundle.features, geometry_columns(bundle.features))
    differences = []
    for name, new in [("event_level_blocked_model_performance.csv", event),
                      ("state_dependent_blocked_model_performance.csv", state)]:
        ref = pd.read_csv(ROOT / "analysis/climate_revision_stats" / name)
        keys = [c for c in ["predictor_set", "response", "block"] if c in ref]
        joined = new.merge(ref, on=keys, suffixes=("_new", "_old"))
        differences.append({"table": name, "rows": len(joined),
                            "max_abs_r2_difference": float((joined.r2_new-joined.r2_old).abs().max())})
    summary = old.best_model_summary(event, state)
    summary.update(pca_evr=pca.explained_variance_ratio.tolist(), comparisons=differences)
    (target / "reproduction_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2), flush=True)
    for i, call in enumerate([lambda: old.figure_1(bundle), lambda: old.figure_2(bundle),
                             lambda: old.figure_3(bundle, f, event),
                             lambda: old.figure_4(bundle, state_df, state),
                             lambda: old.figure_5(bundle, f, event)], 1):
        print(f"Reproducing v1 figure {i}", flush=True)
        call()
    hashes = {str(p.relative_to(target)): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in sorted(target.rglob("*")) if p.is_file()}
    (target / "hashes.json").write_text(json.dumps(hashes, indent=2))


if __name__ == "__main__":
    main()
