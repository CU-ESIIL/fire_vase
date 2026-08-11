"""Occurrence synchrony primitives."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import xarray as xr

from ..config import TIME_DIM
from .spatial import (
    SpatialPairSet,
    build_spatial_pairs,
    edge_to_map,
    pairwise_edge_dataset,
    regional_summary,
    stack_space,
    time_windows,
)


def occurrence_score(
    left: np.ndarray,
    right: np.ndarray,
    *,
    method: str = "jaccard",
) -> tuple[float, float, float, float]:
    """Return occurrence synchrony and audit counts for two boolean series."""

    left_bool = np.asarray(left)
    right_bool = np.asarray(right)
    valid = ~(np.isnan(left_bool.astype(float)) | np.isnan(right_bool.astype(float)))
    if not np.any(valid):
        return (np.nan, 0.0, 0.0, 0.0)
    a = left_bool[valid].astype(bool)
    b = right_bool[valid].astype(bool)
    both = float(np.count_nonzero(a & b))
    left_count = float(np.count_nonzero(a))
    right_count = float(np.count_nonzero(b))
    valid_count = float(a.size)
    union = left_count + right_count - both
    if method == "jaccard":
        score = both / union if union > 0 else np.nan
    elif method in {"joint_probability", "joint"}:
        score = both / valid_count if valid_count > 0 else np.nan
    elif method == "phi":
        n11 = both
        n10 = left_count - both
        n01 = right_count - both
        n00 = valid_count - n11 - n10 - n01
        denom = np.sqrt((n11 + n10) * (n01 + n00) * (n11 + n01) * (n10 + n00))
        score = ((n11 * n00) - (n10 * n01)) / denom if denom > 0 else np.nan
    else:
        raise ValueError("method must be 'jaccard', 'joint_probability', or 'phi'")
    return (float(score), both, union, valid_count)


def occurrence_synchrony(
    state_cube: xr.Dataset | xr.DataArray,
    *,
    state_var: str = "state",
    spatial_mode: str = "neighbors",
    radius_km: float | None = None,
    k_neighbors: int | None = None,
    reference: str | tuple[int, int] | int | None = None,
    method: str = "jaccard",
    window: int | str | None = None,
    stride: int | str | None = None,
    time_dim: str = TIME_DIM,
) -> xr.Dataset:
    """Measure whether states occur at the same times across locations."""

    state = _get_state_array(state_cube, state_var)
    windows = time_windows(state, window=window, stride=stride, time_dim=time_dim)
    window_results = []
    for t_end, sub in windows:
        pairs = build_spatial_pairs(
            sub,
            mode="reference" if spatial_mode == "center" else spatial_mode,
            radius_km=radius_km,
            k_neighbors=k_neighbors,
            reference=reference or ("center" if spatial_mode in {"reference", "center"} else None),
        )
        edge = _occurrence_edges(sub, pairs=pairs, method=method, time_dim=time_dim, t_end=t_end)
        if spatial_mode in {"all_pairs", "blocks"}:
            window_results.append(edge)
        elif spatial_mode == "regional":
            window_results.append(
                regional_summary(edge, metric_var="occurrence_synchrony", time_window_end=t_end)
            )
        else:
            window_results.append(
                _edge_to_output_map(
                    edge,
                    metric_var="occurrence_synchrony",
                    template=sub,
                    pairs=pairs,
                    time_window_end=t_end,
                )
            )
    result = xr.concat(window_results, dim="time_window_end") if len(window_results) > 1 else window_results[0]
    result.attrs.update(
        {
            "analysis": "occurrence_synchrony",
            "spatial_mode": spatial_mode,
            "method": method,
            "state_var": state_var,
            "window": str(window),
            "stride": str(stride),
        }
    )
    return result


def _get_state_array(obj: xr.Dataset | xr.DataArray, state_var: str) -> xr.DataArray:
    if isinstance(obj, xr.DataArray):
        return obj
    if state_var not in obj.data_vars:
        raise ValueError(f"State variable {state_var!r} not found in Dataset")
    return obj[state_var]


def _occurrence_edges(
    state: xr.DataArray,
    *,
    pairs: SpatialPairSet,
    method: str,
    time_dim: str,
    t_end: object,
) -> xr.Dataset:
    stacked = stack_space(state)
    values = []
    both_counts = []
    union_counts = []
    valid_counts = []
    for pair in pairs.pairs:
        left = stacked.isel(space=pair.source)
        right = stacked.isel(space=pair.target)
        score, both, union, valid = xr.apply_ufunc(
            occurrence_score,
            left,
            right,
            input_core_dims=[[time_dim], [time_dim]],
            output_core_dims=[[], [], [], []],
            vectorize=False,
            dask="parallelized",
            output_dtypes=[float, float, float, float],
            kwargs={"method": method},
        )
        values.append(score)
        both_counts.append(both)
        union_counts.append(union)
        valid_counts.append(valid)
    edge = pairwise_edge_dataset(
        values,
        var_name="occurrence_synchrony",
        pairs=pairs,
        time_window_end=t_end,
        extra_vars={
            "joint_event_count": both_counts,
            "event_union_count": union_counts,
            "valid_sample_count": valid_counts,
        },
    )
    return edge


def _edge_to_output_map(
    edge: xr.Dataset,
    *,
    metric_var: str,
    template: xr.DataArray,
    pairs: SpatialPairSet,
    time_window_end: object,
) -> xr.Dataset:
    if pairs.mode == "reference":
        return _reference_edge_to_map(edge, metric_var=metric_var, template=template, pairs=pairs, time_window_end=time_window_end)
    return edge_to_map(
        edge,
        metric_var=metric_var,
        template=template,
        pairs=pairs,
        time_window_end=time_window_end,
        count_var="joint_event_count" if "joint_event_count" in edge else None,
    )


def _reference_edge_to_map(
    edge: xr.Dataset,
    *,
    metric_var: str,
    template: xr.DataArray,
    pairs: SpatialPairSet,
    time_window_end: object,
) -> xr.Dataset:
    y_dim, x_dim = pairs.spatial_dims
    shape = (int(template.sizes[y_dim]), int(template.sizes[x_dim]))
    coords = {dim: template.coords[dim] for dim in pairs.spatial_dims if dim in template.coords}
    data_vars: dict[str, xr.DataArray] = {}
    for name in edge.data_vars:
        vals = np.full(shape, np.nan, dtype=float)
        if name in edge:
            edge_vals = np.asarray(edge[name].isel(time_window_end=0).values, dtype=float)
            for idx, pair in enumerate(pairs.pairs):
                y_idx, x_idx = divmod(pair.source, shape[1])
                vals[y_idx, x_idx] = edge_vals[idx]
        data_vars[name] = xr.DataArray(vals, dims=pairs.spatial_dims, coords=coords).expand_dims(
            {"time_window_end": [time_window_end]}
        )
    return xr.Dataset(data_vars)
