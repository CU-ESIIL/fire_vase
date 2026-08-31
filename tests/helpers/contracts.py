"""Reusable data-cube contracts used by fire-plot integration tests."""

from __future__ import annotations

import numpy as np
import xarray as xr


def _as_data_array(cube: xr.DataArray | xr.Dataset) -> xr.DataArray:
    if isinstance(cube, xr.DataArray):
        return cube
    if not isinstance(cube, xr.Dataset):
        raise AssertionError(f"Expected an xarray DataArray or Dataset, got {type(cube)!r}")
    if len(cube.data_vars) != 1:
        raise AssertionError(
            "Cube Dataset must contain exactly one data variable; "
            f"found {list(cube.data_vars)}"
        )
    return next(iter(cube.data_vars.values()))


def assert_spatiotemporal_cube_contract(
    cube: xr.DataArray | xr.Dataset,
    *,
    allow_empty_time: bool = False,
) -> None:
    """Assert the minimal structural contract for a sampled climate cube.

    A valid cube has one time dimension, exactly two recognized spatial
    dimensions, explicit one-dimensional coordinates for all three axes, and
    finite coordinate values. Spatial dimensions may use either projected
    ``(y, x)`` or geographic ``(lat, lon)`` names.
    """

    array = _as_data_array(cube)
    assert "time" in array.dims, f"Cube is missing a time dimension: {array.dims}"

    spatial_pair = next(
        (pair for pair in (("y", "x"), ("lat", "lon")) if set(pair).issubset(array.dims)),
        None,
    )
    assert spatial_pair is not None, (
        "Cube must contain spatial dimensions (y, x) or (lat, lon); "
        f"found {array.dims}"
    )
    expected_dims = {"time", *spatial_pair}
    assert set(array.dims) == expected_dims, (
        "Cube must have exactly one temporal and two spatial dimensions; "
        f"found {array.dims}"
    )

    for dim in ("time", *spatial_pair):
        assert dim in array.coords, f"Cube dimension {dim!r} has no coordinate"
        coord = array.coords[dim]
        assert coord.dims == (dim,), f"Coordinate {dim!r} must be one-dimensional"
        if dim != "time" or not allow_empty_time:
            assert array.sizes[dim] > 0, f"Cube dimension {dim!r} is empty"
        if coord.size:
            if np.issubdtype(coord.dtype, np.datetime64):
                assert not np.isnat(coord.values).any(), f"Coordinate {dim!r} contains NaT"
            elif np.issubdtype(coord.dtype, np.number):
                assert np.isfinite(coord.values).all(), f"Coordinate {dim!r} is nonfinite"


def assert_not_all_nan(cube: xr.DataArray | xr.Dataset) -> None:
    """Assert that a cube contains at least one non-missing value."""

    array = _as_data_array(cube)
    assert array.size > 0, "Cube contains no values"
    assert bool(array.notnull().any().item()), "Cube values are all missing"
