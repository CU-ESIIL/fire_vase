"""Timing and duration synchrony from detected events."""

from __future__ import annotations

import numpy as np
import xarray as xr

from ..events.matching import match_events, parse_tolerance
from ..events.schemas import EventResult
from ..stats.tails import _rank_1d
from .spatial import build_spatial_pairs, edge_to_map, pairwise_edge_dataset, regional_summary


def timing_synchrony(
    events: EventResult | xr.Dataset,
    *,
    event_anchor: str = "start",
    match_tolerance: str | int = "7D",
    score: str = "exponential",
    timescale: str | int = "3D",
    spatial_mode: str = "neighbors",
    radius_km: float | None = None,
    k_neighbors: int | None = None,
    reference: str | tuple[int, int] | int | None = None,
) -> xr.Dataset:
    """Measure whether matched events begin, peak, or end at similar times."""

    result = _as_event_result(events)
    pairs = build_spatial_pairs(
        result.dataset,
        mode="reference" if spatial_mode == "center" else spatial_mode,
        radius_km=radius_km,
        k_neighbors=k_neighbors,
        reference=reference or ("center" if spatial_mode in {"reference", "center"} else None),
    )
    edge = _event_edges(
        result,
        pairs=pairs,
        metric="timing",
        event_anchor=event_anchor,
        match_tolerance=match_tolerance,
        score=score,
        timescale=timescale,
    )
    if spatial_mode in {"all_pairs", "blocks"}:
        out = edge
    elif spatial_mode == "regional":
        out = regional_summary(edge, metric_var="timing_synchrony", time_window_end=_event_window_end(result))
    else:
        out = edge_to_map(
            edge,
            metric_var="timing_synchrony",
            template=result.dataset["event_active"],
            pairs=pairs,
            time_window_end=_event_window_end(result),
            count_var="matched_event_count",
        )
    out.attrs.update(
        {
            "analysis": "timing_synchrony",
            "event_anchor": event_anchor,
            "match_tolerance": str(match_tolerance),
            "score": score,
            "timescale": str(timescale),
            "spatial_mode": spatial_mode,
        }
    )
    return out


def duration_synchrony(
    events: EventResult | xr.Dataset,
    *,
    match_on: str = "overlap",
    match_tolerance: str | int = "7D",
    method: str = "spearman",
    spatial_mode: str = "neighbors",
    radius_km: float | None = None,
    k_neighbors: int | None = None,
    reference: str | tuple[int, int] | int | None = None,
    min_matched_events: int = 3,
) -> xr.Dataset:
    """Compare how long matched events persist."""

    result = _as_event_result(events)
    if match_on not in {"overlap", "start", "end"}:
        raise ValueError("match_on must be 'overlap', 'start', or 'end'")
    anchor = "start" if match_on == "overlap" else match_on
    pairs = build_spatial_pairs(
        result.dataset,
        mode="reference" if spatial_mode == "center" else spatial_mode,
        radius_km=radius_km,
        k_neighbors=k_neighbors,
        reference=reference or ("center" if spatial_mode in {"reference", "center"} else None),
    )
    edge = _event_edges(
        result,
        pairs=pairs,
        metric="duration",
        event_anchor=anchor,
        match_tolerance=match_tolerance,
        method=method,
        min_matched_events=min_matched_events,
    )
    if spatial_mode in {"all_pairs", "blocks"}:
        out = edge
    elif spatial_mode == "regional":
        out = regional_summary(edge, metric_var="duration_synchrony", time_window_end=_event_window_end(result))
    else:
        out = edge_to_map(
            edge,
            metric_var="duration_synchrony",
            template=result.dataset["event_active"],
            pairs=pairs,
            time_window_end=_event_window_end(result),
            count_var="matched_event_count",
        )
    out.attrs.update(
        {
            "analysis": "duration_synchrony",
            "match_on": match_on,
            "match_tolerance": str(match_tolerance),
            "method": method,
            "spatial_mode": spatial_mode,
            "min_matched_events": min_matched_events,
        }
    )
    return out


