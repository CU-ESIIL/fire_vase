"""Helpers for treating local cubes as comparable spatial blocks."""

from __future__ import annotations

from collections.abc import Iterable, Sequence

import numpy as np
import xarray as xr


def _as_dataset(obj: xr.Dataset | xr.DataArray) -> xr.Dataset:
    if isinstance(obj, xr.Dataset):
        return obj
    if isinstance(obj, xr.DataArray):
        return obj.to_dataset(name=obj.name or "value")
    raise TypeError("Expected an xarray Dataset or DataArray")


def _infer_time_dim(obj: xr.Dataset | xr.DataArray, time_dim: str | None) -> str:
    if time_dim is not None:
        if time_dim not in obj.dims:
            raise ValueError(f"Time dimension {time_dim!r} not found in {tuple(obj.dims)}")
        return time_dim
    for candidate in ("time_window_end", "time"):
        if candidate in obj.dims:
            return candidate
    raise ValueError(
        "Could not infer time dimension; pass time_dim explicitly. "
        f"Available dims: {tuple(obj.dims)}"
    )


def _infer_spatial_dims(
    obj: xr.Dataset | xr.DataArray,
    *,
    time_dim: str,
    spatial_dims: Sequence[str] | None,
    unit_dim: str,
) -> tuple[str, ...]:
    if spatial_dims is not None:
        missing = [dim for dim in spatial_dims if dim not in obj.dims]
        if missing:
            raise ValueError(f"Spatial dims {missing!r} not found in {tuple(obj.dims)}")
        return tuple(spatial_dims)

    inferred = tuple(dim for dim in obj.dims if dim not in (time_dim, unit_dim))
    if not inferred:
        raise ValueError("No spatial dimensions available to summarize")
    return inferred


def aoi_signature(
    obj: xr.Dataset | xr.DataArray,
    *,
    unit_id: str,
    variables: Iterable[str] | None = None,
    time_dim: str | None = None,
    spatial_dims: Sequence[str] | None = None,
    reducer: str = "median",
    unit_dim: str = "unit",
    skipna: bool = True,
) -> xr.Dataset:
    """Reduce an AOI cube to a named spatial-unit time signature.

    The returned dataset keeps the time dimension and adds a length-one
    ``unit`` dimension. It is intended as the first bridge from local cube
    analyses to pairwise and many-unit spatial meta-analysis.
    """

    ds = _as_dataset(obj)
    resolved_time = _infer_time_dim(ds, time_dim)
    resolved_spatial = _infer_spatial_dims(
        ds,
        time_dim=resolved_time,
        spatial_dims=spatial_dims,
        unit_dim=unit_dim,
    )
    if variables is not None:
        selected = list(variables)
        missing = [name for name in selected if name not in ds.data_vars]
        if missing:
            raise ValueError(f"Variables {missing!r} not found in dataset")
        ds = ds[selected]

    if reducer == "median":
        signature = ds.median(dim=resolved_spatial, skipna=skipna, keep_attrs=True)
    elif reducer == "mean":
        signature = ds.mean(dim=resolved_spatial, skipna=skipna, keep_attrs=True)
    else:
        raise ValueError("reducer must be 'median' or 'mean'")

    signature = signature.expand_dims({unit_dim: [unit_id]})
    unit_coords: dict[str, tuple[str, list[float]]] = {}
    for dim in resolved_spatial:
        if dim not in obj.coords:
            continue
        values = np.asarray(obj[dim].values, dtype="float64")
        if values.size == 0:
            continue
        coord_name = f"{dim}_center"
        unit_coords[coord_name] = (unit_dim, [float(np.nanmean(values))])
        unit_coords[f"{dim}_min"] = (unit_dim, [float(np.nanmin(values))])
        unit_coords[f"{dim}_max"] = (unit_dim, [float(np.nanmax(values))])
    if unit_coords:
        signature = signature.assign_coords(unit_coords)

    signature.attrs.update(ds.attrs)
    signature.attrs.update(
        {
            "analysis": "aoi_signature",
            "unit_id": unit_id,
            "time_dim": resolved_time,
            "spatial_dims": resolved_spatial,
            "reducer": reducer,
        }
    )
    return signature


