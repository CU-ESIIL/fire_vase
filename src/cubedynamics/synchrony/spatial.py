"""Spatial pair selection and shared synchrony utilities."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Iterable, Sequence

import numpy as np
import xarray as xr

from ..config import TIME_DIM, X_DIM, Y_DIM
from ..utils.reference import center_pixel_indices


@dataclass(frozen=True)
class SpatialPair:
    """One directed or undirected comparison edge."""

    source: int
    target: int
    distance: float


@dataclass(frozen=True)
class SpatialPairSet:
    """Pair-selection result for synchrony operators."""

    mode: str
    spatial_dims: tuple[str, str]
    pairs: tuple[SpatialPair, ...]
    source_index: tuple[int, ...]
    target_index: tuple[int, ...]
    source_labels: tuple[str, ...]
    target_labels: tuple[str, ...]
    distances: tuple[float, ...]
    reference_index: int | None = None


def infer_spatial_dims(obj: xr.Dataset | xr.DataArray) -> tuple[str, str]:
    """Infer the canonical two spatial dimensions from a cube-like object."""

    dims = tuple(obj.dims)
    if Y_DIM in dims and X_DIM in dims:
        return (Y_DIM, X_DIM)
    candidates = [dim for dim in dims if dim != TIME_DIM and not dim.endswith("_window_end")]
    if len(candidates) == 2:
        return (str(candidates[0]), str(candidates[1]))
    raise ValueError(
        "Could not infer exactly two spatial dimensions; pass a cube with "
        f"{Y_DIM!r} and {X_DIM!r}. Available dims: {dims!r}"
    )


def stack_space(
    da: xr.DataArray,
    *,
    spatial_dims: Sequence[str] | None = None,
    space_dim: str = "space",
) -> xr.DataArray:
    """Stack spatial dimensions into one ``space`` dimension."""

    y_dim, x_dim = tuple(spatial_dims) if spatial_dims is not None else infer_spatial_dims(da)
    return da.stack({space_dim: (y_dim, x_dim)})


def unstack_space(da: xr.DataArray, *, space_dim: str = "space") -> xr.DataArray:
    """Unstack a DataArray with a MultiIndex space dimension if possible."""

    if space_dim in da.dims:
        try:
            return da.unstack(space_dim)
        except ValueError:
            return da
    return da


def build_spatial_pairs(
    cube: xr.Dataset | xr.DataArray,
    *,
    mode: str = "neighbors",
    radius_km: float | None = None,
    k_neighbors: int | None = None,
    reference: str | tuple[int, int] | int | None = None,
    blocks: xr.Dataset | None = None,
) -> SpatialPairSet:
    """Select spatial comparison pairs for synchrony operators.

    Supported modes are ``reference``, ``neighbors``, ``all_pairs``,
    ``regional``, and ``blocks``. ``blocks`` expects an object that already has
    a ``block`` dimension and is mainly an adapter hook for ``compare_blocks``.
    """

    if mode not in {"reference", "neighbors", "all_pairs", "regional", "blocks"}:
        raise ValueError(
            "mode must be one of 'reference', 'neighbors', 'all_pairs', 'regional', or 'blocks'"
        )
    if mode == "blocks":
        if blocks is None and "block" not in cube.dims:
            raise ValueError("blocks mode requires a block collection or block dimension")
        labels = tuple(str(v) for v in cube["block"].values)
        pairs = tuple(
            SpatialPair(i, j, float("nan")) for i, j in combinations(range(len(labels)), 2)
        )
        return SpatialPairSet(
            mode=mode,
            spatial_dims=("block", "block"),
            pairs=pairs,
            source_index=tuple(p.source for p in pairs),
            target_index=tuple(p.target for p in pairs),
            source_labels=tuple(labels[p.source] for p in pairs),
            target_labels=tuple(labels[p.target] for p in pairs),
            distances=tuple(p.distance for p in pairs),
        )

    spatial_dims = infer_spatial_dims(cube)
    y_dim, x_dim = spatial_dims
    y_size = int(cube.sizes[y_dim])
    x_size = int(cube.sizes[x_dim])
    n_space = y_size * x_size
    coords = _space_coordinates(cube, spatial_dims)

    if mode == "reference":
        ref_idx = _reference_index(cube, spatial_dims, reference)
        pairs = tuple(
            SpatialPair(i, ref_idx, _distance(coords[i], coords[ref_idx]))
            for i in range(n_space)
        )
    else:
        pairs_list: list[SpatialPair] = []
        for i, j in combinations(range(n_space), 2):
            distance = _distance(coords[i], coords[j])
            if mode == "neighbors":
                if radius_km is not None and distance > radius_km:
                    continue
                pairs_list.append(SpatialPair(i, j, distance))
            else:
                pairs_list.append(SpatialPair(i, j, distance))
        if mode == "neighbors" and k_neighbors is not None:
            pairs_list = _limit_k_neighbors(pairs_list, n_space, k_neighbors)
        pairs = tuple(pairs_list)
        ref_idx = None

    labels = _space_labels(cube, spatial_dims)
    return SpatialPairSet(
        mode=mode,
        spatial_dims=spatial_dims,
        pairs=pairs,
        source_index=tuple(p.source for p in pairs),
        target_index=tuple(p.target for p in pairs),
        source_labels=tuple(labels[p.source] for p in pairs),
        target_labels=tuple(labels[p.target] for p in pairs),
        distances=tuple(p.distance for p in pairs),
        reference_index=ref_idx,
    )


def time_windows(
    obj: xr.Dataset | xr.DataArray,
    *,
    window: int | str | None = None,
    stride: int | str | None = None,
    time_dim: str = TIME_DIM,
) -> list[tuple[object, xr.Dataset | xr.DataArray]]:
    """Return window-end labels and sliced objects."""

    if time_dim not in obj.dims:
        raise ValueError(f"Synchrony requires time dimension {time_dim!r}")
    times = obj[time_dim].values
    if len(times) == 0:
        raise ValueError("Synchrony requires at least one time step")
    if window is None:
        return [(times[-1], obj)]

    step = _stride_indices(times, stride)
    out: list[tuple[object, xr.Dataset | xr.DataArray]] = []
    if isinstance(window, int) and not np.issubdtype(times.dtype, np.datetime64):
        for end_idx in range(0, len(times), step):
            start_idx = max(0, end_idx - window + 1)
            out.append((times[end_idx], obj.isel({time_dim: slice(start_idx, end_idx + 1)})))
        return out

    window_delta = _window_to_timedelta(window)
    for end_idx in range(0, len(times), step):
        t_end = times[end_idx]
        t_start = t_end - window_delta
        out.append((t_end, obj.sel({time_dim: slice(t_start, t_end)})))
    return out


def pairwise_edge_dataset(
    values: Sequence[xr.DataArray],
    *,
    var_name: str,
    pairs: SpatialPairSet,
    time_window_end: object,
    extra_vars: dict[str, Sequence[xr.DataArray]] | None = None,
) -> xr.Dataset:
    """Build a ``(time_window_end, pair)`` edge Dataset."""

    pair_coord = np.arange(len(values))
    cleaned_values = [_clean_scalar_array(value) for value in values]
    if values:
        data = xr.concat(cleaned_values, dim="pair").expand_dims({"time_window_end": [time_window_end]})
    else:
        data = xr.DataArray(
            np.empty((1, 0), dtype=float),
            dims=("time_window_end", "pair"),
            coords={"time_window_end": [time_window_end], "pair": pair_coord},
        )
    data = data.assign_coords(pair=pair_coord).rename(var_name)
    ds = xr.Dataset({var_name: data})
    ds = ds.assign_coords(
        source=("pair", np.asarray(pairs.source_labels, dtype=object)),
        target=("pair", np.asarray(pairs.target_labels, dtype=object)),
        distance=("pair", np.asarray(pairs.distances, dtype=float)),
    )
    if extra_vars:
        for name, arrays in extra_vars.items():
            cleaned_arrays = [_clean_scalar_array(array) for array in arrays]
            if arrays:
                arr = xr.concat(cleaned_arrays, dim="pair").expand_dims(
                    {"time_window_end": [time_window_end]}
                )
            else:
                arr = xr.DataArray(
                    np.empty((1, 0), dtype=float),
                    dims=("time_window_end", "pair"),
                    coords={"time_window_end": [time_window_end], "pair": pair_coord},
                )
            ds[name] = arr.assign_coords(pair=pair_coord)
    return ds


def _clean_scalar_array(value: xr.DataArray) -> xr.DataArray:
    """Drop non-dimension coords from scalar pair metrics before concat."""

    return value.reset_coords(drop=True)


def edge_to_map(
    edge: xr.Dataset,
    *,
    metric_var: str,
    template: xr.DataArray,
    pairs: SpatialPairSet,
    time_window_end: object,
    count_var: str | None = None,
) -> xr.Dataset:
    """Aggregate edge values back to a cube-like spatial map."""

    spatial_dims = pairs.spatial_dims
    y_dim, x_dim = spatial_dims
    shape = (int(template.sizes[y_dim]), int(template.sizes[x_dim]))
    coords = {dim: template.coords[dim] for dim in spatial_dims if dim in template.coords}
    ds = xr.Dataset()
    for name in edge.data_vars:
        values = np.full(shape, np.nan, dtype=float)
        counts = np.zeros(shape, dtype=float)
        sums = np.zeros(shape, dtype=float)
        edge_vals = np.asarray(edge[name].isel(time_window_end=0).values, dtype=float)
        for idx, pair in enumerate(pairs.pairs):
            if not np.isfinite(edge_vals[idx]):
                continue
            for flat in {pair.source, pair.target}:
                y_idx, x_idx = divmod(flat, shape[1])
                sums[y_idx, x_idx] += edge_vals[idx]
                counts[y_idx, x_idx] += 1
        valid = counts > 0
        values[valid] = sums[valid] / counts[valid]
        ds[name] = xr.DataArray(values, dims=spatial_dims, coords=coords).expand_dims(
            {"time_window_end": [time_window_end]}
        )
    if count_var and count_var not in ds:
        ds[count_var] = xr.DataArray(
            np.zeros(shape, dtype=float), dims=spatial_dims, coords=coords
        ).expand_dims({"time_window_end": [time_window_end]})
    return ds


def regional_summary(
    edge: xr.Dataset,
    *,
    metric_var: str,
    time_window_end: object,
) -> xr.Dataset:
    """Summarize an edge Dataset into regional time-series statistics."""

    metric = edge[metric_var].isel(time_window_end=0)
    ds = xr.Dataset(
        {
            f"mean_{metric_var}": metric.mean(dim="pair", skipna=True).expand_dims(
                {"time_window_end": [time_window_end]}
            ),
            f"median_{metric_var}": metric.median(dim="pair", skipna=True).expand_dims(
                {"time_window_end": [time_window_end]}
            ),
            "pair_count": xr.DataArray(
                [edge.sizes.get("pair", 0)], dims=("time_window_end",), coords={"time_window_end": [time_window_end]}
            ),
        }
    )
    if "distance" in edge.coords:
        ds["mean_pair_distance"] = xr.DataArray(
            [float(np.nanmean(edge["distance"].values)) if edge.sizes.get("pair", 0) else np.nan],
            dims=("time_window_end",),
            coords={"time_window_end": [time_window_end]},
        )
    return ds


def _reference_index(
    cube: xr.Dataset | xr.DataArray,
    spatial_dims: tuple[str, str],
    reference: str | tuple[int, int] | int | None,
) -> int:
    y_dim, x_dim = spatial_dims
    if reference in (None, "center"):
        y_idx, x_idx = center_pixel_indices(cube)
        return int(y_idx) * int(cube.sizes[x_dim]) + int(x_idx)
    if isinstance(reference, int):
        return reference
    if isinstance(reference, tuple) and len(reference) == 2:
        y_idx, x_idx = reference
        if not (0 <= y_idx < cube.sizes[y_dim] and 0 <= x_idx < cube.sizes[x_dim]):
            raise ValueError("reference pixel indices are outside the cube")
        return int(y_idx) * int(cube.sizes[x_dim]) + int(x_idx)
    raise ValueError("reference must be 'center', a flat integer index, or (y_index, x_index)")


def _space_coordinates(
    cube: xr.Dataset | xr.DataArray,
    spatial_dims: tuple[str, str],
) -> list[tuple[float, float]]:
    y_dim, x_dim = spatial_dims
    y_vals = np.asarray(cube.coords[y_dim].values if y_dim in cube.coords else np.arange(cube.sizes[y_dim]), dtype=float)
    x_vals = np.asarray(cube.coords[x_dim].values if x_dim in cube.coords else np.arange(cube.sizes[x_dim]), dtype=float)
    return [(float(y), float(x)) for y in y_vals for x in x_vals]


def _space_labels(
    cube: xr.Dataset | xr.DataArray,
    spatial_dims: tuple[str, str],
) -> list[str]:
    y_dim, x_dim = spatial_dims
    coords = _space_coordinates(cube, spatial_dims)
    return [f"{y_dim}={y:g},{x_dim}={x:g}" for y, x in coords]


def _distance(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Return approximate distance in km for lon/lat-like coords, else Euclidean."""

    y1, x1 = a
    y2, x2 = b
    if all(abs(v) <= 180 for v in (x1, x2)) and all(abs(v) <= 90 for v in (y1, y2)):
        lat1 = np.deg2rad(y1)
        lat2 = np.deg2rad(y2)
        dlat = lat2 - lat1
        dlon = np.deg2rad(x2 - x1)
        h = np.sin(dlat / 2.0) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2.0) ** 2
        return float(6371.0088 * 2.0 * np.arcsin(np.sqrt(h)))
    return float(np.sqrt((y2 - y1) ** 2 + (x2 - x1) ** 2))


