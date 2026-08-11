"""Synthetic event helpers used throughout the documentation."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

import geopandas as gpd
import numpy as np
from shapely import affinity
from shapely.geometry import Polygon

__all__ = ["make_demo_event"]


def _ellipse_polygon(width: float, height: float, n_vertices: int = 120) -> Polygon:
    """Return a simple ellipse polygon centered at the origin."""
    angles = np.linspace(0.0, 2 * np.pi, n_vertices, endpoint=False)
    xy = np.column_stack([width * np.cos(angles), height * np.sin(angles)])
    return Polygon(xy)


def make_demo_event(
    n_days: int = 7,
    *,
    start: date | None = None,
    random_state: Optional[int] = None,
    rotation_per_day: float = 4.5,
    drift_per_day: float = 600.0,
) -> gpd.GeoDataFrame:
    """Create a synthetic FIRED-like GeoDataFrame for demos.

    Parameters
    ----------
    n_days:
        Number of daily polygons that should be generated.
    start:
        Optional ``datetime.date`` value used for the first observation.
        When omitted the demo starts on ``2024-08-01``.
    random_state:
        Seed controlling the small variations applied to each day's hull.
    rotation_per_day:
        Degrees to rotate the geometry on each step.  Small values keep the
        event shape aligned, while larger values accentuate spiral patterns.
    drift_per_day:
        Number of meters to translate the centroid per day along the positive
        X axis.  The value is interpreted in the EPSG:5070 projected CRS.

    Returns
    -------
    geopandas.GeoDataFrame
        Cleaned daily polygons with ``event_day`` and ``date`` columns that are
        compatible with :func:`cubedynamics.hulls.plot_ruled_time_hull`.
    """

    if n_days < 2:
        raise ValueError("At least two days are required to describe growth.")

    rng = np.random.default_rng(random_state)
    base = _ellipse_polygon(4500.0, 2600.0)
    start_date = start or date(2024, 8, 1)

    rows: list[dict[str, object]] = []
    for i in range(n_days):
        growth = 0.75 + 0.35 * rng.random()
        squish = 0.8 + 0.4 * rng.random()
        geom = affinity.scale(base, xfact=growth, yfact=growth * squish, origin=(0.0, 0.0))
        geom = affinity.rotate(geom, rotation_per_day * i, origin=(0.0, 0.0))
        geom = affinity.translate(geom, xoff=drift_per_day * i, yoff=120.0 * np.sin(i / 2))

        rows.append(
            {
                "event_day": float(i + 1),
                "date": start_date + timedelta(days=i),
                "geometry": geom,
            }
        )

    gdf = gpd.GeoDataFrame(rows, geometry="geometry", crs="EPSG:5070")
    return gdf
