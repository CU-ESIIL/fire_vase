"""Render an exploratory report on observed fire-growth cessation.

This workflow uses cached real FIRED candidate events and cached real gridMET
maximum temperature files. It does not compare prescribed and non-prescribed
fires; all candidate fires are treated as non-prescribed by assumption because
the cached FIRED table has no prescribed-fire flag.
"""

from __future__ import annotations

import argparse
import base64
import json
import math
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xarray as xr
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.colors import Normalize
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

from cubedynamics.fire_time_hull import (
    FireEventDaily,
    compute_time_hull_geometry,
    normalize_dates,
)


PROJECTED_CRS_NOTE = "FIRED sinusoidal projected CRS, metre units"
PIXEL_AREA_KM2_DEFAULT = 0.2146585
RNG_SEED = 42


@dataclass
class ReportPaths:
    outputs: Path
    figures: Path
    pdf: Path
    html: Path
    analysis_table: Path
    summary_table: Path
    terminal_features: Path
    quality_control: Path


def make_paths(outputs: Path) -> ReportPaths:
    figures = outputs / "fire_vase_figures"
    return ReportPaths(
        outputs=outputs,
        figures=figures,
        pdf=outputs / "fire_vase_death_exploratory_report.pdf",
        html=outputs / "fire_vase_death_exploratory_report.html",
        analysis_table=outputs / "fire_vase_analysis_table.csv",
        summary_table=outputs / "fire_vase_summary_table.csv",
        terminal_features=outputs / "fire_vase_terminal_features.csv",
        quality_control=outputs / "fire_vase_quality_control.csv",
    )


def load_inputs(cache_dir: Path, candidates_csv: Path) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame, pd.DataFrame]:
    daily_path = cache_dir / "fired_conus-ak_daily_nov2001-march2021.gpkg"
    events_path = cache_dir / "fired_conus-ak_events_nov2001-march2021.gpkg"
    if not daily_path.exists():
        raise FileNotFoundError(daily_path)
    if not events_path.exists():
        raise FileNotFoundError(events_path)
    if not candidates_csv.exists():
        raise FileNotFoundError(candidates_csv)

    candidates = pd.read_csv(candidates_csv)
    ids = set(candidates["event_id"].astype(int))
    daily = gpd.read_file(daily_path)
    events = gpd.read_file(events_path)
    daily = daily[daily["id"].isin(ids)].copy()
    events = events[events["id"].isin(ids)].copy()
    daily["date"] = pd.to_datetime(daily["date"])
    daily["ig_date"] = pd.to_datetime(daily["ig_date"])
    daily["last_date"] = pd.to_datetime(daily["last_date"])
    events["ig_date"] = pd.to_datetime(events["ig_date"])
    events["last_date"] = pd.to_datetime(events["last_date"])
    return daily, events, candidates


def load_temperature_years(gridmet_cache_dir: Path, variable: str = "tmmx") -> xr.DataArray:
    paths = sorted(gridmet_cache_dir.glob(f"{variable}_*.nc"))
    if not paths:
        raise FileNotFoundError(
            f"No cached real gridMET files matching {variable}_*.nc under {gridmet_cache_dir}"
        )
    datasets = []
    for path in paths:
        ds = xr.open_dataset(path)
        var_name = variable if variable in ds.data_vars else next(iter(ds.data_vars))
        da = ds[var_name]
        if "day" in da.dims:
            da = da.rename({"day": "time"})
        if "day" in da.coords:
            da = da.rename({"day": "time"})
        da.name = variable
        datasets.append(da)
    out = xr.concat(datasets, dim="time").sortby("time")
    return out


def temperature_c_from_kelvin(values: Any) -> np.ndarray:
    arr = np.asarray(values, dtype=float)
    if np.isfinite(arr).any() and float(np.nanmedian(arr)) < 150:
        raise ValueError("Temperature values do not look like Kelvin; refusing C/F conversion.")
    return arr - 273.15


def nearest_temperature_series(temp_k: xr.DataArray, lon: float, lat: float, dates: pd.Series) -> pd.Series:
    da = temp_k.sel(lon=float(lon), lat=float(lat), method="nearest")
    index = pd.DatetimeIndex(pd.to_datetime(dates).to_numpy()).normalize()
    vals = da.sel(time=index, method="nearest").values
    return pd.Series(temperature_c_from_kelvin(vals), index=index)


def season(month: int) -> str:
    if month in (12, 1, 2):
        return "winter"
    if month in (3, 4, 5):
        return "spring"
    if month in (6, 7, 8):
        return "summer"
    return "fall"


def count_components(geom: Any) -> int:
    if geom is None or geom.is_empty:
        return 0
    if geom.geom_type == "Polygon":
        return 1
    if geom.geom_type == "MultiPolygon":
        return len(geom.geoms)
    return 1


def bbox_extent_km(geom: Any) -> float:
    if geom is None or geom.is_empty:
        return np.nan
    minx, miny, maxx, maxy = geom.bounds
    return float(math.hypot(maxx - minx, maxy - miny) / 1000.0)


