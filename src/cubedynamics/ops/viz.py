"""Visualization verbs wrapping simple interactive widgets."""

from __future__ import annotations

from typing import Any, Optional, Tuple

import xarray as xr

from ..deprecations import warn_deprecated
from ..verbs.plot import plot as _plot_verb


def plot(
    time_dim: str | None = "time",
    cmap: str = "viridis",
    clim: Optional[Tuple[float, float]] = None,
    aspect: str = "equal",
    camera: Optional[dict] = None,
):
    """Deprecated. Use :func:`cubedynamics.verbs.plot` instead.

    This wrapper exists for backward compatibility and forwards arguments to
    the canonical plotting verb while preserving historical validation.
    """

    def _inner(cube: Any):
        warn_deprecated(
            "cubedynamics.ops.viz.plot",
            "cubedynamics.verbs.plot",
            since="0.2.0",
            removal="0.3.0",
        )

        # Preserve backwards-compatible validation for callers still using this module.
        if not isinstance(cube, xr.DataArray):
            raise TypeError(
                "v.plot expects an xarray.DataArray. "
                f"Got type {type(cube)!r}."
            )

        # Map legacy args to the newer verb implementation.
        return _plot_verb(
            cube,
            time_dim=time_dim,
            cmap=cmap,
            clim=clim,
            camera=camera,
        )

    return _inner


__all__ = ["plot"]
