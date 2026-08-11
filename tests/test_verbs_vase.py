import numpy as np
import pytest
import xarray as xr
from shapely.geometry import Polygon

from cubedynamics import pipe, verbs as v
from cubedynamics.plotting.cube_plot import CubePlot
from cubedynamics.vase import VaseDefinition, VaseSection


def _square(x0: float, x1: float, y0: float, y1: float) -> Polygon:
    return Polygon([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])


def test_vase_extract_basic():
    times = np.arange(3)
    ys = np.arange(5)
    xs = np.arange(5)
    cube = xr.DataArray(
        np.ones((len(times), len(ys), len(xs))),
        coords={"time": times, "y": ys, "x": xs},
        dims=("time", "y", "x"),
    )

    polygon = _square(1, 4, 1, 4)
    vase = VaseDefinition(
        [
            VaseSection(time=0, polygon=polygon),
            VaseSection(time=2, polygon=polygon),
        ]
    )

    mask = v.vase_mask(cube, vase)
    extracted = v.vase_extract(cube, vase)

    assert mask.shape == cube.shape
    assert extracted.shape == cube.shape
    assert extracted.where(~mask).isnull().all()
    assert extracted.where(mask, drop=True).notnull().all()


def test_stat_vase_updates_cubeplot_data_and_mask():
    cube = xr.DataArray(
        np.ones((2, 4, 4)),
        coords={"time": [0, 1], "y": np.arange(4), "x": np.arange(4)},
        dims=("time", "y", "x"),
    )
    vase = VaseDefinition([VaseSection(time=0, polygon=_square(1, 3, 1, 3))])

    plot = CubePlot(cube).stat_vase(vase)

    assert plot.vase_mask is not None
    assert plot.data.where(~plot.vase_mask).isnull().all()


def test_stat_vase_preserves_dask_chunking():
    da = pytest.importorskip("dask.array")

    data = xr.DataArray(
        da.ones((2, 3, 3), chunks={"time": 1, "y": 3, "x": 3}),
        coords={"time": [0, 1], "y": np.arange(3), "x": np.arange(3)},
        dims=("time", "y", "x"),
    )
    vase = VaseDefinition([VaseSection(time=0, polygon=_square(0, 2, 0, 2))])

    plot = CubePlot(data).stat_vase(vase)

    assert plot.vase_mask is not None
    assert plot.data.chunks is not None
    assert isinstance(plot.data.data, da.Array)


def test_plot_pipe_still_works():
    cube = xr.DataArray(
        np.ones((1, 2, 2)),
        coords={"time": [0], "y": [0, 1], "x": [0, 1]},
        dims=("time", "y", "x"),
    )

    result = pipe(cube) | v.plot()

    viewer = result.unwrap()

    assert isinstance(viewer, CubePlot)
    assert viewer.data.identical(cube)


def test_vase_verb_basic_plot():
    cube = xr.DataArray(
        np.arange(8).reshape(2, 2, 2),
        coords={"time": [0, 1], "y": [0, 1], "x": [0, 1]},
        dims=("time", "y", "x"),
    )
    vase_def = VaseDefinition([VaseSection(time=0, polygon=_square(0, 1, 0, 1))])

    cube.attrs["vase"] = vase_def

    result = pipe(cube) | v.vase()
    viewer = result.unwrap()

    assert isinstance(viewer, CubePlot)
    assert viewer.vase_mask is not None


def test_vase_verb_argument_attaches_vase():
    cube = xr.DataArray(
        np.ones((1, 2, 2)),
        coords={"time": [0], "y": [0, 1], "x": [0, 1]},
        dims=("time", "y", "x"),
    )
    vase_def = VaseDefinition([VaseSection(time=0, polygon=_square(0, 1, 0, 1))])

    result = pipe(cube) | v.vase(vase=vase_def)
    viewer = result.unwrap()

    assert isinstance(viewer, CubePlot)
    assert viewer.vase_mask is not None


def test_vase_verb_requires_vase():
    cube = xr.DataArray(
        np.ones((1, 2, 2)),
        coords={"time": [0], "y": [0, 1], "x": [0, 1]},
        dims=("time", "y", "x"),
    )

    with pytest.raises(ValueError):
        pipe(cube) | v.vase()


def _tiny_cube():
    time = np.arange("2000-01", "2000-05", dtype="datetime64[M]")
    y = np.linspace(0, 3, 4)
    x = np.linspace(0, 3, 4)
    data = np.random.rand(len(time), len(y), len(x)).astype("float32")
    return xr.DataArray(
        data,
        dims=("time", "y", "x"),
        coords={"time": time, "y": y, "x": x},
        name="demo",
    )


def test_vase_demo_smoke():
    cube = _tiny_cube()

    viewer = pipe(cube) | v.vase_demo(n_sections=3, shrink=0.2)
    assert viewer is not None
