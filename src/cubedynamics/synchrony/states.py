"""State-cube construction for synchrony analyses."""

from __future__ import annotations

from typing import Hashable

import numpy as np
import xarray as xr

from ..config import TIME_DIM


def select_dataarray(
    obj: xr.DataArray | xr.Dataset,
    *,
    variable: Hashable | None = None,
    caller: str = "state constructor",
) -> tuple[xr.DataArray, str]:
    """Return the selected DataArray and source variable name."""

    if isinstance(obj, xr.DataArray):
        if variable is not None:
            raise ValueError(f"{caller} received variable= for a DataArray input")
        return obj, obj.name or "value"
    if not isinstance(obj, xr.Dataset):
        raise TypeError(f"{caller} requires an xarray DataArray or Dataset")
    if variable is None:
        if len(obj.data_vars) != 1:
            raise ValueError(
                f"{caller} requires variable= for Dataset inputs with multiple variables"
            )
        variable = next(iter(obj.data_vars))
    if variable not in obj.data_vars:
        raise ValueError(
            f"Variable {variable!r} not found in Dataset variables: {list(obj.data_vars)!r}"
        )
    return obj[variable], str(variable)


def _validate_direction(direction: str) -> str:
    if direction not in {"above", "below"}:
        raise ValueError("direction must be 'above' or 'below'")
    return direction


def _state_from_threshold(
    da: xr.DataArray,
    threshold: float | xr.DataArray,
    *,
    direction: str,
    method: str,
    source_variable: str,
    name: str | None,
    extra_attrs: dict[str, object] | None = None,
) -> xr.Dataset:
    direction = _validate_direction(direction)
    threshold_da = xr.DataArray(threshold) if np.isscalar(threshold) else threshold
    threshold_broadcast = threshold_da.broadcast_like(da)
    if direction == "above":
        magnitude = da - threshold_broadcast
        state = da >= threshold_broadcast
    else:
        magnitude = threshold_broadcast - da
        state = da <= threshold_broadcast

    state = state.rename("state")
    magnitude = magnitude.rename("magnitude")
    threshold_broadcast = threshold_broadcast.rename("threshold")
    state.attrs.update(
        {
            "long_name": name or f"{source_variable}_{direction}_state",
            "threshold_method": method,
            "direction": direction,
            "source_variable": source_variable,
        }
    )
    magnitude.attrs.update(
        {
            "long_name": f"Distance {direction} threshold",
            "threshold_method": method,
            "direction": direction,
            "source_variable": source_variable,
        }
    )
    threshold_broadcast.attrs.update(
        {
            "long_name": "State threshold",
            "threshold_method": method,
            "direction": direction,
            "source_variable": source_variable,
        }
    )
    ds = xr.Dataset(
        {
            "state": state.astype(bool),
            "magnitude": magnitude.astype(float),
            "threshold": threshold_broadcast.astype(float),
        }
    )
    ds.attrs.update(da.attrs)
    attrs: dict[str, object] = {
        "analysis": "state_cube",
        "state_name": name or "state",
        "threshold_method": method,
        "direction": direction,
        "source_variable": source_variable,
    }
    if extra_attrs:
        attrs.update(extra_attrs)
    ds.attrs.update(attrs)
    return ds


def threshold_state(
    obj: xr.DataArray | xr.Dataset,
    *,
    threshold: float | xr.DataArray,
    direction: str,
    variable: Hashable | None = None,
    name: str | None = None,
) -> xr.Dataset:
    """Build a state cube from a scalar or broadcastable threshold."""

    da, source = select_dataarray(obj, variable=variable, caller="threshold_state")
    return _state_from_threshold(
        da,
        threshold,
        direction=direction,
        method="threshold",
        source_variable=source,
        name=name,
        extra_attrs={"threshold_value": float(threshold) if np.isscalar(threshold) else "field"},
    )


