"""Processing manifest state machine for fire VASE runs."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Mapping

STATUSES = (
    "pending",
    "running",
    "geometry_complete",
    "climate_complete",
    "events_complete",
    "traits_complete",
    "assets_complete",
    "validated",
    "published",
    "failed",
)

ALLOWED_TRANSITIONS = {
    "pending": {"running", "failed"},
    "running": {"geometry_complete", "failed"},
    "geometry_complete": {"climate_complete", "failed"},
    "climate_complete": {"events_complete", "traits_complete", "failed"},
    "events_complete": {"traits_complete", "failed"},
    "traits_complete": {"assets_complete", "validated", "failed"},
    "assets_complete": {"validated", "failed"},
    "validated": {"published", "failed"},
    "published": set(),
    "failed": {"pending"},
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass(frozen=True)
class ProcessingRecord:
    fire_id: str
    run_id: str
    status: str = "pending"
    component_versions: Mapping[str, str] = field(default_factory=dict)
    attempts: int = 0
    failure_reason: str | None = None
    updated_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if self.status not in STATUSES:
            raise ValueError(f"Unknown manifest status: {self.status}")


def transition(
    record: ProcessingRecord,
    new_status: str,
    *,
    failure_reason: str | None = None,
) -> ProcessingRecord:
    if new_status not in STATUSES:
        raise ValueError(f"Unknown manifest status: {new_status}")
    if new_status not in ALLOWED_TRANSITIONS[record.status]:
        raise ValueError(f"Cannot transition {record.status!r} to {new_status!r}")
    attempts = record.attempts + 1 if record.status == "pending" and new_status == "running" else record.attempts
    return replace(
        record,
        status=new_status,
        attempts=attempts,
        failure_reason=failure_reason if new_status == "failed" else None,
        updated_at=_now_iso(),
    )


def retry_failed(record: ProcessingRecord) -> ProcessingRecord:
    if record.status != "failed":
        raise ValueError("Only failed records can be retried")
    return transition(record, "pending")
