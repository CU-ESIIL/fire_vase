#!/usr/bin/env python3
"""Bounded second-pass validation of saved v2 results; no new feature selection.

Run with PYTHONPATH=src:scripts and the v2 environment. Nulls are explicitly
simulated references, never observations. Each stage writes deterministic tables.
"""
from pathlib import Path
import argparse
import json
import subprocess
import sys
import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment
from scipy.spatial import cKDTree
from scipy.stats import rankdata, spearmanr
from cubedynamics.analysis_v2 import (CORE, TRAITS, fit_pca, pca_metrics,
    allocation_profile, shape_traits, neighborhood, predictor_sets, complete_cohort,
    exact_transitions, validate_exposure, splits, cohort_hash, evaluate_models,
    unique_matches, cluster_intervals, r2)
from fire_vase_v2_inputs import sha256

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "analysis/v2"
OUT = ROOT / "analysis/scientific_validation"
DATA = ROOT / "data_lake/fire-vase-data-lake-v0.1/files"
SEED = 20260828
CONFIG = dict(seed=SEED, bins=20, stability_anchors=1000, stability_bootstraps=100,
              stability_neighbors=15, distance_pairs=20000, null_events=4000,
              null_replicates=100, uncertainty_replicates=200,
              calipers=[.25, .5, .75, 1.], alpha=1.)


def write(frame, name):
    if isinstance(frame.columns,pd.MultiIndex):
        frame=frame.copy()
        frame.columns=["_".join(str(v) for v in col if str(v)) for col in frame.columns]
    frame.to_csv(OUT / f"{name}.csv", index=False, float_format="%.12g")


def read(name):
    return pd.read_csv(BASE / f"{name}.csv")


def load_data():
    d = pd.read_parquet(BASE / "event_analysis.parquet")
    d.fire_id = d.fire_id.astype(str)
    s = pd.read_parquet(DATA / "scratch/fire_vase_run_full/tables/vase_slices.parquet")
    s.fire_id = s.fire_id.astype(str)
    s.timestamp = pd.to_datetime(s.timestamp)
    return d, s.sort_values(["fire_id", "timestamp", "slice_index"])


def population(d, s):
    counts = []
    for label, mask in [("1", d.observation_count.eq(1)), ("2", d.observation_count.eq(2))] + [
            (f">={n}", d.observation_count.ge(n)) for n in [3, 5, 7]]:
        g = d[mask]
        counts.append(dict(observations=label, all_events=len(g), consecutive=int(g.consecutive.sum()),
            weather_complete=int(g.weather_complete.sum()),
            consecutive_weather_complete=int((g.consecutive & g.weather_complete).sum()),
            primary=int(g.primary_eligible.sum())))
    write(pd.DataFrame(counts), "observation_counts")
    gaps = s.groupby("fire_id").timestamp.diff().dt.total_seconds()/86400
    audit = dict(events=len(d), slices=len(s), adjacent_observed_pairs=int(gaps.notna().sum()),
        exactly_one_day=int(gaps.eq(1).sum()), exactly_two_days=int(gaps.eq(2).sum()),
        greater_than_two_days=int(gaps.gt(2).sum()), missing_dates=int(s.timestamp.isna().sum()),
        duplicate_dates=int(s.duplicated(["fire_id", "timestamp"], keep=False).sum()),
        zero_growth_observations=int(s.ring_area_km2.eq(0).sum()),
        primary=int(d.primary_eligible.sum()), weather_complete=int(d.weather_complete.sum()),
        primary_weather_complete=int((d.primary_eligible & d.weather_complete).sum()),
        date_min=str(s.timestamp.min()), date_max=str(s.timestamp.max()))
    (OUT / "population_audit.json").write_text(json.dumps(audit, indent=2))
    rows = []
    for population_name, group in [("all_events", d), ("primary", d[d.primary_eligible])]:
        for dim in ["region", "year", "observation_count", "neighborhood"]:
            for value, g in group.groupby(dim, observed=True):
                rows.append(dict(population=population_name, dimension=dim, value=value, n=len(g),
                    complete=int(g.weather_complete.sum()), incomplete=int((~g.weather_complete).sum()),
                    complete_fraction=g.weather_complete.mean()))
    write(pd.DataFrame(rows), "weather_selection_counts")
    rows = []
    for population_name, group in [("all_events", d), ("primary", d[d.primary_eligible])]:
        for col in ["duration_days", "catalog_area_km2", "observation_count"] + TRAITS:
            a, b = [g[col].dropna().to_numpy(float) for _, g in group.groupby("weather_complete", sort=True)]
            sd = np.sqrt((a.var()+b.var())/2)
            for complete, x in [(False, a), (True, b)]:
                rows.append(dict(population=population_name, variable=col, complete=complete, n=len(x),
                    mean=x.mean(), q10=np.quantile(x,.1), median=np.median(x), q90=np.quantile(x,.9),
                    complete_minus_incomplete_smd=(b.mean()-a.mean())/sd if sd else np.nan))
    write(pd.DataFrame(rows), "weather_selection_traits")


