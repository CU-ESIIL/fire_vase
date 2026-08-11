from __future__ import annotations

"""Wrapper for GRIDMET loading used by the public API.

This module intentionally re-exports the existing GRIDMET loader that includes
both the real streaming backend and the synthetic fallback used during
prototyping and tests. Having a dedicated module allows the public-facing API
in :mod:`gridmet_api` to remain stable even if the underlying loader changes.
"""

from ..data.gridmet import load_gridmet_cube

__all__ = ["load_gridmet_cube"]
