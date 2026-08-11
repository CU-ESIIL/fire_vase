from pathlib import Path

import pandas as pd
import pytest

from cubedynamics.fire_vase_lakehouse import (
    ProcessingRecord,
    climate_key,
    climate_qc,
    event_aligned_quantiles,
    event_key,
    geometry_key,
    invalidated_components,
    load_schema,
    medoid_by_traits,
    partition_path,
    retry_failed,
    select_cohort,
    stable_json,
    task_qc,
    transition,
    validate_records,
)
from scripts.check_repository_size import check_paths
from scripts.fire_vase_build_climate_tables import build_manifest_tables, normalize_daily
from scripts.fire_vase_build_perimeter_climate_tables import (
    ZONE_ACTIVE,
    ZONE_CUMULATIVE,
    ZONE_EXTENSION,
    cell_mask_for_geometry,
    exposure_geometries,
    variable_codes,
)


def test_cache_keys_are_deterministic_and_versioned():
    assert stable_json({"b": 2, "a": 1}) == stable_json({"a": 1, "b": 2})

    first = geometry_key("fire-1", source_geometry_hash="abc", geometry_version="g1")
    second = geometry_key("fire-1", source_geometry_hash="abc", geometry_version="g1")
    changed = geometry_key("fire-1", source_geometry_hash="abc", geometry_version="g2")

    assert first == second
    assert first != changed


def test_geometry_reuse_and_climate_key_variable_order():
    geom = geometry_key("fire-1", source_geometry_hash="abc", geometry_version="g1")
    first = climate_key(
        "fire-1",
        geometry_cache_key=geom,
        climate_source="gridmet",
        variables=["vpd", "tmmx"],
        temporal_resolution="hourly",
        climate_version="c1",
    )
    second = climate_key(
        "fire-1",
        geometry_cache_key=geom,
        climate_source="gridmet",
        variables=["tmmx", "vpd"],
        temporal_resolution="hourly",
        climate_version="c1",
    )

    assert first == second


def test_climate_only_and_event_only_invalidation():
    assert invalidated_components(["climate"]) == ("climate", "events", "traits", "vase", "render")
    assert invalidated_components(["events"]) == ("events", "traits", "vase", "render")
    with pytest.raises(ValueError):
        invalidated_components(["unknown"])


def test_partition_path_uses_cohort_dimensions_not_fire_id():
    path = partition_path(
        "fire_traits",
        year=2020,
        lon=-105.2,
        lat=40.1,
        processing_version="pv/1",
        base="lakehouse",
    )

    assert path == Path(
        "lakehouse/fire_traits/year=2020/region=intermountain/spatial_bucket=n040_w0106/processing_version=pv_1"
    )
    assert "fire_id" not in path.as_posix()
    with pytest.raises(ValueError):
        partition_path("fire_id=abc", year=2020, lon=-105.2, lat=40.1, processing_version="pv1")


def test_manifest_transitions_and_retry():
    record = ProcessingRecord("fire-1", "run-1")
    running = transition(record, "running")
    done = transition(running, "geometry_complete")
    failed = transition(done, "failed", failure_reason="missing climate")
    retry = retry_failed(failed)

    assert running.attempts == 1
    assert done.status == "geometry_complete"
    assert failed.failure_reason == "missing climate"
    assert retry.status == "pending"
    assert retry.failure_reason is None
    with pytest.raises(ValueError):
        transition(record, "published")


def test_schema_validation_for_fire_traits():
    schema = load_schema("fire_traits")
    valid = [
        {
            "fire_id": "fire-1",
            "trait_version": "t1",
            "processing_version": "p1",
            "total_area_km2": 10.0,
        }
    ]
    invalid = [{"fire_id": "fire-1", "trait_version": 2}]

    assert validate_records(valid, schema) == []
    errors = validate_records(invalid, schema)
    assert any("missing required column 'processing_version'" in error for error in errors)
    assert any("column 'trait_version' expected string" in error for error in errors)


def test_task_specific_qc_flags():
    geometry = task_qc(
        "geometry",
        {"area_km2": 0, "is_valid": False, "is_empty": True, "newly_added_geometry": True},
    )
    climate = climate_qc(observed_steps=94, expected_steps=100, variable="tmmx")

    assert geometry["passed"] is False
    assert set(geometry["flags"]) == {
        "empty_geometry",
        "invalid_geometry",
        "nonpositive_area",
        "newly_added_geometry",
    }
    assert climate["passed"] is False
    assert climate["flags"] == ["tmmx_missing_gt_5pct"]


