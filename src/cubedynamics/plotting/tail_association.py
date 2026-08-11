"""Copula-style tail-association plots for paired synchrony series."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Mapping, Optional, Sequence, Tuple, Union

import matplotlib.pyplot as plt
import numpy as np
import xarray as xr

from ..stats.tails import _rank_1d

PreprocessMode = Optional[Union[str, Callable[[np.ndarray, np.ndarray], Tuple[np.ndarray, np.ndarray]]]]
Selector = Optional[Union[Mapping[str, object], Sequence[int]]]


@dataclass(frozen=True)
class TailAssociationStats:
    """Summary statistics for one paired tail-association comparison."""

    n: int
    pearson: float
    spearman: float
    lower_partial_spearman: float
    upper_partial_spearman: float
    difference: float
    lower_count: int
    upper_count: int
    dominance: str


def paired_finite_arrays(x: object, y: object) -> tuple[np.ndarray, np.ndarray]:
    """Return equal-length 1D arrays after dropping paired missing values."""

    x_arr = np.asarray(x.to_numpy() if isinstance(x, xr.DataArray) else x, dtype=float)
    y_arr = np.asarray(y.to_numpy() if isinstance(y, xr.DataArray) else y, dtype=float)
    if x_arr.ndim != 1 or y_arr.ndim != 1:
        raise ValueError("x and y must be one-dimensional series")
    if x_arr.shape != y_arr.shape:
        raise ValueError(f"x and y must have the same length, got {x_arr.shape} and {y_arr.shape}")
    mask = np.isfinite(x_arr) & np.isfinite(y_arr)
    return x_arr[mask], y_arr[mask]


def normalized_ranks(a: object) -> np.ndarray:
    """Return ``rank(a) / (n + 1)`` using average ranks for tied values.

    Normalized ranks are the empirical copula coordinates used here to remove
    marginal scale and units before asking whether dependence changes in the
    lower or upper tails.
    """

    arr = np.asarray(a.to_numpy() if isinstance(a, xr.DataArray) else a, dtype=float)
    if arr.ndim != 1:
        raise ValueError("normalized_ranks expects a one-dimensional array")
    if arr.size == 0:
        return np.asarray([], dtype=float)
    return _rank_1d(arr) / float(arr.size + 1)


def ghosh_tail_band_mask(u: np.ndarray, v: np.ndarray, lower_bound: float, upper_bound: float) -> np.ndarray:
    """Return points inside the diagonal band ``2 lb < u + v < 2 ub``."""

    if not 0.0 <= lower_bound < upper_bound <= 1.0:
        raise ValueError("bounds must satisfy 0 <= lower_bound < upper_bound <= 1")
    total = u + v
    return (total > 2.0 * lower_bound) & (total < 2.0 * upper_bound)


def ghosh_partial_spearman(
    u: np.ndarray,
    v: np.ndarray,
    lower_bound: float,
    upper_bound: float,
    min_points: int = 2,
) -> tuple[float, int]:
    """Compute Ghosh-style partial Spearman correlation in a diagonal band.

    Means and variances are computed from the full normalized-rank vectors,
    while the covariance sum is restricted to points whose rank coordinates
    fall inside the selected tail band. This differs from ordinary Spearman
    correlation, which summarizes the full copula with one number.
    """

    if u.shape != v.shape:
        raise ValueError("u and v must have the same shape")
    n = u.size
    if n < 2:
        return float("nan"), 0
    mask = ghosh_tail_band_mask(u, v, lower_bound, upper_bound)
    count = int(np.count_nonzero(mask))
    if count < min_points:
        return float("nan"), count

    u_centered = u - float(np.mean(u))
    v_centered = v - float(np.mean(v))
    var_u = float(np.var(u, ddof=1))
    var_v = float(np.var(v, ddof=1))
    denom = (n - 1) * np.sqrt(var_u * var_v)
    if denom <= 0.0 or not np.isfinite(denom):
        return float("nan"), count
    value = float(np.sum(u_centered[mask] * v_centered[mask]) / denom)
    return value, count


def _ordinary_correlation(x: np.ndarray, y: np.ndarray) -> float:
    if x.size < 2:
        return float("nan")
    std_x = float(np.std(x, ddof=1))
    std_y = float(np.std(y, ddof=1))
    if std_x <= 0.0 or std_y <= 0.0:
        return float("nan")
    return float(np.corrcoef(x, y)[0, 1])


def _dominance(lower: float, upper: float, tolerance: float) -> str:
    if not np.isfinite(lower) or not np.isfinite(upper):
        return "undetermined"
    diff = lower - upper
    if abs(diff) <= tolerance:
        return "approximately symmetric"
    if diff > 0:
        return "left-tail dominant"
    return "right-tail dominant"


def tail_association_stats(
    x: object,
    y: object,
    b: float = 1.0 / 3.0,
    min_points: int = 2,
    dominance_tolerance: float = 0.02,
) -> tuple[TailAssociationStats, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Compute full and tail-specific association statistics for paired series."""

    if not 0.0 < b < 0.5:
        raise ValueError("b must be greater than 0 and less than 0.5")

    x_arr, y_arr = paired_finite_arrays(x, y)
    u = normalized_ranks(x_arr)
    v = normalized_ranks(y_arr)

    pearson = _ordinary_correlation(x_arr, y_arr)
    spearman = _ordinary_correlation(u, v)
    lower, lower_count = ghosh_partial_spearman(u, v, 0.0, b, min_points=min_points)
    upper, upper_count = ghosh_partial_spearman(u, v, 1.0 - b, 1.0, min_points=min_points)
    diff = lower - upper if np.isfinite(lower) and np.isfinite(upper) else float("nan")
    stats = TailAssociationStats(
        n=int(x_arr.size),
        pearson=pearson,
        spearman=spearman,
        lower_partial_spearman=lower,
        upper_partial_spearman=upper,
        difference=diff,
        lower_count=lower_count,
        upper_count=upper_count,
        dominance=_dominance(lower, upper, dominance_tolerance),
    )
    return stats, x_arr, y_arr, u, v


