"""Build a real-data fire developmental decision atlas.

The atlas intentionally avoids treating the final observed FIRED record as
physical extinction. It represents each cached candidate fire as a geometric
life history, detects developmental events from geometry, then asks how the
available daily gridMET variables relate to those events.
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
import yaml
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.colors import Normalize
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.signal import find_peaks
from scipy.spatial.distance import pdist, squareform

from cubedynamics.fire_time_hull import FireEventDaily, compute_time_hull_geometry


TITLE = "Fire developmental atlas: geometric life histories and environmental transitions"
PROJECTED_CRS_NOTE = "FIRED sinusoidal projected CRS, metre units"
EVIDENCE_LEVELS = [
    "strong descriptive evidence",
    "moderate descriptive evidence",
    "suggestive",
    "ambiguous",
    "unsupported with current data",
    "not testable with current data",
]


@dataclass(frozen=True)
class AtlasPaths:
    outputs: Path
    figures: Path
    pdf: Path
    html: Path
    time_table: Path
    traits: Path
    events: Path
    qc: Path
    candidate_results: Path
    manifest: Path


def make_paths(outputs: Path) -> AtlasPaths:
    return AtlasPaths(
        outputs=outputs,
        figures=outputs / "fire_vase_developmental_figures",
        pdf=outputs / "fire_vase_developmental_atlas.pdf",
        html=outputs / "fire_vase_developmental_atlas.html",
        time_table=outputs / "fire_vase_time_table.csv",
        traits=outputs / "fire_vase_developmental_traits.csv",
        events=outputs / "fire_vase_event_table.csv",
        qc=outputs / "fire_vase_qc_table.csv",
        candidate_results=outputs / "fire_vase_candidate_results.csv",
        manifest=outputs / "fire_vase_developmental_manifest.json",
    )


def load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    cfg.setdefault("activity_metric", "newly_added_area_km2")
    cfg.setdefault("secondary_activity_metric", "equivalent_radius_change_km")
    cfg.setdefault("lag_window", 3)
    cfg.setdefault("quiescence_length", 2)
    cfg.setdefault("relative_age_bins", 21)
    cfg.setdefault("candidate_clusters", [2, 3, 4])
    cfg.setdefault("minimum_active_observations", 2)
    cfg.setdefault("pulse_threshold", {})
    cfg["pulse_threshold"].setdefault("fixed_abs_km2", 0.10)
    cfg["pulse_threshold"].setdefault("within_fire_percentile", 0.75)
    cfg["pulse_threshold"].setdefault("fraction_of_peak", 0.25)
    cfg["pulse_threshold"].setdefault("prominence_fraction_of_peak", 0.20)
    cfg.setdefault(
        "climate_variables",
        {
            "tmmx": {"output_name": "tmmx_c", "units": "C"},
            "tmmn": {"output_name": "tmmn_c", "units": "C"},
            "vpd": {"output_name": "vpd_kpa", "units": "kPa"},
            "vs": {"output_name": "wind_speed_m_s", "units": "m/s"},
        },
    )
    cfg.setdefault("state_thresholds", {})
    cfg["state_thresholds"].setdefault("major_fraction_of_peak", 0.50)
    cfg["state_thresholds"].setdefault("active_fraction_of_peak", 0.25)
    return cfg


def load_inputs(cache_dir: Path, candidates_csv: Path) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame, pd.DataFrame]:
    daily_path = cache_dir / "fired_conus-ak_daily_nov2001-march2021.gpkg"
    event_path = cache_dir / "fired_conus-ak_events_nov2001-march2021.gpkg"
    if not daily_path.exists():
        raise FileNotFoundError(daily_path)
    if not event_path.exists():
        raise FileNotFoundError(event_path)
    if not candidates_csv.exists():
        raise FileNotFoundError(candidates_csv)

    candidates = pd.read_csv(candidates_csv)
    ids = set(candidates["event_id"].astype(int))
    daily = gpd.read_file(daily_path)
    events = gpd.read_file(event_path)
    daily = daily[daily["id"].isin(ids)].copy()
    events = events[events["id"].isin(ids)].copy()
    for frame in (daily, events):
        for col in ("date", "ig_date", "last_date"):
            if col in frame.columns:
                frame[col] = pd.to_datetime(frame[col])
    return daily, events, candidates


def gridmet_var_name(ds: xr.Dataset, variable: str) -> str:
    if variable in ds.data_vars:
        return variable
    for name, da in ds.data_vars.items():
        attrs = {k: str(v).lower() for k, v in da.attrs.items()}
        if variable.lower() in {attrs.get("long_name", ""), attrs.get("standard_name", "")}:
            return name
    if len(ds.data_vars) == 1:
        return next(iter(ds.data_vars))
    raise KeyError(f"Could not identify gridMET variable {variable!r} in {list(ds.data_vars)}")


def load_gridmet_dataarrays(cache_dir: Path, cfg: dict[str, Any]) -> dict[str, xr.DataArray]:
    arrays: dict[str, xr.DataArray] = {}
    missing: list[str] = []
    for variable in cfg["climate_variables"]:
        paths = sorted(cache_dir.glob(f"{variable}_*.nc"))
        if not paths:
            missing.append(variable)
            continue
        ds = xr.open_mfdataset([str(p) for p in paths], combine="by_coords", chunks={"day": 366})
        if "day" in ds.dims:
            ds = ds.rename({"day": "time"})
        var_name = gridmet_var_name(ds, variable)
        da = ds[var_name].sortby("time")
        da.name = cfg["climate_variables"][variable].get("output_name", variable)
        arrays[variable] = da
    if missing:
        raise FileNotFoundError(
            "Missing cached real gridMET files for: "
            + ", ".join(missing)
            + f" under {cache_dir}. Generate/cache them before running this real-data atlas."
        )
    return arrays


def convert_gridmet_values(values: np.ndarray, variable: str) -> np.ndarray:
    arr = np.asarray(values, dtype=float)
    if variable in {"tmmx", "tmmn"}:
        if np.isfinite(arr).any() and float(np.nanmedian(arr)) < 150:
            raise ValueError(f"{variable} does not look like Kelvin; refusing to label as Celsius.")
        return arr - 273.15
    return arr


def nearest_climate_series(
    arrays: dict[str, xr.DataArray],
    cfg: dict[str, Any],
    lon: float,
    lat: float,
    dates: pd.Series,
) -> dict[str, np.ndarray]:
    out: dict[str, np.ndarray] = {}
    time_index = pd.DatetimeIndex(pd.to_datetime(dates).to_numpy()).normalize()
    for variable, da in arrays.items():
        selected = da.sel(lon=float(lon), lat=float(lat), method="nearest")
        vals = selected.sel(time=time_index, method="nearest").values
        name = cfg["climate_variables"][variable].get("output_name", variable)
        out[name] = convert_gridmet_values(vals, variable)
    return out


def count_components(geom: Any) -> int:
    if geom is None or geom.is_empty:
        return 0
    if geom.geom_type == "MultiPolygon":
        return len(geom.geoms)
    return 1


def vase_width_km(geom: Any) -> float:
    """Diameter-like cross-sectional width: max projected bbox side in km."""
    if geom is None or geom.is_empty:
        return np.nan
    minx, miny, maxx, maxy = geom.bounds
    return float(max(maxx - minx, maxy - miny) / 1000.0)


def pixel_area_estimate(daily: gpd.GeoDataFrame) -> float:
    valid = daily[(daily["pixels"] > 0) & np.isfinite(daily["dy_ar_km2"])]
    if valid.empty:
        return 0.0
    return float(np.nanmedian(valid["dy_ar_km2"] / valid["pixels"]))


def build_time_table(
    daily: gpd.GeoDataFrame,
    events: gpd.GeoDataFrame,
    arrays: dict[str, xr.DataArray],
    cfg: dict[str, Any],
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    event_meta = events.set_index("id")
    lonlat = daily.to_crs("EPSG:4326")
    px_area = pixel_area_estimate(daily)

    for fire_id, group in daily.sort_values(["id", "date"]).groupby("id"):
        group = group.sort_values("date").copy()
        lonlat_group = lonlat.loc[group.index]
        dates = pd.to_datetime(group["date"]).dt.normalize()
        first = dates.min()
        terminal = dates.max()
        elapsed_days = (dates - first).dt.total_seconds() / 86400.0
        observed_duration_days = max(float((terminal - first).days), 0.0)
        gaps = dates.diff().dt.days.fillna(0).astype(int)
        event_row = event_meta.loc[fire_id]
        event_window_days = int(event_row.get("event_dur", len(group)))

        centroid_lon = np.array([geom.centroid.x for geom in lonlat_group.geometry], dtype=float)
        centroid_lat = np.array([geom.centroid.y for geom in lonlat_group.geometry], dtype=float)
        climate = nearest_climate_series(
            arrays,
            cfg,
            float(np.nanmedian(centroid_lon)),
            float(np.nanmedian(centroid_lat)),
            dates,
        )

        prev_area = np.nan
        prev_radius = np.nan
        prev_perimeter = np.nan
        prev_width = np.nan
        prev_centroid = None
        cumulative_volume = 0.0

        for obs_idx, (idx, row) in enumerate(group.iterrows()):
            geom = row.geometry
            area = float(row.get("tot_ar_km2", geom.area / 1e6))
            new_area = float(row.get("dy_ar_km2", geom.area / 1e6))
            perimeter = float(geom.length / 1000.0)
            compactness = float(4.0 * np.pi * max(geom.area, 0.0) / (geom.length**2)) if geom.length else np.nan
            width = vase_width_km(geom)
            radius = math.sqrt(max(area, 0.0) / math.pi)
            gap = int(gaps.iloc[obs_idx])
            if obs_idx == 0:
                volume_increment = 0.0
            else:
                volume_increment = float(np.nanmean([prev_area, area]) * max(gap, 1))
                cumulative_volume += volume_increment
            centroid = geom.centroid
            centroid_disp = 0.0 if prev_centroid is None else float(centroid.distance(prev_centroid) / 1000.0)

            out = {
                "fire_id": int(fire_id),
                "timestamp": pd.Timestamp(row["date"]).normalize(),
                "observation_index": int(obs_idx),
                "observation_count": int(len(group)),
                "gap_days_since_previous": int(gap),
                "elapsed_days": float(elapsed_days.iloc[obs_idx]),
                "relative_age_observed": float(elapsed_days.iloc[obs_idx] / observed_duration_days) if observed_duration_days > 0 else 0.0,
                "observed_sequence_duration_days": observed_duration_days,
                "candidate_event_window_days": event_window_days,
                "time_to_terminal_observed_days": float((pd.Timestamp(row["date"]).normalize() - terminal).days),
                "cumulative_area_km2": area,
                "newly_added_area_km2": new_area,
                "proportional_area_growth": new_area / area if area > 0 else np.nan,
                "perimeter_km": perimeter,
                "perimeter_change_km": perimeter - prev_perimeter if np.isfinite(prev_perimeter) else np.nan,
                "compactness": compactness,
                "equivalent_radius_km": radius,
                "equivalent_radius_change_km": radius - prev_radius if np.isfinite(prev_radius) else np.nan,
                "vase_width_km": width,
                "vase_width_change_km": width - prev_width if np.isfinite(prev_width) else np.nan,
                "centroid_x_m": float(centroid.x),
                "centroid_y_m": float(centroid.y),
                "centroid_lon": float(centroid_lon[obs_idx]),
                "centroid_lat": float(centroid_lat[obs_idx]),
                "centroid_displacement_km": centroid_disp,
                "polygon_components": count_components(geom),
                "space_time_volume_increment_km2_days": volume_increment,
                "space_time_volume_cumulative_km2_days": cumulative_volume,
                "pixel_area_estimate_km2": px_area,
                "is_first_observation": obs_idx == 0,
                "is_terminal_observed_record": obs_idx == len(group) - 1,
                "physical_extinction_observed": False,
                "date_source": "FIRED daily date column",
                "fire_source": "cached FIRED candidate event polygons",
            }
            for name, vals in climate.items():
                out[name] = float(vals[obs_idx])
            rows.append(out)
            prev_area = area
            prev_radius = radius
            prev_perimeter = perimeter
            prev_width = width
            prev_centroid = centroid

    time_table = pd.DataFrame(rows).sort_values(["fire_id", "timestamp"]).reset_index(drop=True)
    climate_cols = [meta.get("output_name", key) for key, meta in cfg["climate_variables"].items()]
    for col in climate_cols:
        time_table[f"{col}_change"] = time_table.groupby("fire_id")[col].diff()
        time_table[f"{col}_z_within_fire"] = time_table.groupby("fire_id")[col].transform(
            lambda s: (s - s.mean()) / (s.std(ddof=0) if s.std(ddof=0) else np.nan)
        )
        time_table[f"{col}_percentile_within_fire"] = time_table.groupby("fire_id")[col].rank(pct=True)
    return time_table


def local_maxima_indices(values: np.ndarray) -> set[int]:
    if len(values) == 0:
        return set()
    maxima: set[int] = set()
    for idx, val in enumerate(values):
        left = values[idx - 1] if idx > 0 else -np.inf
        right = values[idx + 1] if idx < len(values) - 1 else -np.inf
        if val >= left and val >= right:
            maxima.add(idx)
    return maxima


def detect_events_for_fire(fire: pd.DataFrame, cfg: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, Any]]:
    metric = cfg["activity_metric"]
    values = fire[metric].fillna(0).to_numpy(float)
    n = len(values)
    peak = float(np.nanmax(values)) if n else 0.0
    peak_idx = int(np.nanargmax(values)) if n else -1
    thresholds = cfg["pulse_threshold"]
    fixed_thr = float(thresholds["fixed_abs_km2"])
    percentile_thr = float(np.nanquantile(values, float(thresholds["within_fire_percentile"]))) if n else np.nan
    fraction_thr = float(peak * float(thresholds["fraction_of_peak"]))
    primary_thr = max(fixed_thr, fraction_thr)
    local_max = local_maxima_indices(values)

    methods: dict[str, set[int]] = {
        "fixed_absolute": {i for i, v in enumerate(values) if v >= fixed_thr and i in local_max},
        "within_fire_percentile": {i for i, v in enumerate(values) if v >= percentile_thr and i in local_max},
        "fraction_of_peak": {i for i, v in enumerate(values) if v >= fraction_thr and i in local_max},
        "prominence": set(),
    }
    if n >= 3 and peak > 0:
        peaks, _ = find_peaks(values, prominence=max(peak * float(thresholds["prominence_fraction_of_peak"]), 1e-9))
        methods["prominence"] = set(int(i) for i in peaks)
    if peak_idx >= 0 and peak > 0:
        methods["fraction_of_peak"].add(peak_idx)

    votes = np.zeros(n, dtype=int)
    for selected in methods.values():
        for idx in selected:
            if 0 <= idx < n:
                votes[idx] += 1
    robust_pulses = {i for i in range(n) if votes[i] >= 2}
    if peak_idx >= 0:
        robust_pulses.add(peak_idx)
    active = values >= primary_thr
    active_count = int(active.sum())
    final_meaningful_idx = int(max(np.flatnonzero(active))) if active.any() else peak_idx

    low_after = values <= primary_thr
    quiescence_idx = np.nan
    q_len = int(cfg["quiescence_length"])
    for idx in range(final_meaningful_idx + 1, n):
        if idx + q_len <= n and bool(np.all(low_after[idx : idx + q_len])):
            quiescence_idx = int(idx)
            break
    if not np.isfinite(quiescence_idx) and final_meaningful_idx < n - 1:
        quiescence_idx = int(final_meaningful_idx + 1)

    reactivation_indices: list[int] = []
    if np.isfinite(quiescence_idx):
        q = int(quiescence_idx)
        for idx in sorted(robust_pulses):
            if idx > q:
                reactivation_indices.append(int(idx))

    event_rows: list[dict[str, Any]] = []
    fire_id = int(fire["fire_id"].iloc[0])

    def add_event(kind: str, idx: int, confidence: str, methods_hit: list[str] | None = None) -> None:
        if idx < 0 or idx >= n:
            return
        row = fire.iloc[idx]
        event_rows.append(
            {
                "fire_id": fire_id,
                "event_type": kind,
                "observation_index": int(idx),
                "calendar_date": row["timestamp"],
                "relative_position_observed_sequence": float(row["relative_age_observed"]),
                "activity_metric": metric,
                "activity_magnitude": float(values[idx]),
                "activity_relative_to_peak": float(values[idx] / peak) if peak > 0 else np.nan,
                "confidence_or_robustness": confidence,
                "methods_supporting_event": ",".join(methods_hit or []),
                "threshold_fixed_abs_km2": fixed_thr,
                "threshold_within_fire_percentile_km2": percentile_thr,
                "threshold_fraction_peak_km2": fraction_thr,
                "terminal_observed_record_is_physical_extinction": False,
            }
        )

    add_event("first observed perimeter", 0, "observed", [])
    for idx in sorted(robust_pulses):
        hit = [name for name, selected in methods.items() if idx in selected]
        add_event("expansion pulse", int(idx), f"{votes[idx]}/4 threshold methods", hit)
    add_event("peak expansion", peak_idx, "observed maximum geometric activity", [name for name, selected in methods.items() if peak_idx in selected])
    add_event("final meaningful expansion", final_meaningful_idx, "threshold-defined final active observation", [name for name, selected in methods.items() if final_meaningful_idx in selected])
    if np.isfinite(quiescence_idx):
        add_event("transition into geometric quiescence", int(quiescence_idx), "rule-based sustained low activity", [])
    for idx in reactivation_indices:
        add_event("reactivation after quiescence", int(idx), f"{votes[idx]}/4 threshold methods after quiescence", [name for name, selected in methods.items() if idx in selected])
    add_event("terminal observed record", n - 1, "dataset-observed ending; not physical extinction", [])

    summary = {
        "peak_idx": peak_idx,
        "final_meaningful_idx": final_meaningful_idx,
        "quiescence_idx": int(quiescence_idx) if np.isfinite(quiescence_idx) else np.nan,
        "pulse_indices": sorted(int(i) for i in robust_pulses),
        "reactivation_indices": reactivation_indices,
        "peak_activity": peak,
        "primary_activity_threshold": primary_thr,
        "active_count": active_count,
        "pulse_votes": votes,
        "threshold_method_membership": {k: sorted(int(i) for i in v) for k, v in methods.items()},
    }
    return pd.DataFrame(event_rows), summary


def annotate_time_table(time_table: pd.DataFrame, event_table: pd.DataFrame, summaries: dict[int, dict[str, Any]], cfg: dict[str, Any]) -> pd.DataFrame:
    out = time_table.copy()
    for col in [
        "is_expansion_pulse",
        "is_peak_expansion",
        "is_final_meaningful_expansion",
        "is_quiescence_onset",
    ]:
        out[col] = False
    out["developmental_state"] = "low activity"
    for fire_id, summary in summaries.items():
        mask = out["fire_id"] == fire_id
        idxs = out.index[mask].to_numpy()
        if not len(idxs):
            continue
        peak = float(summary["peak_activity"])
        active_thr = max(float(summary["primary_activity_threshold"]), peak * float(cfg["state_thresholds"]["active_fraction_of_peak"]))
        major_thr = peak * float(cfg["state_thresholds"]["major_fraction_of_peak"])
        vals = out.loc[idxs, cfg["activity_metric"]].to_numpy(float)
        states = np.where(vals >= major_thr, "major expansion", np.where(vals >= active_thr, "active expansion", "low activity"))
        q_idx = summary.get("quiescence_idx")
        if np.isfinite(q_idx):
            states[int(q_idx) :] = np.where(vals[int(q_idx) :] >= active_thr, "reactivation", "quiescence")
        out.loc[idxs, "developmental_state"] = states
        for p in summary["pulse_indices"]:
            out.loc[idxs[p], "is_expansion_pulse"] = True
        out.loc[idxs[int(summary["peak_idx"])], "is_peak_expansion"] = True
        out.loc[idxs[int(summary["final_meaningful_idx"])], "is_final_meaningful_expansion"] = True
        if np.isfinite(q_idx):
            out.loc[idxs[int(q_idx)], "is_quiescence_onset"] = True
    return out


def build_event_and_trait_tables(time_table: pd.DataFrame, cfg: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame, dict[int, dict[str, Any]]]:
    event_frames: list[pd.DataFrame] = []
    summaries: dict[int, dict[str, Any]] = {}
    trait_rows: list[dict[str, Any]] = []

    for fire_id, fire in time_table.groupby("fire_id"):
        fire = fire.sort_values("observation_index").reset_index(drop=True)
        events, summary = detect_events_for_fire(fire, cfg)
        event_frames.append(events)
        summaries[int(fire_id)] = summary
        values = fire[cfg["activity_metric"]].fillna(0).to_numpy(float)
        peak_idx = int(summary["peak_idx"])
        final_idx = int(summary["final_meaningful_idx"])
        q_idx = summary["quiescence_idx"]
        pulse_indices = summary["pulse_indices"]
        final_area = float(fire["cumulative_area_km2"].iloc[-1])
        largest_pulse_idx = peak_idx
        largest_pulse_area = float(values[largest_pulse_idx]) if len(values) else np.nan
        area_before_peak = float(fire["cumulative_area_km2"].iloc[max(peak_idx - 1, 0)]) if len(fire) else np.nan
        area_after_final_major = final_area - float(fire["cumulative_area_km2"].iloc[final_idx]) if len(fire) else np.nan
        inter_pulse = np.diff(pulse_indices) if len(pulse_indices) >= 2 else np.array([])
        terminal_taper = float(values[-1] / summary["peak_activity"]) if summary["peak_activity"] > 0 else np.nan
        decline = summary["peak_activity"] - values[-1] if len(values) else np.nan
        rise = summary["peak_activity"] - values[0] if len(values) else np.nan
        trait_rows.append(
            {
                "fire_id": int(fire_id),
                "final_area_km2": final_area,
                "observation_count": int(len(fire)),
                "observed_duration_days": float(fire["observed_sequence_duration_days"].iloc[0]),
                "candidate_event_window_days": int(fire["candidate_event_window_days"].iloc[0]),
                "number_of_active_observations": int(summary["active_count"]),
                "active_fraction": float(summary["active_count"] / len(fire)) if len(fire) else np.nan,
                "peak_expansion_magnitude_km2": float(summary["peak_activity"]),
                "timing_of_peak_expansion_relative_age": float(fire.loc[peak_idx, "relative_age_observed"]),
                "final_meaningful_expansion_relative_age": float(fire.loc[final_idx, "relative_age_observed"]),
                "number_of_expansion_pulses": int(len(pulse_indices)),
                "pulse_prominence_km2": float(np.nanmax(values[pulse_indices]) - np.nanmedian(values)) if pulse_indices else np.nan,
                "pulse_duration_observations": int(len(pulse_indices)),
                "median_inter_pulse_interval_observations": float(np.median(inter_pulse)) if len(inter_pulse) else np.nan,
                "amount_of_growth_in_largest_pulse_km2": largest_pulse_area,
                "fraction_final_area_accumulated_before_peak": area_before_peak / final_area if final_area > 0 else np.nan,
                "fraction_final_area_accumulated_during_largest_pulse": largest_pulse_area / final_area if final_area > 0 else np.nan,
                "fraction_final_area_accumulated_after_final_major_pulse": area_after_final_major / final_area if final_area > 0 else np.nan,
                "quiescent_persistence_observations": int(len(fire) - q_idx) if np.isfinite(q_idx) else 0,
                "reactivation_count": int(len(summary["reactivation_indices"])),
                "terminal_taper_fraction_of_peak": terminal_taper,
                "growth_asymmetry_decline_minus_rise_km2": float(decline - rise) if np.isfinite(decline) and np.isfinite(rise) else np.nan,
                "geometric_trajectory_length_km2": float(np.nansum(np.abs(np.diff(values)))) if len(values) >= 2 else 0.0,
                "space_time_volume_km2_days": float(fire["space_time_volume_cumulative_km2_days"].iloc[-1]),
                "maximum_vase_width_km": float(fire["vase_width_km"].max()),
                "mean_compactness": float(fire["compactness"].mean()),
                "max_gap_days": int(fire["gap_days_since_previous"].max()),
                "terminal_observed_record_lag_after_final_meaningful_expansion_observations": int(len(fire) - 1 - final_idx),
                "terminal_observed_record_lag_after_final_meaningful_expansion_days": float(
                    (fire["timestamp"].iloc[-1] - fire["timestamp"].iloc[final_idx]).days
                ),
            }
        )
    event_table = pd.concat(event_frames, ignore_index=True).sort_values(["fire_id", "observation_index", "event_type"])
    traits = pd.DataFrame(trait_rows).sort_values("fire_id").reset_index(drop=True)
    return event_table, traits, summaries


def build_qc_table(time_table: pd.DataFrame, traits: pd.DataFrame, summaries: dict[int, dict[str, Any]], cfg: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    climate_cols = [meta.get("output_name", key) for key, meta in cfg["climate_variables"].items()]
    lag = int(cfg["lag_window"])
    for _, tr in traits.iterrows():
        fire_id = int(tr["fire_id"])
        fire = time_table[time_table["fire_id"] == fire_id].sort_values("observation_index")
        climate_complete = bool(fire[climate_cols].notna().all().all())
        obs = int(tr["observation_count"])
        pulse_n = int(tr["number_of_expansion_pulses"])
        max_gap = int(tr["max_gap_days"])
        peak_idx = int(summaries[fire_id]["peak_idx"])
        has_lag_window = peak_idx - lag >= 0 and peak_idx + lag < obs
        rows.append(
            {
                "fire_id": fire_id,
                "observation_count": obs,
                "observed_sequence_duration_days": float(tr["observed_duration_days"]),
                "candidate_event_window_days": int(tr["candidate_event_window_days"]),
                "max_gap_days": max_gap,
                "usable_transitions": max(obs - 1, 0),
                "climate_records": int(fire[climate_cols].notna().all(axis=1).sum()),
                "expansion_pulse_count": pulse_n,
                "usable_for_morphology": bool(obs >= 3),
                "usable_for_pulse_detection": bool(obs >= 4 and pulse_n >= 1),
                "usable_for_lag_analysis": bool(has_lag_window and climate_complete),
                "usable_for_terminal_observation_analysis": bool(obs >= 3 and max_gap <= 2),
                "usable_for_clustering": bool(obs >= 5),
                "usable_for_climate_transition_analysis": bool(pulse_n >= 1 and climate_complete and obs >= 5),
                "physical_cessation_inference_supported": False,
                "qc_note": "Task-specific flags; terminal analysis remains censored by observation timing.",
            }
        )
    return pd.DataFrame(rows)


def interp_trajectory(fire: pd.DataFrame, col: str, bins: np.ndarray) -> np.ndarray:
    x = fire["relative_age_observed"].to_numpy(float)
    y = fire[col].to_numpy(float)
    valid = np.isfinite(x) & np.isfinite(y)
    if valid.sum() < 2:
        return np.full_like(bins, np.nan, dtype=float)
    order = np.argsort(x[valid])
    return np.interp(bins, x[valid][order], y[valid][order])


def standardize_matrix(x: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    mean = np.nanmean(x, axis=0)
    std = np.nanstd(x, axis=0)
    std[std == 0] = 1.0
    z = (x - mean) / std
    z = np.nan_to_num(z, nan=0.0, posinf=0.0, neginf=0.0)
    return z, mean, std


def pca_numpy(x: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    z, _, _ = standardize_matrix(x)
    _, s, vt = np.linalg.svd(z, full_matrices=False)
    scores = z @ vt.T
    variance = (s**2) / max(z.shape[0] - 1, 1)
    explained = variance / variance.sum() if variance.sum() else np.zeros_like(variance)
    return scores, vt, explained


def silhouette_score_manual(x: np.ndarray, labels: np.ndarray) -> float:
    labels = np.asarray(labels)
    if len(set(labels)) < 2 or len(set(labels)) >= len(labels):
        return np.nan
    dist = squareform(pdist(x, metric="euclidean"))
    scores = []
    for i in range(len(x)):
        same = labels == labels[i]
        a = float(np.mean(dist[i, same & (np.arange(len(x)) != i)])) if same.sum() > 1 else 0.0
        b = np.inf
        for lab in sorted(set(labels) - {labels[i]}):
            b = min(b, float(np.mean(dist[i, labels == lab])))
        scores.append((b - a) / max(a, b) if max(a, b) > 0 else 0.0)
    return float(np.mean(scores))


def build_geometry_representations(time_table: pd.DataFrame, traits: pd.DataFrame, cfg: dict[str, Any]) -> dict[str, Any]:
    bins = np.linspace(0, 1, int(cfg["relative_age_bins"]))
    cols = ["newly_added_area_km2", "proportional_area_growth", "vase_width_km", "perimeter_change_km", "compactness"]
    fire_ids = traits["fire_id"].to_numpy(int)
    trajectories = []
    for fire_id in fire_ids:
        fire = time_table[time_table["fire_id"] == fire_id].sort_values("observation_index")
        vecs = []
        for col in cols:
            arr = interp_trajectory(fire, col, bins)
            if col in {"newly_added_area_km2", "vase_width_km"}:
                scale = np.nanmax(np.abs(arr))
                arr = arr / scale if np.isfinite(scale) and scale > 0 else arr
            vecs.append(arr)
        trajectories.append(np.concatenate(vecs))
    trajectory_matrix = np.vstack(trajectories)
    trait_cols = [
        "final_area_km2",
        "observed_duration_days",
        "active_fraction",
        "peak_expansion_magnitude_km2",
        "timing_of_peak_expansion_relative_age",
        "final_meaningful_expansion_relative_age",
        "number_of_expansion_pulses",
        "terminal_taper_fraction_of_peak",
        "geometric_trajectory_length_km2",
        "space_time_volume_km2_days",
        "maximum_vase_width_km",
        "mean_compactness",
    ]
    trait_matrix = traits[trait_cols].to_numpy(float)
    trait_matrix = np.nan_to_num(trait_matrix, nan=np.nanmedian(trait_matrix, axis=0))
    return {"bins": bins, "trajectory_cols": cols, "fire_ids": fire_ids, "trajectory_matrix": trajectory_matrix, "trait_cols": trait_cols, "trait_matrix": trait_matrix}


def cluster_geometry(reps: dict[str, Any], cfg: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    z, _, _ = standardize_matrix(reps["trait_matrix"])
    link = linkage(z, method="ward")
    cluster_rows: list[dict[str, Any]] = []
    label_table = pd.DataFrame({"fire_id": reps["fire_ids"]})
    best = {"k": None, "silhouette": -np.inf, "labels": None}
    for k in cfg["candidate_clusters"]:
        labels = fcluster(link, int(k), criterion="maxclust")
        sil = silhouette_score_manual(z, labels)
        cluster_rows.append({"representation": "derived developmental traits", "method": "hierarchical ward", "candidate_k": int(k), "silhouette_width": sil, "n_fires": len(labels)})
        label_table[f"profile_k{k}"] = labels
        if np.isfinite(sil) and sil > best["silhouette"]:
            best = {"k": int(k), "silhouette": sil, "labels": labels}
    if best["labels"] is None:
        best = {"k": np.nan, "silhouette": np.nan, "labels": np.ones(len(reps["fire_ids"]), dtype=int)}
    label_table["selected_profile"] = [f"Profile {chr(64 + int(v))}" for v in best["labels"]]
    return label_table, pd.DataFrame(cluster_rows), best


def event_centered_table(time_table: pd.DataFrame, event_table: pd.DataFrame, cfg: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    lag_window = int(cfg["lag_window"])
    climate_cols = [meta.get("output_name", key) for key, meta in cfg["climate_variables"].items()]
    event_types = [
        "first observed perimeter",
        "expansion pulse",
        "peak expansion",
        "final meaningful expansion",
        "transition into geometric quiescence",
        "terminal observed record",
    ]
    for _, event in event_table[event_table["event_type"].isin(event_types)].iterrows():
        fire = time_table[time_table["fire_id"] == event["fire_id"]].sort_values("observation_index").reset_index(drop=True)
        idx = int(event["observation_index"])
        for lag in range(-lag_window, lag_window + 1):
            j = idx + lag
            if j < 0 or j >= len(fire):
                continue
            row = fire.iloc[j]
            out = {
                "fire_id": int(event["fire_id"]),
                "anchor_event_type": event["event_type"],
                "anchor_observation_index": idx,
                "lag_observations": lag,
                "lag_days": float((row["timestamp"] - fire.iloc[idx]["timestamp"]).days),
                "activity_value": float(row[cfg["activity_metric"]]),
                "developmental_state": row["developmental_state"],
            }
            for col in climate_cols:
                out[col] = float(row[col])
                out[f"{col}_z_within_fire"] = float(row[f"{col}_z_within_fire"])
                out[f"{col}_change"] = float(row[f"{col}_change"]) if np.isfinite(row[f"{col}_change"]) else np.nan
            rows.append(out)
    return pd.DataFrame(rows)


def alignment_quality_table(time_table: pd.DataFrame, event_table: pd.DataFrame, cfg: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    lag_window = int(cfg["lag_window"])
    clocks = [
        "first observed perimeter",
        "peak expansion",
        "final meaningful expansion",
        "transition into geometric quiescence",
        "terminal observed record",
    ]
    climate_cols = [meta.get("output_name", key) for key, meta in cfg["climate_variables"].items()]
    for clock in clocks:
        centered = event_centered_table(time_table, event_table[event_table["event_type"] == clock], cfg)
        if centered.empty:
            rows.append({"alignment_clock": clock, "n_fires": 0, "geometric_peak_concentration_within_1_obs": np.nan, "mean_among_fire_activity_variance": np.nan, "environmental_direction_consistency": np.nan, "minimum_lag_sample_size": 0})
            continue
        n_fires = centered["fire_id"].nunique()
        peak_events = event_table[event_table["event_type"] == "peak expansion"][["fire_id", "observation_index"]].rename(columns={"observation_index": "peak_idx"})
        anchor_events = event_table[event_table["event_type"] == clock][["fire_id", "observation_index"]].drop_duplicates("fire_id").rename(columns={"observation_index": "anchor_idx"})
        merged = anchor_events.merge(peak_events, on="fire_id", how="inner")
        peak_conc = float((np.abs(merged["peak_idx"] - merged["anchor_idx"]) <= 1).mean()) if len(merged) else np.nan
        variances = centered.groupby("lag_observations")["activity_value"].var()
        min_n = int(centered.groupby("lag_observations")["fire_id"].nunique().min())
        direction_scores = []
        for col in climate_cols:
            lag0 = centered[centered["lag_observations"] == 0][["fire_id", col]]
            lagm1 = centered[centered["lag_observations"] == -1][["fire_id", col]]
            pair = lag0.merge(lagm1, on="fire_id", suffixes=("_0", "_m1"))
            if len(pair):
                signs = np.sign(pair[f"{col}_0"] - pair[f"{col}_m1"])
                direction_scores.append(float(max((signs > 0).mean(), (signs < 0).mean())))
        rows.append(
            {
                "alignment_clock": clock,
                "n_fires": int(n_fires),
                "geometric_peak_concentration_within_1_obs": peak_conc,
                "mean_among_fire_activity_variance": float(variances.mean()) if len(variances) else np.nan,
                "environmental_direction_consistency": float(np.nanmean(direction_scores)) if direction_scores else np.nan,
                "minimum_lag_sample_size": min_n,
                "question_answered": "Which event provides the most coherent fire-centered clock?",
            }
        )
    out = pd.DataFrame(rows)
    out["alignment_rank_for_geometry"] = out["geometric_peak_concentration_within_1_obs"].rank(ascending=False, method="min")
    return out


def ensure_fig(path: Path, fig: plt.Figure, dpi: int = 180) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=dpi, bbox_inches="tight")
    try:
        fig.savefig(path.with_suffix(".svg"), bbox_inches="tight")
    except Exception:
        pass
    plt.close(fig)
    return path


def plot_observational_raster(time_table: pd.DataFrame, event_table: pd.DataFrame, paths: AtlasPaths, cfg: dict[str, Any]) -> Path:
    fires = sorted(time_table["fire_id"].unique())
    start = time_table["timestamp"].min()
    end = time_table["timestamp"].max()
    all_dates = pd.date_range(start, end, freq="D")
    fig, ax = plt.subplots(figsize=(15, 8))
    for y, fire_id in enumerate(fires):
        fire = time_table[time_table["fire_id"] == fire_id]
        dates = set(pd.to_datetime(fire["timestamp"]))
        xs_obs = [(d - start).days for d in dates]
        ax.scatter(xs_obs, [y] * len(xs_obs), s=18, color="#33658a", label="observed perimeter date" if y == 0 else None, zorder=2)
        missing = [d for d in pd.date_range(fire["timestamp"].min(), fire["timestamp"].max(), freq="D") if d not in dates]
        if missing:
            ax.scatter([(d - start).days for d in missing], [y] * len(missing), s=9, color="#dddddd", marker="s", label="missing date inside observed sequence" if y == 0 else None, zorder=1)
        scale = np.sqrt(np.maximum(fire[cfg["activity_metric"]], 0)) * 16 + 10
        ax.scatter([(d - start).days for d in fire["timestamp"]], [y] * len(fire), s=scale, facecolors="none", edgecolors="#f26419", linewidths=0.8, label="newly added area magnitude" if y == 0 else None, zorder=3)
    markers = {
        "terminal observed record": ("v", "#222222"),
        "peak expansion": ("*", "#d62828"),
        "final meaningful expansion": ("D", "#2a9d8f"),
    }
    for event_type, (marker, color) in markers.items():
        sub = event_table[event_table["event_type"] == event_type]
        for _, event in sub.iterrows():
            y = fires.index(int(event["fire_id"]))
            x = (pd.Timestamp(event["calendar_date"]) - start).days
            ax.scatter([x], [y], marker=marker, color=color, s=50, label=event_type if y == 0 else None, zorder=4)
    ticks = np.linspace(0, len(all_dates) - 1, 8).astype(int)
    ax.set_xticks([(all_dates[i] - start).days for i in ticks])
    ax.set_xticklabels([all_dates[i].strftime("%Y-%m-%d") for i in ticks], rotation=30, ha="right")
    ax.set_yticks(range(len(fires)))
    ax.set_yticklabels(fires, fontsize=7)
    ax.set_ylabel("fire id")
    ax.set_title(f"Observation structure, gaps, and developmental markers (n={len(fires)} fires)")
    ax.legend(loc="upper right", fontsize=8)
    ax.grid(axis="x", alpha=0.2)
    return ensure_fig(paths.figures / "01_observational_structure_raster.png", fig)


def plot_activity_correlations(time_table: pd.DataFrame, paths: AtlasPaths) -> Path:
    cols = [
        "newly_added_area_km2",
        "proportional_area_growth",
        "equivalent_radius_change_km",
        "perimeter_change_km",
        "vase_width_change_km",
        "space_time_volume_increment_km2_days",
    ]
    corr = time_table[cols].corr(method="spearman")
    fig, axes = plt.subplots(1, 2, figsize=(15, 6), gridspec_kw={"width_ratios": [1, 1.2]})
    im = axes[0].imshow(corr, vmin=-1, vmax=1, cmap="coolwarm")
    axes[0].set_xticks(range(len(cols)), [c.replace("_", "\n") for c in cols], rotation=45, ha="right", fontsize=8)
    axes[0].set_yticks(range(len(cols)), [c.replace("_", "\n") for c in cols], fontsize=8)
    for i in range(len(cols)):
        for j in range(len(cols)):
            axes[0].text(j, i, f"{corr.iloc[i, j]:.2f}", ha="center", va="center", fontsize=7)
    fig.colorbar(im, ax=axes[0], label="Spearman correlation")
    axes[0].set_title("Candidate activity metric correlations")
    axes[1].scatter(time_table["newly_added_area_km2"], time_table["vase_width_change_km"], c=time_table["proportional_area_growth"], cmap="plasma", s=25, alpha=0.8)
    axes[1].set_xscale("symlog", linthresh=0.1)
    axes[1].axhline(0, color="#999999", linewidth=0.8)
    axes[1].set_xlabel("newly added area (km2), symlog")
    axes[1].set_ylabel("vase width change (km)")
    axes[1].set_title("Rendered width is related, but not identical, to area growth")
    return ensure_fig(paths.figures / "02_activity_metric_correlations.png", fig)


def plot_event_sensitivity(event_table: pd.DataFrame, paths: AtlasPaths) -> Path:
    pulses = event_table[event_table["event_type"] == "expansion pulse"].copy()
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    if not pulses.empty:
        counts = pulses["confidence_or_robustness"].value_counts().sort_index()
        axes[0].bar(counts.index, counts.values, color="#2a9d8f")
        axes[0].set_ylabel("pulse events")
        axes[0].tick_params(axis="x", rotation=30)
        axes[1].scatter(pulses["activity_relative_to_peak"], pulses["relative_position_observed_sequence"], c=pulses["activity_magnitude"], cmap="plasma", s=45)
        axes[1].set_xlabel("activity relative to fire-specific peak")
        axes[1].set_ylabel("relative position in observed sequence")
        axes[1].set_title("Expansion-pulse timing and magnitude")
    for ax in axes:
        ax.grid(alpha=0.2)
    fig.suptitle("Pulse detection sensitivity across fixed, percentile, peak-fraction, and prominence rules")
    return ensure_fig(paths.figures / "03_event_detection_sensitivity.png", fig)


def plot_profile_page(pdf: PdfPages, fire: pd.DataFrame, event_table: pd.DataFrame, daily: gpd.GeoDataFrame, cfg: dict[str, Any]) -> None:
    fire_id = int(fire["fire_id"].iloc[0])
    events = event_table[event_table["fire_id"] == fire_id]
    climate_cols = [meta.get("output_name", key) for key, meta in cfg["climate_variables"].items()]
    labels = {
        "cumulative_area_km2": "cumulative area (km2)",
        "newly_added_area_km2": "newly added area (km2)",
        "proportional_area_growth": "proportional growth",
        "compactness": "compactness",
        "tmmx_c": "maximum temperature (C)",
        "tmmn_c": "minimum temperature (C)",
        "vpd_kpa": "VPD (kPa)",
        "wind_speed_m_s": "wind speed (m/s)",
    }
    cols = ["cumulative_area_km2", "newly_added_area_km2", "proportional_area_growth", "compactness"] + climate_cols
    cols = [c for c in cols if c in fire.columns][:8]
    fig = plt.figure(figsize=(15, 8.5))
    grid = fig.add_gridspec(len(cols), 5, left=0.06, right=0.98, top=0.90, bottom=0.08, wspace=0.35, hspace=0.12)
    x = pd.to_datetime(fire["timestamp"])
    marker_map = {
        "first observed perimeter": ("|", "#111111"),
        "peak expansion": ("*", "#d62828"),
        "final meaningful expansion": ("D", "#2a9d8f"),
        "transition into geometric quiescence": ("s", "#6a4c93"),
        "terminal observed record": ("v", "#111111"),
    }
    for row_idx, col in enumerate(cols):
        ax = fig.add_subplot(grid[row_idx, :4])
        color = "#33658a" if col not in climate_cols else "#588157"
        ax.plot(x, fire[col], color=color, linewidth=1.5)
        ax.scatter(x, fire[col], color=color, s=24, zorder=3)
        for event_type, (marker, event_color) in marker_map.items():
            for _, ev in events[events["event_type"] == event_type].iterrows():
                ev_date = pd.Timestamp(ev["calendar_date"])
                ax.axvline(ev_date, color=event_color, linewidth=0.8, alpha=0.55)
                if col == cols[0]:
                    ax.scatter([ev_date], [fire[col].max()], marker=marker, color=event_color, s=45, zorder=4)
        ax.set_ylabel(labels.get(col, col), fontsize=8)
        ax.grid(alpha=0.2)
        if row_idx != len(cols) - 1:
            ax.set_xticklabels([])
    ax_vase = fig.add_subplot(grid[:, 4], projection="3d")
    try:
        event = FireEventDaily.from_fired(daily, fire_id, date_col="date")
        hull = compute_time_hull_geometry(event, n_ring_samples=48, n_theta=48)
        verts = np.asarray(hull.verts_km, dtype=float)
        faces = [verts[tri] for tri in np.asarray(hull.tris, dtype=int)]
        poly = Poly3DCollection(faces, facecolors="#b41616", edgecolors="#222222", linewidths=0.08, alpha=0.92)
        ax_vase.add_collection3d(poly)
        center = (np.nanmin(verts, axis=0) + np.nanmax(verts, axis=0)) / 2
        span = max(float(np.nanmax(np.nanmax(verts, axis=0) - np.nanmin(verts, axis=0))), 1.0)
        ax_vase.set_xlim(center[0] - span * 0.55, center[0] + span * 0.55)
        ax_vase.set_ylim(center[1] - span * 0.55, center[1] + span * 0.55)
        ax_vase.set_zlim(0, np.nanmax(verts[:, 2]) + span * 0.25)
        ax_vase.view_init(elev=18, azim=-62)
        ax_vase.set_box_aspect((1, 1, 1.4))
    except Exception as exc:
        ax_vase.text2D(0.1, 0.5, f"VASE failed:\n{exc}", transform=ax_vase.transAxes, fontsize=8)
    ax_vase.set_axis_off()
    fig.suptitle(
        f"Fire {fire_id}: observed developmental profile; final meaningful expansion != terminal observed record != physical extinction",
        fontsize=14,
        fontweight="bold",
    )
    pdf.savefig(fig)
    plt.close(fig)


def plot_alignment_comparison(time_table: pd.DataFrame, event_table: pd.DataFrame, paths: AtlasPaths, cfg: dict[str, Any]) -> tuple[Path, pd.DataFrame]:
    centered = event_centered_table(time_table, event_table, cfg)
    clocks = ["first observed perimeter", "peak expansion", "final meaningful expansion", "transition into geometric quiescence", "terminal observed record"]
    metrics = [cfg["activity_metric"], "tmmx_c_z_within_fire", "tmmn_c_z_within_fire", "vpd_kpa_z_within_fire", "wind_speed_m_s_z_within_fire"]
    labels = ["activity", "tmmx z", "tmmn z", "VPD z", "wind z"]
    fig, axes = plt.subplots(len(metrics), len(clocks), figsize=(18, 12), sharex=True)
    for c_idx, clock in enumerate(clocks):
        sub_clock = centered[centered["anchor_event_type"] == clock]
        for r_idx, (metric, label) in enumerate(zip(metrics, labels)):
            ax = axes[r_idx, c_idx]
            if metric == cfg["activity_metric"]:
                col = "activity_value"
            else:
                col = metric
            for _, fire in sub_clock.groupby("fire_id"):
                ax.plot(fire["lag_observations"], fire[col], color="#9ecae1", alpha=0.35, linewidth=0.8)
            grouped = sub_clock.groupby("lag_observations")[col]
            med = grouped.median()
            q1 = grouped.quantile(0.25)
            q3 = grouped.quantile(0.75)
            ax.plot(med.index, med.values, color="#111111", linewidth=1.8)
            ax.fill_between(med.index, q1.values, q3.values, color="#999999", alpha=0.25)
            ax.axvline(0, color="#d62828", linewidth=0.8)
            ax.grid(alpha=0.2)
            if r_idx == 0:
                ax.set_title(clock, fontsize=9)
            if c_idx == 0:
                ax.set_ylabel(label)
            if r_idx == len(metrics) - 1:
                ax.set_xlabel("observation lag")
            ax.text(0.02, 0.86, f"n={sub_clock['fire_id'].nunique()}", transform=ax.transAxes, fontsize=7)
    fig.suptitle("Which event provides the most coherent fire-centered clock?", fontsize=16, fontweight="bold")
    path = ensure_fig(paths.figures / "04_alignment_comparison_grid.png", fig)
    return path, centered


def plot_alignment_quality(quality: pd.DataFrame, paths: AtlasPaths) -> Path:
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    y = np.arange(len(quality))
    axes[0].barh(y, quality["geometric_peak_concentration_within_1_obs"], color="#2a9d8f")
    axes[0].set_title("Peak concentration")
    axes[1].barh(y, quality["environmental_direction_consistency"], color="#588157")
    axes[1].set_title("Environmental direction consistency")
    axes[2].barh(y, quality["minimum_lag_sample_size"], color="#33658a")
    axes[2].set_title("Minimum lag sample size")
    for ax in axes:
        ax.set_yticks(y, quality["alignment_clock"])
        ax.grid(axis="x", alpha=0.2)
    fig.suptitle("Alignment quality summary")
    return ensure_fig(paths.figures / "05_alignment_quality_rankings.png", fig)


def plot_trait_panels(traits: pd.DataFrame, paths: AtlasPaths) -> Path:
    groups = {
        "size": ["final_area_km2", "maximum_vase_width_km", "space_time_volume_km2_days"],
        "tempo": ["observed_duration_days", "active_fraction", "timing_of_peak_expansion_relative_age"],
        "pulse structure": ["number_of_expansion_pulses", "peak_expansion_magnitude_km2", "pulse_prominence_km2"],
        "persistence": ["quiescent_persistence_observations", "reactivation_count", "terminal_taper_fraction_of_peak"],
        "shape": ["mean_compactness", "geometric_trajectory_length_km2", "growth_asymmetry_decline_minus_rise_km2"],
    }
    fig, axes = plt.subplots(len(groups), 3, figsize=(14, 12))
    for r, (group, cols) in enumerate(groups.items()):
        for c, col in enumerate(cols):
            ax = axes[r, c]
            vals = traits[col].replace([np.inf, -np.inf], np.nan).dropna()
            if vals.empty:
                ax.text(0.5, 0.5, "no data", ha="center")
            else:
                ax.hist(vals, bins=min(10, max(4, len(vals) // 2)), color="#6a994e", alpha=0.85)
                if vals.min() > 0 and vals.max() / vals.min() > 20:
                    ax.set_xscale("log")
            ax.set_title(f"{group}: {col}", fontsize=8)
            ax.grid(alpha=0.2)
    fig.suptitle("Geometric life-history traits organized by scientific role", fontsize=15, fontweight="bold")
    return ensure_fig(paths.figures / "06_developmental_trait_panels.png", fig)


def plot_clustering_and_pca(traits: pd.DataFrame, labels: pd.DataFrame, cluster_scores: pd.DataFrame, reps: dict[str, Any], paths: AtlasPaths) -> tuple[Path, Path, pd.DataFrame]:
    scores, loadings, explained = pca_numpy(reps["trait_matrix"])
    pca_cols = reps["trait_cols"]
    pca_loadings = pd.DataFrame(
        {
            "variable": pca_cols,
            "PC1_loading": loadings[0, : len(pca_cols)],
            "PC2_loading": loadings[1, : len(pca_cols)] if loadings.shape[0] > 1 else np.nan,
        }
    )
    merged = labels.merge(traits[["fire_id", "final_area_km2"]], on="fire_id", how="left")
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    axes[0].plot(cluster_scores["candidate_k"], cluster_scores["silhouette_width"], marker="o", color="#33658a")
    axes[0].axhline(0.25, color="#d62828", linestyle="--", linewidth=0.8, label="weak stability guide")
    axes[0].set_xlabel("candidate k")
    axes[0].set_ylabel("silhouette width")
    axes[0].set_title("Do discrete geometry-only profiles stabilize?")
    axes[0].legend()
    for profile, sub in merged.groupby("selected_profile"):
        axes[1].scatter(sub["final_area_km2"], sub["fire_id"], label=f"{profile} (n={len(sub)})", s=45)
    axes[1].set_xscale("log")
    axes[1].set_xlabel("final area (km2, log)")
    axes[1].set_ylabel("fire id")
    axes[1].set_title("Selected transparent grouping, shown against size")
    axes[1].legend(fontsize=8)
    cluster_path = ensure_fig(paths.figures / "07_geometry_clustering.png", fig)

    fig, axes = plt.subplots(1, 2, figsize=(15, 6), gridspec_kw={"width_ratios": [1.2, 1]})
    sc = axes[0].scatter(scores[:, 0], scores[:, 1], c=np.log10(traits["final_area_km2"]), cmap="plasma", s=60)
    for i, fire_id in enumerate(reps["fire_ids"]):
        axes[0].text(scores[i, 0], scores[i, 1], str(fire_id), fontsize=6)
    axes[0].set_xlabel(f"PC1 ({explained[0] * 100:.1f}% variance)")
    axes[0].set_ylabel(f"PC2 ({explained[1] * 100:.1f}% variance)" if len(explained) > 1 else "PC2")
    axes[0].set_title("Continuous geometry-only developmental axes")
    fig.colorbar(sc, ax=axes[0], label="log10 final area")
    top_load = pca_loadings.assign(abs_pc1=lambda d: d["PC1_loading"].abs()).sort_values("abs_pc1", ascending=False).head(10)
    axes[1].barh(top_load["variable"], top_load["PC1_loading"], color="#2a9d8f")
    axes[1].axvline(0, color="#111111", linewidth=0.8)
    axes[1].set_title("PC1 loadings: what drives the axis?")
    pca_path = ensure_fig(paths.figures / "08_continuous_axes_pca.png", fig)
    return cluster_path, pca_path, pca_loadings


def plot_event_centered_climate(centered: pd.DataFrame, paths: AtlasPaths) -> Path:
    variables = ["tmmx_c_z_within_fire", "tmmn_c_z_within_fire", "vpd_kpa_z_within_fire", "wind_speed_m_s_z_within_fire"]
    labels = ["tmmx z", "tmmn z", "VPD z", "wind z"]
    anchors = ["expansion pulse", "peak expansion", "transition into geometric quiescence"]
    fig, axes = plt.subplots(len(variables), len(anchors), figsize=(15, 11), sharex=True)
    for c, anchor in enumerate(anchors):
        sub = centered[centered["anchor_event_type"] == anchor]
        for r, (var, lab) in enumerate(zip(variables, labels)):
            ax = axes[r, c]
            for _, fire in sub.groupby("fire_id"):
                ax.plot(fire["lag_observations"], fire[var], color="#8ecae6", alpha=0.35, linewidth=0.8)
            grouped = sub.groupby("lag_observations")[var]
            med = grouped.median()
            q1 = grouped.quantile(0.25)
            q3 = grouped.quantile(0.75)
            ax.plot(med.index, med.values, color="#111111", linewidth=1.8)
            ax.fill_between(med.index, q1.values, q3.values, color="#999999", alpha=0.22)
            ax.axvline(0, color="#d62828", linewidth=0.8)
            ax.text(0.02, 0.86, f"events={sub[['fire_id','anchor_observation_index']].drop_duplicates().shape[0]}", transform=ax.transAxes, fontsize=7)
            ax.grid(alpha=0.2)
            if r == 0:
                ax.set_title(anchor)
            if c == 0:
                ax.set_ylabel(lab)
            if r == len(variables) - 1:
                ax.set_xlabel("observation lag")
    fig.suptitle("Environment around geometry-defined developmental events", fontsize=15, fontweight="bold")
    return ensure_fig(paths.figures / "09_event_centered_climate.png", fig)


def plot_environmental_roles(time_table: pd.DataFrame, paths: AtlasPaths) -> Path:
    variables = ["tmmx_c", "tmmn_c", "vpd_kpa", "wind_speed_m_s"]
    rows = []
    for col in variables:
        for fire_id, fire in time_table.groupby("fire_id"):
            vals = fire.sort_values("observation_index")[col].to_numpy(float)
            if len(vals) >= 2:
                rows.append(
                    {
                        "variable": col,
                        "fire_id": fire_id,
                        "step_sd": float(np.nanstd(np.diff(vals))),
                        "lag1_autocorr": float(pd.Series(vals).autocorr(lag=1)) if len(vals) >= 3 else np.nan,
                        "within_fire_sd": float(np.nanstd(vals)),
                    }
                )
    env = pd.DataFrame(rows)
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    for ax, metric, title in zip(axes, ["step_sd", "lag1_autocorr", "within_fire_sd"], ["step-to-step variability", "lag-1 autocorrelation", "within-fire spread"]):
        data = [env.loc[env["variable"] == v, metric].dropna() for v in variables]
        ax.boxplot(data, tick_labels=["tmmx", "tmmn", "VPD", "wind"])
        ax.set_title(title)
        ax.grid(axis="y", alpha=0.2)
    fig.suptitle("Do climate variables play different temporal roles?")
    return ensure_fig(paths.figures / "10_environmental_roles.png", fig)


def plot_compound_conditions(time_table: pd.DataFrame, paths: AtlasPaths, cfg: dict[str, Any]) -> Path:
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    states = time_table["developmental_state"].isin(["active expansion", "major expansion", "reactivation"])
    axes[0].scatter(time_table["vpd_kpa"], time_table["wind_speed_m_s"], c=states.map({True: "#d62828", False: "#9aa0a6"}), s=35, alpha=0.75)
    axes[0].set_xlabel("VPD (kPa)")
    axes[0].set_ylabel("wind speed (m/s)")
    axes[0].set_title("High VPD + wind")
    axes[1].scatter(time_table["tmmx_c"], time_table["vpd_kpa"], c=time_table[cfg["activity_metric"]], cmap="plasma", s=35, alpha=0.8)
    axes[1].set_xlabel("tmmx (C)")
    axes[1].set_ylabel("VPD (kPa)")
    axes[1].set_title("Warm + dry state")
    axes[2].scatter(time_table["vpd_kpa_change"], time_table["wind_speed_m_s"], c=states.map({True: "#d62828", False: "#9aa0a6"}), s=35, alpha=0.75)
    axes[2].axvline(0, color="#111111", linewidth=0.8)
    axes[2].set_xlabel("change in VPD since previous observation")
    axes[2].set_ylabel("wind speed (m/s)")
    axes[2].set_title("Rising VPD + wind")
    for ax in axes:
        ax.grid(alpha=0.2)
    n_fires = time_table["fire_id"].nunique()
    fig.suptitle(f"Transparent compound-condition displays; no large model forced on {n_fires} fires")
    return ensure_fig(paths.figures / "11_compound_conditions.png", fig)


def plot_state_transitions(time_table: pd.DataFrame, paths: AtlasPaths) -> tuple[Path, pd.DataFrame]:
    transitions: list[dict[str, Any]] = []
    for fire_id, fire in time_table.groupby("fire_id"):
        states = fire.sort_values("observation_index")["developmental_state"].tolist()
        for a, b in zip(states[:-1], states[1:]):
            transitions.append({"fire_id": fire_id, "from_state": a, "to_state": b})
        if states:
            transitions.append({"fire_id": fire_id, "from_state": states[-1], "to_state": "terminal observed record"})
    table = pd.DataFrame(transitions)
    counts = table.groupby(["from_state", "to_state"]).size().unstack(fill_value=0)
    probs = counts.div(counts.sum(axis=1).replace(0, np.nan), axis=0)
    fig, axes = plt.subplots(1, 2, figsize=(15, 6))
    im0 = axes[0].imshow(counts, cmap="Blues")
    axes[0].set_title("transition counts")
    im1 = axes[1].imshow(probs, cmap="Greens", vmin=0, vmax=1)
    axes[1].set_title("row-normalized transition probabilities")
    for ax, mat in [(axes[0], counts), (axes[1], probs)]:
        ax.set_xticks(range(mat.shape[1]), mat.columns, rotation=45, ha="right")
        ax.set_yticks(range(mat.shape[0]), mat.index)
        for i in range(mat.shape[0]):
            for j in range(mat.shape[1]):
                val = mat.iloc[i, j]
                ax.text(j, i, f"{val:.2g}" if ax is axes[1] else str(int(val)), ha="center", va="center", fontsize=7)
    fig.colorbar(im0, ax=axes[0], fraction=0.046)
    fig.colorbar(im1, ax=axes[1], fraction=0.046)
    fig.suptitle("Exploratory geometry-defined state-transition view")
    return ensure_fig(paths.figures / "12_state_transitions.png", fig), table


def plot_terminal_secondary(time_table: pd.DataFrame, event_table: pd.DataFrame, paths: AtlasPaths) -> Path:
    rows = []
    compare = ["peak expansion", "final meaningful expansion", "transition into geometric quiescence", "terminal observed record"]
    for fire_id, fire in time_table.groupby("fire_id"):
        for event_type in compare:
            ev = event_table[(event_table["fire_id"] == fire_id) & (event_table["event_type"] == event_type)].drop_duplicates("event_type")
            if ev.empty:
                continue
            idx = int(ev.iloc[0]["observation_index"])
            row = fire.sort_values("observation_index").iloc[idx]
            rows.append({"fire_id": fire_id, "event_type": event_type, "tmmx_c": row["tmmx_c"], "vpd_kpa": row["vpd_kpa"], "days_to_terminal": (fire["timestamp"].max() - row["timestamp"]).days})
    comp = pd.DataFrame(rows)
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    for ax, var, title in zip(axes, ["days_to_terminal", "tmmx_c", "vpd_kpa"], ["separation from terminal observed record", "maximum temperature at event", "VPD at event"]):
        data = [comp.loc[comp["event_type"] == e, var].dropna() for e in compare]
        ax.boxplot(data, tick_labels=[e.replace(" ", "\n") for e in compare])
        ax.tick_params(axis="x", labelsize=7)
        ax.set_title(title)
        ax.grid(axis="y", alpha=0.2)
    fig.suptitle("Terminal observation as secondary, censored analysis")
    return ensure_fig(paths.figures / "13_terminal_secondary_analysis.png", fig)


def plot_outlier_influence(time_table: pd.DataFrame, traits: pd.DataFrame, paths: AtlasPaths, cfg: dict[str, Any]) -> Path:
    ordered = traits.sort_values("final_area_km2", ascending=False)["fire_id"].tolist()
    scenarios = {
        "all fires": traits["fire_id"].tolist(),
        "without largest fire": [f for f in traits["fire_id"] if f != ordered[0]],
        "without largest three": [f for f in traits["fire_id"] if f not in set(ordered[:3])],
        "equal fire weights": traits["fire_id"].tolist(),
    }
    rows = []
    for scenario, fires in scenarios.items():
        subset = time_table[time_table["fire_id"].isin(fires)]
        if scenario == "equal fire weights":
            med = subset.groupby("fire_id")[cfg["activity_metric"]].mean().median()
        else:
            med = subset[cfg["activity_metric"]].median()
        rows.append({"scenario": scenario, "n_fires": len(set(fires)), "median_activity": med, "mean_activity": subset[cfg["activity_metric"]].mean(), "max_activity": subset[cfg["activity_metric"]].max()})
    tab = pd.DataFrame(rows)
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    axes[0].bar(tab["scenario"], tab["mean_activity"], color="#bc6c25")
    axes[0].tick_params(axis="x", rotation=25)
    axes[0].set_ylabel("mean newly added area (km2)")
    axes[0].set_title("Raw-area conclusions depend on large fires")
    axes[1].scatter(traits["final_area_km2"].rank(), traits["peak_expansion_magnitude_km2"], c=traits["final_area_km2"], cmap="plasma", s=55)
    axes[1].set_yscale("log")
    axes[1].set_xlabel("rank by final area")
    axes[1].set_ylabel("peak expansion magnitude (km2, log)")
    axes[1].set_title("Skew and influence are explicit")
    for ax in axes:
        ax.grid(alpha=0.2)
    fig.suptitle("Outlier and influence diagnostics")
    return ensure_fig(paths.figures / "14_outlier_influence.png", fig)


def plot_sample_size_power(qc: pd.DataFrame, centered: pd.DataFrame, paths: AtlasPaths) -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    flags = [c for c in qc.columns if c.startswith("usable_for_")]
    counts = qc[flags].sum().sort_values()
    axes[0].barh(counts.index, counts.values, color="#33658a")
    axes[0].set_xlabel("fires")
    axes[0].set_title("Task-specific usable sample sizes")
    lag_counts = centered.groupby(["anchor_event_type", "lag_observations"])["fire_id"].nunique().reset_index()
    for event_type, sub in lag_counts.groupby("anchor_event_type"):
        axes[1].plot(sub["lag_observations"], sub["fire_id"], marker="o", label=event_type)
    axes[1].set_xlabel("observation lag")
    axes[1].set_ylabel("contributing fires")
    axes[1].set_title("Effective sample size by event-centered lag")
    axes[1].legend(fontsize=7)
    axes[1].grid(alpha=0.2)
    fig.suptitle("Sample-size and power diagnostics")
    return ensure_fig(paths.figures / "15_sample_size_power.png", fig)


def table_page(pdf: PdfPages, title: str, df: pd.DataFrame, max_rows: int = 18) -> None:
    fig, ax = plt.subplots(figsize=(11, 8.5))
    ax.axis("off")
    fig.patch.set_facecolor("white")
    ax.set_title(title, loc="left", fontsize=18, fontweight="bold", pad=20)
    view = df.head(max_rows).copy()
    if view.empty:
        ax.text(0.05, 0.7, "No rows available.", transform=ax.transAxes, fontsize=12)
    else:
        wrap_width = max(10, int(120 / max(len(view.columns), 1)))
        for col in view.columns:
            view[col] = view[col].map(lambda x: f"{x:.3g}" if isinstance(x, float) and np.isfinite(x) else str(x))
            view[col] = view[col].map(lambda x: textwrap.fill(x, width=wrap_width))
        headers = [textwrap.fill(str(col), wrap_width) for col in view.columns]
        table = ax.table(cellText=view.values, colLabels=headers, cellLoc="left", colLoc="left", bbox=[0.02, 0.05, 0.96, 0.78])
        table.auto_set_font_size(False)
        table.set_fontsize(6.5)
    pdf.savefig(fig)
    plt.close(fig)


def text_page(pdf: PdfPages, title: str, sections: list[tuple[str, list[str]]]) -> None:
    fig = plt.figure(figsize=(11, 8.5))
    fig.patch.set_facecolor("white")
    y = 0.94
    for title_line in textwrap.wrap(title, width=78):
        fig.text(0.05, y, title_line, fontsize=18, fontweight="bold", va="top")
        y -= 0.045
    y -= 0.02
    for header, bullets in sections:
        if y < 0.14:
            pdf.savefig(fig)
            plt.close(fig)
            fig = plt.figure(figsize=(11, 8.5))
            y = 0.94
        fig.text(0.06, y, header, fontsize=12, fontweight="bold", va="top")
        y -= 0.032
        for bullet in bullets:
            for line in textwrap.wrap(bullet, width=118):
                fig.text(0.08, y, line, fontsize=10.5, va="top")
                y -= 0.026
            y -= 0.006
        y -= 0.015
    pdf.savefig(fig)
    plt.close(fig)


def decision_summary_page(pdf: PdfPages, sections: list[tuple[str, list[str]]]) -> None:
    fig = plt.figure(figsize=(11, 8.5))
    fig.patch.set_facecolor("white")
    y = 0.94
    for title_line in textwrap.wrap(TITLE, width=72):
        fig.text(0.05, y, title_line, fontsize=16, fontweight="bold", va="top")
        y -= 0.042
    y -= 0.012
    for header, bullets in sections:
        fig.text(0.06, y, header, fontsize=10.8, fontweight="bold", va="top")
        y -= 0.026
        for bullet in bullets:
            for line in textwrap.wrap(bullet, width=126):
                fig.text(0.08, y, line, fontsize=8.9, va="top")
                y -= 0.021
            y -= 0.003
        y -= 0.011
    pdf.savefig(fig)
    plt.close(fig)


def image_page(pdf: PdfPages, title: str, path: Path, note: str = "") -> None:
    img = plt.imread(path)
    fig, ax = plt.subplots(figsize=(11, 8.5))
    fig.patch.set_facecolor("white")
    ax.imshow(img)
    ax.axis("off")
    fig.suptitle(title, fontsize=15, fontweight="bold")
    if note:
        fig.text(0.05, 0.035, note, fontsize=9, wrap=True)
    pdf.savefig(fig)
    plt.close(fig)


def scientific_decision_summary(qc: pd.DataFrame, traits: pd.DataFrame, alignment: pd.DataFrame, cluster_scores: pd.DataFrame) -> list[tuple[str, list[str]]]:
    n_fires = int(qc["fire_id"].nunique())
    n_morph = int(qc["usable_for_morphology"].sum())
    n_pulse = int(qc["usable_for_pulse_detection"].sum())
    n_terminal = int(qc["usable_for_terminal_observation_analysis"].sum())
    best_align = alignment.sort_values("alignment_rank_for_geometry").iloc[0]["alignment_clock"] if not alignment.empty else "not available"
    best_sil = float(cluster_scores["silhouette_width"].max()) if not cluster_scores.empty else np.nan
    cluster_statement = "suggestive" if np.isfinite(best_sil) and best_sil >= 0.25 else "ambiguous"
    return [
        (
            "WHAT THE CURRENT DATA CLEARLY SHOW",
            [
                f"{n_fires} fires and {int(qc['usable_transitions'].sum())} usable observation-to-observation transitions are available. Evidence: strong descriptive evidence.",
                f"Task-specific QC is required: morphology is usable for {n_morph} fires, pulse detection for {n_pulse}, and terminal-observation analysis for {n_terminal}. Evidence: strong descriptive evidence.",
                "Final meaningful expansion, terminal observed record, and physical extinction are distinct quantities. Physical extinction is not observed. Evidence: strong descriptive evidence.",
            ],
        ),
        (
            "WHAT THE CURRENT DATA SUGGEST",
            [
                f"The most coherent geometry-centered clock in this sample is {best_align}. Evidence: moderate descriptive evidence from alignment ranking.",
                "Fires show pulses, pauses, repeated expansions, and prolonged low-growth intervals rather than a single uniform terminal pattern. Evidence: moderate descriptive evidence from profiles and event table.",
                f"Discrete geometry-only groups have {cluster_statement} support; best silhouette is {best_sil:.2f}. Continuous axes should be considered alongside clusters.",
            ],
        ),
        (
            "WHAT THE CURRENT DATA DO NOT SUPPORT",
            [
                "A common terminal climate endpoint is unsupported with current data; terminal observed records remain heterogeneous.",
                f"Causal claims about wind, VPD, or temperature triggering expansion are not supported with {n_fires} daily fire sequences.",
                "No prescribed-fire comparison is made or implied.",
            ],
        ),
        (
            "WHAT SHOULD BE ANALYZED NEXT",
            [
                "Expand the event sample and reduce temporal gaps before physical cessation claims.",
                "Compute climate support on newly burned area and advancing boundaries, not only nearest grid cell to event centroid.",
                "Use daily wind speed here only as a scalar first pass; direction, gusts, and subdaily wind remain future work.",
            ],
        ),
        (
            "WHAT COULD BECOME THE MANUSCRIPT",
            [
                "Strongest current manuscript direction: geometric developmental objects, event clocks, and continuous developmental axes.",
                "Secondary direction: geometry-environment transitions around expansion pulses, but this needs larger sample size and better climate support.",
            ],
        ),
    ]


def manuscript_decision_matrix(qc: pd.DataFrame, traits: pd.DataFrame, alignment: pd.DataFrame, cluster_scores: pd.DataFrame) -> pd.DataFrame:
    n_fires = int(qc["fire_id"].nunique())
    pulse_n = int(traits["number_of_expansion_pulses"].sum())
    best_sil = float(cluster_scores["silhouette_width"].max()) if not cluster_scores.empty else np.nan
    rows = [
        {
            "story": "Wildfires converge on a common terminal climate.",
            "supporting_analyses": "terminal secondary analysis",
            "contradicting_analyses": "wide terminal tmmx/VPD/wind spread; censored terminal records",
            "sample_size": n_fires,
            "robustness": "low",
            "dependence_on_definitions": "high",
            "strongest_figure": "13_terminal_secondary_analysis",
            "additional_analysis_needed": "true cessation data; expanded sample; boundary climate",
            "current_evidence_rating": "unsupported with current data",
            "manuscript_potential": "low now",
        },
        {
            "story": "Wildfires share a common transition out of their final expansion pulse.",
            "supporting_analyses": "alignment comparison; final meaningful expansion events",
            "contradicting_analyses": "gaps and varying quiescence persistence",
            "sample_size": n_fires,
            "robustness": "medium",
            "dependence_on_definitions": "medium",
            "strongest_figure": "04_alignment_comparison_grid",
            "additional_analysis_needed": "test pulse thresholds on larger sample",
            "current_evidence_rating": "suggestive",
            "manuscript_potential": "moderate",
        },
        {
            "story": "Wildfires exhibit recurring geometric developmental trajectories.",
            "supporting_analyses": "profiles; event table; clustering",
            "contradicting_analyses": f"cluster silhouette max {best_sil:.2f}",
            "sample_size": n_fires,
            "robustness": "medium-low",
            "dependence_on_definitions": "medium",
            "strongest_figure": "07_geometry_clustering",
            "additional_analysis_needed": "stability with more fires",
            "current_evidence_rating": "ambiguous" if best_sil < 0.25 else "suggestive",
            "manuscript_potential": "moderate",
        },
        {
            "story": "Wildfire development lies along continuous geometric axes rather than discrete types.",
            "supporting_analyses": "PCA loadings and scores",
            "contradicting_analyses": "small sample size",
            "sample_size": n_fires,
            "robustness": "medium",
            "dependence_on_definitions": "medium",
            "strongest_figure": "08_continuous_axes_pca",
            "additional_analysis_needed": "functional PCA and outlier sensitivity",
            "current_evidence_rating": "moderate descriptive evidence",
            "manuscript_potential": "high",
        },
        {
            "story": "Expansion pulses are associated with specific environmental states or changes.",
            "supporting_analyses": "event-centered climate extraction",
            "contradicting_analyses": "daily time step, nearest-grid-cell climate, limited pulse count",
            "sample_size": pulse_n,
            "robustness": "low-medium",
            "dependence_on_definitions": "high",
            "strongest_figure": "09_event_centered_climate",
            "additional_analysis_needed": "larger sample; boundary climate; hourly wind optional",
            "current_evidence_rating": "suggestive",
            "manuscript_potential": "moderate after expansion",
        },
        {
            "story": "Different climate variables play distinct temporal roles in wildfire development.",
            "supporting_analyses": "environmental roles diagnostics",
            "contradicting_analyses": "daily records smooth short wind events",
            "sample_size": n_fires,
            "robustness": "low-medium",
            "dependence_on_definitions": "medium",
            "strongest_figure": "10_environmental_roles",
            "additional_analysis_needed": "more events and subdaily wind if needed",
            "current_evidence_rating": "suggestive",
            "manuscript_potential": "moderate",
        },
        {
            "story": "Observation gaps prevent reliable inference about physical fire cessation.",
            "supporting_analyses": "observational raster; task-specific QC",
            "contradicting_analyses": "none in current cache",
            "sample_size": n_fires,
            "robustness": "high",
            "dependence_on_definitions": "low",
            "strongest_figure": "01_observational_structure_raster",
            "additional_analysis_needed": "independent cessation observations",
            "current_evidence_rating": "strong descriptive evidence",
            "manuscript_potential": "high as limitation/design point",
        },
    ]
    return pd.DataFrame(rows)


def render_pdf(
    paths: AtlasPaths,
    daily: gpd.GeoDataFrame,
    time_table: pd.DataFrame,
    traits: pd.DataFrame,
    event_table: pd.DataFrame,
    qc: pd.DataFrame,
    candidate_results: pd.DataFrame,
    alignment_quality: pd.DataFrame,
    cluster_scores: pd.DataFrame,
    pca_loadings: pd.DataFrame,
    figs: dict[str, Path],
    cfg: dict[str, Any],
) -> None:
    with PdfPages(paths.pdf) as pdf:
        decision_summary_page(pdf, scientific_decision_summary(qc, traits, alignment_quality, cluster_scores))
        qc_pdf = qc[
            [
                "fire_id",
                "observation_count",
                "observed_sequence_duration_days",
                "max_gap_days",
                "expansion_pulse_count",
                "usable_for_morphology",
                "usable_for_pulse_detection",
                "usable_for_lag_analysis",
                "usable_for_terminal_observation_analysis",
                "usable_for_clustering",
                "usable_for_climate_transition_analysis",
            ]
        ]
        table_page(pdf, "Task-specific QC replaces terminal-cessation filtering", qc_pdf, max_rows=25)
        image_page(pdf, "Section 1. Observational structure and limitations", figs["observational_raster"], "Observed perimeter dates, missing dates inside observed sequences, pulse markers, final meaningful expansion, and terminal observed records.")
        image_page(pdf, "Section 2. Defining the developmental object", figs["activity_correlations"], "Vase width is max projected bounding-box side in km; it is compared against, not assumed equivalent to, newly added area.")
        table_page(pdf, "Section 4. Event detection rules and detected events", event_table[["fire_id", "event_type", "observation_index", "calendar_date", "activity_magnitude", "activity_relative_to_peak", "confidence_or_robustness"]], max_rows=28)
        image_page(pdf, "Section 4. Event detection sensitivity", figs["event_sensitivity"], "Expansion activity is detected from geometry only using multiple transparent thresholds.")
        image_page(pdf, "Section 5. Alignment comparison", figs["alignment_grid"], "Observed points and event-centered lags are shown; interpolated relative-age views are secondary diagnostics only.")
        table_page(pdf, "Section 5. Alignment quality ranking", alignment_quality, max_rows=10)
        image_page(pdf, "Section 5. Alignment quality visuals", figs["alignment_quality"])
        image_page(pdf, "Section 6. Geometric life-history traits", figs["trait_panels"], "Traits are grouped as size, tempo, pulse structure, persistence, and shape; skewed axes use log scales where appropriate.")
        image_page(pdf, "Section 7. Geometry-only developmental typology", figs["clustering"], "Clusters use geometry only. Weak silhouette values mean continuous axes may be more appropriate than forced types.")
        image_page(pdf, "Section 8. Continuous developmental axes", figs["pca"], "PCA scores are accompanied by loadings so interpretation remains tied to measurable traits.")
        table_page(pdf, "PCA loadings for continuous geometry axes", pca_loadings, max_rows=15)
        image_page(pdf, "Section 9. Environment around expansion events", figs["event_centered_climate"], "Climate describes geometry-defined events; it does not define them.")
        image_page(pdf, "Section 10. Environmental roles", figs["environmental_roles"], "Daily maximum/minimum temperature, VPD, and scalar wind speed are compared as different temporal signals.")
        image_page(pdf, "Section 11. Interactions and compound conditions", figs["compound_conditions"], "Transparent two-variable displays are used instead of over-parameterized models.")
        image_page(pdf, "Section 12. State-transition view", figs["state_transitions"], "States are exploratory geometry bins, not verified biological states.")
        image_page(pdf, "Section 13. Terminal observation as secondary analysis", figs["terminal_secondary"], "The terminal observed record is compared to peak, final meaningful expansion, and quiescence onset.")
        image_page(pdf, "Section 14. Outlier and influence analysis", figs["outlier_influence"], "Large fires are shown explicitly; they are not silently removed.")
        image_page(pdf, "Section 15. Sample-size and power diagnostics", figs["sample_size_power"], "Every major comparison reports fires, events, or lag contributions.")
        decision_overview = candidate_results[
            [
                "story",
                "current_evidence_rating",
                "manuscript_potential",
                "sample_size",
                "robustness",
                "strongest_figure",
            ]
        ]
        decision_details = candidate_results[
            [
                "story",
                "supporting_analyses",
                "contradicting_analyses",
                "dependence_on_definitions",
                "additional_analysis_needed",
            ]
        ]
        table_page(pdf, "Section 16. Manuscript decision matrix: overview", decision_overview, max_rows=10)
        table_page(pdf, "Section 16. Manuscript decision matrix: evidence details", decision_details, max_rows=10)
        text_page(
            pdf,
            "Section 17. Recommended main figures",
            [
                (
                    "OPTION A: GEOMETRIC DEVELOPMENT PAPER",
                    [
                        "Figure 1: The vase as a fire developmental object - current data are sufficient for a descriptive figure.",
                        "Figure 2: Individual developmental profiles and detected events - current profiles are sufficient, but event rules should be sensitivity-tested on more fires.",
                        "Figure 3: Geometry-only continuous axes or stable trajectory groups - PCA axes are currently stronger than forced clusters.",
                        "Figure 4: Event-aligned expansion and quiescence transitions - current data are suggestive but limited by gaps.",
                        "Figure 5: Conceptual synthesis of wildfire developmental trajectories - appropriate as a hypothesis-generating synthesis.",
                    ],
                ),
                (
                    "OPTION B: GEOMETRY-ENVIRONMENT PAPER",
                    [
                        "Figure 1: The vase and aligned geometry-climate time series - current data are sufficient as an atlas figure.",
                        "Figure 2: Environmental conditions around major expansion pulses - suggestive only with current sample size.",
                        "Figure 3: Compound climate conditions and lagged response - needs more fires and boundary climate support.",
                        "Figure 4: Developmental states and transition probabilities - exploratory, not mechanistic.",
                        "Figure 5: Environmental trajectories across geometric development - promising but requires richer climate support.",
                    ],
                ),
            ],
        )
        text_page(
            pdf,
            "Section 18. Final scientific interpretation - page 1",
            [
                (
                    "What the current data show",
                    [
                        f"Observation: the cached sample contains daily fire perimeters, gaps, and nearest-grid-cell daily climate for {time_table['fire_id'].nunique()} candidate fires.",
                        "Statistical result: expansion activity is uneven, with pulse-like growth, low-growth periods, and variable timing of final meaningful expansion.",
                        "Scientific inference: the current sample is consistent with fire development being organized around geometric events rather than a verified extinction endpoint.",
                        "Speculation: some fires may occupy recurring developmental pathways, but discrete groups are not yet stable enough to name mechanistically.",
                    ],
                )
            ],
        )
        text_page(
            pdf,
            "Section 18. Final scientific interpretation - page 2",
            [
                (
                    "What the current data do not yet establish",
                    [
                        "The current data do not distinguish terminal observed record from physical extinction.",
                        "The current data do not establish causal climate controls on expansion pulses.",
                        "This pattern is sensitive to observation gaps, pulse thresholds, and large-fire influence.",
                        "This result is strongest as a scientific decision atlas for manuscript selection, not as a polished causal argument.",
                    ],
                )
            ],
        )
        for fire_id, fire in time_table.groupby("fire_id", sort=True):
            plot_profile_page(pdf, fire.sort_values("observation_index"), event_table, daily, cfg)


def image_to_data_uri(path: Path) -> str:
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def render_html(paths: AtlasPaths, figs: dict[str, Path], candidate_results: pd.DataFrame, qc: pd.DataFrame) -> None:
    fig_sections = "\n".join(
        f"<section><h2>{name.replace('_', ' ').title()}</h2><img src='{image_to_data_uri(path)}' /></section>"
        for name, path in figs.items()
    )
    html = f"""<!doctype html>