def geometry_similarity(reference, other, anchors, pairs, neighbors=15):
    """Both fits are evaluated on identical anchors; no axis-wise scaling of scores.

    Orthogonal Procrustes permits rotation and one global scale, not anisotropic
    rescaling. Distances and neighbors use the first five *unwhitened* PCs.
    """
    a = reference.transform(anchors)[:, :5]
    b = other.transform(anchors)[:, :5]
    cross = reference.loadings[:, :5].T @ other.loadings[:, :5]
    ii, jj = linear_sum_assignment(-np.abs(cross))
    aligned = b[:, jj] * np.where(cross[ii,jj] < 0, -1., 1.)
    ac, bc = a-a.mean(0), b-b.mean(0)
    ac /= np.linalg.norm(ac); bc /= np.linalg.norm(bc)
    similarity = np.linalg.svd(ac.T @ bc, compute_uv=False).sum()
    i, j = pairs
    da = np.linalg.norm(a[i]-a[j], axis=1); db = np.linalg.norm(b[i]-b[j], axis=1)
    # Remove self by identity, not by dropping the first query result (ties exist).
    def knn(x):
        raw = cKDTree(x).query(x, k=neighbors+1)[1]
        return [set(row[row != i][:neighbors]) for i,row in enumerate(raw)]
    ka, kb = knn(a), knn(b)
    exemplar = []
    n = max(10, int(len(a)*.02))
    for k in range(5):
        aa, bb = np.argsort(a[:,k],kind="stable"), np.argsort(aligned[:,k],kind="stable")
        for side in [slice(None,n), slice(-n,None)]:
            x,y = set(aa[side]),set(bb[side]); exemplar.append(len(x&y)/len(x|y))
    singular = np.linalg.svd(cross, compute_uv=False)
    return dict(procrustes_similarity=similarity, subspace_overlap=np.mean(singular**2),
        pair_distance_spearman=spearmanr(da,db).statistic,
        neighbor_overlap=np.mean([len(x&y)/neighbors for x,y in zip(ka,kb)]),
        exemplar_tail_jaccard=np.mean(exemplar),
        **{f"axis{k+1}_correlation":np.corrcoef(a[:,k],aligned[:,k])[0,1] for k in range(5)},
        **{f"loading{k+1}_cosine":abs(cross[k,jj[k]]) for k in range(5)})


def stability(d, profiles):
    rng = np.random.default_rng(SEED)
    p = d[d.primary_eligible].sort_values("fire_id")
    x = p[profiles].to_numpy(float); ref = fit_pca(x)
    anchor_idx = rng.choice(len(p), min(CONFIG["stability_anchors"],len(p)), replace=False)
    anchors = x[anchor_idx]
    pair = rng.integers(0,len(anchors),(2,CONFIG["distance_pairs"]))
    pair = pair[:,pair[0]!=pair[1]]
    write(p.iloc[anchor_idx][["fire_id", "region", "year", "observation_count"]], "stability_anchors")
    saved = read("pca_loadings")
    np.testing.assert_allclose(ref.loadings, saved[[f"PC{i+1}" for i in range(20)]],atol=2e-10)
    rows = []
    def compare(kind,label,xx):
        other = fit_pca(xx)
        rows.append(dict(comparison=kind, label=str(label), n=len(xx), anchors=len(anchors),
            pc1=other.evr[0], first_five=other.evr[:5].sum(),
            **geometry_similarity(ref,other,anchors,pair,CONFIG["stability_neighbors"])))
    for n in [2,3,5,7]:
        compare("observation_threshold", n, d.loc[d.consecutive & d.growth_valid & d.observation_count.ge(n),profiles].to_numpy(float))
    for dim in ["region", "year"]:
        for label,g in p.groupby(dim):
            if len(g)>=30: compare(dim,label,g[profiles].to_numpy(float))
    for rep in range(CONFIG["stability_bootstraps"]):
        compare("bootstrap",rep,x[rng.integers(0,len(x),len(x))])
    write(pd.DataFrame(rows),"morphospace_stability")
    rows=[]
    for n in [3,5,7]:
        g=d[d.consecutive & d.growth_valid & d.observation_count.ge(n)]
        scores=ref.transform(g[profiles])
        for col in ["catalog_area_km2", "duration_days", "observation_count", "peak_growth_km2_per_day",
                    "mean_catalog_growth_km2_per_day", "mean_observed_growth_km2_per_day"]:
            for axis in range(5):
                rows.append(dict(minimum_observations=n,n=len(g),attribute=col,axis=axis+1,
                    spearman=spearmanr(g[col],scores[:,axis]).statistic))
    write(pd.DataFrame(rows),"endpoint_projections")


