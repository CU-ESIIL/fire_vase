"""Streaming-first contract tests for cubedynamics."""

import inspect

import pytest

import cubedynamics

STREAMING_FUNCTIONS = [
    cubedynamics.stream_global_climate_cube,
    cubedynamics.stream_gridmet_to_cube,
    cubedynamics.stream_prism_to_cube,
]

STREAMING_STUBS = [cubedynamics.stream_prism_to_cube]


@pytest.mark.streaming
@pytest.mark.parametrize("func", STREAMING_FUNCTIONS)
def test_streaming_functions_expose_chunks_argument(func):
    """Every streaming helper must expose a ``chunks`` keyword."""
    signature = inspect.signature(func)
    assert "chunks" in signature.parameters
    assert signature.parameters["chunks"].kind in {
        inspect.Parameter.KEYWORD_ONLY,
        inspect.Parameter.POSITIONAL_OR_KEYWORD,
    }


@pytest.mark.streaming
def test_streaming_stubs_raise_not_implemented():
    """Until implemented, stub helpers should make their status clear."""
    dummy_file_like = object()
    for func in STREAMING_STUBS:
        with pytest.raises(NotImplementedError):
            func(dummy_file_like, chunks={"time": 1})


@pytest.mark.download
def test_stub_download_paths_are_opt_in():
    """Stubs must still raise until real download behavior is implemented."""
    for func in STREAMING_STUBS:
        with pytest.raises(NotImplementedError):
            func("/tmp/local-prism-stack.nc", chunks=None, force_download=True)
