import numpy as np
import pytest
import xarray as xr
from shapely.geometry import Point, Polygon

from cubedynamics import verbs as v

from cubedynamics.piping import pipe
from cubedynamics.plotting import CubePlot
from cubedynamics.vase import VaseDefinition, VaseSection, _polygon_at_time, build_vase_mask


def square(x0: float, x1: float, y0: float, y1: float) -> Polygon:
    return Polygon([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])


def test_vase_definition_sorting():
    sections = [
        VaseSection(time=2, polygon=square(0, 1, 0, 1)),
        VaseSection(time=0, polygon=square(0, 1, 0, 1)),
        VaseSection(time=1, polygon=square(0, 1, 0, 1)),
    ]
    vase = VaseDefinition(sections, interp="nearest")

    assert [s.time for s in vase.sections] == [0, 1, 2]
    sorted_vase = vase.sorted_sections()
    assert [s.time for s in sorted_vase.sections] == [0, 1, 2]


def test_polygon_at_time_nearest():
    sections = [
        VaseSection(time=0, polygon=square(0, 1, 0, 1)),
        VaseSection(time=2, polygon=square(1, 2, 1, 2)),
    ]
    vase = VaseDefinition(sections, interp="nearest")

    poly_before = _polygon_at_time(vase, -1)
    poly_between = _polygon_at_time(vase, 0.4)
    poly_after = _polygon_at_time(vase, 3)

    assert poly_before.equals(sections[0].polygon)
    assert poly_between.equals(sections[0].polygon)
    assert poly_after.equals(sections[1].polygon)


def test_polygon_at_time_linear():
    tri_a = Polygon([(0, 0), (2, 0), (0, 2)])
    tri_b = Polygon([(2, 2), (4, 2), (2, 4)])
    vase = VaseDefinition(
        [VaseSection(time=0, polygon=tri_a), VaseSection(time=2, polygon=tri_b)],
        interp="linear",
    )

    interpolated = _polygon_at_time(vase, 1)
    expected_coords = np.asarray(tri_a.exterior.coords) + 0.5 * (
        np.asarray(tri_b.exterior.coords) - np.asarray(tri_a.exterior.coords)
    )

    np.testing.assert_allclose(np.asarray(interpolated.exterior.coords), expected_coords)


def test_build_vase_mask_shape_and_values():
    times = np.arange(3)
    ys = np.arange(5)
    xs = np.arange(5)
    cube = xr.DataArray(
        np.zeros((len(times), len(ys), len(xs))),
        coords={"time": times, "y": ys, "x": xs},
        dims=("time", "y", "x"),
    )

    poly = square(1, 3, 1, 3)
    vase = VaseDefinition(
        [VaseSection(time=0, polygon=poly), VaseSection(time=2, polygon=poly)],
        interp="nearest",
    )

    mask = build_vase_mask(cube, vase)

    assert mask.dims == cube.dims
    assert mask.dtype == bool

    expected = np.zeros((len(times), len(ys), len(xs)), dtype=bool)
    expected[:, 1:4, 1:4] = True
    np.testing.assert_array_equal(mask.values, expected)


def test_build_vase_mask_with_dask_streaming():
    da = pytest.importorskip("dask.array")

    times = np.arange(2)
    ys = np.arange(4)
    xs = np.arange(4)
    data = da.zeros((len(times), len(ys), len(xs)), chunks={"time": 1, "y": 4, "x": 4})
    cube = xr.DataArray(data, coords={"time": times, "y": ys, "x": xs}, dims=("time", "y", "x"))

    vase = VaseDefinition([VaseSection(time=0, polygon=square(0, 3, 0, 3))])
    mask = build_vase_mask(cube, vase)

    assert mask.shape == (len(times), len(ys), len(xs))
    assert mask.dtype == bool
    assert mask.all()


def test_vase_pipeline_and_viewer():
    cube = xr.DataArray(
        np.arange(300).reshape(3, 10, 10),
        dims=("time", "y", "x"),
        coords={"time": np.arange(3), "y": np.arange(10), "x": np.arange(10)},
    )
    circle_small = Point(5, 5).buffer(3.0)
    circle_big = Point(5, 5).buffer(5.0)
    vase = VaseDefinition(
        [VaseSection(time=0, polygon=circle_small), VaseSection(time=2, polygon=circle_big)],
        interp="nearest",
    )

    vase_cube = v.vase_extract(cube, vase)
    assert "vase" in vase_cube.attrs
    assert vase_cube.count() > 0
    assert (vase_cube.isnull().sum() > 0).item()

    result = (pipe(vase_cube) | v.plot()).unwrap()
    assert isinstance(result, CubePlot)
