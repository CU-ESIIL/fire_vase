"""Plotting helpers for cube visualizations."""

from .axis_rig import AxisRigSpec
from .cube_viewer import cube_from_dataarray
from .cube_plot import CubePlot, CubeTheme, theme_cube_studio
from .tail_association import (
    TailAssociationStats,
    ghosh_partial_spearman,
    normalized_ranks,
    plot_tail_association_from_cube,
    plot_tail_association_grid,
    plot_tail_association_triptych,
    tail_association_stats,
)

__all__ = [
    "cube_from_dataarray",
    "AxisRigSpec",
    "CubePlot",
    "CubeTheme",
    "theme_cube_studio",
    "TailAssociationStats",
    "normalized_ranks",
    "ghosh_partial_spearman",
    "tail_association_stats",
    "plot_tail_association_triptych",
    "plot_tail_association_grid",
    "plot_tail_association_from_cube",
]