def _format_stat(value: float) -> str:
    return "NA" if not np.isfinite(value) else f"{value:.2f}"


def _save_png_pdf(fig: plt.Figure, outpath: str | Path, dpi: int) -> None:
    path = Path(outpath)
    base = path.with_suffix("") if path.suffix else path
    fig.savefig(base.with_suffix(".png"), dpi=dpi, bbox_inches="tight")
    fig.savefig(base.with_suffix(".pdf"), bbox_inches="tight")


def _preprocess_pair(
    x: np.ndarray,
    y: np.ndarray,
    preprocess: PreprocessMode,
) -> tuple[np.ndarray, np.ndarray, str]:
    if preprocess is None or preprocess == "raw":
        return x, y, "raw"
    if callable(preprocess):
        x_out, y_out = preprocess(x.copy(), y.copy())
        return np.asarray(x_out, dtype=float), np.asarray(y_out, dtype=float), "custom"
    if preprocess == "anomaly":
        return x - np.nanmean(x), y - np.nanmean(y), "anomaly"
    if preprocess == "zscore":
        x_std = np.nanstd(x, ddof=1)
        y_std = np.nanstd(y, ddof=1)
        if x_std <= 0.0 or y_std <= 0.0:
            raise ValueError("zscore preprocessing requires non-constant paired series")
        return (x - np.nanmean(x)) / x_std, (y - np.nanmean(y)) / y_std, "zscore"
    if preprocess == "rank_only":
        return normalized_ranks(x), normalized_ranks(y), "rank_only"
    if preprocess in {"event_binary", "event_intensity"}:
        raise NotImplementedError(
            f"{preprocess!r} preprocessing requires a threshold/event contract and is not wired yet"
        )
    raise ValueError(
        "preprocess must be one of raw, anomaly, zscore, rank_only, event_binary, event_intensity, "
        "a callable, or None"
    )


def _plot_band_boundaries(ax: plt.Axes, b: float) -> None:
    x_lower = np.linspace(0.0, 2.0 * b, 60)
    y_lower = 2.0 * b - x_lower
    x_upper = np.linspace(2.0 - 2.0 * b - 1.0, 1.0, 60)
    y_upper = 2.0 - 2.0 * b - x_upper
    ax.plot(x_lower, y_lower, color="0.25", linewidth=1.1, linestyle="--")
    ax.plot(x_upper, y_upper, color="0.25", linewidth=1.1, linestyle="--")
    ax.fill_between(x_lower, y_lower, 0.0, color="#4C78A8", alpha=0.08, linewidth=0)
    ax.fill_between(x_upper, y_upper, 1.0, color="#D65F5F", alpha=0.08, linewidth=0)


def _setup_rank_axis(ax: plt.Axes, labels: tuple[str, str]) -> None:
    ax.set_xlim(0.0, 1.0)
    ax.set_ylim(0.0, 1.0)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel(f"u (rank of {labels[0]} / (n+1))")
    ax.set_ylabel(f"v (rank of {labels[1]} / (n+1))")
    ax.grid(True, alpha=0.16, linewidth=0.6)


def _annotation_box(ax: plt.Axes, text: str, loc: tuple[float, float] = (0.04, 0.96)) -> None:
    ax.text(
        loc[0],
        loc[1],
        text,
        transform=ax.transAxes,
        va="top",
        ha="left",
        fontsize=8.7,
        bbox={"boxstyle": "round,pad=0.35", "facecolor": "white", "edgecolor": "0.78", "alpha": 0.92},
    )


