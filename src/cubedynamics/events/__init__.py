"""Event construction and matching utilities."""

from .detection import detect_events
from .schemas import EventResult

__all__ = ["EventResult", "detect_events"]
