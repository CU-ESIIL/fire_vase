import numpy as np
import xarray as xr

import cubedynamics as cd
from cubedynamics import pipe, verbs as v


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


def test_stacked_polygon_vase_smoke():
    cube = _tiny_cube()
    vase_def = cd.demo.stacked_polygon_vase(cube, n_sections=3, shrink=0.2)

    assert len(vase_def.sections) == 3
    assert vase_def.sections[0].polygon.is_valid

    viewer = pipe(cube) | v.vase(vase=vase_def)
    assert viewer is not None
