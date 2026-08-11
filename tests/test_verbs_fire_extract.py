import numpy as np
import pandas as pd
import geopandas as gpd
import xarray as xr
from shapely.geometry import Polygon

import cubedynamics as cd
from cubedynamics import verbs as v
from cubedynamics.ops_fire.time_hull import FireEventDaily


def _synthetic_climate_cube() -> xr.DataArray:
    time = pd.date_range("2000-01-01", periods=2, freq="D")
    y = np.linspace(-0.5, 1.5, 4)
    x = np.linspace(-0.5, 1.5, 4)
    vals = np.random.rand(len(time), len(y), len(x)).astype("float32")

    da = xr.DataArray(
        vals,
        dims=("time", "y", "x"),
        coords={"time": time, "y": y, "x": x},
        name="synthetic",
    )
    da.attrs["epsg"] = 4326
    return da


def _synthetic_fire_event() -> FireEventDaily:
    rows = []
    for d in range(2):
        poly = Polygon(
            [
                (0.0, 0.0),
                (1.0, 0.0),
                (1.0, 1.0),
                (0.0, 1.0),
            ]
        )
        rows.append(
            {
                "id": 1,
                "date": pd.Timestamp("2000-01-01") + pd.Timedelta(days=d),
                "geometry": poly,
            }
        )
    gdf = gpd.GeoDataFrame(rows, crs="EPSG:4326")
    return FireEventDaily(
        event_id=1,
        gdf=gdf,
        t0=pd.Timestamp("2000-01-01"),
        t1=pd.Timestamp("2000-01-02"),
        centroid_lat=0.5,
        centroid_lon=0.5,
    )


def test_extract_attaches_attrs_and_verbs_run():
    da = _synthetic_climate_cube()
    fired_evt = _synthetic_fire_event()

    out = v.extract(da, fired_event=fired_evt)

    if isinstance(out, xr.DataArray):
        base_da = out
    else:
        base_da = out.data if hasattr(out, "data") else out.to_xarray()

    assert "fire_time_hull" in base_da.attrs
    assert "fire_climate_summary" in base_da.attrs
    assert "vase" in base_da.attrs

    v.climate_hist(base_da)
    v.vase(base_da)