def test_cohort_medoid_and_event_aligned_quantiles():
    traits = [
        {"fire_id": "a", "region": "west", "total_area_km2": 10, "duration_hours": 12},
        {"fire_id": "b", "region": "west", "total_area_km2": 11, "duration_hours": 13},
        {"fire_id": "c", "region": "east", "total_area_km2": 80, "duration_hours": 5},
    ]
    cohort = select_cohort(traits, region="west")
    medoid = medoid_by_traits(cohort, ["total_area_km2", "duration_hours"])
    quantiles = event_aligned_quantiles(
        [
            {"event_offset_hours": -1, "temperature_c": 10},
            {"event_offset_hours": -1, "temperature_c": 20},
            {"event_offset_hours": 0, "temperature_c": 30},
        ],
        value_column="temperature_c",
    )

    assert [record["fire_id"] for record in cohort] == ["a", "b"]
    assert medoid["fire_id"] == "a"
    assert quantiles[0]["event_offset_hours"] == -1
    assert quantiles[0]["q50"] == 15.0


def test_repository_size_checker_blocks_lakehouse_outputs(tmp_path):
    blocked = tmp_path / "scratch" / "fire_vase" / "table.parquet"
    blocked.parent.mkdir(parents=True)
    blocked.write_text("not really parquet", encoding="utf-8")
    allowed = tmp_path / "schemas" / "tiny.schema.json"
    allowed.parent.mkdir()
    allowed.write_text("{}", encoding="utf-8")

    policy = {
        "max_file_size_mb": 1,
        "blocked_extensions": [".parquet"],
        "blocked_paths": ["scratch/"],
        "allowed_paths": ["schemas/"],
    }

    errors = check_paths(
        [Path("scratch/fire_vase/table.parquet"), Path("schemas/tiny.schema.json")],
        policy,
        root=tmp_path,
    )
    assert any("blocked generated-data extension" in error for error in errors)
    assert any("blocked generated-data path" in error for error in errors)


def test_repository_size_checker_blocks_nested_zarr_store(tmp_path):
    nested = tmp_path / "lakehouse" / "climate.zarr" / "0.0.0"
    nested.parent.mkdir(parents=True)
    nested.write_text("chunk", encoding="utf-8")
    policy = {
        "max_file_size_mb": 1,
        "blocked_extensions": [".zarr"],
        "blocked_paths": ["lakehouse/"],
        "allowed_paths": [],
    }

    errors = check_paths([Path("lakehouse/climate.zarr/0.0.0")], policy, root=tmp_path)
    assert any("blocked generated-data extension" in error for error in errors)


def test_event_key_changes_without_recomputing_geometry_identity():
    geom = geometry_key("fire-1", source_geometry_hash="abc", geometry_version="g1")
    clim = climate_key(
        "fire-1",
        geometry_cache_key=geom,
        climate_source="gridmet",
        variables=["tmmx"],
        temporal_resolution="hourly",
        climate_version="c1",
    )
    first = event_key(
        "fire-1",
        climate_cache_key=clim,
        event_version="e1",
        method="threshold",
        parameters={"q": 0.9},
    )
    second = event_key(
        "fire-1",
        climate_cache_key=clim,
        event_version="e2",
        method="threshold",
        parameters={"q": 0.9},
    )

    assert first != second
    assert geom.startswith("geometry:")


def test_climate_table_manifest_splits_complete_and_retryable_failures():
    manifest = [
        {
            "fire_id": "1",
            "run_id": "run",
            "status": "geometry_complete",
            "component_versions": {},
            "attempts": 1,
            "failure_reason": None,
            "updated_at": "2026-01-01T00:00:00+00:00",
        },
        {
            "fire_id": "2",
            "run_id": "run",
            "status": "geometry_complete",
            "component_versions": {},
            "attempts": 1,
            "failure_reason": None,
            "updated_at": "2026-01-01T00:00:00+00:00",
        },
    ]
    complete, failures = build_manifest_tables(
        pd.DataFrame(manifest),
        complete_fire_ids={"1"},
        unsupported_fire_ids={"2"},
        incomplete_cached_fire_ids={"3"},
        run_id="climate-run",
    )

    assert complete["fire_id"].tolist() == ["1"]
    assert complete["status"].tolist() == ["climate_complete"]
    assert set(failures["fire_id"]) == {"2", "3"}
    assert failures["retryable"].all()