def quantile_state(
    obj: xr.DataArray | xr.Dataset,
    *,
    quantile: float,
    direction: str,
    rolling_window: int | None = None,
    climatology: xr.DataArray | None = None,
    variable: Hashable | None = None,
    name: str | None = None,
    time_dim: str = TIME_DIM,
) -> xr.Dataset:
    """Build a state cube from global, rolling, or supplied quantile thresholds."""

    if not 0.0 <= quantile <= 1.0:
        raise ValueError("quantile must be between 0 and 1")
    da, source = select_dataarray(obj, variable=variable, caller="quantile_state")
    if time_dim not in da.dims:
        raise ValueError(f"quantile_state requires time dimension {time_dim!r}")
    if climatology is not None:
        threshold = climatology.broadcast_like(da)
        method = "climatology_quantile"
    elif rolling_window is not None:
        if rolling_window < 1:
            raise ValueError("rolling_window must be at least 1")
        window_dim = f"{time_dim}_window"
        rolled = da.rolling({time_dim: rolling_window}, min_periods=1).construct(window_dim)
        threshold = rolled.quantile(quantile, dim=window_dim)
        method = "rolling_quantile"
    else:
        threshold = da.quantile(quantile, dim=time_dim)
        method = "quantile"

    if "quantile" in threshold.coords:
        threshold = threshold.drop_vars("quantile")
    return _state_from_threshold(
        da,
        threshold,
        direction=direction,
        method=method,
        source_variable=source,
        name=name,
        extra_attrs={
            "quantile": float(quantile),
            "rolling_window": rolling_window,
            "time_dim": time_dim,
        },
    )


def binary_state(
    obj: xr.DataArray | xr.Dataset,
    *,
    variable: Hashable | None = None,
    name: str | None = None,
) -> xr.Dataset:
    """Normalize an existing boolean or numeric event mask into a state cube."""

    da, source = select_dataarray(obj, variable=variable, caller="binary_state")
    state = da.astype(bool).rename("state")
    magnitude = xr.where(state, 1.0, 0.0).rename("magnitude")
    threshold = xr.zeros_like(magnitude).rename("threshold")
    state.attrs.update(
        {
            "long_name": name or f"{source}_binary_state",
            "threshold_method": "binary",
            "source_variable": source,
        }
    )
    ds = xr.Dataset(
        {"state": state, "magnitude": magnitude.astype(float), "threshold": threshold.astype(float)}
    )
    ds.attrs.update(da.attrs)
    ds.attrs.update(
        {
            "analysis": "state_cube",
            "state_name": name or "state",
            "threshold_method": "binary",
            "source_variable": source,
        }
    )
    return ds


def change_state(
    obj: xr.DataArray | xr.Dataset,
    *,
    change: str,
    threshold: float,
    lag: int | str,
    variable: Hashable | None = None,
    name: str | None = None,
    time_dim: str = TIME_DIM,
) -> xr.Dataset:
    """Build a state cube from lagged absolute or relative change."""

    if change not in {"absolute", "relative"}:
        raise ValueError("change must be 'absolute' or 'relative'")
    da, source = select_dataarray(obj, variable=variable, caller="change_state")
    if time_dim not in da.dims:
        raise ValueError(f"change_state requires time dimension {time_dim!r}")
    periods = _lag_to_periods(lag, da[time_dim])
    shifted = da.shift({time_dim: periods})
    delta = da - shifted
    if change == "relative":
        denom = xr.where(np.abs(shifted) > 0, shifted, np.nan)
        signal = delta / denom
    else:
        signal = delta
    return _state_from_threshold(
        signal.rename(source),
        threshold,
        direction="above",
        method=f"{change}_change",
        source_variable=source,
        name=name,
        extra_attrs={"change": change, "lag": str(lag), "lag_periods": periods},
    )


def _lag_to_periods(lag: int | str, time: xr.DataArray) -> int:
    if isinstance(lag, int):
        if lag < 1:
            raise ValueError("lag must be a positive integer or offset string")
        return lag
    if not np.issubdtype(time.dtype, np.datetime64):
        raise ValueError("string lags require a datetime64 time coordinate")
    offset = np.timedelta64(1, "D")
    text = lag.strip().upper()
    if text.endswith("D"):
        offset = np.timedelta64(int(text[:-1]), "D")
    elif text.endswith("Y"):
        offset = np.timedelta64(int(text[:-1]) * 365, "D")
    else:
        raise ValueError("string lag must use 'D' or 'Y' units, e.g. '30D' or '1Y'")
    diffs = np.diff(time.values.astype("datetime64[ns]"))
    if diffs.size == 0:
        raise ValueError("change_state requires at least two time steps")
    step = np.median(diffs).astype("timedelta64[ns]")
    periods = int(round(offset.astype("timedelta64[ns]").astype(float) / step.astype(float)))
    return max(periods, 1)
