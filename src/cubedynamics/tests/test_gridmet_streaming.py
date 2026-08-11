"""Tests for the gridMET streaming helper."""

from __future__ import annotations

import numpy as np
import pandas as pd
import xarray as xr

import cubedynamics as cd
from cubedynamics.streaming import gridmet as gridmet_mod


def test_stream_gridmet_to_cube_default_source_smoke(monkeypatch):
    """Calling the helper without `source` should return a time-indexed cube."""

    times = pd.date_range("2000-01-01", periods=2, freq="MS")
    lat = xr.DataArray([40.0, 39.5], dims="lat")
    lon = xr.DataArray([-105.5, -105.0], dims="lon")

    def _fake_year(variable: str, year: int, chunks=None) -> xr.Dataset:  # pragma: no cover - test helper
        data = xr.DataArray(
            np.arange(times.size * lat.size * lon.size, dtype="float32").reshape(times.size, lat.size, lon.size),
            coords={"time": times, "lat": lat, "lon": lon},
            dims=("time", "lat", "lon"),
            name=variable,
        )
        return xr.Dataset({variable: data})

    monkeypatch.setattr(gridmet_mod, "_open_gridmet_year", _fake_year)

    boulder_aoi = {
        "type": "Feature",
        "properties": {"name": "Boulder, CO"},
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [-105.35, 40.00],
                [-105.35, 40.01],
                [-105.34, 40.01],
                [-105.34, 40.00],
                [-105.35, 40.00],
            ]],
        },
    }

    cube = cd.stream_gridmet_to_cube(
        aoi_geojson=boulder_aoi,
        variable="pr",
        start="2000-01-01",
        end="2000-12-31",
        freq="MS",
        chunks={"time": 12},
    )

    assert "time" in cube.dims
    assert cube.name == "pr"


def test_stream_gridmet_to_cube_descending_lat(monkeypatch):
    """Descending latitude axes should still produce non-empty subsets."""

    times = pd.date_range("2000-01-01", periods=3, freq="D")
    lat = xr.DataArray([50.0, 49.5, 49.0], dims="lat")
    lon = xr.DataArray([-120.0, -119.5, -119.0], dims="lon")

    def _fake_year(variable: str, year: int, chunks=None) -> xr.Dataset:  # pragma: no cover - test helper
        data = xr.DataArray(
            np.arange(times.size * lat.size * lon.size, dtype="float32").reshape(times.size, lat.size, lon.size),
            coords={"time": times, "lat": lat, "lon": lon},
            dims=("time", "lat", "lon"),
            name=variable,
        )
        return xr.Dataset({variable: data})

    monkeypatch.setattr(gridmet_mod, "_open_gridmet_year", _fake_year)

    aoi = {
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [-120.0, 49.1],
                [-120.0, 49.6],
                [-119.4, 49.6],
                [-119.4, 49.1],
                [-120.0, 49.1],
            ]],
        },
    }

    cube = cd.stream_gridmet_to_cube(
        aoi_geojson=aoi,
        variable="pr",
        start="2000-01-01",
        end="2000-01-03",
    )

    assert cube.sizes["lat"] == 1
    assert cube.sizes["lon"] == 2
    assert cube.lat.item() == 49.5


def test_stream_gridmet_to_cube_bbox_padding(monkeypatch):
    """Tiny AOI bounding boxes should still capture at least one grid cell."""

    times = pd.date_range("2000-01-01", periods=2, freq="D")
    lat = xr.DataArray([40.020833, 39.979167], dims="lat")
    lon = xr.DataArray([-105.375, -105.333333, -105.291666], dims="lon")

    def _fake_year(variable: str, year: int, chunks=None) -> xr.Dataset:  # pragma: no cover - test helper
        data = xr.DataArray(
            np.arange(times.size * lat.size * lon.size, dtype="float32").reshape(times.size, lat.size, lon.size),
            coords={"time": times, "lat": lat, "lon": lon},
            dims=("time", "lat", "lon"),
            name=variable,
        )
        return xr.Dataset({variable: data})

    monkeypatch.setattr(gridmet_mod, "_open_gridmet_year", _fake_year)

    aoi = {
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [-105.35, 40.00],
                [-105.35, 40.01],
                [-105.34, 40.01],
                [-105.34, 40.00],
                [-105.35, 40.00],
            ]],
        },
    }

    cube = cd.stream_gridmet_to_cube(
        aoi_geojson=aoi,
        variable="pr",
        start="2000-01-01",
        end="2000-01-02",
    )

    assert cube.sizes["lat"] == 1
    assert cube.sizes["lon"] == 1
    assert np.isclose(cube.lat.item(), float(lat.isel(lat=0)))
    assert np.isclose(cube.lon.item(), float(lon.isel(lon=1)))
