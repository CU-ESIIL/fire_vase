"""Consistent Fire VASE glyph drawing helpers."""

from __future__ import annotations

import numpy as np
import pandas as pd
from matplotlib.collections import LineCollection
from matplotlib.patches import Ellipse
import matplotlib.pyplot as plt

from style import CHARCOAL, CLIMATE_CMAP, MORPH_BLUE


def draw_vase(
    ax: plt.Axes,
    profile: pd.DataFrame,
    *,
    color: str = MORPH_BLUE,
    climate_col: str | None = None,
    climate_norm=None,
    cmap: str = CLIMATE_CMAP,
    outline: str = CHARCOAL,
    linewidth: float = 0.45,
    alpha: float = 0.92,
) -> None:
    ax.set_aspect("equal")
    ax.axis("off")
    if profile is None or profile.empty:
        return
    p = profile.sort_values("relative_time").copy()
    if len(p) == 1:
        p = pd.concat([p, p], ignore_index=True)
        p.loc[:, "relative_time"] = [0.45, 0.55]
    y = p["relative_time"].to_numpy(float)
    width = np.clip(p["width"].to_numpy(float), 0.035, 1.0)
    left = -0.42 * width
    right = 0.42 * width
    ell_h = max(0.035, min(0.075, 0.75 / max(len(p), 6)))
    if climate_col and climate_col in p.columns:
        vals = p[climate_col].to_numpy(float)
        if climate_norm is None:
            finite = vals[np.isfinite(vals)]
            climate_norm = plt.Normalize(float(np.nanquantile(finite, 0.05)), float(np.nanquantile(finite, 0.95))) if finite.size else None
        colors = plt.get_cmap(cmap)(climate_norm(vals)) if climate_norm else [color] * len(p)
    else:
        colors = [color] * len(p)

    segments = []
    for i in range(len(y) - 1):
        segments.append([(left[i], y[i]), (left[i + 1], y[i + 1])])
        segments.append([(right[i], y[i]), (right[i + 1], y[i + 1])])
    ax.add_collection(LineCollection(segments, colors=outline, linewidths=linewidth * 0.65, alpha=0.8))
    for yi, wi, ci in zip(y, width, colors):
        ax.add_patch(
            Ellipse(
                (0, yi),
                width=0.84 * wi,
                height=ell_h,
                facecolor=ci,
                edgecolor=outline,
                linewidth=linewidth,
                alpha=alpha,
            )
        )
    ax.plot(left, y, color=outline, lw=linewidth * 1.3)
    ax.plot(right, y, color=outline, lw=linewidth * 1.3)
    ax.set_xlim(-0.50, 0.50)
    ax.set_ylim(-0.04, 1.04)


def draw_area_history(ax: plt.Axes, profile: pd.DataFrame, *, color: str = MORPH_BLUE) -> None:
    if profile is None or profile.empty:
        return
    p = profile.sort_values("relative_time")
    x = np.arange(len(p))
    y = p["cumulative_area_km2"].to_numpy(float)
    if np.nanmax(y) > 0:
        y = y / np.nanmax(y)
    ax.step(x, y, where="post", color=color, lw=1.4)
    ax.fill_between(x, 0, y, step="post", color=color, alpha=0.13)
    ax.set_ylim(0, 1.04)
    ax.set_xlim(0, max(1, len(p) - 1))
    ax.set_xticks([])
    ax.set_yticks([0, 1])
    ax.tick_params(labelsize=7, length=2)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


def draw_partial_vase_pair(
    ax_partial: plt.Axes,
    ax_full: plt.Axes,
    profile: pd.DataFrame,
    fraction: float,
    *,
    color: str = MORPH_BLUE,
) -> None:
    p = profile.sort_values("relative_time")
    partial = p[p["relative_time"] <= fraction].copy()
    if partial.empty:
        partial = p.iloc[:1].copy()
    draw_vase(ax_partial, partial, color=color)
    draw_vase(ax_full, p, color="#9aa0a6", alpha=0.32)
    draw_vase(ax_full, partial, color=color)
