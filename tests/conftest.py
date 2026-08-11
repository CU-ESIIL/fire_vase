"""Common pytest fixtures for cubedynamics tests."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import xarray as xr

# Ensure ``src`` is importable even when cubedynamics is not installed in site-packages.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
SRC_STR = str(SRC_PATH)
if SRC_STR in sys.path:
    sys.path.remove(SRC_STR)
sys.path.insert(0, SRC_STR)

try:
    import dask.array as da
except ImportError:  # pragma: no cover
    da = None


@pytest.fixture
def tiny_cube() -> xr.DataArray:
    """Small synthetic cube for testing with dims (time=6, y=2, x=3)."""

    time = pd.date_range("2000-01-01", periods=6, freq="D")
    y = np.arange(2)
    x = np.arange(3)
    rng = np.random.RandomState(0)
    data = rng.randn(len(time), len(y), len(x))
    cube = xr.DataArray(
        data,
        coords={"time": time, "y": y, "x": x},
        dims=("time", "y", "x"),
        name="tiny",
    )
    return cube


@pytest.fixture
def monotone_series() -> xr.DataArray:
    """Monotone increasing 1D series useful for rank-based tests."""

    time = pd.date_range("2001-01-01", periods=5, freq="D")
    data = xr.DataArray(np.linspace(1.0, 5.0, num=time.size), coords={"time": time}, dims="time")
    return data


def assert_is_lazy_xarray(obj):
    """Assert that a Dataset/DataArray is backed by dask arrays."""

    if da is None:
        pytest.skip("dask is not available; cannot assert laziness")

    if isinstance(obj, xr.DataArray):
        assert isinstance(obj.data, da.Array), "Expected dask-backed DataArray"
    elif isinstance(obj, xr.Dataset):
        for name, var in obj.data_vars.items():
            assert isinstance(var.data, da.Array), f"Variable {name!r} is not dask-backed"
    else:  # pragma: no cover - defensive
        raise AssertionError(f"Unsupported type for laziness check: {type(obj)!r}")
