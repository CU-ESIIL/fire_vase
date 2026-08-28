#!/usr/bin/env python3
"""Regenerate real-data v2 statistics before rendering any figures.

Run through manuscript_figures/00_run_all.py --generation v2 for the complete
statistics -> figures -> manuscript workflow. No legacy artifact is overwritten.
"""
from __future__ import annotations
import argparse
import json
import platform
from pathlib import Path
import subprocess
import sys
import numpy as np
import pandas as pd
from scipy.stats import spearmanr, rankdata
from cubedynamics.analysis_v2 import (CORE,WEATHER,TRAITS,RULES,growth_summary,shape_traits,
    allocation_profile,neighborhood,fit_pca,pca_metrics,loading_alignment,exact_transitions,
    predictor_sets,evaluate_models,complete_cohort,unique_matches,validate_exposure,r2,cluster_intervals)
from fire_vase_v2_inputs import audit_inputs,day_t_weather,sha256

ROOT = Path(__file__).resolve().parents[1]


def write_csv(frame, output, name):
    if name == "event_semantic_audit":
        frame.to_csv(output/f"{name}.csv.gz",index=False,float_format="%.12g",
                     compression={"method":"gzip","mtime":0})
    else:
        frame.to_csv(output/f"{name}.csv",index=False,float_format="%.12g")


def build_features(slices,traits,output,bins):
    rows, allocations = [], {}
    meta = traits.set_index("fire_id")
    for fid,g in slices.sort_values(["fire_id","timestamp","slice_index"]).groupby("fire_id",sort=False):
        t = meta.loc[fid]
        growth = g.ring_area_km2.to_numpy(float)
        row,p = growth_summary(growth,float(t.duration_hours)/24,float(t.total_area_km2))
        dates = g.timestamp
        gaps = dates.diff().dt.total_seconds().dropna()/86400
        consecutive = dates.notna().all() and (gaps == 1).all() and not dates.duplicated().any()
        span = (dates.max()-dates.min()).days+1 if dates.notna().all() else np.nan
        row.update(fire_id=fid,year=int(t.year),region=t.region,observation_count=len(g),
            duration_days=float(t.duration_hours)/24,calendar_span_days=span,
            start_date=dates.min(),end_date=dates.max(),consecutive=bool(consecutive),
            longer_gaps=int((gaps>1).sum()),missing_dates=int(dates.isna().sum()),
            duplicate_dates=int(dates.duplicated().sum()))
        row["primary_eligible"] = bool(row["growth_valid"] and consecutive and len(g)>=3)
        if row["growth_valid"]:
            tr,profile = shape_traits(p,bins)
            row.update(tr)
            row.update({f"allocation_{i:02d}":v for i,v in enumerate(profile)})
            allocations[fid] = p
        row["neighborhood"] = neighborhood(row)
        rows.append(row)
    features = pd.DataFrame(rows)
    features["month"] = features.start_date.dt.month
    features["season"] = features.month.map({12:"DJF",1:"DJF",2:"DJF",3:"MAM",4:"MAM",5:"MAM",6:"JJA",7:"JJA",8:"JJA",9:"SON",10:"SON",11:"SON"})
    features["log_duration"] = np.log1p(features.duration_days)
    features["log_observations"] = np.log1p(features.observation_count)
    features["log_area"] = np.log1p(features.catalog_area_km2)
    features.to_parquet(output/"event_features.parquet",index=False)
    write_csv(features[["fire_id","catalog_area_km2","reconstructed_area_km2","relative_area_discrepancy",
        "mean_catalog_growth_km2_per_day","mean_observed_growth_km2_per_day","peak_growth_km2_per_day",
        "shannon_entropy","normalized_entropy","observation_count","duration_days","calendar_span_days",
        "longer_gaps","primary_eligible","neighborhood"]],output,"event_semantic_audit")
    write_csv(pd.DataFrame([dict(priority=i+1,landmark=name,rule=rule,n=int(features.neighborhood.eq(name).sum()))
        for i,(name,rule) in enumerate(RULES)]),output,"neighborhood_rules")
    return features,allocations