def block_signature(
    obj: xr.Dataset | xr.DataArray,
    *,
    block_id: str,
    variables: Iterable[str] | None = None,
    time_dim: str | None = None,
    spatial_dims: Sequence[str] | None = None,
    reducer: str = "median",
    block_dim: str = "block",
    skipna: bool = True,
) -> xr.Dataset:
    """Reduce a local cube to a named block time signature.

    A block is the spatial unit CubeDynamics uses to build higher-order
    comparison arenas. It may be an AOI, grid tile, ecological region, sampled
    pixel neighborhood, or any other local cube footprint.
    """

    signature = aoi_signature(
        obj,
        unit_id=block_id,
        variables=variables,
        time_dim=time_dim,
        spatial_dims=spatial_dims,
        reducer=reducer,
        unit_dim=block_dim,
        skipna=skipna,
    )
    signature.attrs.pop("unit_id", None)
    signature.attrs.update(
        {
            "analysis": "block_signature",
            "block_id": block_id,
            "block_dim": block_dim,
        }
    )
    return signature


def _unit_id(ds: xr.Dataset, unit_dim: str) -> str:
    if unit_dim in ds.dims and unit_dim in ds.coords and ds.sizes[unit_dim] == 1:
        return str(ds[unit_dim].values[0])
    return str(ds.attrs.get("block_id", ds.attrs.get("unit_id", "unit")))


def _single_unit(ds: xr.Dataset, unit_dim: str) -> xr.Dataset:
    if unit_dim not in ds.dims:
        return ds
    if ds.sizes[unit_dim] != 1:
        raise ValueError(
            "Pairwise comparison expects one unit per signature; "
            f"received {ds.sizes[unit_dim]} along {unit_dim!r}"
        )
    return ds.isel({unit_dim: 0}, drop=True)


def _pearson_corr(left: xr.DataArray, right: xr.DataArray, time_dim: str) -> xr.DataArray:
    mask = np.isfinite(left) & np.isfinite(right)
    left_valid = left.where(mask)
    right_valid = right.where(mask)
    left_anom = left_valid - left_valid.mean(dim=time_dim, skipna=True)
    right_anom = right_valid - right_valid.mean(dim=time_dim, skipna=True)
    numerator = (left_anom * right_anom).sum(dim=time_dim, skipna=True)
    denominator = np.sqrt(
        (left_anom**2).sum(dim=time_dim, skipna=True)
        * (right_anom**2).sum(dim=time_dim, skipna=True)
    )
    return numerator / denominator


def compare_aoi_signatures(
    left: xr.Dataset | xr.DataArray,
    right: xr.Dataset | xr.DataArray,
    *,
    variables: Iterable[str] | None = None,
    time_dim: str | None = None,
    unit_dim: str = "unit",
    join: str = "inner",
) -> xr.Dataset:
    """Compare two AOI signatures over their shared time axis."""

    left_ds = _as_dataset(left)
    right_ds = _as_dataset(right)
    resolved_time = _infer_time_dim(left_ds, time_dim)
    _infer_time_dim(right_ds, resolved_time)
    left_unit = _unit_id(left_ds, unit_dim)
    right_unit = _unit_id(right_ds, unit_dim)
    left_ds = _single_unit(left_ds, unit_dim)
    right_ds = _single_unit(right_ds, unit_dim)
    left_ds, right_ds = xr.align(left_ds, right_ds, join=join)

    if variables is None:
        selected = [name for name in left_ds.data_vars if name in right_ds.data_vars]
    else:
        selected = list(variables)
    if not selected:
        raise ValueError("No shared variables available for comparison")
    missing = [
        name
        for name in selected
        if name not in left_ds.data_vars or name not in right_ds.data_vars
    ]
    if missing:
        raise ValueError(f"Variables {missing!r} are not present in both signatures")

    coords = {"variable": selected}
    correlations = []
    mean_differences = []
    rmses = []
    counts = []
    for name in selected:
        left_var = left_ds[name]
        right_var = right_ds[name]
        mask = np.isfinite(left_var) & np.isfinite(right_var)
        diff = left_var - right_var
        correlations.append(_pearson_corr(left_var, right_var, resolved_time))
        mean_differences.append(diff.where(mask).mean(dim=resolved_time, skipna=True))
        rmses.append(np.sqrt((diff.where(mask) ** 2).mean(dim=resolved_time, skipna=True)))
        counts.append(mask.sum(dim=resolved_time))

    result = xr.Dataset(
        {
            "pearson_r": xr.concat(correlations, dim="variable").assign_coords(coords),
            "mean_difference": xr.concat(mean_differences, dim="variable").assign_coords(coords),
            "rmse": xr.concat(rmses, dim="variable").assign_coords(coords),
            "n": xr.concat(counts, dim="variable").assign_coords(coords),
        },
        attrs={
            "analysis": "pairwise_aoi_signature_compare",
            "left_unit": left_unit,
            "right_unit": right_unit,
            "time_dim": resolved_time,
            "join": join,
        },
    )
    return result