def build_analysis_table(
    daily: gpd.GeoDataFrame,
    events: gpd.GeoDataFrame,
    candidates: pd.DataFrame,
    temp_k: xr.DataArray,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    lonlat = daily.to_crs("EPSG:4326")
    rows: list[dict[str, Any]] = []
    qc_rows: list[dict[str, Any]] = []
    feature_rows: list[dict[str, Any]] = []

    event_by_id = events.set_index("id")
    pixel_estimates = daily.loc[daily["pixels"] > 0, "dy_ar_km2"] / daily.loc[daily["pixels"] > 0, "pixels"]
    pixel_area_km2 = float(np.nanmedian(pixel_estimates)) if len(pixel_estimates) else PIXEL_AREA_KM2_DEFAULT

    for fire_id, group in daily.sort_values(["id", "date"]).groupby("id"):
        group = group.sort_values("date").copy()
        lonlat_group = lonlat.loc[group.index]
        event = event_by_id.loc[fire_id]
        dates = pd.to_datetime(group["date"])
        first = dates.min()
        last = dates.max()
        terminal_time = dates.max()
        elapsed = (dates - first).dt.total_seconds() / 86400.0
        duration_observed = max(float((terminal_time - first).days), 1.0)
        gaps = dates.diff().dt.days.fillna(0).astype(int)
        obs_count = int(len(group))
        event_duration = int(event.get("event_dur", obs_count))

        centroid_lon = [geom.centroid.x for geom in lonlat_group.geometry]
        centroid_lat = [geom.centroid.y for geom in lonlat_group.geometry]
        temp_c = nearest_temperature_series(temp_k, float(np.nanmedian(centroid_lon)), float(np.nanmedian(centroid_lat)), dates)

        prev_centroid = None
        prev_perim = np.nan
        active_threshold = max(pixel_area_km2, 0.005 * float(event.get("tot_ar_km2", group["tot_ar_km2"].max())))
        for obs_idx, ((idx, row), temp_val) in enumerate(zip(group.iterrows(), temp_c.values)):
            geom = row.geometry
            area_km2 = float(row.get("tot_ar_km2", geom.area / 1e6))
            new_area_km2 = float(row.get("dy_ar_km2", geom.area / 1e6))
            perimeter_km = float(geom.length / 1000.0)
            compact = float((4.0 * np.pi * max(geom.area, 0.0)) / (geom.length**2)) if geom.length else np.nan
            centroid = geom.centroid
            centroid_disp = 0.0 if prev_centroid is None else float(centroid.distance(prev_centroid) / 1000.0)
            perim_change = np.nan if np.isnan(prev_perim) else perimeter_km - prev_perim
            rel_age = float(elapsed.iloc[obs_idx] / duration_observed)
            time_to_end = float((row["date"] - terminal_time).days)
            prop_growth = new_area_km2 / area_km2 if area_km2 > 0 else np.nan
            rows.append(
                {
                    "fire_id": int(fire_id),
                    "timestamp": row["date"],
                    "observation_index": obs_idx,
                    "elapsed_days": float(elapsed.iloc[obs_idx]),
                    "time_to_end_days": time_to_end,
                    "relative_age": rel_age,
                    "cumulative_area_km2": area_km2,
                    "newly_added_area_km2": new_area_km2,
                    "proportional_area_growth": prop_growth,
                    "perimeter_km": perimeter_km,
                    "perimeter_change_km": perim_change,
                    "compactness": compact,
                    "centroid_x_m": float(centroid.x),
                    "centroid_y_m": float(centroid.y),
                    "centroid_lon": float(centroid_lon[obs_idx]),
                    "centroid_lat": float(centroid_lat[obs_idx]),
                    "centroid_displacement_km": centroid_disp,
                    "maximum_spatial_extent_km": bbox_extent_km(geom),
                    "vase_width_km": bbox_extent_km(geom),
                    "polygon_components": count_components(geom),
                    "tmmx_c_nearest_grid_cell": float(temp_val),
                    "climate_mean_c": float(temp_val),
                    "climate_median_c": float(temp_val),
                    "climate_sd_c": np.nan,
                    "climate_min_c": float(temp_val),
                    "climate_max_c": float(temp_val),
                    "climate_newly_added_area_c": np.nan,
                    "climate_cumulative_footprint_c": np.nan,
                    "climate_advancing_boundary_c": np.nan,
                    "climate_support_used": "nearest grid cell to event centroid",
                    "region": event.get("eco_name", ""),
                    "year": int(row["date"].year),
                    "month": int(row["date"].month),
                    "season": season(int(row["date"].month)),
                    "elevation": np.nan,
                    "vegetation_or_landcover_class": event.get("lc_name", ""),
                    "final_fire_area_km2": float(event.get("tot_ar_km2", group["tot_ar_km2"].max())),
                    "duration_days": event_duration,
                    "observation_count": obs_count,
                    "growth_above_one_pixel": bool(new_area_km2 >= pixel_area_km2),
                    "growth_above_primary_threshold": bool(new_area_km2 >= active_threshold),
                }
            )
            prev_centroid = centroid
            prev_perim = perimeter_km

        fire_rows = pd.DataFrame([r for r in rows if r["fire_id"] == fire_id]).sort_values("timestamp")
        terminal_primary = fire_rows[fire_rows["growth_above_primary_threshold"]]
        terminal_idx = int(terminal_primary["observation_index"].max()) if not terminal_primary.empty else obs_count - 1
        max_gap = int(gaps.max()) if len(gaps) else 0
        if obs_count < 3:
            qc_class = "too few observations"
        elif max_gap > 2 or obs_count < event_duration:
            qc_class = "sequence gap near ending"
        elif pd.Timestamp(last).normalize() < pd.Timestamp(event.get("last_date")).normalize():
            qc_class = "uncertain or censored ending"
        else:
            qc_class = "probable cessation"
        qc_rows.append(
            {
                "fire_id": int(fire_id),
                "observation_count": obs_count,
                "event_duration_days": event_duration,
                "observed_span_days": int((last - first).days) + 1,
                "max_gap_days": max_gap,
                "terminal_index_any_positive": int(fire_rows[fire_rows["newly_added_area_km2"] > 0]["observation_index"].max()),
                "terminal_index_one_pixel": int(fire_rows[fire_rows["growth_above_one_pixel"]]["observation_index"].max()) if fire_rows["growth_above_one_pixel"].any() else np.nan,
                "terminal_index_primary": terminal_idx,
                "absolute_threshold_km2": pixel_area_km2,
                "primary_threshold_km2": active_threshold,
                "qc_class": qc_class,
                "primary_quality_pass": qc_class in {"probable cessation", "clear observed cessation"},
                "notes": "No zero-growth post-terminal observation available; terminal means last meaningful detected growth.",
            }
        )

        growth = fire_rows["newly_added_area_km2"].to_numpy(float)
        widths = fire_rows["vase_width_km"].to_numpy(float)
        temps = fire_rows["tmmx_c_nearest_grid_cell"].to_numpy(float)
        peak_idx = int(np.nanargmax(growth)) if growth.size and np.isfinite(growth).any() else 0
        pulses = int(np.sum((growth[1:-1] > growth[:-2]) & (growth[1:-1] > growth[2:]))) if growth.size >= 3 else 0
        terminal_window = fire_rows.tail(min(3, len(fire_rows)))
        active = fire_rows.iloc[: max(1, terminal_idx)]
        feature_rows.append(
            {
                "fire_id": int(fire_id),
                "final_area_km2": float(fire_rows["final_fire_area_km2"].iloc[0]),
                "duration_days": event_duration,
                "observation_count": obs_count,
                "peak_newly_added_area_km2": float(np.nanmax(growth)),
                "maximum_proportional_growth": float(np.nanmax(fire_rows["proportional_area_growth"])),
                "relative_time_of_peak_growth": float(fire_rows.loc[fire_rows["observation_index"] == peak_idx, "relative_age"].iloc[0]),
                "number_of_growth_pulses": pulses,
                "pulse_prominence_km2": float(np.nanmax(growth) - np.nanmedian(growth)),
                "terminal_width_km": float(widths[-1]),
                "terminal_width_fraction_of_max": float(widths[-1] / np.nanmax(widths)) if np.nanmax(widths) > 0 else np.nan,
                "terminal_taper_slope_km_per_obs": float(np.polyfit(np.arange(len(terminal_window)), terminal_window["vase_width_km"], 1)[0]) if len(terminal_window) >= 2 else np.nan,
                "observations_between_peak_growth_and_terminal": int(obs_count - 1 - peak_idx),
                "asymmetry_expansion_decline": float((np.nanmax(growth[: peak_idx + 1]) + 1e-9) / (np.nanmean(growth[peak_idx + 1 :]) + 1e-9)) if peak_idx + 1 < len(growth) else np.nan,
                "climate_range_c": float(np.nanmax(temps) - np.nanmin(temps)),
                "climate_trajectory_length_c": float(np.nansum(np.abs(np.diff(temps)))) if len(temps) > 1 else 0.0,
                "climate_change_terminal_window_c": float(terminal_window["tmmx_c_nearest_grid_cell"].iloc[-1] - terminal_window["tmmx_c_nearest_grid_cell"].iloc[0]) if len(terminal_window) >= 2 else np.nan,
                "geometric_trajectory_length_km2": float(np.nansum(np.abs(np.diff(growth)))) if len(growth) > 1 else 0.0,
                "terminal_value_tmmx_c": float(temps[-1]),
                "previous_value_tmmx_c": float(temps[-2]) if len(temps) >= 2 else np.nan,
                "terminal_change_tmmx_c": float(temps[-1] - temps[-2]) if len(temps) >= 2 else np.nan,
                "terminal_window_mean_tmmx_c": float(terminal_window["tmmx_c_nearest_grid_cell"].mean()),
                "terminal_window_slope_tmmx_c_per_obs": float(np.polyfit(np.arange(len(terminal_window)), terminal_window["tmmx_c_nearest_grid_cell"], 1)[0]) if len(terminal_window) >= 2 else np.nan,
                "terminal_window_variance_tmmx_c": float(terminal_window["tmmx_c_nearest_grid_cell"].var()),
                "lifetime_mean_tmmx_c": float(np.nanmean(temps)),
                "active_growth_period_mean_tmmx_c": float(active["tmmx_c_nearest_grid_cell"].mean()),
                "within_fire_terminal_z_tmmx": float((temps[-1] - np.nanmean(temps)) / (np.nanstd(temps) or np.nan)),
                "terminal_percentile_within_fire_tmmx": float(pd.Series(temps).rank(pct=True).iloc[-1]),
                "terminal_growth_km2": float(growth[-1]),
                "terminal_growth_fraction_of_peak": float(growth[-1] / np.nanmax(growth)) if np.nanmax(growth) > 0 else np.nan,
                "qc_class": qc_class,
            }
        )

    analysis = pd.DataFrame(rows)
    qc = pd.DataFrame(qc_rows)
    features = pd.DataFrame(feature_rows)
    return analysis, qc, features


def build_summary_table(analysis: pd.DataFrame, features: pd.DataFrame, qc: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for name, series in {
        "final_area_km2": features["final_area_km2"],
        "duration_days": features["duration_days"],
        "observation_count": features["observation_count"],
        "peak_newly_added_area_km2": features["peak_newly_added_area_km2"],
        "terminal_tmmx_c": features["terminal_value_tmmx_c"],
        "terminal_growth_km2": features["terminal_growth_km2"],
    }.items():
        rows.append(
            {
                "metric": name,
                "n": int(series.notna().sum()),
                "min": float(series.min()),
                "median": float(series.median()),
                "mean": float(series.mean()),
                "max": float(series.max()),
            }
        )
    rows.append({"metric": "fires_total", "n": int(features["fire_id"].nunique()), "min": np.nan, "median": np.nan, "mean": np.nan, "max": np.nan})
    rows.append({"metric": "fires_primary_quality_pass", "n": int(qc["primary_quality_pass"].sum()), "min": np.nan, "median": np.nan, "mean": np.nan, "max": np.nan})
    rows.append({"metric": "fire_time_rows", "n": int(len(analysis)), "min": np.nan, "median": np.nan, "mean": np.nan, "max": np.nan})
    return pd.DataFrame(rows)


def data_availability_table(paths: ReportPaths, daily: gpd.GeoDataFrame, events: gpd.GeoDataFrame, gridmet_cache: Path) -> pd.DataFrame:
    requested = [
        ("fire polygons/perimeters", True, "fired_conus-ak_daily_nov2001-march2021.gpkg", PROJECTED_CRS_NOTE, "irregular daily detections", "FIRED candidate event polygons", daily.geometry.isna().mean(), True),
        ("fire IDs", True, "daily/events GeoPackages", "integer id", "event-level/time-level", "FIRED id", daily["id"].isna().mean(), True),
        ("timestamps", True, "daily GeoPackage date column", "calendar date", "detected timesteps", "daily records", daily["date"].isna().mean(), True),
        ("maximum temperature", True, "gridmet-cache/tmmx_2001-2003.nc", "deg C after K conversion", "daily", "nearest grid cell to event centroid", 0.0, True),
        ("minimum temperature", False, "not cached", "unavailable", "daily requested", "gridMET", np.nan, False),
        ("vapor pressure deficit", False, "not cached", "unavailable", "daily requested", "gridMET", np.nan, False),
        ("relative humidity", False, "not cached", "unavailable", "daily requested", "gridMET", np.nan, False),
        ("wind speed", False, "not cached", "unavailable", "daily requested", "gridMET", np.nan, False),
        ("precipitation", False, "not cached", "unavailable", "daily requested", "gridMET", np.nan, False),
        ("fuel moisture", False, "not cached", "unavailable", "daily requested", "gridMET", np.nan, False),
        ("drought index", False, "not cached", "unavailable", "daily requested", "gridMET", np.nan, False),
        ("elevation", False, "not available in cached FIRED candidate data", "unavailable", "static", "context", np.nan, False),
    ]
    return pd.DataFrame(
        requested,
        columns=[
            "requested_variable",
            "available",
            "source_file_or_object",
            "units",
            "temporal_resolution",
            "spatial_support",
            "missingness",
            "used_in_analysis",
        ],
    )


def savefig(fig: plt.Figure, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180, bbox_inches="tight")
    return path


def text_page(pdf: PdfPages, title: str, lines: list[str]) -> None:
    def new_page() -> tuple[plt.Figure, float]:
        fig = plt.figure(figsize=(11, 8.5))
        fig.patch.set_facecolor("white")
        y = 0.94
        for title_line in textwrap.wrap(title, width=78):
            fig.text(0.05, y, title_line, fontsize=18, fontweight="bold", va="top")
            y -= 0.042
        return fig, y - 0.035

    fig, y = new_page()
    line_height = 0.030
    paragraph_gap = 0.018
    for line in lines:
        wrapped = textwrap.wrap(line, width=115) if line else [""]
        needed = line_height * len(wrapped) + paragraph_gap
        if y - needed < 0.08:
            pdf.savefig(fig)
            plt.close(fig)
            fig, y = new_page()
        for part in wrapped:
            fig.text(0.06, y, part, fontsize=12, va="top")
            y -= line_height
        y -= paragraph_gap
    pdf.savefig(fig)
    plt.close(fig)


def table_page(pdf: PdfPages, title: str, df: pd.DataFrame, max_rows: int = 18) -> None:
    fig, ax = plt.subplots(figsize=(11, 8.5))
    fig.patch.set_facecolor("white")
    ax.axis("off")
    ax.set_title(title, fontsize=18, fontweight="bold", loc="left", pad=20)
    view = df.head(max_rows).copy()
    wrap_width = max(10, int(120 / max(len(view.columns), 1)))
    for col in view.columns:
        view[col] = view[col].map(lambda x: f"{x:.3g}" if isinstance(x, float) and np.isfinite(x) else str(x))
        view[col] = view[col].map(lambda x: textwrap.fill(x, width=wrap_width))
    headers = [textwrap.fill(str(col), width=wrap_width) for col in view.columns]
    table = ax.table(
        cellText=view.values,
        colLabels=headers,
        cellLoc="left",
        colLoc="left",
        bbox=[0.03, 0.06, 0.94, 0.78],
    )
    table.auto_set_font_size(False)
    table.set_fontsize(6.5)
    pdf.savefig(fig)
    plt.close(fig)


def plot_qc_summary(qc: pd.DataFrame, path: Path) -> Path:
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.8))
    qc["observation_count"].hist(ax=axes[0], bins=range(0, int(qc["observation_count"].max()) + 2), color="#4c78a8")
    axes[0].set_title("Observation counts")
    axes[0].set_xlabel("observations per fire")
    axes[0].set_ylabel("fires")
    qc["max_gap_days"].hist(ax=axes[1], bins=range(0, int(qc["max_gap_days"].max()) + 2), color="#f58518")
    axes[1].set_title("Maximum temporal gap")
    axes[1].set_xlabel("days")
    qc["qc_class"].value_counts().plot.bar(ax=axes[2], color="#54a24b")
    axes[2].set_title("QC class")
    axes[2].tick_params(axis="x", rotation=35)
    fig.suptitle("Data and quality-control summary", fontsize=16, fontweight="bold")
    return savefig(fig, path)


