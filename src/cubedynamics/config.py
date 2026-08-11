"""Global configuration constants for :mod:`cubedynamics`."""

from __future__ import annotations

from typing import Mapping

TIME_DIM: str = "time"
Y_DIM: str = "y"
X_DIM: str = "x"
BAND_DIM: str = "band"
STD_EPS: float = 1e-4
DEFAULT_CHUNKS: Mapping[str, int] = {"time": -1, "y": 256, "x": 256}
