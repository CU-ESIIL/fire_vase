"""Lightweight schema validation for fire VASE lakehouse tables."""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

SCHEMA_DIR = Path(__file__).resolve().parents[3] / "schemas"


def load_schema(table: str, *, schema_dir: str | Path | None = None) -> dict[str, Any]:
    path = Path(schema_dir) if schema_dir is not None else SCHEMA_DIR
    schema_path = path / f"{table}.schema.json"
    if not schema_path.exists():
        raise FileNotFoundError(f"Missing schema for table {table!r}: {schema_path}")
    return json.loads(schema_path.read_text(encoding="utf-8"))


def _type_matches(value: Any, expected: str) -> bool:
    if value is None:
        return True
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "object":
        return isinstance(value, Mapping)
    if expected == "array":
        return isinstance(value, list)
    return True


def validate_records(records: Iterable[Mapping[str, Any]], schema: Mapping[str, Any]) -> list[str]:
    """Validate records against the repository table schema format."""

    errors: list[str] = []
    columns = schema.get("columns", {})
    required = set(schema.get("required", []))
    for row_index, record in enumerate(records):
        missing = required.difference(record)
        for column in sorted(missing):
            errors.append(f"row {row_index}: missing required column {column!r}")
        for column, value in record.items():
            if column not in columns:
                continue
            expected = columns[column].get("type", "any")
            if not _type_matches(value, expected):
                errors.append(
                    f"row {row_index}: column {column!r} expected {expected}, got {type(value).__name__}"
                )
    return errors
