"""Lightweight progress bar utilities.

This module intentionally keeps the dependency surface minimal by using
``tqdm.auto`` when available and falling back to no-op stubs otherwise. The
``progress_bar`` context manager is the public entry point.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Callable, Iterator, Optional

try:  # pragma: no cover - exercised via mocking in tests
    from tqdm.auto import tqdm  # type: ignore
except ImportError:  # pragma: no cover - fallback path
    tqdm = None


@contextmanager
def progress_bar(total: Optional[int] = None, description: str = "") -> Iterator[Callable[[int], None]]:
    """Context manager that yields an ``advance(n)`` function.

    Parameters
    ----------
    total : int, optional
        Optional total count for the progress bar. When omitted or when ``tqdm``
        is not installed, progress updates become no-ops.
    description : str, default ""
        Short description displayed alongside the progress bar.
    """

    if tqdm is None or total is None:
        # No-op fallback
        def advance(_n: int = 1) -> None:
            return

        yield advance
        return

    with tqdm(total=total, desc=description) as bar:  # type: ignore[operator]
        def advance(n: int = 1) -> None:
            bar.update(n)

        yield advance