def plot_feature_distributions(features: pd.DataFrame, path: Path) -> Path:
    cols = ["final_area_km2", "peak_newly_added_area_km2", "terminal_value_tmmx_c", "terminal_growth_fraction_of_peak"]
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    for ax, col in zip(axes.ravel(), cols):
        ax.hist(features[col].dropna(), bins=10, color="#4c78a8", alpha=0.85)
        ax.set_title(col)
        ax.set_ylabel("fires")
    fig.suptitle("Fire-level feature distributions", fontsize=16, fontweight="bold")
    return savefig(fig, path)


def plot_trajectories(analysis: pd.DataFrame, variable: str, ylabel: str, path: Path, standardized: bool = False) -> Path:
    fig, ax = plt.subplots(figsize=(11, 6))
    grid = np.linspace(0, 1, 40)
    interp_values = []
    for fire_id, group in analysis.groupby("fire_id"):
        g = group.sort_values("relative_age")
        y = g[variable].to_numpy(float)
        if standardized:
            sd = np.nanstd(y)
            y = (y - np.nanmean(y)) / sd if sd > 0 else y * np.nan
        x = g["relative_age"].to_numpy(float)
        ax.plot(x, y, color="#4c78a8", alpha=0.22, lw=1)
        if len(np.unique(x)) > 1 and np.isfinite(y).sum() >= 2:
            interp_values.append(np.interp(grid, x, y))
    if interp_values:
        arr = np.asarray(interp_values)
        med = np.nanmedian(arr, axis=0)
        q25 = np.nanpercentile(arr, 25, axis=0)
        q75 = np.nanpercentile(arr, 75, axis=0)
        ax.plot(grid, med, color="black", lw=2, label="fire-level median")
        ax.fill_between(grid, q25, q75, color="black", alpha=0.15, label="IQR")
    ax.set_xlabel("relative fire age")
    ax.set_ylabel(ylabel)
    ax.set_title(f"{ylabel} over normalized life (n={analysis['fire_id'].nunique()} fires)")
    ax.legend(loc="best")
    return savefig(fig, path)


