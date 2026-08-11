"""Public event result schema."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import xarray as xr


@dataclass(frozen=True)
class EventResult:
    """Detected event cube plus a separate tabular event catalog."""

    dataset: xr.Dataset
    catalog: pd.DataFrame

    def unwrap(self) -> xr.Dataset:
        """Return the cube-form event Dataset."""

        return self.dataset
