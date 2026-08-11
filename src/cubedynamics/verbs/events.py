"""Pipe-friendly event verbs."""

from __future__ import annotations

from ..events.detection import detect_events as _detect_events


def detect_events(
    *,
    state_var: str = "state",
    magnitude_var: str = "magnitude",
    min_duration: int = 1,
    max_gap: int = 0,
):
    """Summary
    Detect contiguous state runs as events.

    Grammar contract
    State Dataset -> EventResult containing event cube variables and a catalog.
    """

    def _op(obj):
        return _detect_events(
            obj,
            state_var=state_var,
            magnitude_var=magnitude_var,
            min_duration=min_duration,
            max_gap=max_gap,
        )

    return _op


__all__ = ["detect_events"]
