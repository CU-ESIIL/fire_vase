"""Basic import and pipe integration tests for cubedynamics."""

import numpy as np
import xarray as xr

from cubedynamics import pipe, verbs as v


def test_pipe_anomaly_variance_chain():
    """Smoke-test chaining simple pipe verbs if available."""

    da = xr.DataArray(
        np.arange(6),
        dims=["time"],
        coords={"time": np.arange(6)},
    )

    if pipe is None or v.anomaly is None or v.variance is None:
        return

    result = pipe(da) | v.anomaly(dim="time") | v.variance(dim="time")

    out = getattr(result, "unwrap", lambda: result)()
    assert isinstance(out, xr.DataArray)
