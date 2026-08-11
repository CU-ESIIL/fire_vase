"""Pipe-friendly state-cube verbs."""

from __future__ import annotations

from typing import Hashable

import xarray as xr

from ..synchrony.states import (
    binary_state as _binary_state,
    change_state as _change_state,
    quantile_state as _quantile_state,
    threshold_state as _threshold_state,
)


def threshold_state(
    *,
    threshold: float | xr.DataArray,
    direction: str,
    variable: Hashable | None = None,
    name: str | None = None,
):
    """Summary
    Convert raw values to a standard state cube using a threshold.

    Grammar contract
    Raw cube -> Dataset with ``state``, ``magnitude``, and ``threshold``.
    """

    def _op(obj):
        return _threshold_state(
            obj,
            threshold=threshold,
            direction=direction,
            variable=variable,
            name=name,
        )

    return _op


def quantile_state(
    *,
    quantile: float,
    direction: str,
    rolling_window: int | None = None,
    climatology: xr.DataArray | None = None,
    variable: Hashable | None = None,
    name: str | None = None,
):
    """Summary
    Convert raw values to a state cube using quantile thresholds.

    Grammar contract
    Raw cube -> Dataset with ``state``, ``magnitude``, and ``threshold``.
    """

    def _op(obj):
        return _quantile_state(
            obj,
            quantile=quantile,
            direction=direction,
            rolling_window=rolling_window,
            climatology=climatology,
            variable=variable,
            name=name,
        )

    return _op


def binary_state(*, variable: Hashable | None = None, name: str | None = None):
    """Summary
    Normalize an existing boolean mask into a state cube.

    Grammar contract
    Boolean cube -> Dataset with ``state``, ``magnitude``, and ``threshold``.
    """

    def _op(obj):
        return _binary_state(obj, variable=variable, name=name)

    return _op


def change_state(
    *,
    change: str,
    threshold: float,
    lag: int | str,
    variable: Hashable | None = None,
    name: str | None = None,
):
    """Summary
    Convert lagged absolute or relative change to a state cube.

    Grammar contract
    Raw biological or environmental cube -> state Dataset.
    """

    def _op(obj):
        return _change_state(
            obj,
            change=change,
            threshold=threshold,
            lag=lag,
            variable=variable,
            name=name,
        )

    return _op


def exceedance(*args, **kwargs):
    """Alias for :func:`threshold_state`."""

    return threshold_state(*args, **kwargs)


__all__ = [
    "binary_state",
    "change_state",
    "exceedance",
    "quantile_state",
    "threshold_state",
]