def morphology_analysis(f,allocations,legacy,config,output):
    rng = np.random.default_rng(config["seed"])
    cols = [c for c in f if c.startswith("allocation_")]
    d = f.loc[f.primary_eligible].copy()
    x = d[cols].to_numpy(float)
    fit = fit_pca(x)
    scores = fit.transform(x)
    f.loc[d.index,[f"shape_PC{i+1}" for i in range(5)]] = scores[:,:5]
    write_csv(pd.DataFrame(dict(axis=np.arange(1,len(cols)+1),explained_variance=fit.evr,
                               cumulative_variance=np.cumsum(fit.evr))),output,"pca_variance")
    loadings = pd.DataFrame(fit.loadings,columns=[f"PC{i+1}" for i in range(len(cols))])
    loadings.insert(0,"feature",cols)
    loadings["training_mean"],loadings["training_scale"] = fit.mean,fit.scale
    write_csv(loadings,output,"pca_loadings")
    sensitivities = []
    strata = {"all_observed_histories_observation_time":f.growth_valid,
        "one_slice":f.observation_count.eq(1),"two_slice":f.observation_count.eq(2),
        "multi_observation_including_gaps":f.observation_count.ge(3),
        "primary_consecutive_ge3":f.primary_eligible,
        "consecutive_ge5":f.consecutive & f.observation_count.ge(5),
        "consecutive_ge10":f.consecutive & f.observation_count.ge(10)}
    for name,mask in strata.items():
        xx = f.loc[mask & f.growth_valid,cols].to_numpy(float)
        sensitivities.append(dict(analysis=name,n=len(xx),bins=len(cols),**pca_metrics(xx)))
    for bins in config["alternative_bins"]:
        xx = np.array([allocation_profile(allocations[fid],bins) for fid in d.fire_id])
        sensitivities.append(dict(analysis="primary_resolution",n=len(xx),bins=bins,**pca_metrics(xx)))
    # Exact legacy feature space on the primary IDs, using corrected mean centering.
    lcols=["log_final_area_km2","log_duration_days","log_peak_growth_km2_per_day",
        "log_slenderness_days_per_width","observation_count","pulse_count","reactivation_count",
        "peak_timing","front_loaded_fraction","late_growth_fraction","terminal_taper_fraction",
        "growth_entropy","developmental_velocity","developmental_acceleration"]
    lcols += [c for c in legacy if c.startswith("width_p") or c.startswith("growth_p")]
    legacy_values=legacy.copy()
    for c in ["final_area_km2","duration_days","peak_growth_km2_per_day","slenderness_days_per_width"]:
        legacy_values["log_"+c]=np.log10(legacy_values[c].clip(lower=1e-9))
    legacy_x=legacy_values[lcols].replace([np.inf,-np.inf],np.nan)
    legacy_x=legacy_x.fillna(legacy_x.median()) # faithful legacy comparison only
    for name,mask in [("legacy_features_all_mean_centered",np.ones(len(legacy),bool)),
                      ("legacy_features_primary_mean_centered",legacy.fire_id.isin(d.fire_id))]:
        sensitivities.append(dict(analysis=name,n=int(mask.sum()),bins=0,**pca_metrics(legacy_x.loc[mask])))
    trait_x = d[TRAITS].to_numpy(float)
    sensitivities.append(dict(analysis="shape_traits_only",n=len(d),bins=0,**pca_metrics(trait_x)))
    write_csv(pd.DataFrame(sensitivities),output,"morphospace_sensitivity")
    stability,loading_samples = [],[]
    count = min(len(d),config["pca_bootstrap_sample_size"])
    for rep in range(config["bootstrap_replicates"]):
        other = fit_pca(x[rng.integers(0,len(x),count)])
        aligned,cosine,overlap = loading_alignment(fit.loadings,other.loadings)
        stability.append(dict(rep=rep,n=count,subspace_overlap=overlap,pc1=other.evr[0],
            first_five=other.evr[:5].sum(),**{f"axis{i+1}_cosine":v for i,v in enumerate(cosine)}))
        for i,c in enumerate(cols):
            loading_samples.append(dict(rep=rep,feature=c,**{f"PC{j+1}":aligned[i,j] for j in range(5)}))
    write_csv(pd.DataFrame(stability),output,"pca_bootstrap")
    write_csv(pd.DataFrame(loading_samples),output,"pca_bootstrap_loadings")
    group_rows = []
    for group in ["region","year"]:
        for label,positions in d.groupby(group).indices.items():
            if len(positions)<30:
                continue
            other = fit_pca(x[positions])
            _,cosine,overlap = loading_alignment(fit.loadings,other.loadings)
            group_rows.append(dict(group=group,label=label,n=len(positions),subspace_overlap=overlap,
                pc1=other.evr[0],first_five=other.evr[:5].sum(),**{f"axis{i+1}_cosine":v for i,v in enumerate(cosine)}))
    write_csv(pd.DataFrame(group_rows),output,"pca_geographic_year_stability")
    projection = []
    for axis in range(5):
        for attr in TRAITS+["catalog_area_km2","duration_days","observation_count"]:
            projection.append(dict(axis=axis+1,attribute=attr,spearman=float(spearmanr(scores[:,axis],d[attr]).statistic)))
    write_csv(pd.DataFrame(projection),output,"axis_attribute_projections")
    # Use the same real sample in every null, preserving each event's n and duration.
    ids = rng.choice(d.fire_id.to_numpy(),min(len(d),config["null_sample_size"]),replace=False)
    pp = [allocations[fid] for fid in ids]
    observed = pca_metrics(np.array([allocation_profile(p,len(cols)) for p in pp]))
    nulls = [dict(null="observed_same_sample",rep=-1,n=len(pp),**observed)]
    for rep in range(config["null_replicates"]):
        for name in ["within_fire_permutation","dirichlet_1","dirichlet_10"]:
            xx = np.array([allocation_profile(rng.permutation(p) if name=="within_fire_permutation"
                else rng.dirichlet(np.repeat(1. if name=="dirichlet_1" else 10.,len(p))),len(cols)) for p in pp])
            nulls.append(dict(null=name,rep=rep,n=len(pp),**pca_metrics(xx)))
    null_df = pd.DataFrame(nulls)
    write_csv(null_df,output,"null_comparisons")
    tests=[]
    for label,g in null_df[null_df.rep.ge(0)].groupby("null"):
        for metric,value in observed.items():
            tests.append(dict(null=label,metric=metric,observed=value,null_mean=g[metric].mean(),
                null_low=g[metric].quantile(.025),null_high=g[metric].quantile(.975),
                empirical_upper_p=(1+g[metric].ge(value).sum())/(1+len(g)),
                empirical_lower_p=(1+g[metric].le(value).sum())/(1+len(g))))
    write_csv(pd.DataFrame(tests),output,"null_tests")
    return f,cols


