"""Vegetation index helpers."""

from __future__ import annotations

import xarray as xr

from ..config import BAND_DIM


def _get_band_dataarray(s2: xr.Dataset | xr.DataArray) -> xr.DataArray:
    if isinstance(s2, xr.DataArray):
        return s2
    if BAND_DIM in s2.dims:
        return s2.to_array().squeeze("variable", drop=True)
    if len(s2.data_vars) == 1:
        return s2[list(s2.data_vars)[0]]
    raise ValueError("Unable to determine data variable containing Sentinel-2 bands.")


def compute_ndvi_from_s2(
    s2: xr.Dataset | xr.DataArray,
    band_nir: str = "B08",
    band_red: str = "B04",
    eps: float = 1e-6,
) -> xr.DataArray:
    """Compute NDVI from a Sentinel-2 Dataset or DataArray."""

    arr = _get_band_dataarray(s2)
    nir = arr.sel({BAND_DIM: band_nir})
    red = arr.sel({BAND_DIM: band_red})
    ndvi = (nir - red) / (nir + red + eps)
    ndvi = ndvi.astype("float32")
    ndvi.name = "ndvi"
    ndvi.attrs = {
        "long_name": "Normalized Difference Vegetation Index",
        "formula": f"({band_nir} - {band_red}) / ({band_nir} + {band_red})",
        "bands": {"nir": band_nir, "red": band_red},
    }
    return ndvi