def null_growth(g, name, rng):
    """Keep actual reconstructed total and count; shuffle also preserves multiset."""
    if name == "temporal_shuffle": return rng.permutation(g)
    alpha = {"dirichlet_1":1., "dirichlet_10":10.}[name]
    return rng.dirichlet(np.full(len(g),alpha))*np.sum(g)


def null_histories(d,s,profiles):
    rng=np.random.default_rng(SEED)
    primary=d[d.primary_eligible].sort_values("fire_id")
    selected=primary.iloc[rng.choice(len(primary),CONFIG["null_events"],replace=False)]
    selected_ids=set(selected.fire_id)
    growth={fid:g.ring_area_km2.to_numpy(float) for fid,g in s[s.fire_id.isin(selected_ids)].groupby("fire_id",sort=False)}
    original=[growth[fid] for fid in selected.fire_id]
    write(selected[["fire_id","observation_count","reconstructed_area_km2"]],"null_sample")
    ref=fit_pca(primary[profiles]); pairs=rng.integers(0,len(original),(2,CONFIG["distance_pairs"]))
    pairs=pairs[:,pairs[0]!=pairs[1]]
    def metrics(histories):
        records=[]; profiles_x=[]
        for g in histories:
            p=g/g.sum(); tr,xx=shape_traits(p)
            tr["normalized_entropy"]=-np.sum(p[p>0]*np.log(p[p>0]))/np.log(len(p))
            tr.update(growth_valid=True,consecutive=True,observation_count=len(p))
            tr["landmark"]=neighborhood(tr)
            records.append(tr);profiles_x.append(xx)
        xx=np.array(profiles_x);t=pd.DataFrame(records)
        zz=(xx-ref.mean)/ref.scale
        dist=np.sqrt(np.mean((zz[pairs[0]]-zz[pairs[1]])**2,axis=1))
        result=pca_metrics(xx)
        for q in [.1,.5,.9]: result[f"profile_distance_q{int(q*100)}"]=np.quantile(dist,q)
        for c in ["front_loaded_fraction","normalized_entropy","pulse_count","reactivation_count","peak_timing"]:
            result[c+"_mean"]=t[c].mean()
            for q in [.1,.5,.9]:result[c+f"_q{int(q*100)}"]=t[c].quantile(q)
        for label in ["multiple detected pulses","late peak","front-loaded taper","distributed growth"]:
            result["landmark_"+label.replace(" ","_")]=t.landmark.eq(label).mean()
        return result
    observed=metrics(original);rows=[dict(null="observed",rep=-1,n=len(original),**observed)]
    for rep in range(CONFIG["null_replicates"]):
        for name in ["temporal_shuffle","dirichlet_1","dirichlet_10"]:
            histories=[null_growth(g,name,rng) for g in original]
            assert all(len(a)==len(b) and np.isclose(a.sum(),b.sum()) for a,b in zip(original,histories))
            if name=="temporal_shuffle":assert all(np.array_equal(np.sort(a),np.sort(b)) for a,b in zip(original,histories))
            rows.append(dict(null=name,rep=rep,n=len(original),**metrics(histories)))
        if rep%20==0:print(f"Null-history replicate {rep+1}/100",flush=True)
    null=pd.DataFrame(rows);write(null,"null_history_replicates")
    rows=[]
    for name,g in null[null.rep.ge(0)].groupby("null"):
        for metric,value in observed.items():
            vals=g[metric];tol=1e-10*max(1,abs(value))
            rows.append(dict(null=name,metric=metric,n=len(original),observed=value,null_mean=vals.mean(),
                null_low=vals.quantile(.025),null_high=vals.quantile(.975),difference=value-vals.mean(),
                upper_tail=(1+vals.ge(value-tol).sum())/(len(vals)+1),
                lower_tail=(1+vals.le(value+tol).sum())/(len(vals)+1)))
    write(pd.DataFrame(rows),"null_history_comparison")


