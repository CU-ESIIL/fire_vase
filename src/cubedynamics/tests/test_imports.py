"""Basic import smoke tests for the cubedynamics package."""

import cubedynamics


def test_version_exposed():
    """Ensure the package exposes a version string."""
    assert isinstance(cubedynamics.__version__, str)


def test_streaming_helpers_are_callable():
    """All public streaming helpers should be importable."""
    public_funcs = [
        cubedynamics.stream_global_climate_cube,
        cubedynamics.stream_gridmet_to_cube,
        cubedynamics.stream_prism_to_cube,
        cubedynamics.correlation_cube,
    ]
    for func in public_funcs:
        assert callable(func)
