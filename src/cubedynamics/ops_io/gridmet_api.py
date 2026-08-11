from __future__ import annotations

import xarray as xr

from .gridmet_loader import load_gridmet_cube


def gridmet(
    *,
    lat: float,
    lon: float,
    start: str,
    end: str,
    variable: str = "tmmx",
    buffer_deg: float = 0.5,
    chunks=None,
    verbose: bool = False,
) -> xr.DataArray:
    """
    Load a GRIDMET variable as an xarray.DataArray suitable for CubePlot.

    Parameters
    ----------
    lat, lon : float
        Center point of area of interest.
    start, end : str
        ISO8601 date strings.
    variable : str
        GRIDMET variable name, e.g. "tmmx", "vpd".
    buffer_deg : float
        Degrees of padding around the point AOI.
    chunks : dict or None
        Passed through to xarray.open_mfdataset.
    verbose : bool, default False
        If True, print loader diagnostics and show synthetic progress bars.

    Returns
    -------
    xr.DataArray
        Climate cube with dims (time, y, x) and
        attrs["epsg"] = 4326.
    """

    aoi = {
        "min_lat": lat - buffer_deg,
        "max_lat": lat + buffer_deg,
        "min_lon": lon - buffer_deg,
        "max_lon": lon + buffer_deg,
    }

    ds = load_gridmet_cube(
        variables=[variable],
        start=start,
        end=end,
        aoi=aoi,
        chunks=chunks,
        show_progress=verbose,
    )

    da = ds[variable]

    if "time" not in da.dims:
        raise ValueError("GRIDMET data must include a 'time' dimension")

    spatial_dims = set(da.dims) & {"y", "x"}
    latlon_dims = set(da.dims) & {"lat", "lon"}
    if not (spatial_dims == {"y", "x"} or latlon_dims == {"lat", "lon"}):
        raise ValueError("GRIDMET data must include 'y'/'x' or 'lat'/'lon' dimensions")

    da.attrs["epsg"] = 4326
    da.attrs["gridmet_source"] = ds.attrs.get("note", "real")
    return da