def plot_terminal_alignment(analysis: pd.DataFrame, variable: str, ylabel: str, path: Path, standardized: bool = False) -> Path:
    fig, ax = plt.subplots(figsize=(11, 6))
    positions = np.arange(-6, 1)
    aligned = []
    for fire_id, group in analysis.groupby("fire_id"):
        tail = group.sort_values("observation_index").tail(7)
        y = tail[variable].to_numpy(float)
        if standardized:
            all_y = group[variable].to_numpy(float)
            sd = np.nanstd(all_y)
            y = (y - np.nanmean(all_y)) / sd if sd > 0 else y * np.nan
        x = np.arange(-len(y) + 1, 1)
        ax.plot(x, y, color="#e45756", alpha=0.25)
        if len(y) == 7:
            aligned.append(y)
    if aligned:
        arr = np.asarray(aligned)
        ax.plot(positions, np.nanmedian(arr, axis=0), color="black", lw=2, label="median")
        ax.fill_between(positions, np.nanpercentile(arr, 25, axis=0), np.nanpercentile(arr, 75, axis=0), color="black", alpha=0.15)
    ax.axvline(0, color="black", linestyle="--", lw=1)
    ax.set_xlabel("observation steps to terminal observation")
    ax.set_ylabel(ylabel)
    ax.set_title(f"Terminal-aligned {ylabel}")
    ax.legend(loc="best")
    return savefig(fig, path)


