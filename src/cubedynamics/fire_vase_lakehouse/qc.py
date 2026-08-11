"""QC flag helpers for fire VASE processing tasks."""

from __future__ import annotations

from typing import Any


def geometry_qc(
    *,
    area_km2: float | None,
    is_valid: bool,
    is_empty: bool,
    newly_added_geometry: bool = False,
) -> dict[str, Any]:
    flags: list[str] = []
    if is_empty:
        flags.append("empty_geometry")
    if not is_valid:
        flags.append("invalid_geometry")
    if area_km2 is None or area_km2 <= 0:
        flags.append("nonpositive_area")
    if newly_added_geometry:
        flags.append("newly_added_geometry")
    return {"passed": not flags, "flags": flags}


def climate_qc(*, observed_steps: int, expected_steps: int, variable: str) -> dict[str, Any]:
    flags: list[str] = []
    if expected_steps <= 0:
        flags.append("invalid_expected_steps")
    elif observed_steps < expected_steps:
        missing_fraction = 1 - (observed_steps / expected_steps)
        if missing_fraction > 0.05:
            flags.append(f"{variable}_missing_gt_5pct")
        elif missing_fraction > 0:
            flags.append(f"{variable}_missing_le_5pct")
    return {"passed": not any(flag.endswith("gt_5pct") for flag in flags), "flags": flags}


def task_qc(task: str, metrics: dict[str, Any]) -> dict[str, Any]:
    """Dispatch simple task-specific QC without coupling to storage engines."""

    if task == "geometry":
        return geometry_qc(
            area_km2=metrics.get("area_km2"),
            is_valid=bool(metrics.get("is_valid", False)),
            is_empty=bool(metrics.get("is_empty", True)),
            newly_added_geometry=bool(metrics.get("newly_added_geometry", False)),
        )
    if task == "climate":
        return climate_qc(
            observed_steps=int(metrics.get("observed_steps", 0)),
            expected_steps=int(metrics.get("expected_steps", 0)),
            variable=str(metrics.get("variable", "unknown")),
        )
    raise ValueError(f"Unknown QC task: {task}")