def event_weather(f,slices,output):
    s = slices.copy()
    # Completeness means every observed row has every required variable.
    # It says nothing about unobserved dates; those events are not primary.
    s["complete_weather"] = np.isfinite(s[WEATHER]).all(1)
    means = s.groupby("fire_id")[WEATHER].mean().add_prefix("mean_")
    agg = s.groupby("fire_id").agg(weather_complete=("complete_weather","all"),
        observed_weather_rows=("complete_weather","sum"),max_vpd=("vpd_kpa","max"))
    agg["q90_vpd"] = s.groupby("fire_id").vpd_kpa.quantile(.9)
    agg["vpd_gt_2_fraction"] = s.vpd_kpa.gt(2).where(s.vpd_kpa.notna()).groupby(s.fire_id).mean()
    agg["wet_fraction"] = s.precipitation_mm.gt(.1).where(s.precipitation_mm.notna()).groupby(s.fire_id).mean()
    agg["any_precipitation"] = s.precipitation_mm.gt(.1).groupby(s.fire_id).max().astype(float)
    d = f.merge(means,on="fire_id",validate="one_to_one").merge(agg,on="fire_id",validate="one_to_one")
    # A partially observed mean must never masquerade as a complete event exposure.
    predictor_cols = list(dict.fromkeys(sum(predictor_sets().values(),[])))
    meteorological = [c for c in predictor_cols if not c.startswith("log_")]
    d.loc[~d.weather_complete,meteorological] = np.nan
    d["duration_bin"] = pd.cut(d.duration_days,[0,1,2,3,5,10,30,np.inf]).astype(str)
    d["area_bin"] = pd.cut(d.catalog_area_km2,[0,1,10,100,1000,np.inf]).astype(str)
    rows=[]
    for dimension in ["region","year","duration_bin","area_bin","neighborhood"]:
        for (value,complete),part in d.groupby([dimension,"weather_complete"],observed=True):
            rows.append(dict(dimension=dimension,value=value,weather_complete=complete,n=len(part),
                primary_n=int(part.primary_eligible.sum()),median_duration=part.duration_days.median(),
                median_area=part.catalog_area_km2.median(),median_entropy=part.normalized_entropy.median(),
                median_front_loading=part.front_loaded_fraction.median()))
    write_csv(pd.DataFrame(rows),output,"weather_inclusion_exclusion")
    return d


