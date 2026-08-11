import numpy as np
import pytest
import xarray as xr
from shapely.geometry import Polygon

from cubedynamics.vase import VaseDefinition, VaseSection
from cubedynamics.vase_viz import (
    extract_vase_points,
    vase_scatter_plot,
    vase_to_mesh,
)


def _make_cube():
    time = np.arange(3)
    y = np.arange(3)
    x = np.arange(3)
    data = np.arange(27).reshape(3, 3, 3)
    cube = xr.DataArray(
        data,
        coords={"time": time, "y": y, "x": x},
        dims=("time", "y", "x"),
        name="test_cube",
    )
    return cube


def test_extract_vase_points():
    cube = _make_cube()
    mask = xr.DataArray(
        [[
            [False, True, False],
            [False, False, False],
            [True, False, False],
        ],
        [
            [False, False, False],
            [False, True, False],
            [False, False, False],
        ],
        [
            [False, False, True],
            [False, False, False],
            [False, False, False],
        ]],
        coords=cube.coords,
        dims=cube.dims,
    )

    points = extract_vase_points(cube, mask)
    assert set(points.keys()) == {"time", "y", "x", "value"}

    expected_true = int(mask.sum())
    assert len(points["value"]) == expected_true
    assert points["time"].dtype == cube["time"].dtype
    assert points["y"].dtype == cube["y"].dtype
    assert points["x"].dtype == cube["x"].dtype

    for t, y, x, val in zip(points["time"], points["y"], points["x"], points["value"]):
        assert cube.loc[{"time": t, "y": y, "x": x}].item() == val


def test_vase_scatter_plot_smoke():
    pv = pytest.importorskip("pyvista")
    cube = _make_cube()
    mask = xr.DataArray(np.ones_like(cube, dtype=bool), coords=cube.coords, dims=cube.dims)

    pv.OFF_SCREEN = True
    vase_scatter_plot(cube, mask)


def test_vase_to_mesh():
    trimesh = pytest.importorskip("trimesh")

    square = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
    triangle = Polygon([(0, 0), (1, 0), (0.5, 1), (0, 0)])
    vase = VaseDefinition(
        sections=[
            VaseSection(time=0, polygon=square),
            VaseSection(time=1, polygon=triangle),
        ],
        interp="linear",
    )

    mesh = vase_to_mesh(vase)
    assert len(mesh.vertices) > 0
    assert len(mesh.faces) > 0
