"""Shared visual style for the Fire VASE main figures."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/cubedynamics-mpl-cache")

import matplotlib as mpl
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[2]
MAIN_FIGURE_DIR = ROOT / "figures/main"
SUPPLEMENT_DIR = ROOT / "figures/supplement"
DERIVED_STATS_DIR = MAIN_FIGURE_DIR / "derived_stats"

SEED = 20260722
FULL_WIDTH = (7.1, 4.8)
TALL_WIDTH = (7.1, 6.3)
CHARCOAL = "#252525"
MUTED = "#6f7378"
LIGHT = "#e5e7eb"
MID_GRAY = "#9aa0a6"
BACKGROUND = "#ffffff"
MORPH_BLUE = "#4f86c6"
MORPH_DARK = "#1f4e79"
FIREBRICK = "#b23a32"
TEAL = "#2a9d8f"
PURPLE = "#7b5bbd"
GOLD = "#c49a29"
CLIMATE_CMAP = "viridis"

SHAPE_COLORS = {
    "single flash": "#6f7378",
    "skinny persistent": MORPH_BLUE,
    "compact steady": TEAL,
    "multi-pulse complex": MORPH_DARK,
    "front-loaded plateau": GOLD,
    "late surge": PURPLE,
    "broad rapid": FIREBRICK,
}


def set_style() -> None:
    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
            "figure.facecolor": BACKGROUND,
            "axes.facecolor": BACKGROUND,
            "axes.edgecolor": CHARCOAL,
            "axes.labelcolor": CHARCOAL,
            "axes.titlecolor": CHARCOAL,
            "axes.linewidth": 0.7,
            "xtick.color": CHARCOAL,
            "ytick.color": CHARCOAL,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "axes.labelsize": 9,
            "axes.titlesize": 9,
            "legend.fontsize": 8,
            "figure.dpi": 150,
            "savefig.dpi": 600,
            "savefig.facecolor": BACKGROUND,
            "savefig.edgecolor": BACKGROUND,
            "lines.linewidth": 1.2,
        }
    )


def panel_label(ax: plt.Axes, label: str, *, x: float = -0.12, y: float = 1.05) -> None:
    ax.text(
        x,
        y,
        label,
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=12,
        fontweight="bold",
        color=CHARCOAL,
    )


def clean_axis(ax: plt.Axes) -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(color=LIGHT, lw=0.45, alpha=0.9)


def save_figure(fig: plt.Figure, name: str) -> dict[str, str]:
    MAIN_FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    paths = {
        "pdf": MAIN_FIGURE_DIR / f"{name}.pdf",
        "png": MAIN_FIGURE_DIR / f"{name}.png",
        "svg": MAIN_FIGURE_DIR / f"{name}.svg",
    }
    for suffix, path in paths.items():
        fig.savefig(path, bbox_inches="tight", dpi=600)
    return {key: value.as_posix() for key, value in paths.items()}


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def pc_axis_label(axis: int, evr: float) -> str:
    return f"Developmental gradient {axis} ({evr * 100:.1f}% variance)"
