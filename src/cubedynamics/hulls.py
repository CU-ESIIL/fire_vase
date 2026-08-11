"""Plotting helper that builds ruled surfaces from daily polygons."""

from __future__ import annotations


import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from shapely.geometry import LineString, MultiPolygon, Polygon

__all__ = ["plot_ruled_time_hull"]


def _largest_polygon(geom: Polygon | MultiPolygon | None) -> Polygon | None:
    if geom is None or geom.is_empty:
        return None
    if isinstance(geom, Polygon):
        return geom
    if isinstance(geom, MultiPolygon):
        polys = [p for p in geom.geoms if isinstance(p, Polygon)]
        return max(polys, key=lambda p: p.area) if polys else None
    return None


def _sample_ring_equal_steps(poly: Polygon, n_samples: int = 160) -> np.ndarray:
    """Equal-arclength samples on the polygon exterior."""
    if poly is None or poly.is_empty:
        return np.empty((0, 2))
    ring = LineString(poly.exterior.coords)
    if ring.coords and ring.coords[0] == ring.coords[-1]:
        ring = LineString(list(ring.coords)[:-1])
    length = ring.length
    if not np.isfinite(length) or length <= 0:
        return np.empty((0, 2))
    steps = np.linspace(0, length, n_samples, endpoint=False)
    pts = np.array([ring.interpolate(dist).coords[0] for dist in steps], dtype=float)
    return pts


def _center_xy(xy: np.ndarray) -> np.ndarray:
    if xy.size == 0:
        return xy
    return xy - xy.mean(axis=0)


def plot_ruled_time_hull(
    eg_clean: gpd.GeoDataFrame,
    *,
    date_col: str = "date",
    z_col: str = "event_day",
    n_ring_samples: int = 200,
    n_theta: int = 128,
    center_each_day: bool = True,
    crs_epsg: int | None = 5070,
    smooth_over_z: int | None = 3,
    cmap: str = "cividis",
    wall_alpha: float = 0.35,
    edge_alpha: float = 0.25,
    elev: float = 26,
    azim: float = -58,
    figsize: tuple[float, float] = (9, 8),
) -> tuple[Figure, Axes]:
    """Build a 3D ruled surface describing event growth through time."""

    eg = eg_clean.copy()
    eg[date_col] = pd.to_datetime(eg[date_col], errors="coerce")
    eg = eg.sort_values(date_col).reset_index(drop=True)

    if z_col in eg.columns:
        z_values = eg[z_col].to_numpy(float)
    else:
        z_values = np.arange(1, len(eg) + 1, dtype=float)

    if crs_epsg is not None:
        try:
            eg = eg.to_crs(epsg=crs_epsg)
        except Exception:
            pass

    rings: list[np.ndarray | None] = []
    for geom in eg.geometry:
        poly = _largest_polygon(geom)
        if poly is None:
            rings.append(None)
            continue
        xy = _sample_ring_equal_steps(poly, n_ring_samples)
        if xy.size == 0:
            rings.append(None)
            continue
        if center_each_day:
            xy = _center_xy(xy)
        rings.append(xy)

    keep = [i for i, xy in enumerate(rings) if xy is not None]
    if len(keep) < 2:
        raise ValueError("At least two valid polygons are required to build a hull.")

    rings = [rings[i] for i in keep]
    z_values = z_values[keep]
    dates = eg.iloc[keep][date_col]

    thetas = np.linspace(0, 2 * np.pi, n_theta, endpoint=False)
    directions = np.stack([np.cos(thetas), np.sin(thetas)], axis=1)

    radii = np.zeros((len(rings), n_theta), dtype=float)
    for i, xy in enumerate(rings):
        dots = directions @ xy.T
        radii[i, :] = dots.max(axis=1)

    if smooth_over_z and smooth_over_z > 1 and smooth_over_z % 2 == 1:
        try:
            from scipy.ndimage import uniform_filter1d  # type: ignore

            radii = uniform_filter1d(radii, size=smooth_over_z, axis=0, mode="nearest")
        except Exception:
            pass

    mesh = np.zeros((len(rings), n_theta, 3), dtype=float)
    mesh[:, :, 0] = radii * directions[None, :, 0]
    mesh[:, :, 1] = radii * directions[None, :, 1]
    mesh[:, :, 2] = z_values[:, None]

    quads: list[np.ndarray] = []
    for i in range(len(rings) - 1):
        for j in range(n_theta):
            j_next = (j + 1) % n_theta
            quad = np.array(
                [
                    mesh[i, j],
                    mesh[i, j_next],
                    mesh[i + 1, j_next],
                    mesh[i + 1, j],
                ]
            )
            if np.all(np.isfinite(quad)):
                quads.append(quad)

    fig = plt.figure(figsize=figsize)
    ax = fig.add_subplot(111, projection="3d")

    hull_color = plt.get_cmap(cmap)(0.6)
    wall = Poly3DCollection(
        quads,
        facecolors=(hull_color[0], hull_color[1], hull_color[2], wall_alpha),
        edgecolors=(0, 0, 0, edge_alpha),
        linewidths=0.25,
    )
    if hasattr(wall, "set_zsort"):
        wall.set_zsort("min")
    ax.add_collection3d(wall)

    ax.set_xlim(np.nanmin(mesh[:, :, 0]), np.nanmax(mesh[:, :, 0]))
    ax.set_ylim(np.nanmin(mesh[:, :, 1]), np.nanmax(mesh[:, :, 1]))
    ax.set_zlim(np.nanmin(mesh[:, :, 2]), np.nanmax(mesh[:, :, 2]))

    km_fmt = FuncFormatter(lambda value, pos: f"{value / 1000:.1f}")
    ax.xaxis.set_major_formatter(km_fmt)
    ax.yaxis.set_major_formatter(km_fmt)
    ax.set_xlabel("X (km)")
    ax.set_ylabel("Y (km)")
    ax.set_zlabel("Event day")

    ax.view_init(elev=elev, azim=azim)
    fig.subplots_adjust(left=0.08, right=0.98, bottom=0.08, top=0.92)

    t0 = dates.iloc[0].date() if dates.notna().any() else "?"
    t1 = dates.iloc[-1].date() if dates.notna().any() else "?"
    ax.set_title(f"Ruled time hull — {t0} → {t1} (θ={n_theta}, days={len(rings)})")

    return fig, ax
