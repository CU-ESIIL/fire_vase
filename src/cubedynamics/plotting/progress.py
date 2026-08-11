"""Notebook-friendly progress helpers for cube rendering."""

from __future__ import annotations

import sys


class _CubeProgress:
    """Simple progress helper that prints inline status updates."""

    def __init__(self, total: int, enabled: bool = True, style: str = "bar") -> None:
        self.total = max(int(total), 0)
        self.enabled = enabled
        self.style = style
        self.completed = 0
        self._last_msg: str | None = None
        if self.enabled:
            self._render(0.0)

    def _render(self, pct: float) -> str:
        pct_clamped = max(0.0, min(1.0, pct))
        pct_label = f"Preparing cube… {int(pct_clamped * 100):02d}%"
        sys.stdout.write("\r" + pct_label)
        sys.stdout.flush()
        self._last_msg = pct_label
        return pct_label

    def step(self) -> None:
        if not self.enabled:
            return
        self.completed += 1
        pct = self.completed / self.total if self.total else 1.0
        self._render(pct)

    def done(self) -> None:
        if not self.enabled:
            return
        self._render(1.0)
        sys.stdout.write("\n")
        sys.stdout.flush()


__all__ = ["_CubeProgress"]
