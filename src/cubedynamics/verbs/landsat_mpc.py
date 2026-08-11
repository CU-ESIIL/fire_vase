"""Landsat-8 streaming via Microsoft Planetary Computer (MPC).

The :func:`landsat8_mpc` verb streams Landsat 8 Collection 2 Level-2 surface
reflectance from the Microsoft Planetary Computer STAC catalog. It returns a
lazy, dask-backed :class:`xarray.DataArray` with dimensions ``(time, band, y,
x)`` so downstream computations can be composed without loading the full
dataset into memory.

Example
-------
>>> from cubedynamics import pipe, verbs as v
>>> bbox = [-105.35, 39.9, -105.15, 40.1]
>>> cube = pipe(None) | v.landsat8_mpc(
...     bbox=bbox,
...     start="2019-07-01",
...     end="2019-08-01",
... )
>>> da = cube.unwrap()
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from functools import wraps
from typing import Iterable

import numpy as np
import planetary_computer as pc
import rioxarray as rxr
import xarray as xr
from pystac_client import Client

from ..piping import Verb

MPC_STAC_URL = "https://planetarycomputer.microsoft.com/api/stac/v1"

BAND_MAP: Mapping[str, str] = {
    "red": "SR_B4",
    "nir": "SR_B5",
}


def pipeable(func):
    """Decorator that makes a verb callable or pipe-friendly.

    When called without the first positional argument, a :class:`Verb` is
    returned so the function can be used in ``pipe(...) | v.some_verb(...)``
    chains. When called with a ``value`` argument, the function executes
    immediately.
    """

    @wraps(func)
    def _wrapper(*args, **kwargs):
        if args:
            return func(*args, **kwargs)
        return Verb(lambda value: func(value, **kwargs))

    return _wrapper


def landsat8_mpc_stream(
    bbox: Sequence[float],
    start: str,
    end: str,
    band_aliases: Iterable[str] = ("red", "nir"),
    max_cloud_cover: float = 50,
    chunks_xy: Mapping[str, int] | None = None,
    stac_url: str = MPC_STAC_URL,
) -> xr.DataArray:
    """Stream Landsat-8 Collection 2 Level-2 scenes from Microsoft Planetary Computer.

    The stream lazily opens surface reflectance COGs (SR_B4 for red and SR_B5 for
    near-infrared by default) and stacks them into a cube with dimensions
    ``(time, band, y, x)``. Data are returned as ``float32`` and remain dask-backed
    so downstream computations trigger IO as needed.

    Parameters
    ----------
    bbox
        Bounding box ``[minx, miny, maxx, maxy]`` in lon/lat for the STAC search.
    start, end
        ISO date strings delimiting the search interval.
    band_aliases
        Sequence of band aliases to load. Must be keys in :data:`BAND_MAP`.
    max_cloud_cover
        Maximum allowable ``eo:cloud_cover`` percentage for candidate scenes.
    chunks_xy
        Optional mapping for dask chunk sizes along x/y passed to
        :func:`rioxarray.open_rasterio`. Defaults to ``{"x": 1024, "y": 1024}``.
    stac_url
        STAC API endpoint. Defaults to the MPC STAC service.

    Returns
    -------
    xarray.DataArray
        DataArray with dimensions ``(time, band, y, x)`` containing the stacked
        scenes.
    """

    if chunks_xy is None:
        chunks_xy = {"x": 1024, "y": 1024}

    catalog = Client.open(stac_url)

    search = catalog.search(
        collections=["landsat-8-c2-l2"],
        bbox=bbox,
        datetime=f"{start}/{end}",
        query={"eo:cloud_cover": {"lt": max_cloud_cover}},
    )

    items = list(search.get_items())
    if not items:
        raise RuntimeError("No Landsat-8 items found for this query.")

    signed_items = [pc.sign(item) for item in items]
    scene_das: list[xr.DataArray] = []

    for item in signed_items:
        band_das: list[xr.DataArray] = []
        skip_item = False

        for alias in band_aliases:
            asset_id = BAND_MAP[alias]
            asset = item.assets.get(asset_id)
            if asset is None:
                skip_item = True
                break

            href = asset.href
            da = rxr.open_rasterio(href, masked=True, chunks=chunks_xy)
            if "band" in da.dims and da.sizes.get("band", 1) == 1:
                da = da.squeeze("band", drop=True)
            da = da.expand_dims(band=[alias])
            band_das.append(da)

        if skip_item or not band_das:
            continue

        scene = xr.concat(band_das, dim="band")
        dt = np.datetime64(item.properties["datetime"])
        scene = scene.expand_dims(time=[dt])
        scene_das.append(scene)

    if not scene_das:
        raise RuntimeError("No scenes could be stacked (missing assets?).")

    cube = xr.concat(scene_das, dim="time", join="outer").sortby("time")
    cube = cube.astype("float32")
    return cube


@pipeable
def landsat8_mpc(
    value,
    *,
    bbox,
    start,
    end,
    band_aliases=("red", "nir"),
    max_cloud_cover=50,
    chunks_xy=None,
    stac_url="https://planetarycomputer.microsoft.com/api/stac/v1",
):
    """
    Landsat 8 (MPC) streaming verb for cubedynamics.

    Parameters
    ----------
    value : Any
        Required for pipeable verbs but unused here.
    bbox : list[float]
        [min_lon, min_lat, max_lon, max_lat]
    start : str
        ISO start date (YYYY-MM-DD)
    end : str
        ISO end date (YYYY-MM-DD)
    band_aliases : tuple[str]
        Bands to extract (e.g., ("red","nir"))
    max_cloud_cover : int
        Maximum cloud cover percentage
    chunks_xy : dict or None
        Dask spatial chunking, e.g. {"x": 1024, "y": 1024}
    stac_url : str
        STAC endpoint, defaults to the Microsoft Planetary Computer.

    Returns
    -------
    xarray.DataArray
        DataArray with dims (time, band, y, x).
    """
    return landsat8_mpc_stream(
        bbox=bbox,
        start=start,
        end=end,
        band_aliases=band_aliases,
        max_cloud_cover=max_cloud_cover,
        chunks_xy=chunks_xy,
        stac_url=stac_url,
    )


def _compute_ndvi_from_stack(
    stack: xr.DataArray, *, red_alias: str = "red", nir_alias: str = "nir"
) -> xr.DataArray:
    """Compute NDVI from a Landsat stack with a ``band`` dimension."""

    if "band" not in stack.dims:
        raise ValueError("Landsat stack must include a 'band' dimension to compute NDVI.")

    bands = stack.coords.get("band")
    if bands is not None and red_alias in bands.values and nir_alias in bands.values:
        red = stack.sel(band=red_alias)
        nir = stack.sel(band=nir_alias)
    else:
        # Fallback to positional selection if aliases are missing
        red = stack.isel(band=0)
        nir = stack.isel(band=1)

    ndvi = (nir - red) / (nir + red)
    ndvi = ndvi.rename("ndvi")
    ndvi.attrs.setdefault("long_name", "Normalized Difference Vegetation Index")
    ndvi.attrs.setdefault("units", "1")
    return ndvi


def _bounding_box_from_mask(mask: xr.DataArray) -> tuple[slice, slice]:
    """Return slices that crop to the non-NaN footprint of ``mask``.

    Raises
    ------
    ValueError
        If the mask contains no finite pixels.
    """

    mask_values = np.asarray(mask.values)
    finite = np.isfinite(mask_values)
    if not finite.any():
        raise ValueError("No finite pixels available to crop Landsat NDVI.")

    y_idx, x_idx = np.nonzero(finite)
    y_min, y_max = int(y_idx.min()), int(y_idx.max())
    x_min, x_max = int(x_idx.min()), int(x_idx.max())
    return slice(y_min, y_max + 1), slice(x_min, x_max + 1)


def _coarsen_if_needed(da: xr.DataArray, *, max_y: int, max_x: int) -> xr.DataArray:
    """Coarsen ``da`` along y/x so sizes do not exceed ``max_*``."""

    factors: dict[str, int] = {}
    if da.sizes.get("y", 0) > max_y:
        factors["y"] = int(math.ceil(da.sizes["y"] / max_y))
    if da.sizes.get("x", 0) > max_x:
        factors["x"] = int(math.ceil(da.sizes["x"] / max_x))

    if not factors:
        return da

    return da.coarsen(**factors, boundary="trim").mean()


def landsat_vis_ndvi(
    bbox,
    start,
    end,
    *,
    collection: str = "landsat-8-c2-l2",
    max_y: int = 256,
    max_x: int = 256,
    max_time: int = 16,
    auto_crop_valid: bool = True,
    band_aliases: Iterable[str] = ("red", "nir"),
    max_cloud_cover: float = 50,
    chunks_xy: Mapping[str, int] | None = None,
    stac_url: str = MPC_STAC_URL,
    stack_da: xr.DataArray | None = None,
) -> xr.DataArray:
    """Return a visualization-friendly Landsat NDVI cube.

    The helper keeps in-memory footprints small by cropping out empty borders and
    coarsening spatial/time axes when needed. It mirrors ``v.landsat8_mpc`` for
    sourcing data but materializes the reduced cube for plotting.
    """

    if collection != "landsat-8-c2-l2":
        raise ValueError("Only the 'landsat-8-c2-l2' collection is supported currently.")

    stack = stack_da
    if stack is None:
        stack = landsat8_mpc_stream(
            bbox=bbox,
            start=start,
            end=end,
            band_aliases=band_aliases,
            max_cloud_cover=max_cloud_cover,
            chunks_xy=chunks_xy,
            stac_url=stac_url,
        )

    ndvi = _compute_ndvi_from_stack(stack)

    if auto_crop_valid:
        finite_mask = xr.apply_ufunc(np.isfinite, ndvi)
        valid_mask = finite_mask.any(dim="time") if "time" in ndvi.dims else finite_mask
        y_slice, x_slice = _bounding_box_from_mask(valid_mask)
        ndvi = ndvi.isel(y=y_slice, x=x_slice)

    if ndvi.sizes.get("time", 0) > max_time:
        step = int(math.ceil(ndvi.sizes["time"] / max_time))
        ndvi = ndvi.isel(time=slice(0, None, step))

    ndvi = _coarsen_if_needed(ndvi, max_y=max_y, max_x=max_x)

    return ndvi.transpose("time", "y", "x").compute()


def landsat_ndvi_plot(
    bbox,
    start,
    end,
    *,
    max_y: int = 256,
    max_x: int = 256,
    max_time: int = 16,
    **plot_kwargs,
):
    """Load Landsat NDVI, downsample for visualization, and render the cube viewer."""

    ndvi_vis = landsat_vis_ndvi(
        bbox=bbox,
        start=start,
        end=end,
        max_y=max_y,
        max_x=max_x,
        max_time=max_time,
    )

    from cubedynamics import pipe, verbs as v

    return pipe(ndvi_vis) | v.plot(time_dim="time", **plot_kwargs)


__all__ = ["landsat8_mpc", "landsat8_mpc_stream", "BAND_MAP", "MPC_STAC_URL"]
