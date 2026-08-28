"""Auditable second-generation morphology, validation and matching primitives.

No file discovery, synthetic fallback, or global fitted preprocessing lives here.
All randomization is explicit and seeded. Null simulations are not observations.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import numpy as np
import pandas as pd
from scipy.signal import find_peaks
from scipy.spatial import cKDTree, ConvexHull
from scipy.optimize import linear_sum_assignment

CORE = ["maximum_temperature_c", "minimum_temperature_c", "vpd_kpa", "wind_speed_m_s"]
WEATHER = CORE + ["precipitation_mm", "maximum_relative_humidity_pct",
    "minimum_relative_humidity_pct", "specific_humidity_kg_kg", "fuel_moisture_100hr_pct",
    "fuel_moisture_1000hr_pct", "energy_release_component", "burning_index",
    "reference_evapotranspiration_mm", "potential_evapotranspiration_mm", "solar_radiation_w_m2"]
TRAITS = ["front_loaded_fraction", "late_growth_fraction", "peak_timing",
          "terminal_taper_fraction", "normalized_entropy", "pulse_count", "reactivation_count",
          "normalized_first_difference", "normalized_second_difference"]
RULES = [
    ("invalid growth", "missing/nonfinite/negative increment or nonpositive reconstructed total"),
    ("one observation", "observation_count == 1 (no internal history)"),
    ("two observations", "observation_count == 2 (limited internal history)"),
    ("gappy or undated", "missing/duplicate dates or any non-one-day interval"),
    ("multiple detected pulses", "at least 2 local maxima with prominence >= 0.20 * observed peak"),
    ("late peak", "peak_timing >= 2/3"),
    ("front-loaded taper", "front_loaded_fraction >= .75 and terminal_taper_fraction <= .35"),
    ("distributed growth", "all remaining eligible histories"),
]


def growth_summary(growth, duration_days, catalog_area):
    """Peak is max observed daily increment, never total/duration or hourly peak."""
    g = np.asarray(growth, float)
    valid = len(g) > 0 and np.isfinite(g).all() and (g >= 0).all()
    total = float(g.sum()) if valid else np.nan
    positive = valid and total > 0
    p = g / total if positive else np.full(len(g), np.nan)
    entropy = float(-np.sum(p[p > 0] * np.log(p[p > 0]))) if positive else np.nan
    return {"reconstructed_area_km2": total, "catalog_area_km2": float(catalog_area),
        "area_discrepancy_km2": total - catalog_area,
        "relative_area_discrepancy": (total - catalog_area) / catalog_area if catalog_area > 0 else np.nan,
        "mean_catalog_growth_km2_per_day": catalog_area / duration_days if duration_days > 0 else np.nan,
        "mean_observed_growth_km2_per_day": total / len(g) if valid else np.nan,
        "peak_growth_km2_per_day": float(g.max()) if valid else np.nan,
        "shannon_entropy": entropy,
        "normalized_entropy": entropy / np.log(len(g)) if positive and len(g) > 1 else (0. if positive else np.nan),
        "growth_valid": bool(positive)}, p


def allocation_profile(probabilities, bins=20):
    """Mass-conserving rebinning of consecutive daily increments on [0,1].

    Each observed day occupies an equal-width interval. Interpolate cumulative
    mass at interval edges, then difference. Returned bin masses sum to one.
    Gappy histories may use this only as an explicitly observation-time sensitivity.
    """
    p = np.asarray(probabilities, float)
    if not len(p) or not np.isfinite(p).all() or (p < 0).any() or not np.isclose(p.sum(), 1.):
        raise ValueError("A complete, nonnegative probability allocation summing to one is required")
    cdf = np.interp(np.linspace(0, 1, bins + 1), np.linspace(0, 1, len(p) + 1), np.r_[0., np.cumsum(p)])
    mass = np.diff(cdf)
    return mass / mass.sum()


def pulse_counts(growth):
    g = np.asarray(growth, float)
    if not np.isfinite(g).all() or (g < 0).any():
        raise ValueError("Pulse detection does not impute missing growth")
    if len(g) == 0 or g.max() == 0:
        return 0, 0
    peaks, _ = find_peaks(np.r_[0., g, 0.], prominence=.20 * g.max())
    active = g >= .25 * g.max()
    reactivations, low, seen = 0, 0, False
    for value in active:
        if value:
            reactivations += int(seen and low >= 2)
            seen, low = True, 0
        elif seen:
            low += 1
    return int(len(peaks)), reactivations


def neighborhood(row):
    if not row["growth_valid"]:
        return RULES[0][0]
    if row["observation_count"] == 1:
        return RULES[1][0]
    if row["observation_count"] == 2:
        return RULES[2][0]
    if not row["consecutive"]:
        return RULES[3][0]
    if row["pulse_count"] >= 2:
        return RULES[4][0]
    if row["peak_timing"] >= 2/3:
        return RULES[5][0]
    if row["front_loaded_fraction"] >= .75 and row["terminal_taper_fraction"] <= .35:
        return RULES[6][0]
    return RULES[7][0]


def shape_traits(p, bins=20):
    profile = allocation_profile(p, bins)
    density = profile * bins
    cdf = np.r_[0., np.cumsum(p)]
    pulses, reactivations = pulse_counts(p)
    return dict(front_loaded_fraction=float(np.interp(.5, np.linspace(0, 1, len(p)+1), cdf)),
        late_growth_fraction=float(1-np.interp(.75, np.linspace(0, 1, len(p)+1), cdf)),
        peak_timing=float((np.argmax(p)+.5)/len(p)),
        terminal_taper_fraction=float(p[-1]/p.max()), pulse_count=pulses,
        reactivation_count=reactivations,
        normalized_first_difference=float(np.abs(np.diff(density)).mean()),
        normalized_second_difference=float(np.abs(np.diff(density, n=2)).mean())), profile


@dataclass
class PCA:
    mean: np.ndarray
    scale: np.ndarray
    loadings: np.ndarray
    evr: np.ndarray

    def transform(self, x):
        return ((np.asarray(x, float)-self.mean)/self.scale) @ self.loadings


def fit_pca(x):
    x = np.asarray(x, float)
    if len(x) < 2 or not np.isfinite(x).all():
        raise ValueError("PCA requires at least two finite rows; no silent imputation")
    mu, sd = x.mean(axis=0), x.std(axis=0)
    sd[sd < 1e-12] = 1.
    z = (x-mu)/sd
    eigenvalues, vectors = np.linalg.eigh(z.T @ z / len(z))
    order = np.argsort(eigenvalues)[::-1]
    eigenvalues, vectors = np.maximum(eigenvalues[order], 0), vectors[:, order]
    for j in range(vectors.shape[1]):
        if vectors[np.argmax(np.abs(vectors[:, j])), j] < 0:
            vectors[:, j] *= -1
    evr = eigenvalues/eigenvalues.sum() if eigenvalues.sum() > 1e-20 else np.zeros_like(eigenvalues)
    return PCA(mu, sd, vectors, evr)


def pca_metrics(x):
    fit = fit_pca(x)
    scores = fit.transform(x)[:, :2]
    if fit.evr.sum() == 0:
        return dict(pc1=0., first_five=0., effective_dimension=0., hull_fill=np.nan, occupied_fraction=np.nan)
    lo, hi = np.quantile(scores, [.01, .99], axis=0)
    z = np.clip((scores-lo)/np.maximum(hi-lo, 1e-10), 0, 1)
    occupancy = len(np.unique(np.minimum((z * 20).astype(int), 19), axis=0))/400
    hull = ConvexHull(z).volume if np.linalg.matrix_rank(z-z.mean(0)) == 2 else 0.
    return dict(pc1=fit.evr[0], first_five=fit.evr[:5].sum(),
        effective_dimension=1/np.sum(fit.evr**2), hull_fill=hull, occupied_fraction=occupancy)


def loading_alignment(reference, other, k=5):
    k = min(k, reference.shape[1], other.shape[1])
    corr = reference[:, :k].T @ other[:, :k]
    a, b = linear_sum_assignment(-np.abs(corr))
    aligned = other[:, b] * np.sign(corr[a, b])[None, :]
    singular = np.linalg.svd(corr, compute_uv=False)
    return aligned, np.abs(corr[a, b]), float(np.mean(singular**2))


def exact_transitions(slices):
    """Build responses before weather filtering; missing dates/areas stay missing."""
    s = slices.copy()
    s["timestamp"] = pd.to_datetime(s.timestamp, errors="coerce")
    s = s.sort_values(["fire_id", "timestamp", "slice_index"]).reset_index(drop=True)
    g = s.groupby("fire_id", sort=False)
    s["response_date"] = g.timestamp.shift(-1)
    s["gap_days"] = (s.response_date-s.timestamp).dt.total_seconds()/86400
    s["previous_gap_days"] = (s.timestamp-g.timestamp.shift()).dt.total_seconds()/86400
    s["next_growth_km2"] = g.ring_area_km2.shift(-1)
    s["previous_growth_km2"] = g.ring_area_km2.shift().where(s.previous_gap_days.eq(1))
    duplicated = s.duplicated(["fire_id", "timestamp"], keep=False)
    s["duplicate_date"] = duplicated
    next_duplicate = s.groupby("fire_id").duplicate_date.shift(-1).eq(True)
    s["elapsed_day"] = (s.timestamp-g.timestamp.transform("min")).dt.days
    audit = {"rows": len(s), "one_day_transitions": int(s.gap_days.eq(1).sum()),
        "longer_gaps": int(s.gap_days.gt(1).sum()), "missing_dates": int(s.timestamp.isna().sum()),
        "duplicate_date_rows": int(duplicated.sum()), "terminal_rows": int(s.response_date.isna().sum()),
        "zero_day_transitions": int(s.gap_days.eq(0).sum())}
    eligible = s.gap_days.eq(1) & ~duplicated & ~next_duplicate
    eligible &= s.ring_area_km2.ge(0) & s.next_growth_km2.ge(0)
    audit["eligible_transitions"] = int(eligible.sum())
    audit["excluded_rows"] = int((~eligible).sum())
    return s.loc[eligible].copy(), audit


def validate_exposure(frame, prospective=True):
    if prospective:
        allowed = {"day_t_newly_burned_centroid", "day_t_cumulative_centroid", "day_t_active_area"}
        if not frame.exposure_geometry.isin(allowed).all():
            raise ValueError("Final-event geometry is prohibited in prospective exposure")
        if not pd.to_datetime(frame.geometry_max_date).le(pd.to_datetime(frame.timestamp)).all():
            raise ValueError("Future geometry entered a prospective model")


def predictor_sets():
    core = ["mean_" + c for c in CORE]
    full = ["mean_" + c for c in WEATHER]
    length = ["log_duration", "log_observations"]
    return {"core_means": core, "max_vpd_only": ["max_vpd"],
        "core_plus_max": core+["max_vpd"], "comprehensive_means": full,
        "comprehensive_plus_max": full+["max_vpd"], "length_only": length,
        "length_plus_max": length+["max_vpd"], "length_plus_core": length+core,
        "length_plus_core_max": length+core+["max_vpd"],
        "core_quantile_exceedance": core+["q90_vpd", "vpd_gt_2_fraction", "wet_fraction"]}


def complete_cohort(frame, sets, responses):
    columns = list(dict.fromkeys(sum(sets.values(), []) + list(responses)))
    return frame.replace([np.inf, -np.inf], np.nan).dropna(subset=columns).sort_values("fire_id").reset_index(drop=True)


def cohort_hash(frame):
    keys = frame.fire_id.astype(str)
    if "timestamp" in frame:
        keys = keys + "@" + frame.timestamp.astype(str)
    return hashlib.sha256("\n".join(keys).encode()).hexdigest()


def splits(frame, kind):
    year = ((frame.year.to_numpy(int)-2000)//5).clip(0, 4)
    region = frame.region.to_numpy(str)
    if kind == "random_fire":
        values = pd.util.hash_pandas_object(frame.fire_id.astype(str), index=False).to_numpy()%5
    elif kind == "year_block":
        values = year
    elif kind == "region_block":
        values = region
    elif kind == "spatiotemporal":
        for r in sorted(set(region)):
            for y in sorted(set(year)):
                yield f"{r}:{2000+5*y}-{2004+5*y}", (region != r) & (year != y), (region == r) & (year == y)
        return
    else:
        raise ValueError(kind)
    for value in sorted(set(values)):
        yield str(value), values != value, values == value


def ridge_predict(xtrain, xtest, ytrain, alpha=1.):
    mu = xtrain.mean(0)
    sd = xtrain.std(0)
    sd[sd < 1e-12] = 1.
    a, b = (xtrain-mu)/sd, (xtest-mu)/sd
    ym = ytrain.mean(0)
    beta = np.linalg.solve(a.T @ a + alpha*np.eye(a.shape[1]), a.T @ (ytrain-ym))
    return b @ beta + ym, mu, sd


def r2(y, pred):
    den = ((y-y.mean())**2).sum()
    return float(1-((y-pred)**2).sum()/den) if den > 1e-15 else np.nan


def cluster_intervals(frame, y, pred, reference, reps=200, seed=20260828):
    """Paired cluster bootstrap of fixed held-out predictions (not model refits)."""
    rng = np.random.default_rng(seed)
    rows = []
    for unit in ["fire_id", "year", "region"]:
        codes, uniques = pd.factorize(frame[unit], sort=True)
        groups = len(uniques)
        sums = np.column_stack([np.bincount(codes), np.bincount(codes, weights=y),
            np.bincount(codes, weights=y*y), np.bincount(codes, weights=(y-pred)**2),
            np.bincount(codes, weights=(y-reference)**2)])
        vals = []
        for _ in range(reps):
            n, sy, sy2, se, sr = sums[rng.integers(0, groups, groups)].sum(0)
            den = sy2-sy*sy/n
            vals.append([1-se/den, (sr-se)/den] if den > 1e-12 else [np.nan, np.nan])
        vals = np.asarray(vals)
        q = np.nanquantile(vals, [.025, .975], axis=0) if np.isfinite(vals).any() else np.full((2,2), np.nan)
        rows.append(dict(resampling=unit, groups=groups, r2_low=q[0,0], r2_high=q[1,0],
            delta_low=q[0,1], delta_high=q[1,1]))
    return rows


def evaluate_models(frame, sets, responses, *, profile_columns=(), alphas=(.01, 1., 100.),
                    reps=200, reference="mean_only", kinds=None):
    """Identical population, group-safe folds, train-only transforms and PCA targets.

    PCA scores are standardized by the TRAINING eigenvalue and centered within
    each held-out fold for pooling. Axis signs are local deterministic conventions;
    per-fold metrics remain authoritative when axes rotate between folds.
    """
    kinds = kinds or ["random_fire", "year_block", "region_block", "spatiotemporal"]
    d = complete_cohort(frame, sets, list(responses)+list(profile_columns))
    if len(d) < 30:
        raise ValueError(f"Insufficient complete events/transitions: {len(d)}")
    identity = cohort_hash(d)
    base_y = d[list(responses)].to_numpy(float)
    pc_names = [f"shape_PC{i+1}_fold" for i in range(3)] if profile_columns else []
    names = list(responses)+pc_names
    def known_outcome(response, columns):
        aliases = {"legacy_duration_days":"log_duration", "legacy_final_area_km2":"log_area"}
        return aliases.get(response,response) in columns
    results, fold_rows, intervals, preprocessing, prediction_frames = [], [], [], [], []
    for kind in kinds:
        for alpha in alphas:
            predictions = {name: np.full((len(d), len(names)), np.nan) for name in sets}
            truths = np.full((len(d), len(names)), np.nan)
            mean_pred = np.full_like(truths, np.nan)
            for fold, train, test in splits(d, kind):
                if train.sum() < 30 or test.sum() < 2:
                    continue
                # Each fire must belong wholly to train, test, or excluded buffer.
                if set(d.loc[train,"fire_id"]) & set(d.loc[test,"fire_id"]):
                    raise AssertionError("Fire leakage across folds")
                ytr, yte = base_y[train], base_y[test]
                if profile_columns:
                    pfit = fit_pca(d.loc[train, list(profile_columns)])
                    ptr = pfit.transform(d.loc[train, list(profile_columns)])[:, :3]
                    pte = pfit.transform(d.loc[test, list(profile_columns)])[:, :3]
                    sd = np.maximum(ptr.std(0), 1e-12)
                    ytr, yte = np.c_[ytr, ptr/sd], np.c_[yte, pte/sd]
                    if alpha == 1.:
                        preprocessing.extend(dict(kind=kind, fold=fold, stage="outcome_pca", feature=c,
                            center=pfit.mean[j], scale=pfit.scale[j], train_n=int(train.sum()),
                            pc1_loading=pfit.loadings[j,0], pc1_evr=pfit.evr[0]) for j,c in enumerate(profile_columns))
                truths[test] = yte
                mean_pred[test] = ytr.mean(0)
                for name, cols in sets.items():
                    if name == "mean_only":
                        pred = np.broadcast_to(ytr.mean(0), yte.shape)
                    elif name == "persistence":
                        pred = d.loc[test, "current_growth_log1p"].to_numpy()[:,None]
                    else:
                        x = d[cols].to_numpy(float)
                        pred, mu, sd = ridge_predict(x[train], x[test], ytr, alpha)
                        if alpha == 1.:
                            preprocessing.extend(dict(kind=kind, fold=fold, stage=name, feature=c,
                                center=mu[j], scale=sd[j], train_n=int(train.sum())) for j,c in enumerate(cols))
                    predictions[name][test] = pred
                    for j,response in enumerate(names):
                        fold_rows.append(dict(kind=kind, fold=fold, alpha=alpha, predictor_set=name,
                            response=response, n=int(test.sum()), train_n=int(train.sum()),
                            r2=np.nan if known_outcome(response,cols) else r2(yte[:,j], pred[:,j]),
                            status="excluded_known_outcome" if known_outcome(response,cols) else "evaluated",
                            cohort_hash=identity))
                if profile_columns:
                    # Fold centering affects the evaluation denominator only;
                    # predictions were already made without held-out outcomes.
                    offset = yte[:, len(responses):].mean(0)
                    truths[np.ix_(test, np.arange(len(responses),len(names)))] -= offset
                    mean_pred[np.ix_(test, np.arange(len(responses),len(names)))] -= offset
                    for name in predictions:
                        predictions[name][np.ix_(test, np.arange(len(responses),len(names)))] -= offset
            ref = predictions.get(reference, mean_pred)
            for name, pred in predictions.items():
                valid = np.isfinite(pred).all(1) & np.isfinite(truths).all(1) & np.isfinite(ref).all(1)
                if valid.sum() < 2:
                    continue
                for j,response in enumerate(names):
                    y, pp, rr = truths[valid,j], pred[valid,j], ref[valid,j]
                    if known_outcome(response,sets[name]):
                        results.append(dict(kind=kind,alpha=alpha,predictor_set=name,response=response,
                            n=int(valid.sum()),cohort_n=len(d),cohort_hash=identity,r2=np.nan,
                            reference=reference,delta_r2=np.nan,status="excluded_known_outcome"))
                        continue
                    score, base = r2(y,pp), r2(y,rr)
                    row = dict(kind=kind, alpha=alpha, predictor_set=name, response=response,
                        n=int(valid.sum()), cohort_n=len(d), cohort_hash=identity, r2=score,
                        reference=reference, delta_r2=score-base,status="evaluated")
                    results.append(row)
                    if alpha == 1.:
                        intervals.extend({**row, **ci} for ci in cluster_intervals(d.loc[valid],y,pp,rr,reps))
                if alpha == 1. and not profile_columns:
                    keep = [c for c in ["fire_id","timestamp","year","region","season","catalog_area_km2","observation_quality"] if c in d]
                    pf = d.loc[valid,keep].copy()
                    pf["kind"], pf["predictor_set"] = kind,name
                    pf["observed"], pf["predicted"], pf["reference"] = truths[valid,0],pred[valid,0],ref[valid,0]
                    prediction_frames.append(pf)
    return (pd.DataFrame(results), pd.DataFrame(fold_rows), pd.DataFrame(intervals),
            pd.DataFrame(preprocessing), pd.concat(prediction_frames,ignore_index=True) if prediction_frames else pd.DataFrame(), d)


def unique_matches(frame, columns, *, caliper=.5, k=10, metric="euclidean", area_log_caliper=np.log(2)):
    """Greedy disjoint nearest-neighbor graph within exact nuisance strata.

    Edge priority depends only on the matching space, never on mismatch outcomes.
    Distances are RMS z-differences (L2), mean absolute z-difference (L1).
    """
    d = frame.reset_index(drop=True)
    x = d[list(columns)].to_numpy(float)
    sd = x.std(0); sd[sd < 1e-12] = 1.
    z = (x-x.mean(0))/sd
    power = 2 if metric == "euclidean" else 1
    norm = len(columns)**(1/power)
    edges = []
    strata = ["region", "season", "duration_days", "observation_count"]
    for _, positions in d.groupby(strata, sort=True).indices.items():
        positions = np.asarray(positions)
        if len(positions) < 2:
            continue
        distances, neighbors = cKDTree(z[positions]).query(z[positions], k=min(k+1,len(positions)), p=power)
        for a in range(len(positions)):
            for dist,b in zip(np.atleast_1d(distances[a]), np.atleast_1d(neighbors[a])):
                i,j = sorted((int(positions[a]),int(positions[b])))
                if i == j or dist/norm > caliper:
                    continue
                if abs(np.log(d.catalog_area_km2.iloc[i]/d.catalog_area_km2.iloc[j])) > area_log_caliper:
                    continue
                edges.append((float(dist/norm), i,j))
    candidate_ids = {i for _,i,j in edges} | {j for _,i,j in edges}
    used, rows = set(), []
    for distance,i,j in sorted(set(edges)):
        if i in used or j in used:
            continue
        used.update((i,j))
        rows.append(dict(i=i,j=j, fire_id_a=d.fire_id.iloc[i],fire_id_b=d.fire_id.iloc[j],
            match_distance=distance, caliper=caliper,k=k,metric=metric,
            log_area_distance=abs(np.log(d.catalog_area_km2.iloc[i]/d.catalog_area_km2.iloc[j]))))
    result = pd.DataFrame(rows)
    result.attrs["good_match_exists_fraction"] = len(candidate_ids)/len(d) if len(d) else 0.
    return result, z
