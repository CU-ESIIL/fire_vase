import numpy as np
import pandas as pd
import geopandas as gpd
import xarray as xr
from shapely.geometry import Polygon

from cubedynamics.ops_fire.time_hull import FireEventDaily
from cubedynamics.ops_fire.climate_hull_extract import build_inside_outside_climate_samples


def _synthetic_fire_event_simple() -> FireEventDaily:
    poly = Polygon(
        [
            (0.0, 0.0),
            (1.0, 0.0),
            (1.0, 1.0),
            (0.0, 1.0),
        ]
    )
    gdf = gpd.GeoDataFrame(
        [{"id": 1, "date": pd.Timestamp("2000-01-01"), "geometry": poly}],
        crs="EPSG:4326",
    )
    return FireEventDaily(
        event_id=1,
        gdf=gdf,
        t0=pd.Timestamp("2000-01-01"),
        t1=pd.Timestamp("2000-01-01"),
        centroid_lat=0.5,
        centroid_lon=0.5,
    )


def _synthetic_climate_cube() -> xr.DataArray:
    time = pd.date_range("2000-01-01", periods=1, freq="D")
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


def test_build_inside_outside_climate_samples():
    event = _synthetic_fire_event_simple()
    da = _synthetic_climate_cube()

    summary = build_inside_outside_climate_samples(event, da)

    assert summary.values_inside.size > 0
    assert summary.values_outside.size > 0
    assert len(summary.per_day_mean.index) >= 1
