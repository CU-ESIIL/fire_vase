#!/usr/bin/env python3
"""Render Figure 3: PC1 robustness and defensible null developmental universes."""

from __future__ import annotations

import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from style import CHARCOAL, FIREBRICK, MORPH_BLUE, ROOT, save_figure, set_style

AUDIT_DIR = ROOT / "analysis" / "claim_audit_stats"


def _require_csv(name: str) -> pd.DataFrame:
    path = AUDIT_DIR / name
    if not path.exists():
        raise FileNotFoundError(
            f"Missing audit table {path}. Run "
            "`python scripts/fire_vase_manuscript_claim_audit.py --sample-size 6000 --reps 12` first."
        )
    return pd.read_csv(path)


def _short_null_labels(labels: list[str]) -> list[str]:
    mapping = {
        "duration-bin mean profile": "duration-bin\nmean",
        "shuffled daily growth order within fire": "shuffled\norder",
        "duration-bin empirical increments": "empirical\nincrements",
        "dirichlet duration and final area": "dirichlet\nsize+duration",
        "zero-preserving dirichlet": "zero-preserving\ndirichlet",
        "independent feature permutation": "feature\npermutation",
    }
    return [mapping.get(label, label) for label in labels]


def build(data=None, stats=None):
    set_style()
    ablation = _require_csv("pc1_ablation_results.csv")
    null = _require_csv("null_model_summary.csv")

    fig, axes = plt.subplots(2, 2, figsize=(7.1, 6.2))
    axes = axes.ravel()

    keep = [
        "full current feature set",
        "all scale and duration variables removed",
        "normalized profile variables only",
        "growth-share profile only",
        "interpolated profile features removed",
        "full current feature set, duration >= 10 days",
    ]
    show = ablation[ablation["feature_set"].isin(keep)].copy()
    labels = ["full", "no scale/\nduration", "profiles\nonly", "growth\nshares", "no\nprofiles", ">=10 d"]

    axes[0].bar(range(len(show)), show["pc1"] * 100, color=MORPH_BLUE)
    axes[0].set_xticks(range(len(show)), labels, rotation=25, ha="right")
    axes[0].set_ylabel("PC1 variance (%)")
    axes[0].set_title("A. Dominant axis sensitivity", loc="left", fontsize=9, fontweight="bold")

    axes[1].bar(range(len(show)), show["cumvar_pc1_5"] * 100, color=FIREBRICK)
    axes[1].set_xticks(range(len(show)), labels, rotation=25, ha="right")
    axes[1].set_ylabel("First five axes variance (%)")
    axes[1].set_title("B. Low-dimensionality sensitivity", loc="left", fontsize=9, fontweight="bold")

    order = null.sort_values("cumvar_pc1_5_mean")["null_model"].tolist()
    y = np.arange(len(order))
    null = null.set_index("null_model").loc[order].reset_index()
    axes[2].errorbar(
        null["cumvar_pc1_5_mean"] * 100,
        y,
        xerr=[
            (null["cumvar_pc1_5_mean"] - null["cumvar_pc1_5_lo"]) * 100,
            (null["cumvar_pc1_5_hi"] - null["cumvar_pc1_5_mean"]) * 100,
        ],
        fmt="o",
        color=CHARCOAL,
        ecolor="#9aa3ad",
        capsize=2,
    )
    axes[2].axvline(float(null["observed_cumvar_pc1_5"].iloc[0]) * 100, color=FIREBRICK, lw=1.2, label="observed")
    axes[2].set_yticks(y, _short_null_labels(order), fontsize=6.9)
    axes[2].set_xlabel("First five axes variance (%)")
    axes[2].set_title("C. Null developmental universes", loc="left", fontsize=9, fontweight="bold")
    axes[2].legend(frameon=False, fontsize=7)

    axes[3].scatter(
        null["synthetic_logdet_cov_pc1_5_mean"],
        null["synthetic_to_observed_median_mean"],
        s=36,
        color=MORPH_BLUE,
    )
    label_offsets = {
        1: (-2, 0),
        2: (0, 16),
        3: (20, 5),
        4: (-10, 18),
        5: (-22, 5),
        6: (0, 13),
    }
    for i, row in enumerate(null.itertuples(index=False), start=1):
        axes[3].annotate(
            str(i),
            xy=(row.synthetic_logdet_cov_pc1_5_mean, row.synthetic_to_observed_median_mean),
            xytext=label_offsets.get(i, (0, 0)),
            textcoords="offset points",
            fontsize=7.0,
            ha="center",
            va="center",
            color=CHARCOAL,
            bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.85, "pad": 0.4},
        )
    axes[3].axvline(float(null["observed_logdet_cov_pc1_5"].iloc[0]), color=FIREBRICK, lw=1.2)
    axes[3].set_xlabel("Log covariance volume in observed PC1-PC5")
    axes[3].set_ylabel("Null-to-observed median distance")
    axes[3].set_title("D. Support overlap diagnostics (labels follow C)", loc="left", fontsize=9, fontweight="bold")

    for ax in axes:
        ax.spines[["top", "right"]].set_visible(False)
        ax.tick_params(labelsize=7)
    fig.tight_layout()
    return fig


def main() -> int:
    fig = build()
    save_figure(fig, "Figure_3")
    plt.close(fig)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
