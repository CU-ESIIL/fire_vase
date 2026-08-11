#!/usr/bin/env python3
"""Render Figure 4: climate aligns with developmental geometry without determining it."""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from morphospace import axis_limits, fit_pca, geometry_columns, load_data, profiles_for_fire_ids
from statistics import compute_validation_bundle
from style import CLIMATE_CMAP, FIREBRICK, MORPH_BLUE, TALL_WIDTH, clean_axis, panel_label, pc_axis_label, save_figure, set_style
from vase_glyphs import draw_vase


def _cv_summary(cv: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for keys, sub in cv.groupby(["model", "fold_kind", "target"]):
        vals = sub["r2"].dropna().to_numpy(float)
        if vals.size == 0:
            continue
        rows.append(
            {
                "model": keys[0],
                "fold_kind": keys[1],
                "target": keys[2],
                "mean": float(np.mean(vals)),
                "lo": float(np.quantile(vals, 0.025)),
                "hi": float(np.quantile(vals, 0.975)),
                "n_folds": int(vals.size),
            }
        )
    return pd.DataFrame(rows)


def build(data=None, stats=None):
    set_style()
    data = load_data() if data is None else data
    stats = compute_validation_bundle(data) if stats is None else stats
    features = data["features"]
    columns = geometry_columns(features, data["loadings"])
    pca = fit_pca(features, columns, n_components=5)
    complete = features[features["climate_available"]].dropna(subset=["mean_vpd_kpa", "max_vpd_kpa", "mean_maximum_temperature_c", "mean_wind_speed_m_s"]).copy()
    xlim, ylim = axis_limits(features)

    fig = plt.figure(figsize=(7.1, 7.8))

    ax_a = fig.add_axes([0.08, 0.43, 0.43, 0.45])
    hb = ax_a.hexbin(
        complete["morph_pc1"],
        complete["morph_pc2"],
        C=complete["max_vpd_kpa"],
        reduce_C_function=np.nanmedian,
        gridsize=120,
        mincnt=25,
        cmap=CLIMATE_CMAP,
        linewidths=0,
        rasterized=True,
    )
    ax_a.set_xlim(xlim)
    ax_a.set_ylim(ylim)
    ax_a.set_xlabel(pc_axis_label(1, pca.explained_variance_ratio[0]))
    ax_a.set_ylabel(pc_axis_label(2, pca.explained_variance_ratio[1]))
    ax_a.text(0.02, 0.98, f"centroid climate-complete fires n = {len(complete):,}", transform=ax_a.transAxes, ha="left", va="top", fontsize=8)
    clean_axis(ax_a)
    panel_label(ax_a, "A")
    cb = fig.colorbar(hb, ax=ax_a, fraction=0.035, pad=0.02)
    cb.set_label("Median daily maximum VPD (kPa)", fontsize=8)
    cb.ax.tick_params(labelsize=7)

    specs = [
        ("mean_maximum_temperature_c", "Average daily high temp. (C)"),
        ("mean_vpd_kpa", "Average VPD (kPa)"),
        ("mean_wind_speed_m_s", "Average wind speed (m/s)"),
    ]
    small_axes = [
        [0.61, 0.70, 0.14, 0.18],
        [0.82, 0.70, 0.14, 0.18],
        [0.61, 0.47, 0.14, 0.18],
    ]
    for i, (col, label) in enumerate(specs):
        ax = fig.add_axes(small_axes[i])
        h = ax.hexbin(complete["morph_pc1"], complete["morph_pc2"], C=complete[col], reduce_C_function=np.nanmedian, gridsize=70, mincnt=25, cmap=CLIMATE_CMAP, linewidths=0, rasterized=True)
        ax.set_xlim(xlim)
        ax.set_ylim(ylim)
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_title(label, pad=2, fontsize=7.2)
        clean_axis(ax)
        cbi = fig.colorbar(h, ax=ax, fraction=0.045)
        cbi.ax.tick_params(labelsize=6.5)
        if i == 0:
            panel_label(ax, "B", x=-0.30, y=0.98)

    ax_c = fig.add_axes([0.82, 0.47, 0.14, 0.18])
    cv = stats.climate_cv[
        stats.climate_cv["fold_kind"].isin(["random", "region"])
        & stats.climate_cv["model"].isin(["climate predicts morphology", "morphology predicts climate"])
    ].copy()
    labels = []
    colors = []
    means = []
    los = []
    his = []
    order = [
        ("climate predicts morphology", "random", "shape\nrandom"),
        ("climate predicts morphology", "region", "shape\nregion"),
        ("morphology predicts climate", "random", "climate\nrandom"),
        ("morphology predicts climate", "region", "climate\nregion"),
    ]
    for model, fold, label in order:
        vals = cv[(cv["model"] == model) & (cv["fold_kind"] == fold)]["r2"].dropna().to_numpy(float)
        labels.append(label)
        colors.append(MORPH_BLUE if model == "climate predicts morphology" else FIREBRICK)
        means.append(float(np.mean(vals)) if vals.size else np.nan)
        los.append(float(np.mean(vals) - np.quantile(vals, 0.025)) if vals.size else np.nan)
        his.append(float(np.quantile(vals, 0.975) - np.mean(vals)) if vals.size else np.nan)
    ypos = np.arange(len(labels))
    ax_c.barh(ypos, means, color=colors, alpha=0.86)
    ax_c.errorbar(means, ypos, xerr=[los, his], fmt="none", color="#333333", lw=0.7, capsize=2)
    ax_c.axvline(0, color="#333333", lw=0.6)
    ax_c.set_yticks(ypos, labels, fontsize=5.9)
    ax_c.set_xlabel("Held-out variance explained (R2)", fontsize=6.8)
    ax_c.set_title("Climate-shape association", pad=2, fontsize=7.4)
    ax_c.tick_params(axis="x", labelsize=6.5)
    clean_axis(ax_c)
    panel_label(ax_c, "C", x=-0.15, y=1.22)

    pairs = data["matched"].groupby("comparison_type").head(1).reset_index(drop=True)
    profiles = profiles_for_fire_ids(data["slices"], set(pairs["fire_id_a"].astype(str)) | set(pairs["fire_id_b"].astype(str)))
    ax_d = fig.add_axes([0.07, 0.08, 0.48, 0.24])
    ax_d.axis("off")
    panel_label(ax_d, "D", x=-0.03, y=1.12)
    for i, row in pairs.iterrows():
        x0 = 0.10 + (i % 2) * 0.25
        y0 = 0.170
        for j, fid in enumerate([row["fire_id_a"], row["fire_id_b"]]):
            iax = fig.add_axes([x0 + j * 0.054, y0, 0.041, 0.078])
            draw_vase(iax, profiles[str(fid)], climate_col="vpd_kpa")
        caption = "same shape,\ndifferent climate" if "similar morphology" in str(row["comparison_type"]) else "same climate,\ndifferent shape"
        fig.text(
            x0 + 0.050,
            0.118,
            f"{caption}\n"
            f"shape distance {row['geometry_distance']:.2f}\nclimate distance {row['climate_distance']:.2f}\n"
            f"VPD {row['vpd_a_kpa']:.2f}/{row['vpd_b_kpa']:.2f} kPa",
            fontsize=6.3,
            ha="center",
            va="top",
        )

    ax_e = fig.add_axes([0.70, 0.10, 0.25, 0.22])
    mp = stats.matched_population
    x = np.arange(len(mp))
    ax_e.bar(x - 0.18, mp.get("climate_distance", pd.Series([np.nan] * len(mp))), width=0.35, color=FIREBRICK, label="climate distance")
    ax_e.bar(x + 0.18, mp.get("morphology_distance", pd.Series([np.nan] * len(mp))), width=0.35, color=MORPH_BLUE, label="morphology distance")
    ax_e.set_xticks(x, mp["matching_basis"])
    ax_e.set_ylabel("Median distance", fontsize=7.5)
    ax_e.tick_params(axis="x", labelsize=7)
    ax_e.legend(frameon=False, fontsize=7)
    clean_axis(ax_e)
    panel_label(ax_e, "E", x=-0.20, y=1.12)

    return fig


def main() -> int:
    fig = build()
    save_figure(fig, "Figure_4")
    plt.close(fig)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
