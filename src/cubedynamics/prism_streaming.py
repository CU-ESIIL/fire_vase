"""Streaming-first helpers for PRISM datasets.

The real PRISM readers still live under ``code/cubedynamics`` today, but the
public interface is defined here so that we can publish a lightweight package.
Future contributions MUST preserve a streaming-first mindset.
"""

from __future__ import annotations

from typing import Iterable, Mapping, Sequence

import xarray as xr


def stream_prism_to_cube(
    source: str | Mapping[str, str] | Iterable[str],
    variables: Sequence[str] | None = None,
    *,
    chunks: dict | str | None = None,
    preferred_driver: str | None = None,
    **stream_kwargs,
) -> xr.Dataset:
    """Stream PRISM data into an xarray object.

    Implementations should only fetch the bytes required to satisfy the request
    rather than downloading entire yearly stacks.  The ``preferred_driver``
    parameter leaves room for deciding between rasterio, fsspec, or GDAL-based
    readers depending on what can yield streaming-friendly file objects.

    TODO: implement the actual streaming logic.
    """
    raise NotImplementedError("stream_prism_to_cube not implemented yet.")


__all__ = ["stream_prism_to_cube"]
