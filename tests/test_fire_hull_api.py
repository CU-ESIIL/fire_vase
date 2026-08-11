import numpy as np
import pandas as pd
import xarray as xr

from cubedynamics.fire_time_hull import (
    FireEventDaily,
    FireHull,
    HullEnvironmentField,
    HullClimateSummary,
    TimeHull,
    build_fire_event,
)
from cubedynamics import verbs as v
from cubedynamics.verbs import fire as fire_verbs


def _template_cube() -> xr.DataArray:
    times = pd.date_range("2020-07-01", periods=3, freq="D")
    y = np.linspace(39.95, 40.30, 8)
    x = np.linspace(-105.15, -104.80, 8)
    vals = np.arange(len(times) * len(y) * len(x), dtype=float).reshape(len(times), len(y), len(x))
    da = xr.DataArray(vals, coords={"time": times, "y": y, "x": x}, dims=("time", "y", "x"), name="vpd")
    da.attrs["epsg"] = 4326
    return da


def test_fire_event_daily_example_and_to_hull():
    event = FireEventDaily.example()
    assert event.duration_days == 3
    assert len(event.daily_perimeters) == 3

    hull = event.to_hull(n_ring_samples=16, n_theta=12)
    assert isinstance(hull, FireHull)
    assert isinstance(hull, TimeHull)
    assert hull.metrics["duration_days"] == 3.0
    assert hull.metrics()["hull_surface_km_day"] > 0


def test_fire_event_from_fired_and_legacy_builder():
    event = FireEventDaily.example()
    rebuilt = FireEventDaily.from_fired(event.gdf, event.event_id)
    legacy = build_fire_event(event.gdf, event.event_id)

    assert rebuilt.event_id == event.event_id
    assert legacy.t0 == event.t0
    assert legacy.t1 == event.t1


def test_fire_hull_to_mesh_and_to_cube():
    event = FireEventDaily.example()
    hull = event.to_hull(n_ring_samples=16, n_theta=12)

    mesh = hull.to_mesh()
    assert set(mesh) == {"verts_km", "tris", "t_days_vert", "t_norm_vert"}
    assert mesh["verts_km"].shape[1] == 3

    mask = hull.to_cube(_template_cube())
    assert mask.dtype == bool
    assert mask.sizes["time"] == 3
    assert mask.attrs["fire_event_id"] == event.event_id


def test_fire_hull_to_cube_without_template_is_explicit():
    event = FireEventDaily.example()
    hull = event.to_hull(n_ring_samples=16, n_theta=12)

    try:
        hull.to_cube()
    except NotImplementedError as exc:
        assert "requires a template DataArray" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("Expected FireHull.to_cube() to require a template")


def test_fire_hull_attach_environment_and_plot_smoke():
    event = FireEventDaily.example()
    hull = event.to_hull(n_ring_samples=16, n_theta=12)
    cube = _template_cube()

    enriched = hull.attach_environment(cube, variables=["vpd"])
    assert "vpd" in enriched.environment
    assert isinstance(enriched.environment["vpd"], HullEnvironmentField)
    field = enriched.environment["vpd"]
    assert isinstance(field.summary, HullClimateSummary)
    assert field.vertex_values.shape[0] == hull.verts_km.shape[0]
    assert field.layer_values.shape[0] == len(np.unique(hull.t_days_vert))
    assert field.vertex_slice_index.shape[0] == hull.verts_km.shape[0]

    fig = enriched.plot(color="vpd")
    intensity = np.asarray(fig.data[0].intensity, dtype=float)
    np.testing.assert_allclose(intensity, field.vertex_values)


def test_public_fire_verbs_bind_to_canonical_fire_module():
    assert v.extract is fire_verbs.extract
    assert v.climate_hist is fire_verbs.climate_hist
    assert v.vase is fire_verbs.vase
    assert v.fire_plot is fire_verbs.fire_plot
    assert v.fire_panel is fire_verbs.fire_panel
