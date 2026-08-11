import numpy as np
import pandas as pd
import geopandas as gpd
import shapely.geometry as geom
import pytest
import re

from cubedynamics import fire_time_hull as fth
from cubedynamics.fire_time_hull import (
    FireEventDaily,
    HullClimateSummary,
    TimeHull,
    plot_climate_filled_hull,
)


def _synthetic_hull(days: int = 3, verts_per_layer: int = 4) -> TimeHull:
    verts = []
    t_days = []
    for layer in range(days):
        z = 10.0 + layer  # intentionally non-1-based to catch index/order bugs
        t_days.extend([z] * verts_per_layer)
        for j in range(verts_per_layer):
            angle = 2.0 * np.pi * j / verts_per_layer
            radius = 1.0 + 0.1 * layer
            verts.append([radius * np.cos(angle), radius * np.sin(angle), z])
    verts = np.asarray(verts, dtype=float)

    tris = []
    for i in range(days - 1):
        for j in range(verts_per_layer):
            jn = (j + 1) % verts_per_layer
            v1 = i * verts_per_layer + j
            v2 = i * verts_per_layer + jn
            v3 = (i + 1) * verts_per_layer + jn
            v4 = (i + 1) * verts_per_layer + j
            tris.append([v1, v2, v3])
            tris.append([v1, v3, v4])

    gdf = gpd.GeoDataFrame(
        {"id": [1], "date": [pd.Timestamp("2020-07-01")], "geometry": [geom.box(0, 0, 1, 1)]},
        crs="EPSG:4326",
    )
    event = FireEventDaily(1, gdf, pd.Timestamp("2020-07-01"), pd.Timestamp("2020-07-03"), 0.0, 0.0)
    return TimeHull(
        event=event,
        verts_km=verts,
        tris=np.asarray(tris, dtype=int),
        t_days_vert=np.asarray(t_days, dtype=float),
        t_norm_vert=np.linspace(0, 1, len(t_days)),
        metrics={"days": float(days), "scale_km": 1.0, "volume_km2_days": 1.0, "surface_km_day": 1.0},
    )


@pytest.fixture
def _plotly_stub(monkeypatch):
    class _Mesh3d:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    class _Figure:
        def __init__(self, data):
            self.data = data
            self.layout = type("Layout", (), {})()
            self.layout.scene = type("Scene", (), {})()
            self.layout.scene.aspectratio = type("Aspect", (), {})()

        def update_layout(self, **kwargs):
            scene = kwargs.get("scene", {})
            aspect = scene.get("aspectratio", {})
            self.layout.scene.aspectratio.z = aspect.get("z")

        def write_image(self, *_args, **_kwargs):
            return None

    monkeypatch.setattr(fth.go, "Mesh3d", _Mesh3d, raising=False)
    monkeypatch.setattr(fth.go, "Figure", _Figure, raising=False)


def test_plot_climate_filled_hull_attaches_scalars_by_layer_order(_plotly_stub):
    hull = _synthetic_hull(days=3, verts_per_layer=4)
    summary = HullClimateSummary(
        values_inside=np.array([1.0, 2.0, 3.0]),
        values_outside=np.array([0.0, 0.0]),
        per_day_mean=pd.Series([1.0, 5.0, 9.0], index=pd.date_range("2020-07-01", periods=3, freq="D")),
    )

    fig = plot_climate_filled_hull(hull, summary, color_limits=None)
    got = np.asarray(fig.data[0].intensity, dtype=float)
    expected = np.repeat(np.array([1.0, 5.0, 9.0]), 4)
    np.testing.assert_allclose(got, expected)


def test_plot_climate_filled_hull_aligns_layers_by_event_dates_not_series_prefix(_plotly_stub):
    hull = _synthetic_hull(days=3, verts_per_layer=4)
    # Include buffer days before/after event window to emulate cube-first fire_plot.
    summary = HullClimateSummary(
        values_inside=np.array([1.0, 2.0, 3.0]),
        values_outside=np.array([0.0, 0.0]),
        per_day_mean=pd.Series(
            [100.0, 1.0, 5.0, 9.0, 200.0],
            index=pd.date_range("2020-06-30", periods=5, freq="D"),
        ),
    )

    fig = plot_climate_filled_hull(hull, summary, color_limits=None)
    got = np.asarray(fig.data[0].intensity, dtype=float)
    expected = np.repeat(np.array([1.0, 5.0, 9.0]), 4)
    np.testing.assert_allclose(got, expected)


def test_plot_climate_filled_hull_debug_z_mode_and_z_exaggeration(_plotly_stub):
    hull = _synthetic_hull(days=3, verts_per_layer=4)
    summary = HullClimateSummary(
        values_inside=np.array([1.0]),
        values_outside=np.array([0.0]),
        per_day_mean=pd.Series([2.0, 2.1, 2.2], index=pd.date_range("2020-07-01", periods=3, freq="D")),
    )

    fig = plot_climate_filled_hull(
        hull,
        summary,
        scalar_debug_mode="z",
        z_exaggeration=2.8,
        color_limits=None,
    )
    got = np.asarray(fig.data[0].intensity, dtype=float)
    np.testing.assert_allclose(got, hull.verts_km[:, 2])
    assert float(fig.layout.scene.aspectratio.z) == 2.8


