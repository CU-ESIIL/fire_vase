"""Data loading and morphospace utilities for Fire VASE figures."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from style import ROOT


DATA_DIR = ROOT / "scratch/fire_vase_developmental_morphology"
TABLE_DIR = ROOT / "scratch/fire_vase_run_full/tables"

CLIMATE_COLS = [
    "mean_maximum_temperature_c",
    "mean_minimum_temperature_c",
    "mean_vpd_kpa",
    "max_vpd_kpa",
    "mean_wind_speed_m_s",
    "wind_present_fraction",
]

MORPH_COLS = ["morph_pc1", "morph_pc2", "morph_pc3", "morph_pc4", "morph_pc5"]


@dataclass
class PcaFit:
    scores: np.ndarray
    loadings: pd.DataFrame
    explained_variance_ratio: np.ndarray
    center: pd.Series
    scale: pd.Series
    columns: list[str]


def require_file(path: Path) -> Path:
    if not path.exists():
        raise FileNotFoundError(f"Required Fire VASE input is missing: {path}")
    return path


def load_data() -> dict[str, pd.DataFrame]:
    frames = {
        "features": pd.read_parquet(require_file(DATA_DIR / "developmental_morphospace_features.parquet")),
        "medoids": pd.read_parquet(require_file(DATA_DIR / "developmental_morphospace_medoids.parquet")),
        "stage": pd.read_parquet(require_file(DATA_DIR / "developmental_stage_table.parquet")),
        "coupling": pd.read_parquet(require_file(DATA_DIR / "developmental_climate_coupling.parquet")),
        "matched": pd.read_parquet(require_file(DATA_DIR / "developmental_matched_pairs.parquet")),
        "slices": pd.read_parquet(require_file(TABLE_DIR / "vase_slices.parquet")),
        "traits": pd.read_parquet(require_file(TABLE_DIR / "fire_traits.parquet")),
    }
    frames["loadings"] = pd.read_csv(require_file(DATA_DIR / "developmental_morphospace_loadings.csv"), index_col=0)
    for name in ["features", "medoids", "stage", "matched", "slices", "traits"]:
        if "fire_id" in frames[name].columns:
            frames[name]["fire_id"] = frames[name]["fire_id"].astype(str)
    frames["slices"]["timestamp"] = pd.to_datetime(frames["slices"]["timestamp"])
    return frames


def geometry_columns(features: pd.DataFrame, loadings: pd.DataFrame | None = None) -> list[str]:
    if loadings is not None:
        return [str(c) for c in loadings.index]
    cols = [
        "log_final_area_km2",
        "log_duration_days",
        "log_peak_growth_km2_per_day",
        "log_slenderness_days_per_width",
        "observation_count",
        "pulse_count",
        "reactivation_count",
        "peak_timing",
        "front_loaded_fraction",
        "late_growth_fraction",
        "terminal_taper_fraction",
        "growth_entropy",
        "developmental_velocity",
        "developmental_acceleration",
    ]
    cols.extend([c for c in features.columns if c.startswith("width_p") or c.startswith("growth_p")])
    return cols


def feature_matrix(features: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    x = features.copy()
    for col in ["final_area_km2", "duration_days", "peak_growth_km2_per_day", "slenderness_days_per_width"]:
        log_col = f"log_{col}"
        if log_col not in x.columns and col in x.columns:
            x[log_col] = np.log10(x[col].astype(float).clip(lower=1e-9))
    return x[columns].astype(float).replace([np.inf, -np.inf], np.nan)


def robust_standardize(x: pd.DataFrame) -> tuple[np.ndarray, pd.Series, pd.Series]:
    center = x.median()
    clean = x.fillna(center)
    scale = clean.std(ddof=0).replace(0, 1.0)
    z = ((clean - center) / scale).to_numpy(float)
    return z, center, scale


def fit_pca(features: pd.DataFrame, columns: list[str], n_components: int = 10) -> PcaFit:
    x = feature_matrix(features, columns)
    z, center, scale = robust_standardize(x)
    u, s, vt = np.linalg.svd(z, full_matrices=False)
    ev = (s**2) / max(z.shape[0] - 1, 1)
    evr = ev / ev.sum()
    loadings = pd.DataFrame(vt[:n_components].T, index=columns, columns=[f"PC{i}" for i in range(1, n_components + 1)])
    return PcaFit(
        scores=u[:, :n_components] * s[:n_components],
        loadings=loadings,
        explained_variance_ratio=evr[:n_components],
        center=center,
        scale=scale,
        columns=columns,
    )


def align_signs(loadings: np.ndarray, reference: np.ndarray) -> np.ndarray:
    out = loadings.copy()
    for i in range(min(out.shape[1], reference.shape[1])):
        if float(np.dot(out[:, i], reference[:, i])) < 0:
            out[:, i] *= -1
    return out


def axis_limits(features: pd.DataFrame) -> tuple[tuple[float, float], tuple[float, float]]:
    x = features["morph_pc1"].to_numpy(float)
    y = features["morph_pc2"].to_numpy(float)
    xlim = tuple(np.nanquantile(x, [0.002, 0.998]))
    ylim = tuple(np.nanquantile(y, [0.002, 0.998]))
    pad_x = (xlim[1] - xlim[0]) * 0.04
    pad_y = (ylim[1] - ylim[0]) * 0.05
    return (xlim[0] - pad_x, xlim[1] + pad_x), (ylim[0] - pad_y, ylim[1] + pad_y)


def profiles_for_fire_ids(slices: pd.DataFrame, fire_ids: list[str] | set[str]) -> dict[str, pd.DataFrame]:
    wanted = set(str(v) for v in fire_ids)
    out: dict[str, pd.DataFrame] = {}
    sub = slices[slices["fire_id"].isin(wanted)].copy()
    for fire_id, group in sub.groupby("fire_id", sort=False):
        g = group.sort_values("slice_index").reset_index(drop=True)
        obs = len(g)
        rel_t = np.array([0.5]) if obs == 1 else np.linspace(0.0, 1.0, obs)
        final_area = max(float(g["cumulative_area_km2"].max()), 1e-9)
        out[fire_id] = pd.DataFrame(
            {
                "relative_time": rel_t,
                "width": g["normalized_vase_width"].fillna(0).clip(lower=0).to_numpy(float),
                "growth_km2": g["ring_area_km2"].fillna(0).clip(lower=0).to_numpy(float),
                "growth_fraction": g["ring_area_km2"].fillna(0).clip(lower=0).to_numpy(float) / final_area,
                "cumulative_area_km2": g["cumulative_area_km2"].fillna(0).to_numpy(float),
                "timestamp": g["timestamp"].to_numpy(),
                "maximum_temperature_c": g["maximum_temperature_c"].to_numpy(float),
                "minimum_temperature_c": g["minimum_temperature_c"].to_numpy(float),
                "vpd_kpa": g["vpd_kpa"].to_numpy(float),
                "wind_speed_m_s": g["wind_speed_m_s"].to_numpy(float),
                "climate_available": g["climate_available"].to_numpy(bool),
            }
        )
    return out


def medoid_profile_ids(medoids: pd.DataFrame, n: int | None = None) -> list[str]:
    frame = medoids.sort_values("representative_id")
    if n is not None:
        frame = frame.head(n)
    return frame["fire_id"].astype(str).tolist()


def pick_shape_examples(features: pd.DataFrame, wanted: list[str]) -> pd.DataFrame:
    rows = []
    for label in wanted:
        sub = features[features["shape_label"] == label]
        if sub.empty:
            continue
        pc = sub[["morph_pc1", "morph_pc2", "morph_pc3"]].to_numpy(float)
        center = np.nanmedian(pc, axis=0)
        idx = np.argmin(np.linalg.norm(pc - center, axis=1))
        rows.append(sub.iloc[idx])
    return pd.DataFrame(rows)


def transect_examples(features: pd.DataFrame, pc: str, bins: int = 7, eligible: pd.Series | None = None) -> pd.DataFrame:
    sub = features.copy()
    if eligible is not None:
        sub = sub[eligible].copy()
    qs = np.linspace(0.04, 0.96, bins)
    targets = np.nanquantile(sub[pc], qs)
    rows = []
    for target in targets:
        idx = (sub[pc] - target).abs().idxmin()
        rows.append(sub.loc[idx])
    return pd.DataFrame(rows).drop_duplicates("fire_id")