def _limit_k_neighbors(
    pairs: Iterable[SpatialPair],
    n_space: int,
    k_neighbors: int,
) -> list[SpatialPair]:
    if k_neighbors < 1:
        raise ValueError("k_neighbors must be at least 1")
    by_source: dict[int, list[SpatialPair]] = {i: [] for i in range(n_space)}
    distance_by_pair: dict[tuple[int, int], float] = {}
    for pair in pairs:
        distance_by_pair[tuple(sorted((pair.source, pair.target)))] = pair.distance
        by_source[pair.source].append(pair)
        by_source[pair.target].append(SpatialPair(pair.target, pair.source, pair.distance))
    selected: set[tuple[int, int]] = set()
    for source, source_pairs in by_source.items():
        for pair in sorted(source_pairs, key=lambda p: p.distance)[:k_neighbors]:
            selected.add(tuple(sorted((source, pair.target))))
    return [SpatialPair(i, j, distance_by_pair[(i, j)]) for i, j in sorted(selected)]


def _stride_indices(times: np.ndarray, stride: int | str | None) -> int:
    if stride is None:
        return 1
    if isinstance(stride, int):
        if stride < 1:
            raise ValueError("stride must be at least 1")
        return stride
    if not np.issubdtype(times.dtype, np.datetime64):
        raise ValueError("string stride requires datetime64 time coordinates")
    delta = _window_to_timedelta(stride)
    diffs = np.diff(times.astype("datetime64[ns]"))
    if diffs.size == 0:
        return 1
    step_ns = int(np.median(diffs).astype("timedelta64[ns]").astype(np.int64))
    delta_ns = int(delta.astype("timedelta64[ns]").astype(np.int64))
    return max(1, int(round(delta_ns / step_ns)))


def _window_to_timedelta(window: int | str) -> np.timedelta64:
    if isinstance(window, int):
        if window < 1:
            raise ValueError("window must be positive")
        return np.timedelta64(window, "D")
    text = window.strip().upper()
    if text.endswith("D"):
        return np.timedelta64(int(text[:-1]), "D")
    if text.endswith("Y"):
        return np.timedelta64(int(text[:-1]) * 365, "D")
    raise ValueError("window and stride strings must use 'D' or 'Y', e.g. '30D'")