def _event_edges(
    events: EventResult,
    *,
    pairs,
    metric: str,
    event_anchor: str,
    match_tolerance: str | int,
    score: str = "exponential",
    timescale: str | int = "3D",
    method: str = "spearman",
    min_matched_events: int = 3,
) -> xr.Dataset:
    values = []
    matched_counts = []
    mean_lags = []
    median_abs_lags = []
    source_unmatched = []
    target_unmatched = []
    duration_similarity = []
    mean_duration_difference = []
    t_end = _event_window_end(events)
    catalog = events.catalog
    for pair in pairs.pairs:
        source = catalog[(catalog["y_index"] == pair.source // events.dataset.sizes["x"]) & (catalog["x_index"] == pair.source % events.dataset.sizes["x"])]
        target = catalog[(catalog["y_index"] == pair.target // events.dataset.sizes["x"]) & (catalog["x_index"] == pair.target % events.dataset.sizes["x"])]
        matches = match_events(
            source,
            target,
            anchor=event_anchor,
            tolerance=match_tolerance,
        )
        matched = len(matches)
        matched_counts.append(xr.DataArray(float(matched)))
        source_unmatched.append(xr.DataArray(float(max(len(source) - matched, 0))))
        target_unmatched.append(xr.DataArray(float(max(len(target) - matched, 0))))
        if matched:
            lags = np.asarray(matches["lag_days"], dtype=float)
            mean_lags.append(xr.DataArray(float(np.nanmean(lags))))
            median_abs_lags.append(xr.DataArray(float(np.nanmedian(np.abs(lags)))))
        else:
            mean_lags.append(xr.DataArray(np.nan))
            median_abs_lags.append(xr.DataArray(np.nan))
        if metric == "timing":
            if not matched:
                value = np.nan
            elif score == "exponential":
                scale_days = float(parse_tolerance(timescale) / np.timedelta64(1, "D"))
                scale_days = max(scale_days, 1e-9)
                value = float(np.nanmean(np.exp(-np.abs(matches["lag_days"].to_numpy(dtype=float)) / scale_days)))
            elif score == "inverse":
                value = float(np.nanmean(1.0 / (1.0 + np.abs(matches["lag_days"].to_numpy(dtype=float)))))
            else:
                raise ValueError("score must be 'exponential' or 'inverse'")
            values.append(xr.DataArray(value))
            duration_similarity.append(xr.DataArray(np.nan))
            mean_duration_difference.append(xr.DataArray(np.nan))
        else:
            value, sim, mean_diff = _duration_metrics(matches, method=method, min_matched_events=min_matched_events)
            values.append(xr.DataArray(value))
            duration_similarity.append(xr.DataArray(sim))
            mean_duration_difference.append(xr.DataArray(mean_diff))

    var_name = "timing_synchrony" if metric == "timing" else "duration_synchrony"
    extra = {
        "matched_event_count": matched_counts,
        "mean_lag": mean_lags,
        "median_absolute_lag": median_abs_lags,
        "source_unmatched_event_count": source_unmatched,
        "target_unmatched_event_count": target_unmatched,
    }
    if metric == "duration":
        extra["duration_similarity"] = duration_similarity
        extra["mean_duration_difference"] = mean_duration_difference
    return pairwise_edge_dataset(
        values,
        var_name=var_name,
        pairs=pairs,
        time_window_end=t_end,
        extra_vars=extra,
    )


def _duration_metrics(matches, *, method: str, min_matched_events: int) -> tuple[float, float, float]:
    if matches.empty:
        return (np.nan, np.nan, np.nan)
    source = matches["source_duration"].to_numpy(dtype=float)
    target = matches["target_duration"].to_numpy(dtype=float)
    diff = source - target
    similarity = float(np.nanmean(1.0 - (np.abs(diff) / np.maximum(np.maximum(source, target), 1.0))))
    mean_diff = float(np.nanmean(diff))
    if len(matches) < min_matched_events:
        return (np.nan, similarity, mean_diff)
    if method == "spearman":
        source = _rank_1d(source)
        target = _rank_1d(target)
    elif method != "pearson":
        raise ValueError("method must be 'spearman' or 'pearson'")
    source_centered = source - source.mean()
    target_centered = target - target.mean()
    denom = np.sqrt(np.sum(source_centered**2) * np.sum(target_centered**2))
    corr = float(np.sum(source_centered * target_centered) / denom) if denom > 0 else np.nan
    return (corr, similarity, mean_diff)


def _as_event_result(events: EventResult | xr.Dataset) -> EventResult:
    if isinstance(events, EventResult):
        return events
    raise TypeError("timing_synchrony and duration_synchrony require EventResult from detect_events")


def _event_window_end(events: EventResult) -> object:
    time_dim = "time" if "time" in events.dataset.dims else next(iter(events.dataset.dims))
    return events.dataset[time_dim].values[-1]
