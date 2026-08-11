import numpy as np
import xarray as xr

from cubedynamics import pipe, verbs as v
from cubedynamics.plotting import cube_viewer
from cubedynamics.plotting.cube_plot import CubePlot
from cubedynamics.plotting.geom import GeomVaseOutline


def _demo_cube(time: int = 10, y: int = 8, x: int = 8) -> xr.DataArray:
    data = np.arange(time * y * x, dtype=float).reshape(time, y, x)
    return xr.DataArray(data, dims=("time", "y", "x"), name="demo")


def test_plain_cube_plot_smoke():
    cube = _demo_cube()

    viewer = (pipe(cube) | v.plot()).unwrap()

    assert isinstance(viewer, CubePlot)
    assert viewer.vase_mask is None
    assert viewer.vase_outline is None


def test_plot_ignores_missing_vase_attrs():
    cube = _demo_cube()
    cube.attrs.pop("vase", None)

    viewer = (pipe(cube) | v.plot()).unwrap()

    assert isinstance(viewer, CubePlot)
    assert viewer.vase_mask is None


def test_broken_vase_attr_is_non_fatal():
    cube = _demo_cube()
    cube.attrs["vase"] = {"invalid": True}

    viewer = (pipe(cube) | v.plot()).unwrap()

    assert isinstance(viewer, CubePlot)
    assert viewer.vase_mask is None
    assert viewer.vase_outline is None


def test_cube_viewer_skips_incompatible_vase_mask(tmp_path):
    data = _demo_cube(time=2, y=4, x=4)
    bad_mask = xr.DataArray(
        np.ones((1, 4, 4), dtype=bool),
        dims=("time", "y", "x"),
    )

    html = cube_viewer.cube_from_dataarray(
        data,
        out_html=str(tmp_path / "bad_vase.html"),
        return_html=True,
        show_progress=False,
        vase_mask=bad_mask,
        vase_outline=GeomVaseOutline(),
    )

    assert "data:image/png" in html