def test_plot_climate_filled_hull_debug_slice_mode(_plotly_stub):
    hull = _synthetic_hull(days=3, verts_per_layer=4)
    summary = HullClimateSummary(
        values_inside=np.array([1.0]),
        values_outside=np.array([0.0]),
        per_day_mean=pd.Series([2.0, 2.1, 2.2], index=pd.date_range("2020-07-01", periods=3, freq="D")),
    )

    fig = plot_climate_filled_hull(
        hull,
        summary,
        scalar_debug_mode="slice",
        color_limits=None,
    )
    got = np.asarray(fig.data[0].intensity, dtype=float)
    np.testing.assert_allclose(got, np.repeat(np.array([0.0, 1.0, 2.0]), 4))


def test_plot_climate_filled_hull_maps_climate_by_explicit_vertex_slice_index(_plotly_stub):
    hull = _synthetic_hull(days=3, verts_per_layer=4)

    # Reorder vertices so same-slice vertices are interleaved rather than stored
    # as contiguous blocks. This catches the old "np.repeat by block" bug.
    perm = np.array([0, 4, 8, 1, 5, 9, 2, 6, 10, 3, 7, 11], dtype=int)
    inv_perm = np.empty_like(perm)
    inv_perm[perm] = np.arange(len(perm))
    hull = TimeHull(
        event=hull.event,
        verts_km=hull.verts_km[perm],
        tris=inv_perm[hull.tris],
        t_days_vert=hull.t_days_vert[perm],
        t_norm_vert=hull.t_norm_vert[perm],
        metrics=hull.metrics,
    )

    summary = HullClimateSummary(
        values_inside=np.array([1.0, 2.0, 3.0]),
        values_outside=np.array([0.0, 0.0]),
        per_day_mean=pd.Series([1.0, 5.0, 9.0], index=pd.date_range("2020-07-01", periods=3, freq="D")),
    )

    fig = plot_climate_filled_hull(hull, summary, color_limits=None)
    got = np.asarray(fig.data[0].intensity, dtype=float)
    expected = np.array([1.0, 5.0, 9.0, 1.0, 5.0, 9.0, 1.0, 5.0, 9.0, 1.0, 5.0, 9.0])
    np.testing.assert_allclose(got, expected)


def test_plot_climate_filled_hull_debug_output_reports_stats_and_alignment(_plotly_stub, capsys):
    hull = _synthetic_hull(days=3, verts_per_layer=4)
    summary = HullClimateSummary(
        values_inside=np.array([1.0]),
        values_outside=np.array([0.0]),
        per_day_mean=pd.Series([2.0, 2.1, 2.2], index=pd.date_range("2020-07-01", periods=3, freq="D")),
    )

    plot_climate_filled_hull(hull, summary, scalar_debug_mode="slice", color_limits=None, debug=True)
    out = capsys.readouterr().out

    assert "fire_hull_scalar_debug:" in out
    assert "scalar_stats" in out
    assert "approx_unique_count" in out
    assert "vertex_alignment" in out
    assert "face_alignment" in out
    assert re.search(r"'min_slice_span':\s*1", out)
    assert re.search(r"'max_slice_span':\s*1", out)


def test_plot_climate_filled_hull_drops_nonfinite_vertices_and_remaps_tris(_plotly_stub):
    hull = _synthetic_hull(days=3, verts_per_layer=4)
    verts = hull.verts_km.copy()
    verts[0, 0] = np.nan
    hull = TimeHull(
        event=hull.event,
        verts_km=verts,
        tris=hull.tris,
        t_days_vert=hull.t_days_vert,
        t_norm_vert=hull.t_norm_vert,
        metrics=hull.metrics,
    )
    summary = HullClimateSummary(
        values_inside=np.array([1.0]),
        values_outside=np.array([0.0]),
        per_day_mean=pd.Series([1.0, 5.0, 9.0], index=pd.date_range("2020-07-01", periods=3, freq="D")),
    )

    fig = plot_climate_filled_hull(hull, summary, color_limits=None)

    x = np.asarray(fig.data[0].x, dtype=float)
    y = np.asarray(fig.data[0].y, dtype=float)
    z = np.asarray(fig.data[0].z, dtype=float)
    i = np.asarray(fig.data[0].i, dtype=int)
    j = np.asarray(fig.data[0].j, dtype=int)
    k = np.asarray(fig.data[0].k, dtype=int)
    intensity = np.asarray(fig.data[0].intensity, dtype=float)

    assert x.shape[0] == verts.shape[0] - 1
    assert np.isfinite(x).all() and np.isfinite(y).all() and np.isfinite(z).all()
    assert i.size > 0 and j.size > 0 and k.size > 0
    assert (i >= 0).all() and (j >= 0).all() and (k >= 0).all()
    assert (i < x.shape[0]).all() and (j < x.shape[0]).all() and (k < x.shape[0]).all()
    assert intensity.shape[0] == x.shape[0]