def partial_rank(x,y,c):
    ranks=np.column_stack([rankdata(x),rankdata(y)])
    residual=ranks-c@np.linalg.lstsq(c,ranks,rcond=None)[0]
    return np.corrcoef(ranks.T)[0,1],np.corrcoef(residual.T)[0,1],residual


def association_intervals(d,residual,reps=200):
    rows=[];rng=np.random.default_rng(SEED)
    for unit in ["fire_id","year","region"]:
        codes,groups=pd.factorize(d[unit],sort=True);x,y=residual.T
        sums=np.c_[np.bincount(codes),np.bincount(codes,weights=x),np.bincount(codes,weights=y),
            np.bincount(codes,weights=x*x),np.bincount(codes,weights=y*y),np.bincount(codes,weights=x*y)]
        vals=[]
        for _ in range(reps):
            n,sx,sy,sxx,syy,sxy=sums[rng.integers(0,len(groups),len(groups))].sum(0)
            vals.append((sxy-sx*sy/n)/np.sqrt(max((sxx-sx*sx/n)*(syy-sy*sy/n),1e-20)))
        rows.append(dict(resampling=unit,groups=len(groups),low=np.quantile(vals,.025),high=np.quantile(vals,.975)))
    return rows


def weather(d,profiles):
    rows=[]
    for name,mask in [("primary",d.primary_eligible),("gappy_inclusive_sensitivity",d.growth_valid & d.observation_count.ge(3))]:
        g=d[mask & d.weather_complete].copy()
        for with_year in [False,True]:
            nuisance=pd.get_dummies(g[["region","month"]+(["year"] if with_year else [])].astype(str),drop_first=True,dtype=float)
            for c in ["log_duration","log_observations","log_area"]:nuisance[c]=rankdata(g[c])
            cov=np.c_[np.ones(len(g)),nuisance.to_numpy(float)]
            for predictor in ["mean_precipitation_mm","wet_fraction","mean_vpd_kpa","max_vpd"]:
                for response in TRAITS:
                    raw,partial,residual=partial_rank(g[predictor],g[response],cov)
                    for ci in association_intervals(g,residual):
                        rows.append(dict(population=name,year_adjusted=with_year,predictor=predictor,response=response,
                            n=len(g),raw_spearman=raw,partial_rank=partial,change=partial-raw,
                            sign_change=bool(raw*partial<0),**ci))
    write(pd.DataFrame(rows),"adjusted_weather_associations")
    perf=read("event_performance");ci=read("event_uncertainty")
    write(ci,"weather_response_validation")
    write(ci[ci.resampling.eq("fire_id")].pivot(index=["response","predictor_set","n"],columns="kind",values=["r2","r2_low","r2_high"]).reset_index(),"weather_response_validation_wide")
    comparisons=[]
    for base,added,label in [("core_means","core_plus_max","max_above_core"),
        ("comprehensive_means","comprehensive_plus_max","max_above_full"),
        ("length_only","length_plus_max","max_above_length"),
        ("length_plus_core","length_plus_core_max","max_above_length_and_core")]:
        a=perf[(perf.alpha==1)&perf.predictor_set.eq(base)].set_index(["kind","response"])
        b=perf[(perf.alpha==1)&perf.predictor_set.eq(added)].set_index(["kind","response"])
        for (kind,response),row in b.iterrows():
            comparisons.append(dict(comparison=label,kind=kind,response=response,n=row.n,
                base_r2=a.loc[(kind,response),"r2"],added_r2=row.r2,increment=row.r2-a.loc[(kind,response),"r2"]))
    write(pd.DataFrame(comparisons),"maximum_vpd_increment")
    opportunity=[]
    for name,mask in [("primary",d.primary_eligible),("all_complete",d.growth_valid)]:
        g=d[mask & d.weather_complete]
        for length in ["duration_days","observation_count"]:
            for exposure in ["max_vpd","mean_vpd_kpa","q90_vpd","vpd_gt_2_fraction"]:
                opportunity.append(dict(population=name,n=len(g),length=length,exposure=exposure,
                    spearman=spearmanr(g[length],g[exposure]).statistic))
    write(pd.DataFrame(opportunity),"maximum_vpd_opportunity")
    # Targeted numerical replay: the primary prespecified penalty only, no old/gappy grid rerun.
    print("Replaying primary event models at prespecified alpha=1",flush=True)
    result,folds,intervals,prep,_,cohort=evaluate_models(d[d.primary_eligible],{"mean_only":[],**predictor_sets()},
        TRAITS+["log_area","log_duration"],profile_columns=profiles,alphas=(1.,),reps=200)
    keys=["kind","alpha","predictor_set","response"]
    a=result.sort_values(keys).reset_index(drop=True);b=perf[perf.alpha.eq(1)].sort_values(keys).reset_index(drop=True)
    assert a[keys].equals(b[keys]);np.testing.assert_allclose(a.r2,b.r2,atol=1e-10,equal_nan=True)
    ci_keys=keys+["resampling"]
    ci_new=intervals.sort_values(ci_keys).reset_index(drop=True)
    ci_old=ci.sort_values(ci_keys).reset_index(drop=True)
    np.testing.assert_allclose(ci_new[["r2_low","r2_high","delta_low","delta_high"]],
        ci_old[["r2_low","r2_high","delta_low","delta_high"]],atol=1e-10,equal_nan=True)
    fold_keys=keys+["fold"]
    prior_folds=read("event_folds").query("alpha==1").copy()
    prior_folds["fold"]=prior_folds.fold.astype(str)
    f_new=folds.sort_values(fold_keys).reset_index(drop=True)
    f_old=prior_folds.sort_values(fold_keys).reset_index(drop=True)
    assert f_new[fold_keys].equals(f_old[fold_keys])
    np.testing.assert_allclose(f_new.r2,f_old.r2,atol=1e-10,equal_nan=True)
    recorded=pd.read_parquet(BASE/"event_cohort.parquet");recorded.fire_id=recorded.fire_id.astype(str)
    assert cohort_hash(cohort)==cohort_hash(recorded)
    audits=[]
    for kind in ["random_fire","year_block","region_block","spatiotemporal"]:
        for fold,train,test in splits(cohort,kind):
            if train.sum()<30 or test.sum()<2:continue
            old=read("event_preprocessing")
            fit=fit_pca(cohort.loc[train,profiles]);saved=old[(old.kind==kind)&(old.fold.astype(str)==fold)&(old.stage=="outcome_pca")]
            np.testing.assert_allclose(fit.mean,saved.center,atol=1e-10)
            audits.append(dict(kind=kind,fold=fold,train_n=int(train.sum()),test_n=int(test.sum()),
                train_hash=cohort_hash(cohort[train]),test_hash=cohort_hash(cohort[test]),fire_overlap=0,
                pca_train_mean_max_error=np.max(np.abs(fit.mean-saved.center.to_numpy()))))
    write(pd.DataFrame(audits),"event_fold_replay")
    (OUT/"event_replay.json").write_text(json.dumps(dict(status="pass",n=len(cohort),
        max_r2_error=float(np.nanmax(np.abs(a.r2-b.r2))),cohort_hash=cohort_hash(cohort)),indent=2))