def plot_heatmap(analysis: pd.DataFrame, variable: str, path: Path, standardized: bool = False) -> Path:
    grid = np.linspace(0, 1, 50)
    rows = []
    labels = []
    sort_values = []
    for fire_id, group in analysis.groupby("fire_id"):
        g = group.sort_values("relative_age")
        y = g[variable].to_numpy(float)
        if standardized:
            sd = np.nanstd(y)
            y = (y - np.nanmean(y)) / sd if sd > 0 else y * np.nan
        if len(np.unique(g["relative_age"])) > 1 and np.isfinite(y).sum() >= 2:
            rows.append(np.interp(grid, g["relative_age"], y))
            labels.append(str(fire_id))
            sort_values.append(float(g["final_fire_area_km2"].iloc[0]))
    order = np.argsort(sort_values)
    arr = np.asarray(rows)[order]
    fig, ax = plt.subplots(figsize=(11, 7))
    im = ax.imshow(arr, aspect="auto", interpolation="nearest", cmap="viridis")
    ax.set_title(f"Heatmap: {variable}{' standardized' if standardized else ''}")
    ax.set_xlabel("relative age bin")
    ax.set_ylabel("fires sorted by final area")
    fig.colorbar(im, ax=ax, shrink=0.7)
    return savefig(fig, path)


