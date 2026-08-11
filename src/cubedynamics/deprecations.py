"""Helpers for emitting consistent deprecation warnings.

This module centralizes deprecation messaging so legacy entry points can warn
without changing their behavior. Use ``DeprecationWarning`` with a ``stacklevel``
of 2 so the warning points at user code instead of the library.
"""

from __future__ import annotations

import warnings


def warn_deprecated(old_name: str, new_name: str, *, since: str, removal: str | None = None) -> None:
    """Issue a standardized :class:`DeprecationWarning` for a legacy symbol.

    Parameters
    ----------
    old_name:
        The dotted path or human-readable name of the deprecated entry point.
    new_name:
        The recommended replacement to direct users toward.
    since:
        Version where the deprecation was introduced.
    removal:
        Optional version string indicating when the legacy symbol may be
        removed.
    """

    message = f"{old_name} is deprecated as of {since}; use {new_name} instead."
    if removal:
        message += f" This alias will be removed in {removal}."

    warnings.warn(message, DeprecationWarning, stacklevel=2)
