"""Generic biological observation rasterization."""

from __future__ import annotations

import numpy as np
import pandas as pd
import xarray as xr

from ..config import TIME_DIM, X_DIM, Y_DIM


def rasterize_observations(
    observations,
    *,
    template: xr.DataArray | xr.Dataset,
    time_col: str = "date",
    y_col: str = Y_DIM,
    x_col: str = X_DIM,
    value_col: str = "value",
    reducer: str = "sum",
    name: str | None = None,
) -> xr.DataArray:
    """Rasterize point observations into the time/y/x grid of a template cube."""

    df = pd.DataFrame(observations).copy()
    for col in (time_col, y_col, x_col, value_col):
        if col not in df.columns:
            raise ValueError(f"Observation column {col!r} not found")
    if reducer not in {"sum", "mean", "count"}:
        raise ValueError("reducer must be 'sum', 'mean', or 'count'")
    if TIME_DIM not in template.coords or Y_DIM not in template.coords or X_DIM not in template.coords:
        raise ValueError("template must provide time, y, and x coordinates")

    times = pd.to_datetime(template[TIME_DIM].values)
    y_vals = np.asarray(template[Y_DIM].values, dtype=float)
    x_vals = np.asarray(template[X_DIM].values, dtype=float)
    out = np.full((len(times), len(y_vals), len(x_vals)), np.nan, dtype=float)
    counts = np.zeros_like(out)
    sums = np.zeros_like(out)

    obs_times = pd.to_datetime(df[time_col])
    for row_idx, row in df.iterrows():
        time_idx = int(np.argmin(np.abs(times - obs_times.loc[row_idx])))
        y_idx = int(np.argmin(np.abs(y_vals - float(row[y_col]))))
        x_idx = int(np.argmin(np.abs(x_vals - float(row[x_col]))))
        value = 1.0 if reducer == "count" else float(row[value_col])
        sums[time_idx, y_idx, x_idx] += value
        counts[time_idx, y_idx, x_idx] += 1

    observed = counts > 0
    if reducer == "mean":
        out[observed] = sums[observed] / counts[observed]
    else:
        out[observed] = sums[observed]
    da = xr.DataArray(
        out,
        dims=(TIME_DIM, Y_DIM, X_DIM),
        coords={TIME_DIM: template[TIME_DIM], Y_DIM: template[Y_DIM], X_DIM: template[X_DIM]},
        name=name or value_col,
    )
    da.attrs.update(
        {
            "analysis": "rasterize_observations",
            "time_col": time_col,
            "y_col": y_col,
            "x_col": x_col,
            "value_col": value_col,
            "reducer": reducer,
            "missing_value_semantics": "NaN means unobserved; numeric zero means observed zero",
        }
    )
    return da