def pca_features(features: pd.DataFrame, cols: list[str]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    X = features[cols].to_numpy(float)
    means = np.nanmean(X, axis=0)
    stds = np.nanstd(X, axis=0)
    stds[stds == 0] = 1
    Xs = (np.where(np.isfinite(X), X, means) - means) / stds
    U, S, Vt = np.linalg.svd(Xs, full_matrices=False)
    scores = U[:, :2] * S[:2]
    var = (S**2) / np.sum(S**2)
    return scores, var[:2], Vt[:2]


def plot_pca(features: pd.DataFrame, path: Path) -> Path:
    cols = [
        "final_area_km2",
        "duration_days",
        "peak_newly_added_area_km2",
        "terminal_growth_fraction_of_peak",
        "terminal_value_tmmx_c",
        "terminal_change_tmmx_c",
        "terminal_width_fraction_of_max",
    ]
    scores, var, _ = pca_features(features, cols)
    fig, ax = plt.subplots(figsize=(8, 7))
    sc = ax.scatter(scores[:, 0], scores[:, 1], c=features["terminal_value_tmmx_c"], cmap="viridis", s=60)
    for x, y, fire_id in zip(scores[:, 0], scores[:, 1], features["fire_id"]):
        ax.text(x, y, str(fire_id), fontsize=6)
    ax.set_xlabel(f"PC1 ({var[0] * 100:.1f}% var)")
    ax.set_ylabel(f"PC2 ({var[1] * 100:.1f}% var)")
    ax.set_title("Multivariate terminal state space")
    fig.colorbar(sc, ax=ax, label="terminal tmmx (C)")
    return savefig(fig, path)


def draw_vase(ax, hull, layer_days: np.ndarray, layer_values: np.ndarray, norm: Normalize, cmap_name: str = "viridis") -> None:
    verts = np.asarray(hull.verts_km, dtype=float)
    t_days = np.asarray(hull.t_days_vert, dtype=float)
    faces: list[np.ndarray] = []
    values: list[float] = []
    for layer_idx in range(len(layer_days) - 1):
        lower = np.flatnonzero(t_days == layer_days[layer_idx])
        upper = np.flatnonzero(t_days == layer_days[layer_idx + 1])
        if lower.size == 0 or upper.size == 0 or lower.size != upper.size:
            continue
        for j in range(lower.size):
            nxt = (j + 1) % lower.size
            faces.append(verts[[lower[j], lower[nxt], upper[nxt], upper[j]]])
            values.append(float(layer_values[layer_idx + 1]))
    cmap = plt.get_cmap(cmap_name)
    poly = Poly3DCollection(faces, facecolors=cmap(norm(values)), edgecolors="#222", linewidths=0.05, alpha=0.96)
    ax.add_collection3d(poly)
    mins = np.nanmin(verts, axis=0)
    maxs = np.nanmax(verts, axis=0)
    center = (mins + maxs) / 2
    span = max(float(np.nanmax(maxs - mins)), 1.0)
    ax.set_xlim(center[0] - span * 0.55, center[0] + span * 0.55)
    ax.set_ylim(center[1] - span * 0.55, center[1] + span * 0.55)
    ax.set_zlim(max(0, mins[2] - 0.2), maxs[2] + span * 0.25)
    ax.view_init(elev=18, azim=-62)
    ax.set_axis_off()
    ax.set_box_aspect((1, 1, 1.4))


def vase_gallery(daily: gpd.GeoDataFrame, analysis: pd.DataFrame, path: Path, title: str, max_fires: int = 12) -> Path:
    fire_ids = analysis.groupby("fire_id")["final_fire_area_km2"].first().sort_values(ascending=False).head(max_fires).index.tolist()
    vals = analysis["tmmx_c_nearest_grid_cell"].dropna()
    norm = Normalize(float(vals.quantile(0.02)), float(vals.quantile(0.98)))
    fig = plt.figure(figsize=(14, 9))
    fig.suptitle(title, fontsize=16, fontweight="bold")
    rows = int(np.ceil(len(fire_ids) / 4))
    for idx, fire_id in enumerate(fire_ids):
        ax = fig.add_subplot(rows, 4, idx + 1, projection="3d")
        event = FireEventDaily.from_fired(daily, fire_id, date_col="date")
        hull = compute_time_hull_geometry(event, n_ring_samples=48, n_theta=48)
        layer_days = np.unique(np.asarray(hull.t_days_vert, dtype=float))
        fire = analysis[analysis["fire_id"] == fire_id].sort_values("timestamp")
        layer_dates = normalize_dates(event.t0 + pd.to_timedelta(layer_days - np.nanmin(layer_days), unit="D"))
        climate = fire.set_index(normalize_dates(fire["timestamp"]))["tmmx_c_nearest_grid_cell"].reindex(layer_dates).ffill().bfill().to_numpy(float)
        draw_vase(ax, hull, layer_days, climate, norm)
        ax.text2D(0.03, -0.03, f"id {fire_id}\narea {fire['final_fire_area_km2'].iloc[0]:.0f} km2", transform=ax.transAxes, fontsize=8, fontweight="bold")
    cax = fig.add_axes([0.35, 0.04, 0.30, 0.02])
    sm = plt.cm.ScalarMappable(norm=norm, cmap="viridis")
    fig.colorbar(sm, cax=cax, orientation="horizontal", label="tmmx (C)")
    return savefig(fig, path)


def build_figures(paths: ReportPaths, daily: gpd.GeoDataFrame, analysis: pd.DataFrame, features: pd.DataFrame, qc: pd.DataFrame) -> dict[str, Path]:
    figs = {
        "qc": plot_qc_summary(qc, paths.figures / "qc_summary.png"),
        "features": plot_feature_distributions(features, paths.figures / "feature_distributions.png"),
        "growth_traj": plot_trajectories(analysis, "newly_added_area_km2", "newly added area (km2)", paths.figures / "new_area_trajectories.png"),
        "temp_traj": plot_trajectories(analysis, "tmmx_c_nearest_grid_cell", "tmmx (C)", paths.figures / "tmmx_trajectories.png"),
        "growth_term": plot_terminal_alignment(analysis, "newly_added_area_km2", "newly added area (km2)", paths.figures / "terminal_growth_alignment.png"),
        "temp_term_z": plot_terminal_alignment(analysis, "tmmx_c_nearest_grid_cell", "within-fire tmmx z-score", paths.figures / "terminal_tmmx_standardized_alignment.png", standardized=True),
        "growth_heatmap": plot_heatmap(analysis, "newly_added_area_km2", paths.figures / "new_area_heatmap.png"),
        "temp_heatmap_z": plot_heatmap(analysis, "tmmx_c_nearest_grid_cell", paths.figures / "tmmx_heatmap_standardized.png", standardized=True),
        "pca": plot_pca(features, paths.figures / "terminal_feature_pca.png"),
        "gallery": vase_gallery(daily, analysis, paths.figures / "vase_gallery_largest_fires.png", "VASE gallery: largest cached candidate fires"),
    }
    return figs


def image_page(pdf: PdfPages, title: str, image_path: Path, note: str = "") -> None:
    img = plt.imread(image_path)
    fig, ax = plt.subplots(figsize=(11, 8.5))
    fig.patch.set_facecolor("white")
    ax.imshow(img)
    ax.axis("off")
    fig.suptitle(title, fontsize=16, fontweight="bold")
    if note:
        fig.text(0.05, 0.04, note, fontsize=9, wrap=True)
    pdf.savefig(fig)
    plt.close(fig)


def render_pdf(
    paths: ReportPaths,
    availability: pd.DataFrame,
    analysis: pd.DataFrame,
    summary: pd.DataFrame,
    features: pd.DataFrame,
    qc: pd.DataFrame,
    figs: dict[str, Path],
) -> None:
    with PdfPages(paths.pdf) as pdf:
        text_page(
            pdf,
            "Fire death atlas: observed cessation of detectable spatial growth",
            [
                "Informal title note: 'fire death' is used here only as shorthand for observed cessation of detectable spatial growth in cached FIRED non-prescribed candidate fires.",
                f"Candidate fires: {features['fire_id'].nunique()}; fire-time records: {len(analysis)}; primary QC pass: {int(qc['primary_quality_pass'].sum())}.",
                f"Final area range: {features['final_area_km2'].min():.2f}-{features['final_area_km2'].max():.2f} km2.",
                f"Observation count range: {features['observation_count'].min()}-{features['observation_count'].max()} records per fire.",
                "Available climate variable used: gridMET daily maximum temperature (tmmx), converted from Kelvin to Celsius.",
                "Primary limitation: climate is nearest grid cell to event centroid. Newly burned area, cumulative footprint, and advancing-boundary climate are not separately estimated because these candidate fires are often smaller than gridMET cell support.",
                "No prescribed-fire comparisons are made or implied.",
            ],
        )
        availability_pdf = availability[
            [
                "requested_variable",
                "available",
                "units",
                "temporal_resolution",
                "spatial_support",
                "used_in_analysis",
            ]
        ]
        table_page(pdf, "Data availability", availability_pdf, max_rows=20)
        table_page(pdf, "Summary table", summary, max_rows=20)
        table_page(pdf, "Quality-control sample-size flow", qc[["fire_id", "observation_count", "event_duration_days", "max_gap_days", "qc_class", "primary_quality_pass"]], max_rows=16)
        image_page(pdf, "Data and quality control", figs["qc"], "Most candidate endings have sequence gaps; interpret terminal observations as dataset-observed endings, not physical extinction.")
        image_page(pdf, "VASE gallery with common tmmx scale", figs["gallery"], "Gallery uses common tmmx color scale and largest fires by final area.")
        image_page(pdf, "Fire morphology distributions", figs["features"])
        image_page(pdf, "Complete life histories: growth", figs["growth_traj"])
        image_page(pdf, "Complete life histories: maximum temperature", figs["temp_traj"])
        image_page(pdf, "Terminal alignment: geometric activity", figs["growth_term"])
        image_page(pdf, "Terminal alignment: within-fire tmmx anomaly", figs["temp_term_z"])
        image_page(pdf, "Heatmap: growth over relative age", figs["growth_heatmap"])
        image_page(pdf, "Heatmap: standardized temperature over relative age", figs["temp_heatmap_z"])
        image_page(pdf, "Multivariate terminal state space", figs["pca"])
        text_page(
            pdf,
            "Candidate scientific decisions",
            [
                "A. Common absolute terminal state: weak evidence with current data; terminal tmmx remains geographically/seasonally heterogeneous.",
                "B. Within-fire anomaly convergence: ambiguous; standardized terminal trajectories do not justify a strong convergence claim.",
                "C. Common direction without common endpoint: plausible for geometric growth decline by construction, but climate direction is mixed.",
                "D. Multiple recurring terminal pathways: possible, but sample size is too small for stable clustering.",
                "E. Climate alone explains cessation: not supported from this exploratory atlas; geometry and observation process dominate the current evidence.",
                "F. Data quality/censoring limits terminal-process claims: strong caution. Many fires have irregular observation gaps near the observed ending.",
                "Recommended next analysis: add VPD, wind, precipitation, fuel moisture, and climate normals; expand beyond the 25 candidate fires; compute climate on newly burned and advancing-boundary supports at a spatial resolution matched to the fire perimeters.",
            ],
        )


def image_to_data_uri(path: Path) -> str:
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{data}"


def render_html(paths: ReportPaths, availability: pd.DataFrame, summary: pd.DataFrame, qc: pd.DataFrame, figs: dict[str, Path]) -> None:
    sections = [
        ("Data availability", availability.to_html(index=False)),
        ("Summary", summary.to_html(index=False)),
        ("Quality control", qc.head(30).to_html(index=False)),
    ]
    fig_html = "\n".join(
        f"<section><h2>{name}</h2><img src='{image_to_data_uri(path)}' /></section>"
        for name, path in figs.items()
    )
    body = f"""
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Fire vase observed cessation exploratory report</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 32px; color: #111; }}
h1, h2 {{ margin-top: 1.4em; }}
img {{ max-width: 100%; border: 1px solid #ddd; }}
table {{ border-collapse: collapse; font-size: 12px; }}
td, th {{ border: 1px solid #ccc; padding: 4px 6px; text-align: left; }}
.note {{ background: #f5f5f5; padding: 12px; border-left: 4px solid #777; }}
</style>
</head>
<body>
<h1>Fire death atlas: observed cessation of detectable spatial growth</h1>
<p class="note">All cached candidate fires are treated as non-prescribed by assumption. The report does not infer physical extinction and does not compare prescribed versus non-prescribed fires.</p>
{''.join(f'<section><h2>{title}</h2>{html}</section>' for title, html in sections)}
{fig_html}
</body>
</html>
"""
    paths.html.write_text(body, encoding="utf-8")


def write_readme(outputs: Path) -> None:
    readme = outputs / "README_fire_vase_death_report.md"
    readme.write_text(
        """# Fire VASE observed-cessation exploratory report

Rerun from the repository root:

```bash
env MPLCONFIGDIR=/private/tmp/mplconfig .venv/bin/python examples/fire_vase_death_exploratory_report.py
```

The workflow uses cached FIRED candidate events under
`artifacts/fire-vase-gridmet-real/fired-cache/` and cached real gridMET tmmx
NetCDF files under `artifacts/fire-vase-gridmet-real/gridmet-cache/`.

Terminology: "fire death" is shorthand only. The report analyzes observed
cessation of detectable spatial growth, not independently verified physical
extinction.
""",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the fire VASE observed-cessation exploratory report.")
    parser.add_argument("--outputs", type=Path, default=Path("outputs"))
    parser.add_argument("--fire-cache-dir", type=Path, default=Path("artifacts/fire-vase-gridmet-real/fired-cache"))
    parser.add_argument("--candidates-csv", type=Path, default=Path("artifacts/fire-vase-gridmet-real/candidate_events.csv"))
    parser.add_argument("--gridmet-cache-dir", type=Path, default=Path("artifacts/fire-vase-gridmet-real/gridmet-cache"))
    args = parser.parse_args()

    np.random.seed(RNG_SEED)
    paths = make_paths(args.outputs)
    paths.outputs.mkdir(parents=True, exist_ok=True)
    paths.figures.mkdir(parents=True, exist_ok=True)

    print("loading inputs")
    daily, events, candidates = load_inputs(args.fire_cache_dir, args.candidates_csv)
    temp_k = load_temperature_years(args.gridmet_cache_dir, variable="tmmx")
    availability = data_availability_table(paths, daily, events, args.gridmet_cache_dir)
    availability.to_csv(paths.outputs / "fire_vase_data_availability.csv", index=False)

    print("building analysis tables")
    analysis, qc, features = build_analysis_table(daily, events, candidates, temp_k)
    summary = build_summary_table(analysis, features, qc)
    analysis.to_csv(paths.analysis_table, index=False)
    summary.to_csv(paths.summary_table, index=False)
    features.to_csv(paths.terminal_features, index=False)
    qc.to_csv(paths.quality_control, index=False)

    print("building figures")
    figs = build_figures(paths, daily, analysis, features, qc)
    print("rendering report")
    render_pdf(paths, availability, analysis, summary, features, qc, figs)
    render_html(paths, availability, summary, qc, figs)
    write_readme(paths.outputs)

    manifest = {
        "pdf": str(paths.pdf),
        "html": str(paths.html),
        "analysis_table": str(paths.analysis_table),
        "summary_table": str(paths.summary_table),
        "terminal_features": str(paths.terminal_features),
        "quality_control": str(paths.quality_control),
        "figures": {k: str(v) for k, v in figs.items()},
        "n_fires": int(features["fire_id"].nunique()),
        "n_fire_time_rows": int(len(analysis)),
    }
    (paths.outputs / "fire_vase_report_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