def state_data(d,s):
    t,audit=exact_transitions(s)
    exposure=pd.read_parquet(BASE/"day_t_weather.parquet");exposure.fire_id=exposure.fire_id.astype(str)
    t=t.drop(columns=CORE).merge(exposure,on=["fire_id","timestamp"],validate="one_to_one")
    validate_exposure(t)
    t=t.merge(d[["fire_id","region","year","season","catalog_area_km2","consecutive"]].rename(columns={"year":"ignition_year"}),on="fire_id",validate="many_to_one")
    t["year"]=t.ignition_year
    for a,b in [("ring_area_km2","current_growth_log1p"),("previous_growth_km2","previous_growth_log1p"),
                ("cumulative_area_km2","cumulative_log1p"),("next_growth_km2","next_growth_log1p"),("elapsed_day","elapsed_log1p")]:
        t[b]=np.log1p(t[a])
    state=["current_growth_log1p","previous_growth_log1p","cumulative_log1p","elapsed_log1p"]
    interactions=[]
    for c in CORE:
        for st in state[:2]:
            col=f"{c}_x_{st}";t[col]=t[c]*t[st];interactions.append(col)
    t=complete_cohort(t,{"full":state+CORE+interactions},["next_growth_log1p"])
    recorded=pd.read_parquet(BASE/"state_cohort.parquet");recorded.fire_id=recorded.fire_id.astype(str)
    assert cohort_hash(t)==cohort_hash(recorded)
    assert (t.response_date-t.timestamp).dt.days.eq(1).all()
    assert t.previous_gap_days.eq(1).all()
    t["size_class"]=pd.cut(t.catalog_area_km2,[0,1,10,100,1000,np.inf]).astype(str)
    t["observation_quality"]=np.where(t.consecutive,"consecutive_history","history_has_gaps")
    return t,state,interactions


