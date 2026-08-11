import geopandas as gpd
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from shapely.geometry import box
import xarray as xr

from cubedynamics import pipe, verbs as v
from cubedynamics.piping import Verb
from cubedynamics.verbs import fire as fire_verbs


def _fired_daily() -> gpd.GeoDataFrame:
    rows = []
    for event_id, x0 in [(1, -122.10), (2, -121.80)]:
        for day in range(3):
            rows.append(
                {
                    "id": event_id,
                    "date": pd.Timestamp("2020-07-01") + pd.Timedelta(days=day),
                    "geometry": box(x0, 39.0, x0 + 0.04 + day * 0.01, 39.05 + day * 0.01),
                }
            )
    return gpd.GeoDataFrame(rows, crs="EPSG:4326")


def _fired_events() -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(
        {
            "id": [1, 2],
            "fire_type": ["prescribed burn", "wildfire"],
            "geometry": [box(-122.10, 39.0, -122.02, 39.08), box(-121.80, 39.0, -121.72, 39.08)],
        },
        crs="EPSG:4326",
    )


def _cube() -> xr.DataArray:
    times = pd.date_range("2020-06-30", periods=6, freq="D")
    data = np.ones((len(times), 4, 4), dtype=float)
    return xr.DataArray(
        data,
        coords={"time": times, "y": np.linspace(38.9, 39.2, 4), "x": np.linspace(-122.2, -121.6, 4)},
        dims=("time", "y", "x"),
        name="tmmx",
        attrs={"epsg": 4326},
    )


def _fake_fire_plot(calls):
    def _inner(da=None, *, fired_event=None, fired_daily=None, event_id=None, climate_variable="vpd", **kwargs):
        del fired_daily, event_id, kwargs
        calls.append({"event_id": fired_event.event_id, "cube_name": da.name, "variable": climate_variable})
        fig = go.Figure(
            data=[
                go.Mesh3d(
                    x=[0, 1, 0],
                    y=[0, 0, 1],
                    z=[1, 1, 2],
                    i=[0],
                    j=[1],
                    k=[2],
                    intensity=[295.0, 295.0, 296.0],
                    colorscale="Viridis",
                )
            ]
        )
        return {
            "event": fired_event,
            "fig_hull": fig,
            "color_limits": (294.0, 297.0),
            "summary": object(),
            "hull": object(),
            "cube": object(),
        }

    return _inner


def test_fire_vase_panel_selects_prescribed_events_and_builds_panel(monkeypatch):
    calls = []
    monkeypatch.setattr(fire_verbs, "fire_plot", _fake_fire_plot(calls))

    out = fire_verbs.fire_vase_panel(
        _cube(),
        fired_daily=_fired_daily(),
        fired_events=_fired_events(),
        climate_variable="tmmx",
        columns=2,
    )

    assert out["event_ids"] == ["1"]
    assert out["prescribed_filter_available"] is True
    assert out["prescribed_evidence"] == {"fire_type": ["prescribed burn"]}
    assert out["failures"] == []
    assert calls == [{"event_id": 1, "cube_name": "tmmx", "variable": "tmmx"}]
    assert isinstance(out["fig_panel"], go.Figure)
    assert len(out["fig_panel"].data) == 1


def test_fire_vase_panel_is_pipe_friendly(monkeypatch):
    calls = []
    monkeypatch.setattr(fire_verbs, "fire_plot", _fake_fire_plot(calls))

    stage = v.fire_vase_panel(
        fired_daily=_fired_daily(),
        fired_events=_fired_events(),
        climate_variable="tmmx",
    )

    assert isinstance(stage, Verb)
    out = (pipe(_cube()) | stage).unwrap()
    assert out["event_ids"] == ["1"]
    assert calls[0]["event_id"] == 1


def test_public_fire_vase_panel_binds_to_canonical_fire_module():
    assert v.fire_vase_panel is fire_verbs.fire_vase_panel
