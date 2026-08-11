"""NDVI-related pipeable operations."""

from __future__ import annotations

import xarray as xr


def ndvi_from_s2(nir_band: str = "B08", red_band: str = "B04"):
    """Factory returning a Sentinel-2 NDVI transform for pipe chains."""

    def _inner(s2: xr.DataArray | xr.Dataset):
        if "band" not in s2.dims:
            raise ValueError("ndvi_from_s2 expects a 'band' dimension.")

        nir = s2.sel(band=nir_band)
        red = s2.sel(band=red_band)

        ndvi = (nir - red) / (nir + red)
        ndvi = ndvi.rename("ndvi").astype("float32")
        ndvi.attrs.update(
            {
                "long_name": "Normalized Difference Vegetation Index",
                "formula": "(NIR - Red) / (NIR + Red)",
                "nir_band": nir_band,
                "red_band": red_band,
            }
        )
        return ndvi

    return _inner


__all__ = ["ndvi_from_s2"]
