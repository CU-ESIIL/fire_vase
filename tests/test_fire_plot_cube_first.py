import numpy as np
import pandas as pd
import geopandas as gpd
import shapely.geometry as geom
import xarray as xr

from cubedynamics.fire_time_hull import (
    build_fire_event_daily,
    infer_epsg,
    infer_spatial_dims,
    sample_inside_outside,
)
from cubedynamics.verbs import fire as fire_verbs

from tests.helpers.contracts import assert_not_all_nan, assert_spatiotemporal_cube_contract


def _synthetic_event():
    dates = pd.date_range("2020-07-01", periods=3, freq="D")
    geoms = [geom.box(-105.1, 40.0, -105.0, 40.1), geom.box(-105.1, 40.0, -104.95, 40.15), geom.box(-105.1, 40.0, -104.9, 40.2)]
    gdf = gpd.GeoDataFrame({"id": [1, 1, 1], "date": dates, "geometry": geoms}, crs="EPSG:4326")
    return build_fire_event_daily(fired_daily=gdf, event_id=1)


def _grid_like_cube(name: str = "vpd"):
    # Ensure temporal overlap with the synthetic event dates (2020-07-01 to 2020-07-03)
    times = pd.date_range("2020-06-30", periods=8, freq="D")
    y = np.linspace(40.0, 40.25, 5)
    x = np.linspace(-105.2, -104.8, 5)
    data = np.random.default_rng(0).normal(size=(len(times), len(y), len(x)))
    da = xr.DataArray(data, coords={"time": times, "y": y, "x": x}, dims=("time", "y", "x"), name=name)
    return da


def _sentinel_like_cube():
    times = pd.date_range("2020-06-25", periods=6, freq="D")
    y = np.linspace(4_400_000, 4_401_000, 3)
    x = np.linspace(500_000, 501_000, 4)
    data = np.random.default_rng(1).normal(size=(len(times), len(y), len(x)))
    da = xr.DataArray(
        data,
        coords={"time": times, "y": y, "x": x, "epsg": 32613},
        dims=("time", "y", "x"),
        name="ndvi",
    )
    return da


def test_infer_epsg_fallbacks():
    da_grid = _grid_like_cube()
    assert infer_epsg(da_grid) == 4326

    da_latlon = _grid_like_cube().rename({"y": "lat", "x": "lon"})
    assert infer_epsg(da_latlon) == 4326

    da_proj = _sentinel_like_cube()
    assert infer_epsg(da_proj) == 32613


def test_spatial_dims_inference():
    da_grid = _grid_like_cube()
    assert infer_spatial_dims(da_grid) == ("y", "x")

    da_latlon = da_grid.rename({"y": "lat", "x": "lon"})
    assert infer_spatial_dims(da_latlon) == ("lat", "lon")


def test_sample_inside_outside_counts():
    event = _synthetic_event()
    da = _grid_like_cube()
    subset = da.sel(time=slice(event.t0, event.t1))
    summary = sample_inside_outside(event, subset)
    assert summary.values_inside.size > 1
    assert summary.values_outside.size > 1


def test_cube_first_fire_plot_does_not_fetch(monkeypatch):
    def _fail_loader(*args, **kwargs):  # pragma: no cover - will fail test if called
        raise AssertionError("Loader should not be called in cube-first mode")

    monkeypatch.setattr("cubedynamics.data.gridmet.load_gridmet_cube", _fail_loader)
    monkeypatch.setattr("cubedynamics.data.prism.load_prism_cube", _fail_loader)
    monkeypatch.setattr("cubedynamics.data.sentinel2.load_s2_ndvi_cube", _fail_loader)
    monkeypatch.setattr(fire_verbs, "plot_climate_filled_hull", lambda *args, **kwargs: "fig")
    event = _synthetic_event()
    da = _grid_like_cube()

    out = fire_verbs.fire_plot(
        da,
        fired_event=event,
        time_buffer_days=0,
        show_hist=False,
        verbose=True,
    )

    assert "summary" in out
    cube = out["cube"].da
    assert_spatiotemporal_cube_contract(cube, allow_empty_time=False)
    assert_not_all_nan(cube)
    xr.testing.assert_equal(cube, da.sel(time=slice(event.t0, event.t1)))


def test_fast_path_optional():
    event = _synthetic_event()
    da = _grid_like_cube()
    subset = da.sel(time=slice(event.t0, event.t1))
    try:
        summary = sample_inside_outside(event, subset, fast=True)
    except Exception:
        summary = sample_inside_outside(event, subset, fast=False)
    assert summary.values_inside.size > 1
