"""Offline guardrails for the real FIRED + gridMET fire-vase example."""

from __future__ import annotations

from types import SimpleNamespace

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import box
import xarray as xr

from examples import real_fire_vase_gridmet_smoke as smoke


def _fake_fired_daily() -> gpd.GeoDataFrame:
    dates = pd.date_range("2020-07-01", periods=5, freq="D")
    geoms = [
        box(-122.10, 39.00, -122.04, 39.06),
        box(-122.10, 39.00, -122.02, 39.08),
        box(-122.10, 39.00, -122.00, 39.10),
        box(-122.08, 39.02, -122.00, 39.10),
        box(-122.07, 39.03, -122.01, 39.09),
    ]
    return gpd.GeoDataFrame(
        {"id": [7] * len(dates), "date": dates, "geometry": geoms},
        crs="EPSG:4326",
    )


def _fake_fired_events() -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(
        {
            "id": [7],
            "fire_type": ["prescribed burn"],
            "geometry": [box(-122.10, 39.00, -122.00, 39.10)],
        },
        crs="EPSG:4326",
    )


def test_real_fire_vase_gridmet_smoke_uses_streaming_and_writes_artifacts(tmp_path, monkeypatch):
    calls: dict[str, object] = {}

    def fake_load_fired_conus_ak(*, which, **kwargs):
        calls.setdefault("downloads", []).append((which, kwargs.get("download")))
        return _fake_fired_daily() if which == "daily" else _fake_fired_events()

    def fake_stream_gridmet_to_cube(*, aoi_geojson, variable, start, end, chunks, show_progress):
        calls["stream"] = {
            "aoi_geojson": aoi_geojson,
            "variable": variable,
            "start": start,
            "end": end,
            "chunks": chunks,
            "show_progress": show_progress,
        }
        times = pd.date_range(start, end, freq="D")
        data = np.full((len(times), 2, 2), 295.0)
        return xr.DataArray(
            data,
            coords={"time": times, "lat": [39.0, 39.1], "lon": [-122.1, -122.0]},
            dims=("time", "lat", "lon"),
            name=variable,
        )

    def fake_fire_plot(cube, *, fired_event, climate_variable, **kwargs):
        calls["fire_plot"] = {
            "cube_name": cube.name,
            "event_id": fired_event.event_id,
            "climate_variable": climate_variable,
            "allow_synthetic": kwargs["allow_synthetic"],
        }

        class FakeFigure:
            data = []

            def write_html(self, path, include_plotlyjs):
                del include_plotlyjs
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write("<html><title>GRIDMET tmmx: Max temperature (K)</title></html>")

        return {
            "event": fired_event,
            "hull": SimpleNamespace(
                metrics={
                    "days": 5.0,
                    "duration_days": 5.0,
                    "hull_volume_km2_days": 1.25,
                }
            ),
            "fig_hull": FakeFigure(),
            "summary": SimpleNamespace(values_inside=np.ones(3), values_outside=np.ones(4)),
            "color_limits": (294.0, 296.0),
        }

    def fake_static_png(results, output_path):
        assert results["event"].event_id == 7
        output_path.write_bytes(b"\x89PNG\r\n\x1a\n")

    monkeypatch.setattr(smoke, "load_fired_conus_ak", fake_load_fired_conus_ak)
    monkeypatch.setattr(smoke, "stream_gridmet_to_cube", fake_stream_gridmet_to_cube)
    monkeypatch.setattr(smoke, "fire_verbs", SimpleNamespace(fire_plot=fake_fire_plot))
    monkeypatch.setattr(smoke, "_save_static_hull_png", fake_static_png)

    manifest = smoke.run(tmp_path, min_days=3, max_days=14, variable="tmmx")

    assert calls["downloads"] == [("daily", True), ("events", True)]
    assert calls["stream"]["variable"] == "tmmx"
    assert calls["stream"]["start"] == "2020-06-30"
    assert calls["stream"]["end"] == "2020-07-06"
    assert calls["stream"]["chunks"] == {"time": 16}
    assert calls["fire_plot"] == {
        "cube_name": "tmmx",
        "event_id": 7,
        "climate_variable": "tmmx",
        "allow_synthetic": False,
    }
    assert manifest["event_id"] == "7"
    assert manifest["prescribed_filter_available"] is True
    assert manifest["selected_from_prescribed_ids"] is True
    assert manifest["gridmet_shape"] == {"time": 7, "lat": 2, "lon": 2}
    assert (tmp_path / "real_fire_vase_gridmet_interactive.html").read_text(encoding="utf-8").endswith("</html>")
    assert (tmp_path / "real_fire_vase_gridmet_static.png").read_bytes().startswith(b"\x89PNG")
    assert (tmp_path / "real_fire_vase_gridmet_diagnostic.png").read_bytes().startswith(b"\x89PNG")
    assert (tmp_path / "manifest.json").exists()
    assert (tmp_path / "candidate_events.csv").exists()


def test_static_png_face_values_follow_daily_bands_not_triangle_averages():
    event = SimpleNamespace(t0=pd.Timestamp("2020-07-01"))
    hull = SimpleNamespace(
        verts_km=np.array(
            [
                [0.0, 0.0, 1.0],
                [1.0, 0.0, 1.0],
                [1.0, 0.0, 2.0],
                [0.0, 0.0, 2.0],
            ],
            dtype=float,
        ),
        tris=np.array([[0, 1, 2], [0, 2, 3]], dtype=int),
        t_days_vert=np.array([1.0, 1.0, 2.0, 2.0], dtype=float),
    )
    results = {
        "event": event,
        "hull": hull,
        "fig_hull": SimpleNamespace(data=[SimpleNamespace(intensity=np.array([10.0, 10.0, 20.0, 20.0]))]),
        "summary": SimpleNamespace(
            per_day_mean=pd.Series(
                [100.0, 200.0],
                index=pd.date_range("2020-07-01", periods=2, freq="D"),
            )
        ),
    }

    _, _, tri_values = smoke._static_face_values_by_day(results)

    np.testing.assert_allclose(tri_values, [100.0, 100.0])
