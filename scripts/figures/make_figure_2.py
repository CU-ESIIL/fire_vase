#!/usr/bin/env python3
"""Render Figure 2: recurring developmental forms in a continuous atlas."""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np

from morphospace import axis_limits, fit_pca, geometry_columns, load_data, profiles_for_fire_ids, transect_examples
from statistics import compute_validation_bundle
from style import CHARCOAL, FIREBRICK, MORPH_BLUE, SHAPE_COLORS, TALL_WIDTH, clean_axis, panel_label, save_figure, set_style
from vase_glyphs import draw_vase


def _place_insets(ax, fig, coords, width=0.036, height=0.060):
    trans = ax.transData.transform
    inv = fig.transFigure.inverted().transform
    placed = []
    out = []
    for x, y in coords:
        fx, fy = inv(trans((x, y)))
        fx = float(np.clip(fx, 0.08, 0.49))
        fy = float(np.clip(fy, 0.45, 0.84))
        for _ in range(60):
            moved = False
            for px, py in placed:
                if abs(fx - px) < width * 0.9 and abs(fy - py) < height * 0.85:
                    fy += height * 0.22
                    fx += width * 0.10
                    moved = True
            if not moved:
                break
        fx = float(np.clip(fx, 0.08, 0.49))
        fy = float(np.clip(fy, 0.45, 0.84))
        placed.append((fx, fy))
        out.append((fx, fy))
    return out


def build(data=None, stats=None):
    set_style()
    data = load_data() if data is None else data
    stats = compute_validation_bundle(data) if stats is None else stats
    features = data["features"]
    medoids = data["medoids"].sort_values("representative_id").reset_index(drop=True)
    profiles = profiles_for_fire_ids(data["slices"], medoids["fire_id"].astype(str).tolist())

    fig = plt.figure(figsize=(7.1, 7.2))

    ax_a = fig.add_axes([0.08, 0.43, 0.44, 0.45])
    xlim, ylim = axis_limits(features)
    ax_a.hexbin(features["morph_pc1"], features["morph_pc2"], gridsize=120, bins="log", cmap="Greys", mincnt=1, linewidths=0, rasterized=True)
    shown = medoids.sort_values("represented_fire_count", ascending=False).head(18).copy()
    ax_a.scatter(shown["morph_pc1"], shown["morph_pc2"], s=9, color=FIREBRICK, edgecolor="white", linewidth=0.25, zorder=2)
    ax_a.set_xlim(xlim)
    ax_a.set_ylim(ylim)
    ax_a.set_xlabel("Main developmental gradient")
    ax_a.set_ylabel("Secondary developmental gradient")
    clean_axis(ax_a)
    panel_label(ax_a, "A")
    inset_positions = _place_insets(ax_a, fig, shown[["morph_pc1", "morph_pc2"]].to_numpy(float))
    for (fx, fy), row in zip(inset_positions, shown.itertuples(index=False)):
        ax_a.annotate("", xy=(row.morph_pc1, row.morph_pc2), xycoords="data", xytext=(fx + 0.018, fy + 0.030), textcoords=fig.transFigure, arrowprops={"arrowstyle": "-", "lw": 0.30, "color": "#7a7a7a"})
        iax = fig.add_axes([fx, fy, 0.036, 0.060])
        draw_vase(iax, profiles[row.fire_id], color=SHAPE_COLORS.get(row.shape_label, MORPH_BLUE), linewidth=0.28)
        fig.text(fx + 0.018, fy - 0.004, row.representative_id, ha="center", va="top", fontsize=5.4, color=CHARCOAL)

    ax_b = fig.add_axes([0.62, 0.62, 0.30, 0.24])
    top = medoids.sort_values("represented_fire_count", ascending=False).head(18).sort_values("represented_fire_count")
    ax_b.barh(top["representative_id"], top["represented_fire_count"], color=MORPH_BLUE)
    ax_b.set_xlabel("Fires represented")
    ax_b.set_ylabel("Representative fire")
    clean_axis(ax_b)
    panel_label(ax_b, "B")

    ax_c = fig.add_axes([0.62, 0.39, 0.30, 0.17])
    cov = stats.medoid_coverage
    ax_c.plot(cov["n_medoids"], cov["p90_nearest_distance"], marker="o", color=FIREBRICK, label="90th percentile")
    ax_c.plot(cov["n_medoids"], cov["median_nearest_distance"], marker="o", color=MORPH_BLUE, label="median")
    ax_c.set_xlabel("Number of representative fires")
    ax_c.set_ylabel("Distance to nearest representative")
    ax_c.legend(frameon=False, loc="upper right", fontsize=6.8)
    clean_axis(ax_c)
    panel_label(ax_c, "C")

    ax_d = fig.add_axes([0.06, 0.08, 0.62, 0.23])
    ax_d.axis("off")
    panel_label(ax_d, "D", x=-0.02, y=1.08)
    transects = [
        ("gradient 1", "morph_pc1", 0.05),
        ("gradient 2", "morph_pc2", 0.36),
        ("gradient 3", "morph_pc3", 0.67),
    ]
    profile_ids = []
    transect_rows = []
    for label, pc, x0 in transects:
        rows = transect_examples(features, pc, bins=5, eligible=features["duration_days"] >= 2).reset_index(drop=True)
        transect_rows.append((label, pc, x0, rows))
        profile_ids.extend(rows["fire_id"].astype(str).tolist())
    tran_profiles = profiles_for_fire_ids(data["slices"], profile_ids)
    for label, pc, x0, rows in transect_rows:
        fig.text(0.08 + x0 * 0.62, 0.265, label, ha="left", va="bottom", fontsize=8.2, fontweight="bold")
        for i, row in rows.iterrows():
            fx = 0.08 + x0 * 0.62 + i * 0.035
            iax = fig.add_axes([fx, 0.150, 0.030, 0.070])
            draw_vase(iax, tran_profiles[row["fire_id"]], color=SHAPE_COLORS.get(row["shape_label"], MORPH_BLUE), linewidth=0.23)
        vals = rows[pc].to_numpy(float)
        fig.text(0.08 + x0 * 0.62, 0.122, f"{vals.min():.1f}", fontsize=6.5, color="#555555")
        fig.text(0.08 + x0 * 0.62 + 0.145, 0.122, f"{vals.max():.1f}", fontsize=6.5, color="#555555")

    ax_e = fig.add_axes([0.74, 0.10, 0.20, 0.21])
    overlap = stats.category_overlap
    val = float(overlap.loc[overlap["metric"].str.contains("purity"), "value"].iloc[0])
    ref = float(overlap.loc[overlap["metric"].str.contains("purity"), "null_or_reference"].iloc[0])
    ax_e.bar(["observed\nlocal purity", "class-frequency\nreference"], [val, ref], color=[MORPH_BLUE, "#c8d0d8"])
    ax_e.set_ylim(0, 1)
    ax_e.set_ylabel("Neighbors with same label")
    ax_e.text(0.5, 0.92, "labels remain\nsoft landmarks", transform=ax_e.transAxes, ha="center", va="top", fontsize=8)
    clean_axis(ax_e)
    panel_label(ax_e, "E", x=-0.30, y=1.08)

    return fig


def main() -> int:
    fig = build()
    save_figure(fig, "Figure_2")
    plt.close(fig)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
