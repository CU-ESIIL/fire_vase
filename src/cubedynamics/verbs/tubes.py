from __future__ import annotations

from typing import Callable, Union

import xarray as xr

from .. import tubes as tubes_backend
from .vase import vase as vase_verb


def tubes(
    rule: Union[str, Callable[[xr.DataArray], xr.DataArray]] = "ndvi",
    lo: float = 0.3,
    hi: float = 0.8,
    connectivity: int = 6,
    select: Union[str, int] = "longest",  # "longest", "largest", or explicit tube_id
    hull_method: str = "convex",
    time_dim: str = "time",
    y_dim: str = "y",
    x_dim: str = "x",
    **plot_kwargs,
):
    """
    High-level verb: find suitability tubes and plot one as a vase.

    Usage:
        pipe(cube) | v.tubes()
        pipe(cube) | v.tubes(lo=0.2, hi=0.9, select="largest")
        pipe(cube) | v.tubes(select=5, elev=45, azim=35)

    Steps:
      1) Build a suitability mask (default: NDVI-based).
      2) Label 3D connected components (tubes) in (time, y, x).
      3) Compute per-tube metrics.
      4) Select a tube by rule or explicit tube_id.
      5) Convert that tube into a VaseDefinition.
      6) Delegate to v.vase(vase=...) to render the 3D cube plot.
    """

    def _inner(da: xr.DataArray):
        # 1. Suitability mask
        if isinstance(rule, str):
            if rule == "ndvi":
                mask = tubes_backend.compute_suitability_from_ndvi(
                    da, lo=lo, hi=hi, time_dim=time_dim, y_dim=y_dim, x_dim=x_dim
                )
            else:
                raise ValueError(f"Unknown rule {rule!r}; only 'ndvi' is supported for now.")
        else:
            # callable rule: rule(da) -> boolean mask
            mask = rule(da)
            if not isinstance(mask, xr.DataArray):
                raise TypeError("Custom rule must return an xarray.DataArray.")
            if mask.dims != da.dims:
                raise ValueError("Custom rule mask must have the same dims as the input cube.")

        # 2. Label tubes
        tube_da = tubes_backend.label_tubes(
            mask,
            connectivity=connectivity,
            time_dim=time_dim,
            y_dim=y_dim,
            x_dim=x_dim,
        )

        # 3. Compute tube metrics
        metrics = tubes_backend.compute_tube_metrics(
            tube_da,
            time_dim=time_dim,
            y_dim=y_dim,
            x_dim=x_dim,
        )

        if metrics.empty:
            raise ValueError("No tubes found in suitability mask; try adjusting thresholds.")

        # 4. Select tube
        if isinstance(select, str):
            if select == "longest":
                row = metrics.sort_values(["duration_steps", "n_voxels"], ascending=False).iloc[0]
            elif select == "largest":
                row = metrics.sort_values(["n_voxels", "duration_steps"], ascending=False).iloc[0]
            else:
                raise ValueError("select must be 'longest', 'largest', or an integer tube_id.")
            tube_id_val = int(row["tube_id"])
        else:
            # explicit tube_id
            tube_id_val = int(select)
            if tube_id_val not in metrics["tube_id"].values:
                raise ValueError(f"tube_id {tube_id_val} not found in computed tubes.")

        # 5. Convert selected tube -> VaseDefinition
        vase_def = tubes_backend.tube_to_vase_definition(
            cube=da,
            tube_da=tube_da,
            tube_id=tube_id_val,
            time_dim=time_dim,
            y_dim=y_dim,
            x_dim=x_dim,
            hull_method=hull_method,
            interp="nearest",
        )

        # 6. Delegate to v.vase for plotting
        return vase_verb(vase=vase_def, **plot_kwargs)(da)

    return _inner