def test_perimeter_exposure_geometries_include_active_cumulative_and_extension():
    gpd = pytest.importorskip("geopandas")
    shapely = pytest.importorskip("shapely")

    daily = gpd.GeoDataFrame(
        {
            "id": [1, 1],
            "fire_id": ["1", "1"],
            "date": pd.to_datetime(["2020-01-01", "2020-01-02"]),
            "event_day": [1, 2],
            "event_dur": [2, 2],
            "dy_ar_km2": [1.0, 1.0],
            "tot_ar_km2": [2.0, 2.0],
        },
        geometry=[
            shapely.box(0, 0, 1000, 1000),
            shapely.box(1000, 0, 2000, 1000),
        ],
        crs="EPSG:5070",
    )

    rows = list(exposure_geometries(daily, extension_distances_m=[1000]))

    assert len(rows) == 6
    assert [row["exposure_zone"] for row in rows[:3]] == [
        ZONE_ACTIVE,
        ZONE_CUMULATIVE,
        ZONE_EXTENSION,
    ]
    assert rows[0]["exposure_area_km2"] == pytest.approx(1.0)
    assert rows[3]["exposure_area_km2"] == pytest.approx(1.0)
    assert rows[4]["exposure_area_km2"] == pytest.approx(2.0)
    assert rows[5]["exposure_area_km2"] > rows[4]["exposure_area_km2"]


def test_perimeter_cell_mask_uses_inside_cells_then_explicit_fallback():
    shapely = pytest.importorskip("shapely")
    lat = pd.Series([0.0, 1.0, 2.0]).to_numpy(float)
    lon = pd.Series([0.0, 1.0, 2.0]).to_numpy(float)

    lat_idx, lon_idx, mask, method = cell_mask_for_geometry(
        shapely.box(0.4, 0.4, 1.6, 1.6),
        lat=lat,
        lon=lon,
    )

    assert method == "grid_cells_inside_zone"
    assert mask.sum() == 1
    assert lat[lat_idx][mask.any(axis=1)].tolist() == [1.0]
    assert lon[lon_idx][mask.any(axis=0)].tolist() == [1.0]

    lat_idx, lon_idx, mask, method = cell_mask_for_geometry(
        shapely.box(0.01, 0.01, 0.02, 0.02),
        lat=lat,
        lon=lon,
    )

    assert method == "fallback_nearest_cell_to_zone"
    assert mask.sum() == 1
    assert lat_idx.tolist() == [0]
    assert lon_idx.tolist() == [0]


def test_perimeter_variable_codes_can_include_optional_gridmet_variables():
    config = {
        "climate": {
            "variables": {"maximum_temperature_c": "tmmx"},
            "optional_variables": {"precipitation_mm": "pr", "fuel_moisture_100hr_pct": "fm100"},
        }
    }

    assert variable_codes(config, include_optional=False, variables=None) == ["tmmx"]
    assert variable_codes(config, include_optional=True, variables=None) == ["tmmx", "pr", "fm100"]


def test_normalize_daily_marks_cached_year_support():
    events = pd.DataFrame(
        {
            "id": [1],
            "ig_date": [pd.Timestamp("2001-01-01")],
            "last_date": [pd.Timestamp("2004-01-01")],
            "centroid_lon": [-105.0],
            "centroid_lat": [40.0],
        }
    )
    daily = pd.DataFrame(
        {
            "id": [1, 1],
            "date": [pd.Timestamp("2001-01-01"), pd.Timestamp("2004-01-01")],
            "event_day": [1, 2],
            "event_dur": [2, 2],
            "dy_ar_km2": [1.0, 3.0],
            "tot_ar_km2": [4.0, 4.0],
        }
    )

    supported, unsupported = normalize_daily(events, daily, [2001])

    assert supported["year"].tolist() == [2001]
    assert unsupported["year"].tolist() == [2004]
    assert supported["normalized_vase_width"].iloc[0] == 0.5
