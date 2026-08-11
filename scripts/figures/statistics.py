"""Statistical validation utilities for the Fire VASE figure suite."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

from morphospace import CLIMATE_COLS, MORPH_COLS, feature_matrix, fit_pca, geometry_columns, robust_standardize
from style import DERIVED_STATS_DIR, SEED


@dataclass
class ValidationBundle:
    observed: dict
    pca_bootstrap: pd.DataFrame
    pca_null: pd.DataFrame
    duration_sensitivity: pd.DataFrame
    ablation: pd.DataFrame
    medoid_coverage: pd.DataFrame
    category_overlap: pd.DataFrame
    climate_cv: pd.DataFrame
    matched_population: pd.DataFrame
    safe_stage_prediction: pd.DataFrame
    safe_stage_predictions_pc1: pd.DataFrame
    leakage_audit: pd.DataFrame


def _write(frame: pd.DataFrame, name: str) -> None:
    DERIVED_STATS_DIR.mkdir(parents=True, exist_ok=True)
    frame.to_csv(DERIVED_STATS_DIR / f"{name}.csv", index=False)


def _read(name: str) -> pd.DataFrame:
    return pd.read_csv(DERIVED_STATS_DIR / f"{name}.csv")


def _ols_fit_predict(x_train: np.ndarray, y_train: np.ndarray, x_test: np.ndarray) -> np.ndarray:
    x_train = np.c_[np.ones(len(x_train)), x_train]
    x_test = np.c_[np.ones(len(x_test)), x_test]
    coef = np.linalg.pinv(x_train).dot(y_train)
    return x_test.dot(coef)


def _r2(y: np.ndarray, pred: np.ndarray) -> float:
    mask = np.isfinite(y) & np.isfinite(pred)
    y = y[mask]
    pred = pred[mask]
    if len(y) < 10 or np.nanstd(y) <= 0:
        return np.nan
    ss_res = float(np.sum((y - pred) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    return 1.0 - ss_res / ss_tot if ss_tot > 0 else np.nan


def _standardized(frame: pd.DataFrame, cols: list[str]) -> tuple[np.ndarray, list[str]]:
    cols = [c for c in cols if c in frame.columns]
    x = frame[cols].astype(float).replace([np.inf, -np.inf], np.nan)
    x = x.fillna(x.median()).fillna(0.0)
    z = ((x - x.mean()) / x.std(ddof=0).replace(0, 1.0)).to_numpy(float)
    return z, cols


def _fold_assignments(frame: pd.DataFrame, kind: str, n_folds: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    if kind == "region":
        groups = frame["region"].fillna("unknown").astype(str).to_numpy()
        unique = np.array(sorted(set(groups)))
        rng.shuffle(unique)
        mapping = {g: i % n_folds for i, g in enumerate(unique)}
        return np.array([mapping[g] for g in groups])
    if kind == "year_block":
        years = frame["year"].astype(int).to_numpy()
        bins = pd.qcut(years, q=min(n_folds, len(np.unique(years))), labels=False, duplicates="drop")
        return np.asarray(bins, dtype=int)
    return rng.integers(0, n_folds, size=len(frame))


def cross_validated_r2(
    frame: pd.DataFrame,
    predictors: list[str],
    targets: list[str],
    *,
    fold_kind: str,
    n_folds: int = 5,
    seed: int = SEED,
    label: str,
) -> pd.DataFrame:
    clean = frame.dropna(subset=[c for c in predictors + targets if c in frame.columns]).copy()
    if len(clean) < 100:
        return pd.DataFrame()
    folds = _fold_assignments(clean, fold_kind, n_folds, seed)
    rows = []
    for fold in sorted(np.unique(folds)):
        train = folds != fold
        test = folds == fold
        if train.sum() < 100 or test.sum() < 20:
            continue
        x_all, used = _standardized(clean, predictors)
        for target in targets:
            y = clean[target].to_numpy(float)
            pred = _ols_fit_predict(x_all[train], y[train], x_all[test])
            rows.append(
                {
                    "model": label,
                    "fold_kind": fold_kind,
                    "fold": int(fold),
                    "target": target,
                    "n_train": int(train.sum()),
                    "n_test": int(test.sum()),
                    "r2": _r2(y[test], pred),
                    "predictors": ",".join(used),
                }
            )
    return pd.DataFrame(rows)


def pca_bootstrap(features: pd.DataFrame, columns: list[str], observed_loadings: pd.DataFrame, *, reps: int, sample_size: int, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    ref = observed_loadings.iloc[:, :5].to_numpy(float)
    strata = pd.DataFrame(
        {
            "duration_bin": pd.qcut(features["duration_days"].rank(method="first"), 4, labels=False),
            "area_bin": pd.qcut(features["final_area_km2"].rank(method="first"), 4, labels=False),
            "year_bin": pd.qcut(features["year"].rank(method="first"), 4, labels=False),
            "region": features["region"].astype(str),
        }
    )
    groups = strata.astype(str).agg("|".join, axis=1)
    features = features.copy()
    features["_stratum"] = groups
    group_sizes = features["_stratum"].value_counts(normalize=True)
    group_indices = {group: idx.to_numpy() for group, idx in features.groupby("_stratum").groups.items()}
    rows = []
    for rep in range(reps):
        take_indices = []
        for group, frac in group_sizes.items():
            n = max(1, int(round(frac * sample_size)))
            idx = group_indices[group]
            take = rng.choice(idx, size=n, replace=len(idx) < n)
            take_indices.append(take)
        sample = features.iloc[np.concatenate(take_indices)]
        pca = fit_pca(sample, columns, n_components=5)
        load = pca.loadings.iloc[:, :5].to_numpy(float)
        cosines = []
        for i in range(5):
            if float(np.dot(load[:, i], ref[:, i])) < 0:
                load[:, i] *= -1
            cosines.append(float(np.dot(load[:, i], ref[:, i]) / (np.linalg.norm(load[:, i]) * np.linalg.norm(ref[:, i]))))
        q, _ = np.linalg.qr(load)
        rq, _ = np.linalg.qr(ref)
        overlap = float(np.linalg.norm(q.T.dot(rq), ord="fro") ** 2 / 5)
        rows.append(
            {
                "replicate": rep,
                "cumvar_pc1_5": float(pca.explained_variance_ratio[:5].sum()),
                "pc1": float(pca.explained_variance_ratio[0]),
                "pc2": float(pca.explained_variance_ratio[1]),
                "pc3": float(pca.explained_variance_ratio[2]),
                "pc4": float(pca.explained_variance_ratio[3]),
                "pc5": float(pca.explained_variance_ratio[4]),
                "mean_loading_cosine": float(np.mean(cosines)),
                "min_loading_cosine": float(np.min(cosines)),
                "subspace_overlap": overlap,
            }
        )
    return pd.DataFrame(rows)


def pca_nulls(features: pd.DataFrame, columns: list[str], observed: float, *, reps: int, sample_size: int, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    sample = features.sample(min(sample_size, len(features)), random_state=seed).reset_index(drop=True)
    x = feature_matrix(sample, columns)
    rows = [{"null_model": "observed", "replicate": -1, "cumvar_pc1_5": observed}]
    for rep in range(reps):
        perm = x.copy()
        for col in perm.columns:
            perm[col] = rng.permutation(perm[col].to_numpy())
        z, _, _ = robust_standardize(perm)
        _, s, _ = np.linalg.svd(z, full_matrices=False)
        evr = (s**2) / np.sum(s**2)
        rows.append({"null_model": "feature-wise permutation", "replicate": rep, "cumvar_pc1_5": float(evr[:5].sum())})

        temporal = x.copy()
        growth_cols = [c for c in temporal.columns if c.startswith("growth_p")]
        for idx in range(len(temporal)):
            temporal.loc[idx, growth_cols] = rng.permutation(temporal.loc[idx, growth_cols].to_numpy())
        z, _, _ = robust_standardize(temporal)
        _, s, _ = np.linalg.svd(z, full_matrices=False)
        evr = (s**2) / np.sum(s**2)
        rows.append({"null_model": "within-fire growth-profile permutation", "replicate": rep, "cumvar_pc1_5": float(evr[:5].sum())})
    return pd.DataFrame(rows)


def duration_sensitivity(features: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    thresholds = [("all fires", 0), (">=2 days", 2), (">=4 days", 4), (">=8 days", 8), (">=10 days", 10)]
    rows = []
    for label, threshold in thresholds:
        sub = features if threshold == 0 else features[features["duration_days"] >= threshold]
        if len(sub) < 500:
            continue
        pca = fit_pca(sub, columns, n_components=5)
        rows.append(
            {
                "subset": label,
                "duration_threshold_days": threshold,
                "n": int(len(sub)),
                "pc1": float(pca.explained_variance_ratio[0]),
                "pc2": float(pca.explained_variance_ratio[1]),
                "pc3": float(pca.explained_variance_ratio[2]),
                "pc4": float(pca.explained_variance_ratio[3]),
                "pc5": float(pca.explained_variance_ratio[4]),
                "cumvar_pc1_5": float(pca.explained_variance_ratio[:5].sum()),
            }
        )
    return pd.DataFrame(rows)


def feature_ablation(features: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    groups = {
        "all geometry features": columns,
        "scalar summaries only": [c for c in columns if not c.startswith("width_p") and not c.startswith("growth_p")],
        "profile features only": [c for c in columns if c.startswith("width_p") or c.startswith("growth_p")],
        "no final area": [c for c in columns if "final_area" not in c],
        "no duration": [c for c in columns if "duration" not in c],
        "no observation count": [c for c in columns if c != "observation_count"],
        "no scale variables": [c for c in columns if all(key not in c for key in ["area", "duration", "peak_growth", "slenderness"])],
        "one per conceptual group": [
            c for c in [
                "log_final_area_km2",
                "log_duration_days",
                "pulse_count",
                "peak_timing",
                "growth_entropy",
                "terminal_taper_fraction",
                "developmental_velocity",
                "width_p05",
                "growth_p05",
            ] if c in columns
        ],
    }
    rows = []
    for label, cols in groups.items():
        if len(cols) < 2:
            continue
        pca = fit_pca(features, cols, n_components=min(5, len(cols)))
        rows.append({"feature_set": label, "n_features": len(cols), "cumvar_pc1_5": float(pca.explained_variance_ratio[:5].sum()), "pc1": float(pca.explained_variance_ratio[0])})
    return pd.DataFrame(rows)


def medoid_coverage(features: pd.DataFrame, medoids: pd.DataFrame) -> pd.DataFrame:
    pc = features[["morph_pc1", "morph_pc2", "morph_pc3"]].to_numpy(float)
    reps = medoids.sort_values("representative_id")[["morph_pc1", "morph_pc2", "morph_pc3", "represented_fire_count"]].to_numpy(float)
    rows = []
    for k in [4, 8, 12, 16, 24, 30, 36]:
        sub = reps[: min(k, len(reps)), :3]
        tree = cKDTree(sub)
        dist, _ = tree.query(pc, k=1)
        rows.append(
            {
                "n_medoids": int(k),
                "median_nearest_distance": float(np.median(dist)),
                "p90_nearest_distance": float(np.quantile(dist, 0.90)),
                "density_mass_within_1sd": float(np.mean(dist <= 1.0)),
            }
        )
    return pd.DataFrame(rows)


def category_overlap(features: pd.DataFrame) -> pd.DataFrame:
    pc = features[["morph_pc1", "morph_pc2", "morph_pc3"]].to_numpy(float)
    labels = features["shape_label"].astype(str).to_numpy()
    rng = np.random.default_rng(SEED)
    idx = rng.choice(len(features), size=min(25000, len(features)), replace=False)
    pc = pc[idx]
    labels = labels[idx]
    tree = cKDTree(pc)
    _, neigh = tree.query(pc, k=16)
    purities = []
    margins = []
    for i, nidx in enumerate(neigh):
        nlabels = labels[nidx[1:]]
        purities.append(float(np.mean(nlabels == labels[i])))
        counts = pd.Series(nlabels).value_counts(normalize=True)
        margins.append(float(counts.iloc[0] - counts.iloc[1]) if len(counts) > 1 else 1.0)
    label_counts = pd.Series(labels).value_counts(normalize=True)
    chance = float(np.sum(label_counts**2))
    return pd.DataFrame(
        [
            {
                "metric": "15-nearest-neighbor same-label purity",
                "value": float(np.mean(purities)),
                "null_or_reference": chance,
                "interpretation": "Values near the class-frequency reference indicate overlapping landmarks rather than sharply separated classes.",
            },
            {
                "metric": "mean nearest-neighbor purity margin",
                "value": float(np.mean(margins)),
                "null_or_reference": np.nan,
                "interpretation": "Low margins indicate mixed local neighborhoods.",
            },
        ]
    )


def climate_cross_validation(features: pd.DataFrame) -> pd.DataFrame:
    complete = features[features["climate_available"]].dropna(subset=CLIMATE_COLS + MORPH_COLS + ["region", "year"]).copy()
    rows = []
    for fold_kind in ["random", "region", "year_block"]:
        rows.append(cross_validated_r2(complete, CLIMATE_COLS, ["morph_pc1", "morph_pc2", "morph_pc3"], fold_kind=fold_kind, label="climate predicts morphology"))
        rows.append(cross_validated_r2(complete, ["morph_pc1", "morph_pc2", "morph_pc3"], CLIMATE_COLS, fold_kind=fold_kind, label="morphology predicts climate"))
    return pd.concat([r for r in rows if not r.empty], ignore_index=True)


def matched_population(features: pd.DataFrame, seed: int = SEED) -> pd.DataFrame:
    complete = features[features["climate_available"]].dropna(subset=CLIMATE_COLS + ["morph_pc1", "morph_pc2", "morph_pc3"]).copy()
    sample = complete.sample(min(35000, len(complete)), random_state=seed).reset_index(drop=True)
    geom, _ = _standardized(sample, ["morph_pc1", "morph_pc2", "morph_pc3"])
    clim, _ = _standardized(sample, ["mean_maximum_temperature_c", "mean_vpd_kpa", "mean_wind_speed_m_s"])
    rng = np.random.default_rng(seed)
    rows = []
    for mode, basis, other, basis_name, other_name in [
        ("similar morphology", geom, clim, "morphology_distance", "climate_distance"),
        ("similar climate", clim, geom, "climate_distance", "morphology_distance"),
    ]:
        tree = cKDTree(basis)
        dist, neigh = tree.query(basis, k=2)
        other_dist = np.linalg.norm(other[np.ravel(neigh[:, 1])] - other, axis=1)
        random_idx = rng.permutation(len(sample))
        random_other = np.linalg.norm(other[random_idx] - other, axis=1)
        rows.append(
            {
                "matching_basis": mode,
                "n_pairs": int(len(sample)),
                basis_name: float(np.median(np.ravel(dist[:, 1]))),
                other_name: float(np.median(other_dist)),
                "random_other_distance_median": float(np.median(random_other)),
                "standardized_effect": float((np.median(other_dist) - np.median(random_other)) / np.std(random_other)),
            }
        )
    return pd.DataFrame(rows)


def safe_stage_table(slices: pd.DataFrame, features: pd.DataFrame) -> pd.DataFrame:
    target = features[["fire_id", "year", "region", "final_area_km2", "duration_days", "morph_pc1", "morph_pc2", "morph_pc3"]].copy()
    target["fire_id"] = target["fire_id"].astype(str)
    g = slices.sort_values(["fire_id", "slice_index"]).copy()
    g["fire_id"] = g["fire_id"].astype(str)
    grouped = g.groupby("fire_id", sort=False)
    g["elapsed_observations"] = grouped.cumcount() + 1
    growth = g["ring_area_km2"].fillna(0).clip(lower=0)
    g["growth_so_far_km2"] = growth.groupby(g["fire_id"]).cumsum()
    g["max_growth_so_far_km2"] = growth.groupby(g["fire_id"]).cummax()
    g["active_days_so_far"] = (growth > 0).astype(int).groupby(g["fire_id"]).cumsum()
    for src, dst in [
        ("maximum_temperature_c", "mean_tmax_so_far_c"),
        ("vpd_kpa", "mean_vpd_so_far_kpa"),
        ("wind_speed_m_s", "mean_wind_so_far_m_s"),
    ]:
        vals = g[src].astype(float)
        counts = vals.notna().astype(int).groupby(g["fire_id"]).cumsum().replace(0, np.nan)
        sums = vals.fillna(0).groupby(g["fire_id"]).cumsum()
        g[dst] = sums / counts
    g["climate_complete_so_far"] = g["climate_available"].astype(bool).groupby(g["fire_id"]).cummin()
    keep = g[g["elapsed_observations"].isin([1, 2, 4, 8])].copy()
    keep["stage_order"] = keep["elapsed_observations"].astype(int)
    keep["stage"] = "day " + keep["stage_order"].astype(str)
    out = keep[
        [
            "fire_id",
            "stage",
            "stage_order",
            "elapsed_observations",
            "cumulative_area_km2",
            "growth_so_far_km2",
            "max_growth_so_far_km2",
            "active_days_so_far",
            "mean_tmax_so_far_c",
            "mean_vpd_so_far_kpa",
            "mean_wind_so_far_m_s",
            "climate_complete_so_far",
        ]
    ].rename(columns={"cumulative_area_km2": "area_so_far_km2"})
    return out.merge(target, on="fire_id", how="left")


def safe_stage_prediction(slices: pd.DataFrame, features: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    stage = safe_stage_table(slices, features)
    geometry = ["area_so_far_km2", "growth_so_far_km2", "max_growth_so_far_km2", "active_days_so_far", "elapsed_observations"]
    climate = ["mean_tmax_so_far_c", "mean_vpd_so_far_kpa", "mean_wind_so_far_m_s"]
    trivial = ["area_so_far_km2", "elapsed_observations"]
    rows = []
    pred_rows = []
    for stage_name, sub in stage.groupby("stage"):
        sub = sub.dropna(subset=["morph_pc1", "morph_pc2", "morph_pc3"]).copy()
        if len(sub) < 500:
            continue
        for label, predictors in [
            ("trivial stage summary", trivial),
            ("geometry only", geometry),
            ("climate only", climate),
            ("geometry + climate", geometry + climate),
        ]:
            for fold_kind in ["random", "region", "year_block"]:
                cv = cross_validated_r2(sub, predictors, ["morph_pc1", "morph_pc2", "morph_pc3"], fold_kind=fold_kind, label=label)
                cv["stage"] = stage_name
                cv["stage_order"] = int(stage_name.split()[1])
                rows.append(cv)
        if stage_name == "day 4":
            clean = sub.dropna(subset=geometry + ["morph_pc1"]).copy()
            if len(clean) > 500:
                folds = _fold_assignments(clean, "region", 5, SEED)
                x, _ = _standardized(clean, geometry)
                y = clean["morph_pc1"].to_numpy(float)
                for fold in sorted(np.unique(folds)):
                    train = folds != fold
                    test = folds == fold
                    pred = _ols_fit_predict(x[train], y[train], x[test])
                    pred_rows.append(pd.DataFrame({"fire_id": clean.loc[test, "fire_id"].to_numpy(), "observed_pc1": y[test], "predicted_pc1": pred, "fold": fold}))
    return pd.concat(rows, ignore_index=True), pd.concat(pred_rows, ignore_index=True) if pred_rows else pd.DataFrame()


def leakage_audit_table() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "feature_source": "developmental_stage_table.stage_growth_fraction",
                "status": "leakage risk",
                "reason": "Computed as growth divided by final event area, unavailable at early prediction time.",
                "action": "Excluded from safe fixed-day prediction models.",
            },
            {
                "feature_source": "developmental_stage_table.stage_width_mean",
                "status": "leakage risk",
                "reason": "Uses normalized VASE width based on final cumulative area.",
                "action": "Excluded from safe fixed-day prediction models.",
            },
            {
                "feature_source": "developmental_stage_table.pulse_count",
                "status": "leakage risk",
                "reason": "Full-event pulse count can include future pulses.",
                "action": "Excluded from safe fixed-day prediction models.",
            },
            {
                "feature_source": "fixed-day safe stage predictors",
                "status": "audited",
                "reason": "Use only cumulative area, growth, active days, and climate observed up to day 1, 2, 4, or 8.",
                "action": "Used for Figure 5.",
            },
        ]
    )


def compute_validation_bundle(data: dict[str, pd.DataFrame], *, reps: int = 160, sample_size: int = 25000, force: bool = False) -> ValidationBundle:
    DERIVED_STATS_DIR.mkdir(parents=True, exist_ok=True)
    required = [
        "observed.json",
        "pca_bootstrap.csv",
        "pca_null.csv",
        "duration_sensitivity.csv",
        "ablation.csv",
        "medoid_coverage.csv",
        "category_overlap.csv",
        "climate_cv.csv",
        "matched_population.csv",
        "safe_stage_prediction.csv",
        "safe_stage_predictions_pc1.csv",
        "leakage_audit.csv",
    ]
    if not force and all((DERIVED_STATS_DIR / name).exists() for name in required):
        observed = json.loads((DERIVED_STATS_DIR / "observed.json").read_text(encoding="utf-8"))
        return ValidationBundle(
            observed=observed,
            pca_bootstrap=_read("pca_bootstrap"),
            pca_null=_read("pca_null"),
            duration_sensitivity=_read("duration_sensitivity"),
            ablation=_read("ablation"),
            medoid_coverage=_read("medoid_coverage"),
            category_overlap=_read("category_overlap"),
            climate_cv=_read("climate_cv"),
            matched_population=_read("matched_population"),
            safe_stage_prediction=_read("safe_stage_prediction"),
            safe_stage_predictions_pc1=_read("safe_stage_predictions_pc1"),
            leakage_audit=_read("leakage_audit"),
        )
    features = data["features"]
    columns = geometry_columns(features, data["loadings"])
    pca = fit_pca(features, columns, n_components=10)
    observed = {
        "n_fires": int(len(features)),
        "n_slices": int(len(data["slices"])),
        "n_climate_complete_fires": int(features["climate_available"].sum()),
        "pc_explained_variance": [float(v) for v in pca.explained_variance_ratio[:10]],
        "cumvar_pc1_5": float(pca.explained_variance_ratio[:5].sum()),
        "bootstrap_replicates": reps,
        "bootstrap_sample_size": sample_size,
    }
    (DERIVED_STATS_DIR / "observed.json").write_text(json.dumps(observed, indent=2), encoding="utf-8")
    boot = pca_bootstrap(features, columns, pca.loadings, reps=reps, sample_size=sample_size, seed=SEED)
    null = pca_nulls(features, columns, observed["cumvar_pc1_5"], reps=max(60, reps // 2), sample_size=sample_size, seed=SEED + 1)
    duration = duration_sensitivity(features, columns)
    ablation = feature_ablation(features, columns)
    coverage = medoid_coverage(features, data["medoids"])
    overlap = category_overlap(features)
    climate = climate_cross_validation(features)
    matched = matched_population(features)
    stage_pred, stage_pc1 = safe_stage_prediction(data["slices"], features)
    leakage = leakage_audit_table()
    for name, frame in [
        ("pca_bootstrap", boot),
        ("pca_null", null),
        ("duration_sensitivity", duration),
        ("ablation", ablation),
        ("medoid_coverage", coverage),
        ("category_overlap", overlap),
        ("climate_cv", climate),
        ("matched_population", matched),
        ("safe_stage_prediction", stage_pred),
        ("safe_stage_predictions_pc1", stage_pc1),
        ("leakage_audit", leakage),
    ]:
        _write(frame, name)
    return ValidationBundle(observed, boot, null, duration, ablation, coverage, overlap, climate, matched, stage_pred, stage_pc1, leakage)