def run_model_grid(d,sets,responses,config,output,prefix,**kwargs):
    result,folds,ci,prep,pred,cohort = evaluate_models(d,sets,responses,
        alphas=tuple(config["ridge_alphas"]),reps=config["bootstrap_replicates"],**kwargs)
    for name,frame in [("performance",result),("folds",folds),("uncertainty",ci),("preprocessing",prep)]:
        write_csv(frame,output,f"{prefix}_{name}")
    if not pred.empty:
        pred.to_parquet(output/f"{prefix}_predictions.parquet",index=False)
    write_csv(pd.DataFrame([dict(predictor_set=name,position=i,feature=c) for name,cols in sets.items()
                           for i,c in enumerate(cols)]),output,f"{prefix}_predictors")
    cohort[[c for c in ["fire_id","timestamp","year","region","duration_days","observation_count"] if c in cohort]].to_parquet(output/f"{prefix}_cohort.parquet",index=False)
    return result,ci,pred,cohort


def adjusted_associations(d,config,output):
    # Partial rank association removes size, opportunity, regional and month effects.
    rows=[]
    predictors = ["mean_precipitation_mm","wet_fraction","any_precipitation","mean_vpd_kpa","max_vpd"]
    responses = TRAITS+["log_duration","log_observations"]
    complete = d[d.weather_complete & d.growth_valid & d.observation_count.ge(3)].copy()
    nuisance = pd.get_dummies(complete[["region","month"]].astype(str),drop_first=True,dtype=float)
    for c in ["log_duration","log_observations","log_area"]:
        nuisance[c] = rankdata(complete[c])
    cov = np.c_[np.ones(len(complete)),nuisance.to_numpy(float)]
    rng = np.random.default_rng(config["seed"])
    for predictor in predictors:
        for response in responses:
            a,b = rankdata(complete[predictor]),rankdata(complete[response])
            # Do not adjust a response for itself.
            keep = [i for i,c in enumerate(["intercept"]+nuisance.columns.tolist()) if c!=response]
            c = cov[:,keep]
            residuals = np.c_[a,b]-c@np.linalg.lstsq(c,np.c_[a,b],rcond=None)[0]
            adjusted = np.corrcoef(residuals.T)[0,1]
            base=dict(predictor=predictor,response=response,n=len(complete),
                raw_spearman=float(np.corrcoef(a,b)[0,1]),partial_rank=adjusted)
            for unit in ["fire_id","year","region"]:
                codes,groups = pd.factorize(complete[unit],sort=True)
                x,y=residuals.T
                sums=np.column_stack([np.bincount(codes),np.bincount(codes,weights=x),np.bincount(codes,weights=y),
                    np.bincount(codes,weights=x*x),np.bincount(codes,weights=y*y),np.bincount(codes,weights=x*y)])
                vals=[]
                for _ in range(config["bootstrap_replicates"]):
                    n,sx,sy,sxx,syy,sxy=sums[rng.integers(0,len(groups),len(groups))].sum(0)
                    vals.append((sxy-sx*sy/n)/np.sqrt(max((sxx-sx*sx/n)*(syy-sy*sy/n),1e-20)))
                rows.append({**base,"resampling":unit,"low":np.quantile(vals,.025),"high":np.quantile(vals,.975)})
    write_csv(pd.DataFrame(rows),output,"adjusted_associations")


