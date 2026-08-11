#!/usr/bin/env python3
"""Render compact supplementary validation figures for the Fire VASE suite."""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np

from morphospace import load_data
from statistics import compute_validation_bundle
from style import FIREBRICK, MORPH_BLUE, SUPPLEMENT_DIR, clean_axis, panel_label, set_style


def save_supplement(fig, name: str) -> dict[str, str]:
    SUPPLEMENT_DIR.mkdir(parents=True, exist_ok=True)
    out = {}
    for suffix in ["pdf", "png", "svg"]:
        path = SUPPLEMENT_DIR / f"{name}.{suffix}"
        fig.savefig(path, bbox_inches="tight", dpi=600)
        out[suffix] = path.as_posix()
    return out


def build(data=None, stats=None):
    set_style()
    data = load_data() if data is None else data
    stats = compute_validation_bundle(data) if stats is None else stats
    fig, axes = plt.subplots(3, 3, figsize=(7.1, 7.2))
    axes = axes.ravel()

    boot = stats.pca_bootstrap
    axes[0].hist(boot["cumvar_pc1_5"] * 100, bins=24, color=MORPH_BLUE, alpha=0.82)
    axes[0].axvline(stats.observed["cumvar_pc1_5"] * 100, color=FIREBRICK)
    axes[0].set_xlabel("PC1-PC5 variance (%)")
    axes[0].set_ylabel("bootstrap count")
    panel_label(axes[0], "A")
    clean_axis(axes[0])

    null = stats.pca_null[stats.pca_null["null_model"] != "observed"]
    for label, sub in null.groupby("null_model"):
        axes[1].hist(sub["cumvar_pc1_5"] * 100, bins=22, alpha=0.55, label=label)
    axes[1].axvline(stats.observed["cumvar_pc1_5"] * 100, color=FIREBRICK)
    axes[1].set_xlabel("PC1-PC5 variance (%)")
    axes[1].legend(frameon=False, fontsize=6)
    panel_label(axes[1], "B")
    clean_axis(axes[1])

    dur = stats.duration_sensitivity
    axes[2].plot(dur["subset"], dur["cumvar_pc1_5"] * 100, marker="o", color=MORPH_BLUE)
    axes[2].tick_params(axis="x", rotation=35)
    axes[2].set_ylabel("PC1-PC5 variance (%)")
    panel_label(axes[2], "C")
    clean_axis(axes[2])

    abl = stats.ablation.sort_values("cumvar_pc1_5")
    axes[3].barh(abl["feature_set"], abl["cumvar_pc1_5"] * 100, color=MORPH_BLUE)
    axes[3].set_xlabel("PC1-PC5 variance (%)")
    axes[3].tick_params(labelsize=6)
    panel_label(axes[3], "D")
    clean_axis(axes[3])

    cov = stats.medoid_coverage
    axes[4].plot(cov["n_medoids"], cov["median_nearest_distance"], marker="o", color=MORPH_BLUE, label="median")
    axes[4].plot(cov["n_medoids"], cov["p90_nearest_distance"], marker="o", color=FIREBRICK, label="p90")
    axes[4].set_xlabel("number of medoids")
    axes[4].set_ylabel("nearest distance")
    axes[4].legend(frameon=False)
    panel_label(axes[4], "E")
    clean_axis(axes[4])

    cv = stats.climate_cv.groupby(["model", "fold_kind"])["r2"].mean().reset_index()
    labels = cv["model"].str.replace(" predicts ", "\n->\n") + "\n" + cv["fold_kind"]
    axes[5].bar(range(len(cv)), cv["r2"], color=[MORPH_BLUE if "climate predicts" in m else FIREBRICK for m in cv["model"]])
    axes[5].set_xticks(range(len(cv)), labels, rotation=45, ha="right", fontsize=6)
    axes[5].set_ylabel("mean held-out R2")
    panel_label(axes[5], "F")
    clean_axis(axes[5])

    stage = stats.safe_stage_prediction.groupby(["stage", "model"])["r2"].mean().reset_index()
    for model, sub in stage.groupby("model"):
        axes[6].plot(sub["stage"], sub["r2"], marker="o", label=model)
    axes[6].tick_params(axis="x", rotation=25)
    axes[6].set_ylabel("mean R2")
    axes[6].legend(frameon=False, fontsize=6)
    panel_label(axes[6], "G")
    clean_axis(axes[6])

    mp = stats.matched_population
    axes[7].bar(mp["matching_basis"], mp["standardized_effect"], color=[MORPH_BLUE, FIREBRICK])
    axes[7].set_ylabel("standardized effect")
    axes[7].tick_params(axis="x", rotation=20)
    panel_label(axes[7], "H")
    clean_axis(axes[7])

    leak = stats.leakage_audit["status"].value_counts()
    axes[8].bar(leak.index, leak.values, color=["#aab2bb", FIREBRICK][: len(leak)])
    axes[8].set_ylabel("audit entries")
    panel_label(axes[8], "I")
    clean_axis(axes[8])

    fig.suptitle("Supplementary validation summaries", x=0.01, y=0.995, ha="left", fontsize=12, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    return fig


def main() -> int:
    fig = build()
    save_supplement(fig, "Supplementary_Figure_1_validation")
    plt.close(fig)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
