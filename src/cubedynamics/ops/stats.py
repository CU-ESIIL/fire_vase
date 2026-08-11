"""Statistical pipeable operations."""

from __future__ import annotations

import xarray as xr

from ..config import STD_EPS
from ..deprecations import warn_deprecated
from ..verbs import stats as _verbs_stats


def correlation_cube(other: xr.DataArray | xr.Dataset | None, dim: str = "time"):
    """Factory placeholder for a future correlation cube operation.

    Parameters
    ----------
    other:
        The comparison cube captured by the factory.
    dim:
        Dimension over which correlations would be computed once implemented.
    """

    if other is None or not isinstance(dim, str):
        raise NotImplementedError("correlation_cube is not implemented yet.")

    def _inner(da: xr.DataArray | xr.Dataset):  # pragma: no cover - stub
        raise NotImplementedError("correlation_cube is not implemented yet.")

    return _inner


def anomaly(dim: str = "time", *, keep_dim: bool = True):
    """Deprecated. Use :func:`cubedynamics.verbs.anomaly` instead.

    This shim exists for backward compatibility and forwards to the canonical
    verb implementation.
    """

    warn_deprecated(
        "cubedynamics.ops.stats.anomaly",
        "cubedynamics.verbs.anomaly",
        since="0.2.0",
        removal="0.3.0",
    )
    return _verbs_stats.anomaly(dim=dim, keep_dim=keep_dim)


def mean(dim: str = "time", *, keep_dim: bool = False):
    """Deprecated. Use :func:`cubedynamics.verbs.mean` instead.

    This shim exists for backward compatibility and forwards to the canonical
    reducer verb.
    """

    warn_deprecated(
        "cubedynamics.ops.stats.mean",
        "cubedynamics.verbs.mean",
        since="0.2.0",
        removal="0.3.0",
    )
    return _verbs_stats.mean(dim=dim, keep_dim=keep_dim)


def variance(dim: str = "time", *, keep_dim: bool = False):
    """Deprecated. Use :func:`cubedynamics.verbs.variance` instead.

    This shim exists for backward compatibility and forwards to the canonical
    reducer verb.
    """

    warn_deprecated(
        "cubedynamics.ops.stats.variance",
        "cubedynamics.verbs.variance",
        since="0.2.0",
        removal="0.3.0",
    )
    return _verbs_stats.variance(dim=dim, keep_dim=keep_dim)


def zscore(
    dim: str = "time",
    *,
    keep_dim: bool = True,
    std_eps: float = STD_EPS,
    skipna: bool | None = True,
):
    """Deprecated. Use :func:`cubedynamics.verbs.zscore` instead.

    This wrapper exists for backward compatibility and forwards keyword
    arguments to the canonical verb implementation so callers relying on the
    legacy ``std_eps`` parameter continue to work.
    """

    warn_deprecated(
        "cubedynamics.ops.stats.zscore",
        "cubedynamics.verbs.zscore",
        since="0.2.0",
        removal="0.3.0",
    )
    return _verbs_stats.zscore(dim=dim, keep_dim=keep_dim, std_eps=std_eps, skipna=skipna)


__all__ = ["anomaly", "mean", "variance", "correlation_cube", "zscore"]
