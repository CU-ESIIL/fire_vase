"""Event detection from binary state cubes."""

from __future__ import annotations

import numpy as np
import pandas as pd
import xarray as xr

from ..config import TIME_DIM
from ..synchrony.spatial import infer_spatial_dims
from .schemas import EventResult


def detect_events(
    state_cube: xr.Dataset,
    *,
    state_var: str = "state",
    magnitude_var: str = "magnitude",
    min_duration: int = 1,
    max_gap: int = 0,
    time_dim: str = TIME_DIM,
) -> EventResult:
    """Convert contiguous true runs into event cube variables and a catalog."""

    if not isinstance(state_cube, xr.Dataset):
        raise TypeError("detect_events requires a state Dataset")
    if state_var not in state_cube:
        raise ValueError(f"State variable {state_var!r} not found")
    if min_duration < 1:
        raise ValueError("min_duration must be at least 1")
    if max_gap < 0:
        raise ValueError("max_gap must be nonnegative")
    state = state_cube[state_var]
    magnitude = state_cube[magnitude_var] if magnitude_var in state_cube else xr.where(state, 1.0, np.nan)
    if time_dim not in state.dims:
        raise ValueError(f"detect_events requires time dimension {time_dim!r}")
    spatial_dims = infer_spatial_dims(state)
    ordered_state = state.transpose(time_dim, *spatial_dims)
    ordered_mag = magnitude.transpose(time_dim, *spatial_dims)
    active = np.asarray(ordered_state.values).astype(bool)
    mag = np.asarray(ordered_mag.values, dtype=float)
    times = np.asarray(ordered_state[time_dim].values)
    shape = active.shape

    event_active = np.zeros(shape, dtype=bool)
    event_id = np.full(shape, -1, dtype=np.int64)
    event_age = np.full(shape, np.nan, dtype=float)
    event_duration = np.full(shape, np.nan, dtype=float)
    event_peak = np.full(shape, np.nan, dtype=float)
    event_mean = np.full(shape, np.nan, dtype=float)
    event_integral = np.full(shape, np.nan, dtype=float)
    sequence_index = np.full(shape, -1, dtype=np.int64)
    time_since_previous = np.full(shape, np.nan, dtype=float)
    event_start = np.full(shape, np.datetime64("NaT", "ns"), dtype="datetime64[ns]")
    event_end = np.full(shape, np.datetime64("NaT", "ns"), dtype="datetime64[ns]")

    records: list[dict[str, object]] = []
    next_event_id = 1
    for y_idx in range(shape[1]):
        for x_idx in range(shape[2]):
            runs = _find_runs(active[:, y_idx, x_idx], max_gap=max_gap)
            previous_end_idx: int | None = None
            kept_index = 0
            for start_idx, end_idx in runs:
                true_indices = np.flatnonzero(active[start_idx : end_idx + 1, y_idx, x_idx]) + start_idx
                if true_indices.size < min_duration:
                    continue
                event_slice = slice(start_idx, end_idx + 1)
                event_mag = mag[event_slice, y_idx, x_idx]
                finite_mag = event_mag[np.isfinite(event_mag)]
                peak = float(np.nanmax(finite_mag)) if finite_mag.size else np.nan
                mean = float(np.nanmean(finite_mag)) if finite_mag.size else np.nan
                integral = float(np.nansum(finite_mag)) if finite_mag.size else np.nan
                duration = int(true_indices.size)
                start_time = times[start_idx].astype("datetime64[ns]")
                end_time = times[end_idx].astype("datetime64[ns]")
                gap_days = (
                    _timedelta_days(times[start_idx] - times[previous_end_idx])
                    if previous_end_idx is not None
                    else np.nan
                )

                event_active[event_slice, y_idx, x_idx] = active[event_slice, y_idx, x_idx]
                event_id[event_slice, y_idx, x_idx] = next_event_id
                event_age[event_slice, y_idx, x_idx] = np.arange(end_idx - start_idx + 1)
                event_duration[event_slice, y_idx, x_idx] = duration
                event_peak[event_slice, y_idx, x_idx] = peak
                event_mean[event_slice, y_idx, x_idx] = mean
                event_integral[event_slice, y_idx, x_idx] = integral
                sequence_index[event_slice, y_idx, x_idx] = kept_index
                time_since_previous[event_slice, y_idx, x_idx] = gap_days
                event_start[event_slice, y_idx, x_idx] = start_time
                event_end[event_slice, y_idx, x_idx] = end_time

                y_value = _coord_value(state_cube, spatial_dims[0], y_idx)
                x_value = _coord_value(state_cube, spatial_dims[1], x_idx)
                records.append(
                    {
                        "event_id": next_event_id,
                        spatial_dims[0]: y_value,
                        spatial_dims[1]: x_value,
                        "y_index": y_idx,
                        "x_index": x_idx,
                        "start": start_time,
                        "end": end_time,
                        "duration": duration,
                        "peak": peak,
                        "mean": mean,
                        "integral": integral,
                        "sequence_index": kept_index,
                        "time_since_previous_event": gap_days,
                    }
                )
                next_event_id += 1
                kept_index += 1
                previous_end_idx = end_idx

    coords = {time_dim: state[time_dim], spatial_dims[0]: state[spatial_dims[0]], spatial_dims[1]: state[spatial_dims[1]]}
    dims = (time_dim, *spatial_dims)
    ds = xr.Dataset(
        {
            "event_active": xr.DataArray(event_active, dims=dims, coords=coords),
            "event_id": xr.DataArray(event_id, dims=dims, coords=coords),
            "event_start": xr.DataArray(event_start, dims=dims, coords=coords),
            "event_end": xr.DataArray(event_end, dims=dims, coords=coords),
            "event_age": xr.DataArray(event_age, dims=dims, coords=coords),
            "event_duration": xr.DataArray(event_duration, dims=dims, coords=coords),
            "event_peak": xr.DataArray(event_peak, dims=dims, coords=coords),
            "event_mean": xr.DataArray(event_mean, dims=dims, coords=coords),
            "event_integral": xr.DataArray(event_integral, dims=dims, coords=coords),
            "sequence_index": xr.DataArray(sequence_index, dims=dims, coords=coords),
            "time_since_previous_event": xr.DataArray(time_since_previous, dims=dims, coords=coords),
        }
    )
    ds.attrs.update(state_cube.attrs)
    ds.attrs.update(
        {
            "analysis": "detected_events",
            "state_var": state_var,
            "magnitude_var": magnitude_var,
            "min_duration": min_duration,
            "max_gap": max_gap,
            "event_count": len(records),
        }
    )
    catalog = pd.DataFrame.from_records(records)
    return EventResult(dataset=ds, catalog=catalog)


def _find_runs(active: np.ndarray, *, max_gap: int) -> list[tuple[int, int]]:
    true_idx = np.flatnonzero(active)
    if true_idx.size == 0:
        return []
    runs: list[tuple[int, int]] = []
    start = int(true_idx[0])
    prev = int(true_idx[0])
    for idx in true_idx[1:]:
        idx = int(idx)
        if idx - prev - 1 <= max_gap:
            prev = idx
            continue
        runs.append((start, prev))
        start = idx
        prev = idx
    runs.append((start, prev))
    return runs


def _coord_value(ds: xr.Dataset, dim: str, idx: int) -> object:
    if dim in ds.coords:
        return ds[dim].values[idx]
    return idx


def _timedelta_days(delta: np.timedelta64) -> float:
    try:
        return float(delta / np.timedelta64(1, "D"))
    except Exception:
        return float("nan")
