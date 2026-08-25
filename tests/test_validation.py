import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
import xarray as xr
from shapely.geometry import box

from cubedynamics.validation.climate import coordinate_edges, pixel_overlap_attribution
from cubedynamics.validation.contrast import corrupted_cube_variants
from cubedynamics.validation.cube import audit_cube_html, extract_cube_html_planes
from cubedynamics.validation.external import parse_opendap_ascii_block
from cubedynamics.validation.geometry import compactness_roughness, simplification_sensitivity
from cubedynamics.validation.hull3d import temporal_averaging_alternatives
from cubedynamics.validation.pipeline import compare_pipe_and_direct
from cubedynamics.plotting.cube_viewer import cube_from_dataarray


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


def test_temporal_hull_averaging_exposes_declared_decisions():
    radii = np.arange(5 * 8, dtype=float).reshape(5, 8) + 1.0

    alternatives = temporal_averaging_alternatives(radii, windows=(1, 3, 5))

    assert list(alternatives) == [
        "daily support (production)",
        "3-day centered mean",
        "5-day centered mean",
        "cumulative envelope",
    ]
    np.testing.assert_array_equal(alternatives["daily support (production)"], radii)
    assert np.all(np.diff(alternatives["cumulative envelope"], axis=0) >= 0)


def test_cube_html_serializes_every_plane_without_permutation(tmp_path):
    values = np.arange(4 * 3 * 5, dtype=float).reshape(4, 3, 5)
    cube = xr.DataArray(
        values,
        dims=("time", "lat", "lon"),
        coords={
            "time": pd.date_range("2001-01-01", periods=4),
            "lat": [50.0, 49.0, 48.0],
            "lon": [-122.0, -121.5, -121.0, -120.5, -120.0],
        },
        name="index_sentinel",
    )
    html = cube_from_dataarray(
        cube,
        out_html=(tmp_path / "cube.html").as_posix(),
        thin_time_factor=1,
        fill_limits=(0.0, float(values.max())),
        fill_mode="volume",
        volume_density={"time": 2, "x": 3, "y": 1},
        volume_downsample={"time": 1, "space": 1},
        show_progress=False,
        return_html=True,
    )

    faces, interiors = extract_cube_html_planes(html)
    audit = audit_cube_html(cube, html, cmap="viridis", limits=(0.0, float(values.max())))

    assert set(faces) == {"front", "back", "left", "right", "top", "bottom"}
    assert set(interiors) == {
        ("time", 1),
        ("time", 2),
        ("x", 1),
        ("x", 2),
        ("x", 3),
        ("y", 1),
    }
    assert audit["all_planes_present"] is True
    assert audit["all_pixels_exact"] is True
    assert audit["all_time_slices_serialized_once"] is True


def test_cube_negative_controls_are_detectable(tmp_path):
    values = np.arange(8 * 4 * 5, dtype=float).reshape(8, 4, 5)
    cube = xr.DataArray(
        values,
        dims=("time", "lat", "lon"),
        coords={
            "time": pd.date_range("2001-01-01", periods=8),
            "lat": [50.0, 49.0, 48.0, 47.0],
            "lon": [-122.0, -121.5, -121.0, -120.5, -120.0],
        },
        name="index_sentinel",
    )
    html = cube_from_dataarray(
        cube,
        out_html=(tmp_path / "cube.html").as_posix(),
        thin_time_factor=1,
        fill_limits=(0.0, float(values.max())),
        fill_mode="volume",
        volume_density={"time": 6, "x": 3, "y": 2},
        volume_downsample={"time": 1, "space": 1},
        show_progress=False,
        return_html=True,
    )

    variants = corrupted_cube_variants(cube)
    audits = {
        name: audit_cube_html(variant, html, cmap="viridis", limits=(0.0, float(values.max())))
        for name, variant in variants.items()
    }

    assert audits["latitude_values_reversed"]["all_pixels_exact"] is False
    assert audits["time_values_scrambled"]["all_pixels_exact"] is False
    assert audits["middle_day_dropped"]["all_planes_present"] is False
    assert any(
        record["shape_matches"] is False
        for record in audits["middle_day_dropped"]["records"]
    )