def event_models(d,legacy,profiles,config,output):
    sets = {"mean_only":[],**predictor_sets()}
    responses = TRAITS+["log_area","log_duration"]
    run_model_grid(d[d.primary_eligible],sets,responses,config,output,"event",profile_columns=profiles)
    # Same transformations and shared cohorts; stratum-specific fits, not pooled medians.
    strata=[]
    for dimension in ["duration_days","observation_count"]:
        for value in [3,4,5,6]:
            sub=d[d.growth_valid & d.weather_complete & d[dimension].eq(value) & d.observation_count.ge(3)]
            if len(sub)<100:
                continue
            result,*_ = evaluate_models(sub,sets,TRAITS,alphas=(1.,),reps=30,kinds=["region_block"])
            result["stratum_variable"],result["stratum_value"] = dimension,value
            strata.append(result)
    write_csv(pd.concat(strata,ignore_index=True),output,"event_fixed_length_strata")
    # Broader >=3 observation cohort exposes sensitivity to the consecutive-day restriction.
    result,*_ = evaluate_models(d[d.growth_valid & d.observation_count.ge(3)],sets,TRAITS,
        alphas=(1.,),reps=30,kinds=["region_block","year_block"])
    write_csv(result,output,"event_gappy_cohort_sensitivity")
    # Explicit decomposition of the old feature-vs-cohort contrast; not affirmative PCA prediction.
    old_responses=["front_loaded_fraction","late_growth_fraction","terminal_taper_fraction",
        "growth_entropy","pulse_count","reactivation_count","peak_timing","duration_days","final_area_km2","morph_pc1"]
    old = legacy[["fire_id"]+old_responses].rename(columns={c:"legacy_"+c for c in old_responses})
    comp=d.merge(old,on="fire_id",validate="one_to_one")
    for c in ["pulse_count","reactivation_count","duration_days","final_area_km2"]:
        comp["legacy_"+c]=np.log1p(comp["legacy_"+c])
    small_sets={k:sets[k] for k in ["mean_only","core_means","core_plus_max","comprehensive_means","comprehensive_plus_max","length_only","length_plus_max"]}
    result,*_ = evaluate_models(comp,small_sets,["legacy_"+c for c in old_responses],
        alphas=(1.,),reps=30,kinds=["region_block","year_block"])
    write_csv(result,output,"legacy_outcome_feature_cohort_comparison")