def _plot_tail_association_row(
    axes: Sequence[plt.Axes],
    x: object,
    y: object,
    b: float,
    labels: tuple[str, str],
    row_title: str | None = None,
    preprocess: PreprocessMode = None,
    min_points: int = 2,
    dominance_tolerance: float = 0.02,
) -> TailAssociationStats:
    x_arr, y_arr = paired_finite_arrays(x, y)
    x_arr, y_arr, preprocess_label = _preprocess_pair(x_arr, y_arr, preprocess)
    stats, x_clean, y_clean, u, v = tail_association_stats(
        x_arr,
        y_arr,
        b=b,
        min_points=min_points,
        dominance_tolerance=dominance_tolerance,
    )

    raw_ax, rank_ax, tail_ax = axes
    raw_ax.scatter(x_clean, y_clean, s=18, color="#3B3B3B", alpha=0.72, edgecolors="none")
    raw_ax.set_xlabel(labels[0])
    raw_ax.set_ylabel(labels[1])
    raw_ax.grid(True, alpha=0.16, linewidth=0.6)
    raw_title = "Raw paired values" if preprocess_label == "raw" else f"Paired values ({preprocess_label})"
    raw_ax.set_title(raw_title)
    _annotation_box(raw_ax, f"Pearson r = {_format_stat(stats.pearson)}\nSpearman rho = {_format_stat(stats.spearman)}")

    rank_ax.scatter(u, v, s=18, color="#3B3B3B", alpha=0.72, edgecolors="none")
    _setup_rank_axis(rank_ax, labels)
    rank_ax.set_title("Normalized ranks")

    tail_ax.scatter(u, v, s=18, color="#3B3B3B", alpha=0.72, edgecolors="none")
    _plot_band_boundaries(tail_ax, b)
    _setup_rank_axis(tail_ax, labels)
    tail_ax.set_title("Tail bands")
    _annotation_box(
        tail_ax,
        "\n".join(
            [
                f"Lower partial rho = {_format_stat(stats.lower_partial_spearman)} (n={stats.lower_count})",
                f"Upper partial rho = {_format_stat(stats.upper_partial_spearman)} (n={stats.upper_count})",
                f"Lower - upper = {_format_stat(stats.difference)}",
                stats.dominance,
            ]
        ),
    )
    if row_title:
        raw_ax.text(
            -0.23,
            0.5,
            row_title,
            transform=raw_ax.transAxes,
            rotation=90,
            va="center",
            ha="center",
            fontsize=10.5,
            fontweight="bold",
        )
    return stats


def plot_tail_association_triptych(
    x: object,
    y: object,
    b: float = 1.0 / 3.0,
    labels: tuple[str, str] = ("Location A", "Location B"),
    title_prefix: str | None = None,
    outpath: str | Path | None = None,
    preprocess: PreprocessMode = None,
    min_points: int = 2,
    dominance_tolerance: float = 0.02,
    dpi: int = 300,
) -> plt.Figure:
    """Plot raw values, normalized ranks, and Ghosh-style tail bands.

    Use this low-level function for two series already extracted from a cube.
    It drops paired missing values, computes normalized ranks as
    ``rank(x)/(n+1)``, and annotates ordinary correlation alongside lower- and
    upper-tail partial Spearman correlations.
    """

    fig, axes = plt.subplots(1, 3, figsize=(12.0, 3.7), constrained_layout=False)
    fig.subplots_adjust(left=0.07, right=0.985, bottom=0.16, top=0.78, wspace=0.32)
    _plot_tail_association_row(
        axes,
        x,
        y,
        b=b,
        labels=labels,
        preprocess=preprocess,
        min_points=min_points,
        dominance_tolerance=dominance_tolerance,
    )
    title = title_prefix or "Copula-style tail association plot for climate synchrony"
    fig.suptitle(title, fontsize=13.5, fontweight="bold", y=0.97)
    if outpath is not None:
        _save_png_pdf(fig, outpath, dpi=dpi)
    return fig


