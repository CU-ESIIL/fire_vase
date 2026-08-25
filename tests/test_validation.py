import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
import xarray as xr
from shapely.geometry import box

from cubedynamics.validation.climate import coordinate_edges, pixel_overlap_attribution
from cubedynamics.validation.external import parse_opendap_ascii_block
from cubedynamics.validation.geometry import compactness_roughness, simplification_sensitivity
from cubedynamics.validation.pipeline import compare_pipe_and_direct


def test_pipe_validation_is_exact_and_lazy():
    import dask.array as da

    values = da.from_array(np.arange(4 * 3 * 2, dtype=float).reshape(4, 3, 2), chunks=(2, 3, 2))
    cube = xr.DataArray(
        values,
        dims=("time", "y", "x"),
        coords={"time": pd.date_range("2001-01-01", periods=4), "y": range(3), "x": range(2)},
        name="sample",
    )

    comparison = compare_pipe_and_direct(cube)

    assert comparison["max_abs_residual"] == 0.0
    assert comparison["same_object_on_noop_unwrap"] is True
    assert comparison["lazy_before"] is True
    assert comparison["lazy_after"] is True


def test_coordinate_edges_work_for_descending_grid():
    assert coordinate_edges(np.array([3.0, 2.0, 1.0])).tolist() == [3.5, 2.5, 1.5, 0.5]


def test_fractional_overlap_uses_all_intersected_pixels():
    field = xr.DataArray(
        np.array([[0.0, 10.0], [20.0, 30.0]]),
        coords={"lat": [0.0, 1.0], "lon": [0.0, 1.0]},
        dims=("lat", "lon"),
        name="tmmx",
    )
    polygon = box(0.25, -0.25, 0.75, 1.25)

    result = pixel_overlap_attribution(field, polygon)

    assert result["overlap_cell_count"] == 4
    assert result["area_weighted_mean"] == pytest.approx(15.0, abs=0.1)
    assert result["centroid_value"] in {0.0, 10.0, 20.0, 30.0}


def test_polygon_simplification_metrics_preserve_valid_geometry():
    jagged = box(0, 0, 1000, 1000).buffer(100, resolution=8)
    frame = gpd.GeoDataFrame(
        {"id": [1], "date": [pd.Timestamp("2020-01-01")]},
        geometry=[jagged],
        crs=5070,
    )

    records, geometries = simplification_sensitivity(frame, [0, 50])

    assert len(records) == 2
    assert all(geometry.is_valid for geometry in geometries.values())
    assert records[1]["vertices"] <= records[0]["vertices"]
    assert compactness_roughness(jagged) >= 1.0


def test_parse_gridmet_opendap_ascii_block():
    response = """
air_temperature.air_temperature[1][2][3]
[0][0], 10, 11, 12
[0][1], 13, 14, 15
"""

    values = parse_opendap_ascii_block(response, expected_count=6)

    assert values.tolist() == [10, 11, 12, 13, 14, 15]
