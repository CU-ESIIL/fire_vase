#!/usr/bin/env python3
"""Render Figure 1: whole-fire histories collapse into a common coordinate system."""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np

from morphospace import axis_limits, fit_pca, geometry_columns, load_data, pick_shape_examples, profiles_for_fire_ids
from statistics import compute_validation_bundle
from style import (
    CHARCOAL,
    FIREBRICK,
    LIGHT,
    MORPH_BLUE,
    SHAPE_COLORS,
    TALL_WIDTH,
    clean_axis,
    panel_label,
    pc_axis_label,
    save_figure,
    set_style,
)
from vase_glyphs import draw_area_history, draw_vase


def build(data=None, stats=None):
    set_style()
    data = load_data() if data is None else data
    stats = compute_validation_bundle(data) if stats is None else stats
    features = data["features"]
    loadings = data["loadings"]
    columns = geometry_columns(features, loadings)
    pca = fit_pca(features, columns, n_components=10)
    evr = np.array(stats.observed["pc_explained_variance"], dtype=float)

    fig = plt.figure(figsize=(7.1, 7.8))

    example_labels = ["single flash", "compact steady", "skinny persistent", "late surge", "multi-pulse complex"]
    examples = pick_shape_examples(features, example_labels)
    profiles = profiles_for_fire_ids(data["slices"], examples["fire_id"].astype(str).tolist())
    ax_a = fig.add_axes([0.05, 0.77, 0.90, 0.20])
    ax_a.axis("off")
    panel_label(ax_a, "A", x=-0.04, y=1.00)
    for i, row in enumerate(examples.itertuples(index=False)):
        x0 = 0.065 + i * 0.18
        hist_ax = fig.add_axes([x0, 0.842, 0.055, 0.073])
        vase_ax = fig.add_axes([x0 + 0.066, 0.815, 0.047, 0.125])
        color = SHAPE_COLORS.get(row.shape_label, MORPH_BLUE)
        draw_area_history(hist_ax, profiles[row.fire_id], color=color)
        draw_vase(vase_ax, profiles[row.fire_id], color=color)
        fig.text(x0 + 0.056, 0.790, row.shape_label.replace(" ", "\n"), ha="center", va="top", fontsize=6.8, color=CHARCOAL)
        fig.text(x0 + 0.056, 0.752, f"{row.duration_days:.0f} d; {row.final_area_km2:.1f} km2", ha="center", va="top", fontsize=6.1, color="#555555")

    ax_b = fig.add_axes([0.08, 0.08, 0.46, 0.58])
    xlim, ylim = axis_limits(features)
    hb = ax_b.hexbin(
        features["morph_pc1"],
        features["morph_pc2"],
        gridsize=150,
        bins="log",
        cmap="Greys",
        mincnt=1,
        linewidths=0,
        rasterized=True,
    )
    medoids = data["medoids"].sort_values("represented_fire_count", ascending=False).head(16)
    ax_b.scatter(medoids["morph_pc1"], medoids["morph_pc2"], s=18, color=FIREBRICK, edgecolor="white", linewidth=0.35, zorder=3)
    for row in medoids.itertuples(index=False):
        ax_b.text(row.morph_pc1, row.morph_pc2, row.representative_id, fontsize=6.5, ha="left", va="bottom", color=CHARCOAL)
    ax_b.set_xlim(xlim)
    ax_b.set_ylim(ylim)
    ax_b.set_xlabel(pc_axis_label(1, evr[0]))
    ax_b.set_ylabel(pc_axis_label(2, evr[1]))
    ax_b.text(0.02, 0.98, f"n = {len(features):,} fires", transform=ax_b.transAxes, ha="left", va="top", fontsize=8.2)
    clean_axis(ax_b)
    panel_label(ax_b, "B")
    ax_b.text(0.98, 0.02, "darker = higher density", transform=ax_b.transAxes, ha="right", va="bottom", fontsize=7.2, color="#555555")

    ax_c = fig.add_axes([0.62, 0.48, 0.31, 0.22])
    pcs = np.arange(1, 11)
    boot = stats.pca_bootstrap
    med = [boot[f"pc{i}"].median() if f"pc{i}" in boot else np.nan for i in pcs[:5]]
    lo = [boot[f"pc{i}"].quantile(0.025) if f"pc{i}" in boot else np.nan for i in pcs[:5]]
    hi = [boot[f"pc{i}"].quantile(0.975) if f"pc{i}" in boot else np.nan for i in pcs[:5]]
    ax_c.bar(pcs, evr[:10] * 100, color=[MORPH_BLUE if p <= 5 else "#c8d0d8" for p in pcs], width=0.72)
    ax_c.plot(pcs, np.cumsum(evr[:10]) * 100, color=FIREBRICK, marker="o", ms=3, lw=1.1, label="cumulative")
    ax_c.errorbar(pcs[:5], np.array(med) * 100, yerr=[(np.array(med) - np.array(lo)) * 100, (np.array(hi) - np.array(med)) * 100], fmt="none", ecolor=CHARCOAL, elinewidth=0.7, capsize=2)
    ax_c.axvline(5.5, color=LIGHT, lw=1)
    ax_c.text(0.98, 0.62, f"first five axes =\n{stats.observed['cumvar_pc1_5'] * 100:.1f}%", transform=ax_c.transAxes, ha="right", va="center", fontsize=8.5)
    ax_c.set_xlabel("Developmental axis")
    ax_c.set_ylabel("Variance explained (%)")
    ax_c.set_ylim(0, 104)
    ax_c.set_xticks(pcs)
    clean_axis(ax_c)
    panel_label(ax_c, "C")

    ax_d = fig.add_axes([0.62, 0.27, 0.31, 0.14])
    null = stats.pca_null[stats.pca_null["null_model"] != "observed"]
    order = ["feature-wise permutation", "within-fire growth-profile permutation"]
    parts = [null.loc[null["null_model"] == label, "cumvar_pc1_5"].to_numpy() * 100 for label in order]
    ax_d.violinplot(parts, positions=[1, 2], widths=0.72, showmeans=False, showextrema=False)
    ax_d.scatter([1, 2], [stats.observed["cumvar_pc1_5"] * 100] * 2, color=FIREBRICK, s=18, zorder=3, label="observed")
    ax_d.set_xticks([1, 2])
    ax_d.set_xticklabels(["shuffled\nfeatures", "shuffled\ngrowth timing"], fontsize=7.5)
    ax_d.set_ylabel("Variance in first 5 axes (%)", fontsize=8)
    ax_d.set_ylim(35, 101)
    ax_d.text(
        0.04,
        0.98,
        f"bootstrap median {stats.pca_bootstrap['cumvar_pc1_5'].median() * 100:.1f}%\n"
        f"95% interval {stats.pca_bootstrap['cumvar_pc1_5'].quantile(0.025) * 100:.1f}-{stats.pca_bootstrap['cumvar_pc1_5'].quantile(0.975) * 100:.1f}%\n"
        f"subspace overlap {stats.pca_bootstrap['subspace_overlap'].median():.3f}",
        transform=ax_d.transAxes,
        ha="left",
        va="top",
        fontsize=6.6,
    )
    clean_axis(ax_d)
    panel_label(ax_d, "D", x=-0.18, y=1.05)

    ax_e = fig.add_axes([0.62, 0.06, 0.31, 0.13])
    dur = stats.duration_sensitivity
    ax_e.plot(dur["subset"], dur["cumvar_pc1_5"] * 100, marker="o", color=MORPH_BLUE)
    ax_e.set_ylabel("Variance in first 5 axes (%)")
    ax_e.set_xlabel("Minimum fire duration included")
    ax_e.set_ylim(0, 105)
    ax_e.tick_params(axis="x", rotation=18, labelsize=6.8)
    for x, row in enumerate(dur.itertuples(index=False)):
        ax_e.text(x, row.cumvar_pc1_5 * 100 + 2.0, f"n={row.n:,}", ha="center", fontsize=7)
    clean_axis(ax_e)
    panel_label(ax_e, "E", x=-0.18, y=1.08)
    return fig


def main() -> int:
    fig = build()
    save_figure(fig, "Figure_1")
    plt.close(fig)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