def ridge_effects(d,columns,alpha=1.):
    """Full-sample descriptive coefficients with fire-cluster sandwich covariance.

    Fixed design/penalty, asymptotic cluster uncertainty; not a causal effect nor
    a post-selection test. Units are log1p(km2) per original-unit product.
    """
    x=d[columns].to_numpy(float);mu=x.mean(0);sd=x.std(0);sd[sd<1e-12]=1
    design=np.c_[np.ones(len(x)),(x-mu)/sd]
    penalty=np.eye(design.shape[1])*alpha;penalty[0,0]=0
    bread=np.linalg.inv(design.T@design+penalty)
    y=d.next_growth_log1p.to_numpy();beta=bread@design.T@y
    codes,groups=pd.factorize(d.fire_id,sort=True)
    score=design*(y-design@beta)[:,None]
    summed=np.zeros((len(groups),design.shape[1]));np.add.at(summed,codes,score)
    cov=bread@(summed.T@summed)@bread*len(groups)/(len(groups)-1)
    return beta[1:]/sd,np.sqrt(np.maximum(np.diag(cov)[1:],0))/sd


def state_validation(d,s):
    t,states,interactions=state_data(d,s)
    vp=[c for c in interactions if c.startswith("vpd_kpa_")]
    nonvp=[c for c in interactions if c not in vp]
    sets={"autoregressive":states,"state_plus_weather":states+CORE,
        "vpd_interactions_only":states+CORE+vp,
        "non_vpd_interactions":states+CORE+nonvp,
        "state_weather_interactions":states+CORE+interactions}
    print("Testing VPD-specific held-out ablations on the unchanged state cohort",flush=True)
    perf,folds,ci,prep,pred,_=evaluate_models(t,sets,["next_growth_log1p"],alphas=(1.,),reps=200,reference="autoregressive")
    old=read("state_performance");keys=["kind","predictor_set"]
    a=perf[perf.predictor_set.isin(["autoregressive","state_plus_weather","state_weather_interactions"])].sort_values(keys)
    b=old[old.alpha.eq(1)&old.predictor_set.isin(a.predictor_set)].sort_values(keys)
    np.testing.assert_allclose(a.r2,b.r2,atol=1e-10)
    replay_error=float(np.max(np.abs(a.r2.to_numpy()-b.r2.to_numpy())))
    write(read("state_uncertainty"),"state_incremental_skill")
    write(perf,"vpd_ablation_performance");write(folds,"vpd_ablation_folds")
    rows=[]
    for kind,g in pred.groupby("kind"):
        for full,base,label in [("vpd_interactions_only","state_plus_weather","VPD_above_additive"),
                               ("state_weather_interactions","non_vpd_interactions","VPD_above_other_interactions")]:
            a=g[g.predictor_set.eq(full)].copy();b=g[g.predictor_set.eq(base)]
            a=a.merge(b[["fire_id","timestamp","predicted"]].rename(columns={"predicted":"ablated"}),on=["fire_id","timestamp"],validate="one_to_one")
            a=a.merge(t[["fire_id","timestamp","size_class"]],on=["fire_id","timestamp"],validate="one_to_one")
            subsets=[("all","all",a)]
            for dim in ["region","year","season","size_class","observation_quality"]:
                subsets.extend((dim,str(v),part) for v,part in a.groupby(dim) if len(part)>=30)
            for dim,value,part in subsets:
                y,p,ref=part.observed.to_numpy(),part.predicted.to_numpy(),part.ablated.to_numpy()
                for interval in cluster_intervals(part,y,p,ref,reps=200):
                    rows.append(dict(kind=kind,comparison=label,stratum=dim,value=value,n=len(part),fires=part.fire_id.nunique(),
                        delta_r2=r2(y,p)-r2(y,ref),**interval))
    write(pd.DataFrame(rows),"vpd_incremental_robustness")
    rows=[]
    subsets=[("all","all",t)]
    for dim in ["region","year","season","size_class"]:
        subsets.extend((dim,str(v),g) for v,g in t.groupby(dim) if len(g)>=100 and g.fire_id.nunique()>=30)
    for kind in ["region_block","year_block","spatiotemporal"]:
        subsets.extend((kind,fold,t[train]) for fold,train,test in splits(t,kind) if train.sum()>=100)
    for dim,value,g in subsets:
        columns=sets["state_weather_interactions"];beta,se=ridge_effects(g,columns)
        for col in vp:
            j=columns.index(col)
            rows.append(dict(stratum=dim,value=value,n=len(g),fires=g.fire_id.nunique(),term=col,
                estimate=beta[j],cluster_se=se[j],low=beta[j]-1.96*se[j],high=beta[j]+1.96*se[j]))
    write(pd.DataFrame(rows),"vpd_interaction_coefficients")
    density=[];ranges=[]
    for st in states[:2]:
        v_edges=np.unique(np.quantile(t.vpd_kpa,np.linspace(0,1,11)))
        s_edges=np.unique(np.quantile(t[st],np.linspace(0,1,11)))
        vbin=pd.cut(t.vpd_kpa,v_edges,labels=False,include_lowest=True)
        sbin=pd.cut(t[st],s_edges,labels=False,include_lowest=True)
        for i in range(len(v_edges)-1):
            for j in range(len(s_edges)-1):
                g=t[vbin.eq(i)&sbin.eq(j)]
                density.append(dict(state=st,vpd_bin=i,state_bin=j,vpd_low=v_edges[i],vpd_high=v_edges[i+1],
                    state_low=s_edges[j],state_high=s_edges[j+1],n=len(g),fires=g.fire_id.nunique(),
                    supported=len(g)>=100 and g.fire_id.nunique()>=30))
        for col in ["vpd_kpa",st]:
            ranges.append(dict(state=st,variable=col,n=len(t),q01=t[col].quantile(.01),q05=t[col].quantile(.05),
                median=t[col].median(),q95=t[col].quantile(.95),q99=t[col].quantile(.99)))
    write(pd.DataFrame(density),"vpd_joint_density");write(pd.DataFrame(ranges),"vpd_supported_ranges")
    rows=[]
    for dim in ["region","year","season","size_class","observation_quality"]:
        for value,g in t.groupby(dim):rows.append(dict(dimension=dim,value=value,transitions=len(g),fires=g.fire_id.nunique()))
    write(pd.DataFrame(rows),"state_population")
    (OUT/"state_replay.json").write_text(json.dumps(dict(status="pass",n=len(t),fires=t.fire_id.nunique(),
        cohort_hash=cohort_hash(t),max_r2_error=replay_error),indent=2))


