import pytest

from cubedynamics.sentinel import _resolve_lat_lon_and_edge_size


def test_resolve_requires_coordinates_or_bbox():
    with pytest.raises(ValueError):
        _resolve_lat_lon_and_edge_size(None, None, None, edge_size=512, resolution=10)


def test_resolve_uses_bbox_center_and_expands_edge():
    lat, lon, edge = _resolve_lat_lon_and_edge_size(
        None, None, (-100.0, 30.0, -99.0, 31.0), edge_size=512, resolution=10
    )

    assert lat == pytest.approx(30.5)
    assert lon == pytest.approx(-99.5)
    assert edge >= 10000  # ~110 km span at 10 m resolution


def test_resolve_retains_edge_for_small_bbox():
    lat, lon, edge = _resolve_lat_lon_and_edge_size(
        None, None, (0.0, 0.0, 0.001, 0.001), edge_size=512, resolution=10
    )

    assert lat == pytest.approx(0.0005)
    assert lon == pytest.approx(0.0005)
    assert edge == 512


def test_resolve_passthrough_when_lat_lon_provided():
    lat, lon, edge = _resolve_lat_lon_and_edge_size(10.0, -120.0, None, 256, 20)

    assert lat == 10.0
    assert lon == -120.0
    assert edge == 256
