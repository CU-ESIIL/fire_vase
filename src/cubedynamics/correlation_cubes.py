"""Correlation and trend helpers for streamed cubes."""

from __future__ import annotations

from typing import Iterable

import xarray as xr


def correlation_cube(
    reference: xr.DataArray | xr.Dataset,
    targets: Iterable[xr.DataArray | xr.Dataset],
    *,
    statistic: str = "pearson",
    chunks: dict | str | None = None,
    compute: bool = False,
) -> xr.DataArray:
    """Compute correlations between a reference cube and streamed targets.

    The correlation helpers are expected to operate lazily and to consume
    iterables of streamed chunks rather than expecting materialized arrays.  In
    practice this will be implemented by composing with Dask-backed xarray
    objects, but the stub exists here to capture the desired public contract.

    TODO: implement streaming-aware rolling correlations.
    """
    raise NotImplementedError("correlation_cube not implemented yet.")


__all__ = ["correlation_cube"]
