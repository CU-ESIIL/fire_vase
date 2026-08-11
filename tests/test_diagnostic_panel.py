from __future__ import annotations

from types import SimpleNamespace

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xarray as xr

from cubedynamics import pipe, verbs as v
from cubedynamics.plotting import CubePlot


def _cube(name: str = "bottom_minus_top") -> xr.DataArray:
    time = pd.date_range("2024-01-01", periods=5, freq="D")
    y = np.arange(3)
    x = np.arange(4)
    data = np.arange(time.size * y.size * x.size, dtype=float).reshape(time.size, y.size, x.size)
    return xr.DataArray(data, coords={"time": time, "y": y, "x": x}, dims=("time", "y", "x"), name=name)


def test_diagnostic_panel_saves_cube_png(tmp_path):
    path = tmp_path / "cube_panel.png"

    fig = (pipe(_cube()) | v.diagnostic_panel(output_path=path)).unwrap()

    assert path.read_bytes().startswith(b"\x89PNG")
    assert len(fig.axes) >= 6
    plt.close(fig)


def test_diagnostic_panel_accepts_cubeplot(tmp_path):
    path = tmp_path / "cubeplot_panel.png"
    viewer = CubePlot(_cube()).geom_cube()

    fig = v.diagnostic_panel(viewer, output_path=path)

    assert path.exists()
    assert fig._suptitle.get_text() == "bottom_minus_top diagnostic panel"
    plt.close(fig)


def test_diagnostic_panel_selects_synchrony_difference_from_dataset(tmp_path):
    base = _cube("bottom_synchrony")
    ds = xr.Dataset(
        {
            "bottom_synchrony": base,
            "top_synchrony": base * 0.5,
            "bottom_minus_top": base * 0.25,
        }
    )

    fig = v.diagnostic_panel(ds, output_path=tmp_path / "sync_panel.png")

    assert fig._suptitle.get_text() == "bottom_minus_top diagnostic panel"
    plt.close(fig)


def test_diagnostic_panel_saves_fire_result_png(tmp_path):
    verts = np.array(
        [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 1.0],
            [1.0, 1.0, 1.0],
        ],
        dtype=float,
    )
    tris = np.array([[0, 1, 2], [1, 2, 3]], dtype=int)
    times = pd.date_range("2024-01-01", periods=4, freq="D")
    cube = xr.Dataset(
        {
            "tmmx": xr.DataArray(
                np.ones((4, 2, 2)) * 300.0,
                coords={"time": times, "y": [0, 1], "x": [0, 1]},
                dims=("time", "y", "x"),
            ),
            "tmmn": xr.DataArray(
                np.ones((4, 2, 2)) * 285.0,
                coords={"time": times, "y": [0, 1], "x": [0, 1]},
                dims=("time", "y", "x"),
            ),
            "vpd": xr.DataArray(
                np.linspace(1.0, 2.0, 16).reshape(4, 2, 2),
                coords={"time": times, "y": [0, 1], "x": [0, 1]},
                dims=("time", "y", "x"),
            ),
        }
    )
    result = {
        "event": SimpleNamespace(event_id=44),
        "hull": SimpleNamespace(
            verts_km=verts,
            tris=tris,
            metrics={
                "duration_days": 4.0,
                "scale_km": 1.0,
                "footprint_area_peak_km2": 0.5,
                "hull_volume_km2_days": 2.0,
            },
        ),
        "summary": SimpleNamespace(
            values_inside=np.array([1.0, 2.0, 3.0]),
            values_outside=np.array([0.5, 1.5]),
            per_day_mean=pd.Series([300.0, 301.0], index=times[:2]),
        ),
        "cube": cube,
    }

    fig = v.diagnostic_panel(result, output_path=tmp_path / "fire_panel.png")

    assert (tmp_path / "fire_panel.png").read_bytes().startswith(b"\x89PNG")
    assert "event 44" in fig._suptitle.get_text()
    plt.close(fig)
