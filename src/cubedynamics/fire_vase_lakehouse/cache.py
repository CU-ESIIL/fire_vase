"""Deterministic identities for fire VASE derived products."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import asdict, is_dataclass
from typing import Any

COMPONENT_ORDER = (
    "source",
    "geometry",
    "climate",
    "events",
    "traits",
    "vase",
    "render",
)

DEPENDENCIES = {
    "source": {"source", "geometry", "climate", "events", "traits", "vase", "render"},
    "geometry": {"geometry", "climate", "events", "traits", "vase", "render"},
    "climate": {"climate", "events", "traits", "vase", "render"},
    "events": {"events", "traits", "vase", "render"},
    "traits": {"traits", "vase", "render"},
    "vase": {"vase", "render"},
    "render": {"render"},
}


def _normalize(value: Any) -> Any:
    if is_dataclass(value):
        return _normalize(asdict(value))
    if isinstance(value, Mapping):
        return {str(key): _normalize(value[key]) for key in sorted(value)}
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray, str)):
        return [_normalize(item) for item in value]
    return str(value)


def stable_json(value: Any) -> str:
    """Serialize values with deterministic key ordering and separators."""

    return json.dumps(_normalize(value), sort_keys=True, separators=(",", ":"))


def content_hash(value: Any, *, length: int = 16) -> str:
    digest = hashlib.sha256(stable_json(value).encode("utf-8")).hexdigest()
    return digest[:length]


def build_cache_key(
    component: str,
    *,
    identity: Mapping[str, Any],
    versions: Mapping[str, Any],
    inputs: Mapping[str, Any] | None = None,
) -> str:
    """Build a content-addressed key for a versioned component."""

    payload = {
        "component": component,
        "identity": identity,
        "versions": versions,
        "inputs": inputs or {},
    }
    return f"{component}:{content_hash(payload, length=24)}"


def geometry_key(
    fire_id: str,
    *,
    source_geometry_hash: str,
    geometry_version: str,
    geometry_method: str = "canonical_fire_time_geometry",
) -> str:
    return build_cache_key(
        "geometry",
        identity={"fire_id": fire_id},
        versions={"geometry": geometry_version},
        inputs={"method": geometry_method, "source_geometry_hash": source_geometry_hash},
    )


def climate_key(
    fire_id: str,
    *,
    geometry_cache_key: str,
    climate_source: str,
    variables: Sequence[str],
    temporal_resolution: str,
    climate_version: str,
) -> str:
    return build_cache_key(
        "climate",
        identity={"fire_id": fire_id},
        versions={"climate": climate_version},
        inputs={
            "climate_source": climate_source,
            "geometry_cache_key": geometry_cache_key,
            "temporal_resolution": temporal_resolution,
            "variables": sorted(variables),
        },
    )


def event_key(
    fire_id: str,
    *,
    climate_cache_key: str,
    event_version: str,
    method: str,
    parameters: Mapping[str, Any],
) -> str:
    return build_cache_key(
        "events",
        identity={"fire_id": fire_id},
        versions={"events": event_version},
        inputs={
            "climate_cache_key": climate_cache_key,
            "method": method,
            "parameters": parameters,
        },
    )


def vase_key(
    fire_id: str,
    *,
    geometry_cache_key: str,
    climate_cache_key: str,
    vase_version: str,
    parameters: Mapping[str, Any],
) -> str:
    return build_cache_key(
        "vase",
        identity={"fire_id": fire_id},
        versions={"vase": vase_version},
        inputs={
            "climate_cache_key": climate_cache_key,
            "geometry_cache_key": geometry_cache_key,
            "parameters": parameters,
        },
    )


def render_key(
    fire_id: str,
    *,
    vase_cache_key: str,
    render_version: str,
    asset_type: str,
    parameters: Mapping[str, Any] | None = None,
) -> str:
    return build_cache_key(
        "render",
        identity={"fire_id": fire_id, "asset_type": asset_type},
        versions={"render": render_version},
        inputs={"parameters": parameters or {}, "vase_cache_key": vase_cache_key},
    )


def invalidated_components(changed_components: Sequence[str]) -> tuple[str, ...]:
    """Return downstream components that must be rebuilt after version changes."""

    invalidated: set[str] = set()
    for component in changed_components:
        if component not in DEPENDENCIES:
            raise ValueError(f"Unknown component: {component}")
        invalidated.update(DEPENDENCIES[component])
    return tuple(component for component in COMPONENT_ORDER if component in invalidated)