def matching(d,profiles):
    d=complete_cohort(d[d.primary_eligible & d.weather_complete],predictor_sets(),profiles)
    weather_cols=["mean_"+c for c in CORE]
    spaces={}
    for name,cols in [("weather",weather_cols),("morphology",profiles)]:
        x=d[cols].to_numpy(float);sd=x.std(0);sd[sd<1e-12]=1
        spaces[name]=(x-x.mean(0))/sd
    rows=[];balance=[];distributions=[]
    for space,cols in [("weather",weather_cols),("morphology",profiles)]:
        other="morphology" if space=="weather" else "weather"
        for caliper in CONFIG["calipers"]:
            for metric in ["euclidean","cityblock"]:
                pairs,_=unique_matches(d,cols,caliper=caliper,k=10,metric=metric)
                i,j=pairs.i.to_numpy(int),pairs.j.to_numpy(int)
                diff=spaces[other][i]-spaces[other][j]
                mismatch=np.sqrt((diff**2).mean(1)) if metric=="euclidean" else np.abs(diff).mean(1)
                rows.append(dict(space=space,caliper=caliper,metric=metric,k=10,n=len(d),pairs=len(pairs),
                    candidate_fraction=pairs.attrs["good_match_exists_fraction"],paired_fraction=2*len(pairs)/len(d),
                    mismatch_q10=np.quantile(mismatch,.1),mismatch_median=np.median(mismatch),mismatch_q90=np.quantile(mismatch,.9),
                    mismatch_gt1=np.mean(mismatch>1)))
                if caliper==.5 and metric=="euclidean":
                    saved=read("matched_pairs").query("matching_space==@space")
                    assert list(zip(pairs.fire_id_a,pairs.fire_id_b))==list(zip(saved.fire_id_a.astype(str),saved.fire_id_b.astype(str)))
                    assert not pd.concat([pairs.fire_id_a,pairs.fire_id_b]).duplicated().any()
                    for c in weather_cols+TRAITS+["duration_days","observation_count","catalog_area_km2"]:
                        a,b=d.iloc[i][c].to_numpy(float),d.iloc[j][c].to_numpy(float);sd=d[c].std(ddof=0)
                        delta=np.abs(a-b)
                        balance.append(dict(space=space,variable=c,pairs=len(pairs),mean_absolute_difference=delta.mean(),
                            median_absolute_difference=np.median(delta),q95_absolute_difference=np.quantile(delta,.95),
                            mean_absolute_standardized_difference=delta.mean()/sd if sd else 0,
                            signed_smd=(a.mean()-b.mean())/sd if sd else 0))
                    for c in ["region","season"]:
                        assert np.array_equal(d.iloc[i][c].to_numpy(),d.iloc[j][c].to_numpy())
                        balance.append(dict(space=space,variable=c,pairs=len(pairs),mean_absolute_difference=0))
                    for target in [space,other]:
                        dist=np.sqrt(((spaces[target][i]-spaces[target][j])**2).mean(1))
                        for q in [.01,.1,.25,.5,.75,.9,.99]:
                            distributions.append(dict(matching_space=space,distance_space=target,quantile=q,distance=np.quantile(dist,q),pairs=len(pairs)))
    write(pd.DataFrame(rows),"matching_caliper_sensitivity");write(pd.DataFrame(balance),"matching_balance")
    write(pd.DataFrame(distributions),"matched_distance_distributions")
    write(read("matching_sensitivity"),"matching_neighbor_sensitivity")
    pairs=read("matched_pairs");perm=read("matching_permutation");rows=[]
    for space,g in pairs.groupby("matching_space"):
        other="morphology" if space=="weather" else "weather";dist=g[other+"_distance"]
        for metric,value in [("median_mismatch",dist.median()),("mismatch_gt1_fraction",dist.gt(1).mean())]:
            null=perm[perm.matching_space.eq(space)][metric]
            rows.append(dict(space=space,metric=metric,pairs=len(g),observed=value,null_mean=null.mean(),
                null_low=null.quantile(.025),null_high=null.quantile(.975),upper_tail=(1+null.ge(value).sum())/(len(null)+1)))
    write(pd.DataFrame(rows),"mismatch_null_comparison")
    d["area_stratum"]=np.floor(np.log2(d.catalog_area_km2))
    sizes=d.groupby(["region","season","duration_days","observation_count","area_stratum"]).size()
    (OUT/"matching_audit.json").write_text(json.dumps(dict(n=len(d),unique_pairs=len(pairs),
        reproduction="exact IDs and order",singleton_strata=int(sizes.eq(1).sum()),
        singleton_event_fraction=float(sizes[sizes.eq(1)].sum()/len(d)),two_by_two="not used; two independent pairs",
        candidate_caveat="Candidate fraction is within the k-neighbor search, not exhaustive existence over all possible pairs."),indent=2))