<html>
<head>
<meta charset="utf-8" />
<title>{TITLE}</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 32px; color: #1f2933; }}
h1 {{ max-width: 980px; }}
.note {{ max-width: 980px; line-height: 1.45; }}
img {{ max-width: 100%; border: 1px solid #ddd; }}
table {{ border-collapse: collapse; font-size: 12px; margin: 16px 0; max-width: 100%; }}
td, th {{ border: 1px solid #ccc; padding: 5px 7px; vertical-align: top; }}
section {{ margin: 34px 0; }}
</style>
</head>
<body>
<h1>{TITLE}</h1>
<p class="note">This atlas is organized around geometric developmental trajectories and environmental transitions. Final meaningful expansion, terminal observed record, and physical extinction are treated as distinct. No prescribed-fire comparison is made or implied.</p>
<h2>Task-specific QC</h2>
{qc.to_html(index=False)}
<h2>Manuscript Decision Matrix</h2>
{candidate_results.to_html(index=False)}
{fig_sections}
</body>
</html>
"""
    paths.html.write_text(html, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the fire VASE developmental atlas.")
    parser.add_argument("--config", type=Path, default=Path("config/fire_vase_developmental_atlas.yml"))
    parser.add_argument("--outputs", type=Path, default=Path("outputs"))
    parser.add_argument("--fire-cache-dir", type=Path, default=Path("artifacts/fire-vase-gridmet-real/fired-cache"))
    parser.add_argument("--candidates-csv", type=Path, default=Path("artifacts/fire-vase-gridmet-real/candidate_events.csv"))
    parser.add_argument("--gridmet-cache-dir", type=Path, default=Path("artifacts/fire-vase-gridmet-real/gridmet-cache"))
    args = parser.parse_args()

    cfg = load_config(args.config)
    paths = make_paths(args.outputs)
    paths.outputs.mkdir(parents=True, exist_ok=True)
    paths.figures.mkdir(parents=True, exist_ok=True)

    print("loading real inputs")
    daily, events, candidates = load_inputs(args.fire_cache_dir, args.candidates_csv)
    arrays = load_gridmet_dataarrays(args.gridmet_cache_dir, cfg)
    print("building fire-by-time table")
    time_table = build_time_table(daily, events, arrays, cfg)
    event_table, traits, summaries = build_event_and_trait_tables(time_table, cfg)
    time_table = annotate_time_table(time_table, event_table, summaries, cfg)
    qc = build_qc_table(time_table, traits, summaries, cfg)
    reps = build_geometry_representations(time_table, traits, cfg)
    cluster_labels, cluster_scores, best_cluster = cluster_geometry(reps, cfg)
    traits = traits.merge(cluster_labels[["fire_id", "selected_profile"]], on="fire_id", how="left")
    centered = event_centered_table(time_table, event_table, cfg)
    alignment_quality = alignment_quality_table(time_table, event_table, cfg)

    print("building figures")
    figs: dict[str, Path] = {}
    figs["observational_raster"] = plot_observational_raster(time_table, event_table, paths, cfg)
    figs["activity_correlations"] = plot_activity_correlations(time_table, paths)
    figs["event_sensitivity"] = plot_event_sensitivity(event_table, paths)
    figs["alignment_grid"], centered_for_plot = plot_alignment_comparison(time_table, event_table, paths, cfg)
    figs["alignment_quality"] = plot_alignment_quality(alignment_quality, paths)
    figs["trait_panels"] = plot_trait_panels(traits, paths)
    figs["clustering"], figs["pca"], pca_loadings = plot_clustering_and_pca(traits, cluster_labels, cluster_scores, reps, paths)
    figs["event_centered_climate"] = plot_event_centered_climate(centered, paths)
    figs["environmental_roles"] = plot_environmental_roles(time_table, paths)
    figs["compound_conditions"] = plot_compound_conditions(time_table, paths, cfg)
    figs["state_transitions"], transition_table = plot_state_transitions(time_table, paths)
    figs["terminal_secondary"] = plot_terminal_secondary(time_table, event_table, paths)
    figs["outlier_influence"] = plot_outlier_influence(time_table, traits, paths, cfg)
    figs["sample_size_power"] = plot_sample_size_power(qc, centered, paths)

    candidate_results = manuscript_decision_matrix(qc, traits, alignment_quality, cluster_scores)

    print("writing tables")
    time_table.to_csv(paths.time_table, index=False)
    traits.to_csv(paths.traits, index=False)
    event_table.to_csv(paths.events, index=False)
    qc.to_csv(paths.qc, index=False)
    candidate_results.to_csv(paths.candidate_results, index=False)
    alignment_quality.to_csv(paths.outputs / "fire_vase_alignment_quality.csv", index=False)
    cluster_scores.to_csv(paths.outputs / "fire_vase_cluster_sensitivity.csv", index=False)
    pca_loadings.to_csv(paths.outputs / "fire_vase_pca_loadings.csv", index=False)
    centered.to_csv(paths.outputs / "fire_vase_event_centered_climate.csv", index=False)
    transition_table.to_csv(paths.outputs / "fire_vase_state_transitions.csv", index=False)

    print("rendering reports")
    render_pdf(paths, daily, time_table, traits, event_table, qc, candidate_results, alignment_quality, cluster_scores, pca_loadings, figs, cfg)
    render_html(paths, figs, candidate_results, qc)

    manifest = {
        "title": TITLE,
        "n_fires": int(time_table["fire_id"].nunique()),
        "n_fire_time_records": int(len(time_table)),
        "n_events": int(len(event_table)),
        "climate_variables": cfg["climate_variables"],
        "best_cluster": {"k": best_cluster["k"], "silhouette": best_cluster["silhouette"]},
        "outputs": {
            "pdf": str(paths.pdf),
            "html": str(paths.html),
            "time_table": str(paths.time_table),
            "traits": str(paths.traits),
            "event_table": str(paths.events),
            "qc": str(paths.qc),
            "candidate_results": str(paths.candidate_results),
            "figures": {k: str(v) for k, v in figs.items()},
        },
        "terminology": "final meaningful expansion != terminal observed record != physical extinction",
        "prescribed_fire_comparison": False,
    }
    paths.manifest.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest["outputs"], indent=2))


if __name__ == "__main__":
    main()
