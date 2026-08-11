"""Helpers for annotating cubes with provenance metadata."""

from __future__ import annotations

from typing import Any

import xarray as xr


def set_cube_provenance(
    ds_or_da: xr.Dataset | xr.DataArray,
    *,
    source: str,
    is_synthetic: bool,
    freq: str | None,
    requested_start: Any,
    requested_end: Any,
    backend_error: str | None = None,
) -> xr.Dataset | xr.DataArray:
    """Attach standardized provenance metadata to a cube.

    Parameters
    ----------
    ds_or_da
        Dataset or DataArray to annotate.
    source
        Identifier for the upstream data source (e.g., "gridmet_streaming").
    is_synthetic
        Whether the data were synthesized locally rather than retrieved
        from a real backend.
    freq
        Temporal frequency code used to construct the time axis.
    requested_start, requested_end
        Original start/end requested by the user.
    backend_error
        Optional backend error text captured during fallback.
    """

    target = ds_or_da
    target.attrs.update(
        {
            "source": source,
            "is_synthetic": bool(is_synthetic),
            "freq": freq,
            "requested_start": str(requested_start) if requested_start is not None else None,
            "requested_end": str(requested_end) if requested_end is not None else None,
        }
    )
    if backend_error is not None:
        target.attrs["backend_error"] = str(backend_error)
    elif "backend_error" in target.attrs:
        target.attrs.pop("backend_error", None)

    return target


__all__ = ["set_cube_provenance"]
