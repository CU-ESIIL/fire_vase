from __future__ import annotations

import numpy as np
import xarray as xr

import cubedynamics as cd
from cubedynamics import progress


def test_progress_bar_updates_when_tqdm_available(monkeypatch):
    class DummyTqdm:
        def __init__(self):
            self.updates: list[int] = []
            self.kwargs: dict[str, object] = {}

        def __call__(self, **kwargs):
            self.kwargs = kwargs
            return self

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def update(self, n: int = 1):
            self.updates.append(n)

    dummy = DummyTqdm()
    monkeypatch.setattr(progress, "tqdm", dummy)

    with progress.progress_bar(total=3, description="demo") as advance:
        for _ in range(3):
            advance(1)

    assert dummy.kwargs["total"] == 3
    assert dummy.kwargs["desc"] == "demo"
    assert dummy.updates == [1, 1, 1]


def test_ndvi_accepts_show_progress(monkeypatch):
    def _fake_loader(**_kwargs):
        return xr.DataArray(
            np.zeros((2, 1, 1)),
            dims=("time", "y", "x"),
            coords={"time": ["2000-01-01", "2000-02-01"], "y": [0], "x": [0]},
        )

    monkeypatch.setattr(cd.variables, "load_sentinel2_ndvi_cube", _fake_loader)

    result = cd.ndvi(
        lat=40.0,
        lon=-105.25,
        start="2000-01-01",
        end="2000-02-01",
        show_progress=False,
    )

    assert isinstance(result, xr.DataArray)
    assert result.sizes == {"time": 2, "y": 1, "x": 1}
