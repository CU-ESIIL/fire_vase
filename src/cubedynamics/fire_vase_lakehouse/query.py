"""Small in-memory query helpers mirroring common lakehouse summaries."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from math import sqrt
from statistics import median
from typing import Any


def select_cohort(records: Sequence[Mapping[str, Any]], **filters: Any) -> list[Mapping[str, Any]]:
    cohort: list[Mapping[str, Any]] = []
    for record in records:
        keep = True
        for key, expected in filters.items():
            if callable(expected):
                keep = bool(expected(record.get(key)))
            elif isinstance(expected, (set, tuple, list)):
                keep = record.get(key) in expected
            else:
                keep = record.get(key) == expected
            if not keep:
                break
        if keep:
            cohort.append(record)
    return cohort


def _distance(left: Mapping[str, Any], right: Mapping[str, Any], columns: Sequence[str]) -> float:
    total = 0.0
    for column in columns:
        total += (float(left[column]) - float(right[column])) ** 2
    return sqrt(total)


def medoid_by_traits(records: Sequence[Mapping[str, Any]], trait_columns: Sequence[str]) -> Mapping[str, Any]:
    if not records:
        raise ValueError("records must not be empty")
    if len(records) == 1:
        return records[0]
    best = records[0]
    best_distance = float("inf")
    for candidate in records:
        distance = sum(_distance(candidate, other, trait_columns) for other in records)
        if distance < best_distance:
            best = candidate
            best_distance = distance
    return best


def event_aligned_quantiles(
    records: Sequence[Mapping[str, Any]],
    *,
    value_column: str,
    offset_column: str = "event_offset_hours",
    quantiles: Sequence[float] = (0.1, 0.5, 0.9),
) -> list[dict[str, Any]]:
    grouped: dict[Any, list[float]] = defaultdict(list)
    for record in records:
        if record.get(value_column) is None or record.get(offset_column) is None:
            continue
        grouped[record[offset_column]].append(float(record[value_column]))
    output: list[dict[str, Any]] = []
    for offset in sorted(grouped):
        values = sorted(grouped[offset])
        row = {offset_column: offset, "count": len(values)}
        for quantile in quantiles:
            if quantile == 0.5:
                value = median(values)
            else:
                index = round((len(values) - 1) * quantile)
                value = values[index]
            row[f"q{int(quantile * 100):02d}"] = value
        output.append(row)
    return output
