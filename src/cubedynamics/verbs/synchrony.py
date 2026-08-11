"""Pipe-friendly synchrony verbs."""

from __future__ import annotations

from ..synchrony.coupling import sync_with as _sync_with
from ..synchrony.occurrence import occurrence_synchrony as _occurrence_synchrony
from ..synchrony.severity import severity_synchrony as _severity_synchrony
from ..synchrony.timing import duration_synchrony as _duration_synchrony
from ..synchrony.timing import timing_synchrony as _timing_synchrony


def occurrence_synchrony(
    *,
    spatial_mode: str = "neighbors",
    radius_km: float | None = None,
    k_neighbors: int | None = None,
    reference=None,
    method: str = "jaccard",
    window: int | str | None = None,
    stride: int | str | None = None,
    state_var: str = "state",
):
    """Summary
    Measure whether states occur at the same times across locations.

    Grammar contract
    State cube -> synchrony Dataset. Reference/neighborhood modes return maps;
    all-pairs returns edge data; regional returns time-series summaries.
    """

    def _op(obj):
        return _occurrence_synchrony(
            obj,
            state_var=state_var,
            spatial_mode=spatial_mode,
            radius_km=radius_km,
            k_neighbors=k_neighbors,
            reference=reference,
            method=method,
            window=window,
            stride=stride,
        )

    return _op


def severity_synchrony(
    *,
    magnitude_var: str = "magnitude",
    state_var: str = "state",
    condition: str = "joint",
    method: str = "spearman",
    spatial_mode: str = "neighbors",
    radius_km: float | None = None,
    k_neighbors: int | None = None,
    reference=None,
    min_joint_events: int = 10,
    window: int | str | None = None,
    stride: int | str | None = None,
):
    """Summary
    Measure magnitude co-variation during jointly active states.

    Grammar contract
    State cube -> synchrony Dataset with joint-observation diagnostics.
    """

    def _op(obj):
        return _severity_synchrony(
            obj,
            state_var=state_var,
            magnitude_var=magnitude_var,
            condition=condition,
            method=method,
            spatial_mode=spatial_mode,
            radius_km=radius_km,
            k_neighbors=k_neighbors,
            reference=reference,
            min_joint_events=min_joint_events,
            window=window,
            stride=stride,
        )

    return _op


def timing_synchrony(
    *,
    event_anchor: str = "start",
    match_tolerance: str | int = "7D",
    score: str = "exponential",
    timescale: str | int = "3D",
    spatial_mode: str = "neighbors",
    radius_km: float | None = None,
    k_neighbors: int | None = None,
    reference=None,
):
    """Summary
    Measure whether one-to-one matched events happen at similar times.

    Grammar contract
    EventResult -> synchrony Dataset with lag and unmatched-event diagnostics.
    """

    def _op(obj):
        return _timing_synchrony(
            obj,
            event_anchor=event_anchor,
            match_tolerance=match_tolerance,
            score=score,
            timescale=timescale,
            spatial_mode=spatial_mode,
            radius_km=radius_km,
            k_neighbors=k_neighbors,
            reference=reference,
        )

    return _op


def duration_synchrony(
    *,
    match_on: str = "overlap",
    match_tolerance: str | int = "7D",
    method: str = "spearman",
    spatial_mode: str = "neighbors",
    radius_km: float | None = None,
    k_neighbors: int | None = None,
    reference=None,
    min_matched_events: int = 3,
):
    """Summary
    Compare durations of one-to-one matched events.

    Grammar contract
    EventResult -> synchrony Dataset with duration and match diagnostics.
    """

    def _op(obj):
        return _duration_synchrony(
            obj,
            match_on=match_on,
            match_tolerance=match_tolerance,
            method=method,
            spatial_mode=spatial_mode,
            radius_km=radius_km,
            k_neighbors=k_neighbors,
            reference=reference,
            min_matched_events=min_matched_events,
        )

    return _op


def sync_with(
    other,
    *,
    synchrony: str = "occurrence",
    spatial_relation: str = "same_pixel",
    lags=("0D",),
    state_var: str = "state",
):
    """Summary
    Compare one aligned state cube with another.

    Grammar contract
    State cube + aligned state cube -> coupling Dataset.
    """

    def _op(obj):
        return _sync_with(
            obj,
            other,
            synchrony=synchrony,
            spatial_relation=spatial_relation,
            lags=lags,
            state_var=state_var,
        )

    return _op


__all__ = [
    "duration_synchrony",
    "occurrence_synchrony",
    "severity_synchrony",
    "sync_with",
    "timing_synchrony",
]