def state_models(slices,features,exposure,config,output):
    s,audit=exact_transitions(slices)
    source=s[["fire_id","timestamp"]+CORE].rename(columns={c:"retrospective_"+c for c in CORE})
    s=s.drop(columns=CORE).merge(exposure,on=["fire_id","timestamp"],validate="one_to_one")
    validate_exposure(s)
    meta=features[["fire_id","region","year","season","catalog_area_km2","consecutive"]].rename(columns={"year":"event_year"})
    s=s.merge(meta,on="fire_id",validate="many_to_one")
    # Fold on ignition year, not slice year; a cross-year fire stays intact.
    s["year"]=s.event_year
    s["observation_quality"]=np.where(s.consecutive,"consecutive_history","history_has_gaps")
    for source_col,target in [("ring_area_km2","current_growth_log1p"),("previous_growth_km2","previous_growth_log1p"),
        ("cumulative_area_km2","cumulative_log1p"),("next_growth_km2","next_growth_log1p")]:
        s[target]=np.log1p(s[source_col])
    s["elapsed_log1p"]=np.log1p(s.elapsed_day)
    # AR includes the previous observed calendar day, requiring t-1, t and t+1.
    state=["current_growth_log1p","previous_growth_log1p","cumulative_log1p","elapsed_log1p"]
    interactions=[]
    for c in CORE:
        for st in state[:2]:
            name=f"{c}_x_{st}"; s[name]=s[c]*s[st]; interactions.append(name)
    sets={"mean_only":[],"persistence":["current_growth_log1p"],"autoregressive":state,
        "weather_only":CORE,"state_plus_weather":state+CORE,
        "state_weather_interactions":state+CORE+interactions}
    s=s.merge(source,on=["fire_id","timestamp"],validate="one_to_one")
    audit.update(day_t_geometry_rows=len(s),missing_previous_calendar_day=int(s.previous_growth_log1p.isna().sum()),
        missing_day_t_weather=int(s[CORE].isna().any(axis=1).sum()))
    result,ci,pred,cohort=run_model_grid(s,sets,["next_growth_log1p"],config,output,"state",reference="autoregressive")
    audit["shared_AR_cohort_rows"],audit["shared_AR_cohort_fires"]=len(cohort),cohort.fire_id.nunique()
    (output/"transition_audit.json").write_text(json.dumps(audit,indent=2))
    # Common state cohort for active-day vs final-centroid exposure comparison.
    compare={"autoregressive":state,"active_day_weather":state+CORE,
             "final_centroid_weather":state+["retrospective_"+c for c in CORE]}
    rr,*_=evaluate_models(cohort,compare,["next_growth_log1p"],alphas=(1.,),reps=30,
        reference="autoregressive",kinds=["region_block","year_block"])
    write_csv(rr,output,"state_spatial_exposure_sensitivity")
    sr=[]
    pred["size_class"]=pd.cut(pred.catalog_area_km2,[0,1,10,100,1000,np.inf]).astype(str)
    for (kind,model),g in pred.groupby(["kind","predictor_set"]):
        for dim in ["region","season","size_class","observation_quality"]:
            for val,sub in g.groupby(dim):
                if len(sub)<30:
                    continue
                y,p,ref=sub.observed.to_numpy(),sub.predicted.to_numpy(),sub.reference.to_numpy()
                interval=cluster_intervals(sub,y,p,ref,reps=config["bootstrap_replicates"])[0]
                sr.append(dict(kind=kind,predictor_set=model,stratum=dim,value=val,n=len(sub),
                    r2=r2(y,p),delta_r2=r2(y,p)-r2(y,ref),**interval))
    write_csv(pd.DataFrame(sr),output,"state_subgroup_sensitivity")
    increments=[]
    for kind,g in pred.groupby("kind"):
        interaction=g[g.predictor_set.eq("state_weather_interactions")].copy()
        additive=g[g.predictor_set.eq("state_plus_weather")][["fire_id","timestamp","predicted"]].rename(columns={"predicted":"additive"})
        joined=interaction.merge(additive,on=["fire_id","timestamp"],validate="one_to_one")
        y,p,ref=joined.observed.to_numpy(),joined.predicted.to_numpy(),joined.additive.to_numpy()
        for interval in cluster_intervals(joined,y,p,ref,reps=config["bootstrap_replicates"]):
            increments.append(dict(kind=kind,n=len(joined),delta_r2=r2(y,p)-r2(y,ref),**interval))
    write_csv(pd.DataFrame(increments),output,"state_interaction_increment")
    return result


