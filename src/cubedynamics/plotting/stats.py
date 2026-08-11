from __future__ import annotations

from dataclasses import dataclass

import xarray as xr

from ..vase import VaseDefinition, build_vase_mask


@dataclass
class StatVase:
    vase: VaseDefinition
    time_dim: str = "time"
    y_dim: str = "y"
    x_dim: str = "x"

    def compute(self, cube: xr.DataArray):
        """Return ``(masked_cube, mask)`` without triggering full cube load.

        This stat is intended for use inside ``CubePlot.stat_vase``. It
        delegates to :func:`cubedynamics.vase.build_vase_mask` to maintain the
        streaming-first contract, then applies ``cube.where(mask)`` so geoms can
        work with the masked data while preserving the mask for overlays.
        """
        mask = build_vase_mask(
            cube,
            self.vase,
            time_dim=self.time_dim,
            y_dim=self.y_dim,
            x_dim=self.x_dim,
        )
        masked_cube = cube.where(mask)
        return masked_cube, mask
