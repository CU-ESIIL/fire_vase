#!/usr/bin/env python3
"""Render Figure 5: partial developmental state predicts final morphospace position."""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from morphospace import load_data, profiles_for_fire_ids
from statistics import compute_validation_bundle
from style import FIREBRICK, MORPH_BLUE, TALL_WIDTH, clean_axis, panel_label, save_figure, set_style
from vase_glyphs import draw_partial_vase_pair, draw_vase


def _cv_mean_ci(frame: pd.DataFrame, fold_kind: str = "region") -> pd.DataFrame:
    sub = frame[frame["fold_kind"] == fold_kind].copy()
    rows = []
    for keys, g in sub.groupby(["stage", "stage_order", "model"]):
        vals = g.groupby("fold")["r2"].mean().dropna().to_numpy(float)
        if vals.size == 0:
            continue
        rows.append(
            {
                "stage": keys[0],
                "stage_order": keys[1],
                "model": keys[2],
                "mean": float(np.mean(vals)),
                "lo": float(np.quantile(vals, 0.025)),
                "hi": float(np.quantile(vals, 0.975)),
                "n_folds": int(vals.size),
                "n_test": int(g["n_test"].sum()),
            }
        )
    return pd.DataFrame(rows).sort_values(["stage_order", "model"])


def build(data=None, stats=None):
    set_style()
    data = load_data() if data is None else data
    stats = compute_validation_bundle(data) if stats is None else stats
    features = data["features"]
    eligible = features[features["duration_days"] >= 10].sort_values("final_area_km2", ascending=False)
    example_id = str(eligible.iloc[min(20, len(eligible) - 1)]["fire_id"])
    profiles = profiles_for_fire_ids(data["slices"], [example_id])
    profile = profiles[example_id]

    fig = plt.figure(figsize=(7.1, 7.0))
    grid = fig.add_gridspec(3, 3, height_ratios=[1.05, 1.25, 1.05], hspace=0.65, wspace=0.52)

    ax_a = fig.add_subplot(grid[0, :])
    ax_a.axis("off")
    panel_label(ax_a, "A", x=-0.03, y=1.08)
    fractions = [0.20, 0.40, 0.70, 1.0]
    labels = ["day 1", "day 2", "day 4", "day 8+"]
    for i, (frac, label) in enumerate(zip(fractions, labels)):
        x0 = 0.10 + i * 0.20
        pax = fig.add_axes([x0, 0.772, 0.045, 0.10])
        fax = fig.add_axes([x0 + 0.060, 0.772, 0.045, 0.10])
        draw_partial_vase_pair(pax, fax, profile, frac, color=MORPH_BLUE)
        fig.text(x0 + 0.052, 0.742, label, ha="center", fontsize=8)
        fig.text(x0 + 0.022, 0.724, "partial", ha="center", fontsize=6.8, color="#666666")
        fig.text(x0 + 0.082, 0.724, "final", ha="center", fontsize=6.8, color="#666666")
    fig.text(0.10, 0.895, "Prediction task: use only observations available by a fixed day to predict final morphospace position.", fontsize=8.5)

    ax_b = fig.add_subplot(grid[1, :2])
    perf = _cv_mean_ci(stats.safe_stage_prediction, fold_kind="region")
    stages = sorted(perf["stage_order"].unique())
    stage_labels = [f"day {s}" for s in stages]
    offsets = {"trivial stage summary": -0.24, "climate only": -0.08, "geometry only": 0.08, "geometry + climate": 0.24}
    colors = {"trivial stage summary": "#aab2bb", "climate only": FIREBRICK, "geometry only": MORPH_BLUE, "geometry + climate": "#2a9d8f"}
    for model, off in offsets.items():
        sub = perf[perf["model"] == model]
        xs = np.array([stages.index(v) for v in sub["stage_order"]]) + off
        ax_b.errorbar(xs, sub["mean"], yerr=[sub["mean"] - sub["lo"], sub["hi"] - sub["mean"]], fmt="o", ms=4, lw=0.8, capsize=2, color=colors[model], label=model)
    ax_b.axhline(0, color="#333333", lw=0.6)
    ax_b.set_xticks(range(len(stages)), stage_labels)
    ax_b.set_ylabel("Prediction accuracy for final shape", fontsize=8.5)
    ax_b.set_xlabel("Last observed day used")
    ax_b.legend(frameon=False, ncol=2, fontsize=7)
    ax_b.set_title("leakage-audited fixed-day benchmark", pad=3)
    clean_axis(ax_b)
    panel_label(ax_b, "B", x=0.01, y=0.98)

    ax_c = fig.add_subplot(grid[1, 2])
    geom = perf[perf["model"] == "geometry only"].set_index("stage_order")
    combo = perf[perf["model"] == "geometry + climate"].set_index("stage_order")
    common = [v for v in stages if v in geom.index and v in combo.index]
    delta = combo.loc[common, "mean"].to_numpy(float) - geom.loc[common, "mean"].to_numpy(float)
    ax_c.axhline(0, color="#333333", lw=0.7)
    ax_c.bar(range(len(common)), delta, color="#2a9d8f")
    ax_c.set_xticks(range(len(common)), [f"day {v}" for v in common], rotation=25)
    ax_c.set_ylabel("Accuracy gain from climate", fontsize=8.5)
    ax_c.set_title("Added value of climate", pad=3)
    clean_axis(ax_c)
    panel_label(ax_c, "C")

    ax_d = fig.add_subplot(grid[2, :2])
    pred = stats.safe_stage_predictions_pc1
    if not pred.empty:
        sample = pred.sample(min(4500, len(pred)), random_state=20260722)
        ax_d.scatter(sample["observed_pc1"], sample["predicted_pc1"], s=3, alpha=0.18, color=MORPH_BLUE, rasterized=True)
        lim = np.nanquantile(np.r_[sample["observed_pc1"], sample["predicted_pc1"]], [0.01, 0.99])
        ax_d.plot(lim, lim, color=FIREBRICK, lw=1)
        ax_d.set_xlim(lim)
        ax_d.set_ylim(lim)
    ax_d.set_xlabel("Observed final main shape score")
    ax_d.set_ylabel("Predicted final main shape score", fontsize=8.5)
    ax_d.set_title("Day-4 prediction, held-out regions", pad=3)
    clean_axis(ax_d)
    panel_label(ax_d, "D", x=0.01, y=0.98)

    ax_e = fig.add_subplot(grid[2, 2])
    ax_e.axis("off")
    panel_label(ax_e, "E", x=-0.15, y=1.05)
    audit = stats.leakage_audit
    txt = "Leakage audit\n" + "\n".join(f"- {row.feature_source}: {row.status}" for row in audit.itertuples(index=False))
    ax_e.text(0.0, 1.0, txt, ha="left", va="top", fontsize=7.4)

    return fig


def main() -> int:
    fig = build()
    save_figure(fig, "Figure_5")
    plt.close(fig)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