def manifest():
    sources=list(BASE.glob("*.csv"))+[BASE/n for n in ["event_analysis.parquet","day_t_weather.parquet","input_hashes.json","run_manifest.json"]]
    payload=dict(baseline_git_sha=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
        command=sys.argv,config=CONFIG,code={"scripts/validate_fire_vase_science.py":sha256(Path(__file__)),
        "src/cubedynamics/analysis_v2.py":sha256(ROOT/"src/cubedynamics/analysis_v2.py")},
        inputs={str(p.relative_to(ROOT)):sha256(p) for p in sources},
        outputs={p.name:sha256(p) for p in sorted(OUT.iterdir()) if p.suffix==".csv"})
    (OUT/"validation_manifest.json").write_text(json.dumps(payload,indent=2))


def main(argv=None):
    global DATA
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage",choices=["all","population","stability","nulls","weather","state","matching","manifest"],default="all")
    parser.add_argument("--data-lake",type=Path,default=DATA)
    args=parser.parse_args(argv);OUT.mkdir(exist_ok=True)
    DATA=args.data_lake.resolve()
    if (DATA/"files").exists():DATA=DATA/"files"
    if args.stage=="manifest":manifest();return
    d,s=load_data();profiles=[c for c in d if c.startswith("allocation_")]
    assert len(profiles)==20
    stages={"population":lambda:population(d,s),"stability":lambda:stability(d,profiles),
        "nulls":lambda:null_histories(d,s,profiles),"weather":lambda:weather(d,profiles),
        "state":lambda:state_validation(d,s),"matching":lambda:matching(d,profiles)}
    for name,run in stages.items():
        if args.stage in ["all",name]:print(f"Scientific validation: {name}",flush=True);run()
    manifest()


if __name__=="__main__":main()