def matching_analysis(d,profiles,config,output):
    sets=predictor_sets()
    d=complete_cohort(d[d.primary_eligible & d.weather_complete],sets,profiles)
    weather=["mean_"+c for c in CORE]
    summary,pairs_all,permutations=[],[],[]
    rng=np.random.default_rng(config["seed"])
    # Standardized distances use the entire declared eligible matching cohort.
    spaces={}
    for name,cols in [("weather",weather),("morphology",profiles)]:
        x=d[cols].to_numpy(float);sd=x.std(0);sd[sd<1e-12]=1
        spaces[name]=(x-x.mean(0))/sd
    d["area_stratum"]=np.floor(np.log2(d.catalog_area_km2))
    perm_groups=list(d.groupby(["region","season","duration_days","observation_count","area_stratum"]).indices.values())
    for space,cols in [("weather",weather),("morphology",profiles)]:
        other="morphology" if space=="weather" else "weather"
        for metric in config["matching_metrics"]:
            for k in config["matching_neighbors"]:
                pairs,_=unique_matches(d,cols,caliper=config["matching_caliper"],k=k,metric=metric)
                if pairs.empty:
                    summary.append(dict(space=space,metric=metric,k=k,n=len(d),pairs=0,matched_fraction=0))
                    continue
                ii,jj=pairs.i.to_numpy(int),pairs.j.to_numpy(int)
                for key in spaces:
                    delta=spaces[key][ii]-spaces[key][jj]
                    pairs[f"{key}_distance"]=np.sqrt((delta**2).mean(1)) if metric=="euclidean" else np.abs(delta).mean(1)
                mismatch=pairs[f"{other}_distance"]
                summary.append(dict(space=space,metric=metric,k=k,n=len(d),pairs=len(pairs),
                    matched_fraction=2*len(pairs)/len(d),median_mismatch=mismatch.median(),
                    good_match_exists_fraction=pairs.attrs["good_match_exists_fraction"],
                    mismatch_gt1_fraction=mismatch.gt(1).mean()))
                if metric=="euclidean" and k==10:
                    pairs["matching_space"]=space
                    for c in ["duration_days","observation_count","catalog_area_km2","region","season","start_date","end_date"]+weather:
                        pairs[c+"_a"]=d.iloc[ii][c].to_numpy();pairs[c+"_b"]=d.iloc[jj][c].to_numpy()
                    pairs_all.append(pairs)
                    z=spaces[other]
                    for rep in range(config["null_replicates"]):
                        indices=np.arange(len(d))
                        for g in perm_groups:
                            indices[g]=rng.permutation(g)
                        dist=np.sqrt(((z[indices[ii]]-z[indices[jj]])**2).mean(1))
                        permutations.append(dict(matching_space=space,rep=rep,median_mismatch=np.median(dist),
                            mismatch_gt1_fraction=np.mean(dist>1),n_pairs=len(pairs)))
    write_csv(pd.DataFrame(summary),output,"matching_sensitivity")
    if not pairs_all:
        raise ValueError("No pairs meet declared matching calipers; no examples will be fabricated")
    allpairs=pd.concat(pairs_all,ignore_index=True)
    write_csv(allpairs,output,"matched_pairs")
    write_csv(pd.DataFrame(permutations),output,"matching_permutation")
    # Representative examples minimize deviation from the population median mismatch.
    examples=[]
    for space,g in allpairs.groupby("matching_space"):
        other="morphology" if space=="weather" else "weather"
        examples.append(g.loc[(g[other+"_distance"]-g[other+"_distance"].median()).abs().idxmin()])
    write_csv(pd.DataFrame(examples),output,"matched_examples")


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-lake",type=Path,default=ROOT/"data_lake/fire-vase-data-lake-v0.1")
    parser.add_argument("--config",type=Path,default=ROOT/"config/analysis_v2.json")
    parser.add_argument("--stage",choices=["all","features","models","matching"],default="all")
    args=parser.parse_args(argv)
    data=args.data_lake.resolve()
    if (data/"files").exists():data=data/"files"
    config=json.loads(args.config.read_text())
    output=ROOT/"analysis/v2";output.mkdir(exist_ok=True)
    if args.stage in ["all","features"]:
        print("Auditing real source inputs",flush=True)
        slices,traits,legacy,events,daily=audit_inputs(data,output)
        print("Rebuilding traits and normalized allocation profiles",flush=True)
        f,allocations=build_features(slices,traits,output,config["profile_bins"])
        semantic=legacy.merge(f,on="fire_id",suffixes=("_old","_new"),validate="one_to_one")
        comparison=dict(n=len(f),primary_n=int(f.primary_eligible.sum()),
            peak_changed_n=int((~np.isclose(semantic.peak_growth_km2_per_day_old,semantic.peak_growth_km2_per_day_new)).sum()),
            entropy_changed_n=int((~np.isclose(semantic.growth_entropy,semantic.normalized_entropy,atol=1e-8)).sum()),
            max_area_relative_discrepancy=float(f.relative_area_discrepancy.abs().max()),
            area_discrepancy_gt_1pct=int(f.relative_area_discrepancy.abs().gt(.01).sum()),
            old_multi_pulse_without_three_pulses=int((legacy.shape_label.eq("multi-pulse complex") & legacy.pulse_count.lt(3)).sum()))
        (output/"semantic_summary.json").write_text(json.dumps(comparison,indent=2))
        print("PCA stability and null histories",flush=True)
        f,profiles=morphology_analysis(f,allocations,legacy,config,output)
        d=event_weather(f,slices,output)
        d.to_parquet(output/"event_analysis.parquet",index=False)
        if args.stage=="features":return
    else:
        d=pd.read_parquet(output/"event_analysis.parquet")
        slices=pd.read_parquet(data/"scratch/fire_vase_run_full/tables/vase_slices.parquet")
        slices.timestamp=pd.to_datetime(slices.timestamp)
        legacy=pd.read_parquet(data/"scratch/fire_vase_developmental_morphology/developmental_morphospace_features.parquet")
        profiles=[c for c in d if c.startswith("allocation_")]
    if args.stage in ["all","models"]:
        print("Identical-cohort event weather model grids",flush=True)
        event_models(d,legacy,profiles,config,output)
        print("Adjusted weather associations",flush=True)
        adjusted_associations(d,config,output)
        exposure=day_t_weather(data,slices,output)
        print("Calendar-day autoregressive state models",flush=True)
        state_models(slices,d,exposure,config,output)
    if args.stage in ["all","matching"]:
        print("Unique caliper matching and permutation references",flush=True)
        matching_analysis(d,profiles,config,output)
    manifest=dict(config=config,command=sys.argv,python=platform.python_version(),
        numpy=np.__version__,pandas=pd.__version__,git_commit=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
        input_hashes=json.loads((output/"input_hashes.json").read_text()),
        code_hashes={str(p.relative_to(ROOT)):sha256(p) for p in [Path(__file__),ROOT/"src/cubedynamics/analysis_v2.py",ROOT/"scripts/fire_vase_v2_inputs.py",args.config]},
        output_hashes={p.name:sha256(p) for p in sorted(output.iterdir()) if p.is_file() and p.name not in
            {"run_manifest.json","publication_manifest.json","audit_report.md","issue_audit.csv","verification.json","verification.md"}})
    (output/"run_manifest.json").write_text(json.dumps(manifest,indent=2))
    print("v2 statistics complete",flush=True)


if __name__=="__main__":
    main()
