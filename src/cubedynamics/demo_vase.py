from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from shapely.geometry import Polygon
import xarray as xr

from .vase import VaseDefinition, VaseSection

__all__ = ["demo"]


@dataclass
class DemoNamespace:
    """
    Namespace for small demo helpers, e.g.:

        cd.demo.stacked_polygon_vase(da)
    """

    def stacked_polygon_vase(
        self,
        da: xr.DataArray,
        n_sections: int = 4,
        shrink: float = 0.1,
        interp: str = "nearest",
        time_dim: str = "time",
        x_dim: str = "x",
        y_dim: str = "y",
    ) -> VaseDefinition:
        """
        Build a simple VaseDefinition composed of stacked polygons over time.

        Parameters
        ----------
        da : xr.DataArray
            Cube with (time, y, x) dims (or compatible); coordinates define
            the spatial extent used to build polygons.
        n_sections : int, default 4
            Number of time sections with distinct polygons (stacked over time).
        shrink : float, default 0.1
            Fraction of width/height to shrink from the cube bounds at each
            step to create a tapering or expanding tube.
        interp : {"nearest", "linear"}, default "nearest"
            Interpolation mode for polygons between sections.
        time_dim, x_dim, y_dim : str
            Dimension names for time, x and y.

        Returns
        -------
        VaseDefinition
            Time-varying vase built from simple geometric polygons.
        """
        if time_dim not in da.dims:
            raise ValueError(f"Expected time dim '{time_dim}' in da.dims")
        if x_dim not in da.dims or y_dim not in da.dims:
            raise ValueError(f"Expected spatial dims '{y_dim}', '{x_dim}' in da.dims")

        times = da[time_dim].values
        if len(times) < n_sections:
            n_sections = len(times)

        idxs = np.linspace(0, len(times) - 1, n_sections, dtype=int)
        section_times = times[idxs]

        x0 = float(da[x_dim].min())
        x1 = float(da[x_dim].max())
        y0 = float(da[y_dim].min())
        y1 = float(da[y_dim].max())

        width = x1 - x0
        height = y1 - y0

        sections = []
        for i, t in enumerate(section_times):
            factor = 1.0 - shrink * i

            cx = 0.5 * (x0 + x1)
            cy = 0.5 * (y0 + y1)

            half_w = 0.5 * width * factor
            half_h = 0.5 * height * factor

            px0 = cx - half_w
            px1 = cx + half_w
            py0 = cy - half_h
            py1 = cy + half_h

            polygon = Polygon(
                [
                    (px0, py0),
                    (px1, py0),
                    (px1, py1),
                    (px0, py1),
                ]
            )

            sections.append(VaseSection(time=t, polygon=polygon))

        return VaseDefinition(sections=sections, interp=interp)


# Public namespace instance
demo = DemoNamespace()
