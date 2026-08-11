"""Safeguards ensuring Tier A APIs keep docstrings present."""

from __future__ import annotations

import types
from collections.abc import Iterator

import pytest

import cubedynamics.verbs as verbs
import cubedynamics.variables as variables
from cubedynamics.data import gridmet, prism


def _iter_public_callables(module: types.ModuleType) -> Iterator[tuple[str, object]]:
    for name, obj in vars(module).items():
        if name.startswith("_"):
            continue
        if callable(obj):
            yield name, obj


@pytest.mark.parametrize(
    "module",
    [verbs, variables, gridmet, prism],
    ids=lambda module: module.__name__,
)
def test_public_callables_have_docstrings(module: types.ModuleType) -> None:
    missing = []
    for name, obj in _iter_public_callables(module):
        if obj.__doc__ is None or not str(obj.__doc__).strip():
            missing.append(name)

    assert not missing, f"Missing docstrings in {module.__name__}: {', '.join(sorted(missing))}"