def collect_blocks(
    first: xr.Dataset | xr.DataArray,
    *others: xr.Dataset | xr.DataArray,
    block_dim: str = "block",
    join: str = "outer",
) -> xr.Dataset:
    """Collect block signatures into one block collection dataset."""

    signatures = [_as_dataset(first), *[_as_dataset(other) for other in others]]
    if not signatures:
        raise ValueError("At least one block signature is required")

    block_ids: list[str] = []
    normalized = []
    for index, signature in enumerate(signatures):
        if block_dim not in signature.dims:
            block_id = _unit_id(signature, block_dim)
            signature = signature.expand_dims({block_dim: [block_id]})
        if signature.sizes[block_dim] != 1:
            raise ValueError(
                "collect_blocks expects one block per input signature; "
                f"input {index} has {signature.sizes[block_dim]} blocks"
            )
        block_ids.append(str(signature[block_dim].values[0]))
        normalized.append(signature)

    if len(set(block_ids)) != len(block_ids):
        raise ValueError(f"Block ids must be unique; received {block_ids!r}")

    collection = xr.concat(normalized, dim=block_dim, join=join)
    collection.attrs.update(
        {
            "analysis": "block_collection",
            "block_dim": block_dim,
            "n_blocks": len(block_ids),
        }
    )
    return collection


def compare_blocks(
    blocks: xr.Dataset | xr.DataArray,
    *,
    variables: Iterable[str] | None = None,
    time_dim: str | None = None,
    block_dim: str = "block",
    join: str = "inner",
) -> xr.Dataset:
    """Compare all unique pairs in a block collection."""

    block_ds = _as_dataset(blocks)
    if block_dim not in block_ds.dims:
        raise ValueError(f"compare_blocks requires a {block_dim!r} dimension")
    block_ids = [str(value) for value in block_ds[block_dim].values]
    if len(block_ids) < 2:
        raise ValueError("compare_blocks requires at least two blocks")

    pair_results = []
    pair_labels = []
    left_ids = []
    right_ids = []
    for left_idx, left_id in enumerate(block_ids[:-1]):
        for right_idx in range(left_idx + 1, len(block_ids)):
            right_id = block_ids[right_idx]
            left = block_ds.isel({block_dim: left_idx}, drop=True).expand_dims(
                {block_dim: [left_id]}
            )
            right = block_ds.isel({block_dim: right_idx}, drop=True).expand_dims(
                {block_dim: [right_id]}
            )
            comparison = compare_aoi_signatures(
                left,
                right,
                variables=variables,
                time_dim=time_dim,
                unit_dim=block_dim,
                join=join,
            )
            label = f"{left_id}__{right_id}"
            pair_results.append(comparison.expand_dims({"pair": [label]}))
            pair_labels.append(label)
            left_ids.append(left_id)
            right_ids.append(right_id)

    result = xr.concat(pair_results, dim="pair")
    result.attrs.pop("left_unit", None)
    result.attrs.pop("right_unit", None)
    result = result.assign_coords(
        {
            "pair": pair_labels,
            "left_block": ("pair", left_ids),
            "right_block": ("pair", right_ids),
        }
    )
    result.attrs.update(
        {
            "analysis": "block_pairwise_compare",
            "block_dim": block_dim,
            "n_blocks": len(block_ids),
            "n_pairs": len(pair_labels),
            "time_dim": result.attrs.get("time_dim", time_dim),
            "join": join,
        }
    )
    return result


__all__ = [
    "aoi_signature",
    "block_signature",
    "collect_blocks",
    "compare_aoi_signatures",
    "compare_blocks",
]