def plot_tail_association_grid(
    pairs: Iterable[tuple[object, object]],
    b: float = 1.0 / 3.0,
    labels: tuple[str, str] = ("Location A", "Location B"),
    row_titles: Sequence[str] | None = None,
    title: str = "Copula-style tail association plots for climate synchrony",
    subtitle: str | None = "Top: left-tail dominant dependence. Bottom: right-tail dominant dependence.",
    outpath: str | Path | None = None,
    preprocess: PreprocessMode = None,
    min_points: int = 2,
    dominance_tolerance: float = 0.02,
    dpi: int = 300,
) -> plt.Figure:
    """Plot a publication-style 2x3 grid for multiple paired series."""

    pair_list = list(pairs)
    if not pair_list:
        raise ValueError("pairs must contain at least one (x, y) pair")
    n_rows = len(pair_list)
    if row_titles is None:
        row_titles = [f"Pair {idx + 1}" for idx in range(n_rows)]
    if len(row_titles) != n_rows:
        raise ValueError("row_titles length must match the number of pairs")

    fig_height = 3.65 * n_rows + 0.95
    fig, axes = plt.subplots(n_rows, 3, figsize=(12.5, fig_height), constrained_layout=False)
    fig.subplots_adjust(left=0.085, right=0.985, bottom=0.07, top=0.84, wspace=0.28, hspace=0.42)
    axes_2d = np.atleast_2d(axes)
    for row, ((x, y), row_title) in enumerate(zip(pair_list, row_titles)):
        _plot_tail_association_row(
            list(axes_2d[row, :]),
            x,
            y,
            b=b,
            labels=labels,
            row_title=row_title,
            preprocess=preprocess,
            min_points=min_points,
            dominance_tolerance=dominance_tolerance,
        )

    fig.suptitle(title, fontsize=14.5, fontweight="bold", y=0.985)
    if subtitle:
        fig.text(0.5, 0.94, subtitle, ha="center", va="top", fontsize=10.5, color="0.25")
    if outpath is not None:
        _save_png_pdf(fig, outpath, dpi=dpi)
    return fig


def _extract_dataarray(ds: xr.Dataset | xr.DataArray, var: str | None) -> xr.DataArray:
    if isinstance(ds, xr.DataArray):
        if var is not None and ds.name not in (None, var):
            raise ValueError(f"DataArray name {ds.name!r} does not match requested var {var!r}")
        return ds
    if var is None:
        raise ValueError("var is required when ds is an xarray Dataset")
    if var not in ds:
        raise KeyError(f"{var!r} is not a variable in the dataset")
    return ds[var]


def _select_series(data: xr.DataArray, selector: Selector, time_dim: str) -> xr.DataArray:
    selected = data
    if selector is None:
        pass
    elif isinstance(selector, Mapping):
        if "isel" in selector:
            selected = selected.isel(selector["isel"])  # type: ignore[arg-type]
        elif "sel" in selector:
            selected = selected.sel(selector["sel"])  # type: ignore[arg-type]
        else:
            selected = selected.sel(selector)
    else:
        spatial_dims = [dim for dim in selected.dims if dim != time_dim]
        if len(selector) != len(spatial_dims):
            raise ValueError(
                f"integer selector must provide one index per non-time dimension: {spatial_dims!r}"
            )
        selected = selected.isel(dict(zip(spatial_dims, selector)))

    remaining_dims = [dim for dim in selected.dims if dim != time_dim]
    if remaining_dims:
        raise ValueError(
            f"selector must reduce the cube to one series along {time_dim!r}; remaining dims: {remaining_dims!r}"
        )
    if time_dim not in selected.dims:
        raise ValueError(f"selected data must retain time dimension {time_dim!r}")
    return selected


def plot_tail_association_from_cube(
    ds: xr.Dataset | xr.DataArray,
    var: str | None,
    selector_a: Selector,
    selector_b: Selector,
    time_dim: str = "time",
    b: float = 1.0 / 3.0,
    preprocess: PreprocessMode = None,
    time_window: slice | tuple[object, object] | None = None,
    mask: xr.DataArray | np.ndarray | None = None,
    labels: tuple[str, str] = ("Location A", "Location B"),
    title_prefix: str | None = None,
    outpath: str | Path | None = None,
    min_points: int = 2,
    dominance_tolerance: float = 0.02,
    dpi: int = 300,
) -> plt.Figure:
    """Extract two cube series and pass them to ``plot_tail_association_triptych``.

    Selectors may be coordinate mappings such as ``{"y": 40.0, "x": -105.2}``,
    explicit ``{"sel": ...}``/``{"isel": ...}`` mappings, or integer index
    tuples ordered by the non-time dimensions. The helper is intentionally
    strict: each selector must return one time series so data extraction remains
    separate from plotting and aggregation choices stay visible.
    """

    data = _extract_dataarray(ds, var)
    if time_dim not in data.dims:
        raise ValueError(f"{time_dim!r} is not a dimension of {data.dims!r}")

    if time_window is not None:
        window = time_window if isinstance(time_window, slice) else slice(time_window[0], time_window[1])
        data = data.sel({time_dim: window})
    if mask is not None:
        data = data.where(mask)

    series_a = _select_series(data, selector_a, time_dim=time_dim)
    series_b = _select_series(data, selector_b, time_dim=time_dim)
    series_a, series_b = xr.align(series_a, series_b, join="inner")

    return plot_tail_association_triptych(
        series_a,
        series_b,
        b=b,
        labels=labels,
        title_prefix=title_prefix,
        outpath=outpath,
        preprocess=preprocess,
        min_points=min_points,
        dominance_tolerance=dominance_tolerance,
        dpi=dpi,
    )
