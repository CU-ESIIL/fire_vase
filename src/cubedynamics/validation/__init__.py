"""Modular validation tools for the Fire VASE data pipeline.

The validation package is intentionally separate from the production builders:
it reads their public outputs, recomputes small independent samples, and emits
human-inspectable QA artifacts plus machine-readable pass/fail summaries.
"""

from .core import QAResult, ValidationPaths
from .runner import run_validation_suite

__all__ = ["QAResult", "ValidationPaths", "run_validation_suite"]
