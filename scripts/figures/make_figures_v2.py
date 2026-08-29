"""Five corrected main figures and validation supplements from saved statistics."""
from pathlib import Path
import json
import shutil
import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse
from figures.style import set_style,save_figure

BLUE,TEAL,GOLD,PURPLE,GRAY = "#31688e","#258b84","#be8b28","#7957a1","#72777c"
BLOCKS=["region_block","year_block","spatiotemporal"]
BLOCK_LABELS={"region_block":"Region holdout","year_block":"Year-block holdout","spatiotemporal":"Space + time holdout"}
LABELS={"front_loaded_fraction":"Front loading","late_growth_fraction":"Late growth",
    "peak_timing":"Peak timing","terminal_taper_fraction":"Terminal taper","normalized_entropy":"Entropy",
    "pulse_count":"Detected pulses","reactivation_count":"Reactivation","normalized_first_difference":"First difference",
    "normalized_second_difference":"Second difference","shape_PC1_fold":"Shape PC1 (fold-fit)",
    "shape_PC2_fold":"Shape PC2 (fold-fit)","shape_PC3_fold":"Shape PC3 (fold-fit)",
    "log_area":"Log area","log_duration":"Log duration"}


def tidy(ax,title,xlabel=None,ylabel=None):
    ax.set_title(title,loc="left",fontweight="bold",pad=12)
    ax.spines[["top","right"]].set_visible(False)
    if xlabel:ax.set_xlabel(xlabel)
    if ylabel:ax.set_ylabel(ylabel)


def glyph(ax,g,title=""):
    dates=pd.to_datetime(g.timestamp)
    t=(dates-dates.min()).dt.days.to_numpy(float)
    t=t/max(t.max(),1)
    width=np.sqrt(g.ring_area_km2.cumsum().to_numpy()/g.ring_area_km2.sum())
    ax.fill_betweenx(t,-width,width,color=TEAL,alpha=.13)
    ax.plot(width,t,color=TEAL);ax.plot(-width,t,color=TEAL)
    for y,w in zip(t,width):
        ax.add_patch(Ellipse((0,y),2*w,.035,facecolor=TEAL,edgecolor="white",lw=.4,alpha=.75))
    ax.set(xlim=(-1.2,1.2),ylim=(-.06,1.06),xticks=[],yticks=[0,1],yticklabels=["start","end"])
    ax.set_title(title,fontsize=8)
    ax.spines[["top","right","bottom"]].set_visible(False)


def example_ids(d):
    primary=d[d.primary_eligible & d.observation_count.ge(5)]
    ids=[]
    for label in ["front-loaded taper","late peak","multiple detected pulses"]:
        g=primary[primary.neighborhood.eq(label)].copy()
        if g.empty:raise ValueError(f"No real example for {label}")
        center=g[["shape_PC1","shape_PC2"]].median()
        ids.append(g.loc[((g[["shape_PC1","shape_PC2"]]-center)**2).sum(1).idxmin(),"fire_id"])
    gap=d[(~d.consecutive)&d.observation_count.between(4,6)].sort_values("fire_id").iloc[0]
    return ids+[gap.fire_id]


def figure1(d,slices):
    ids=example_ids(d)
    fig,axes=plt.subplots(2,4,figsize=(11,6),gridspec_kw={"height_ratios":[1,1.1]},layout="constrained")
    for j,fid in enumerate(ids):
        g=slices[slices.fire_id.eq(fid)].sort_values("timestamp")
        row=d.set_index("fire_id").loc[fid]
        times=(g.timestamp-g.timestamp.min()).dt.days.to_numpy()
        growth=g.ring_area_km2.to_numpy()/g.ring_area_km2.sum()
        ax=axes[0,j]
        ax.bar(times,growth,width=.75,color=BLUE,label="Observed daily share")
        ax.plot(times,np.cumsum(growth),"o-",ms=3,color=GOLD,label="Observed cumulative share")
        missing=np.setdiff1d(np.arange(times.max()+1),times)
        for t in missing:ax.axvspan(t-.4,t+.4,color=GRAY,alpha=.15)
        ticks=np.unique(np.r_[times[0],times[len(times)//2],times[-1]])
        ax.set_xticks(ticks,[(g.timestamp.min()+pd.Timedelta(days=int(t))).strftime("%m-%d") for t in ticks],rotation=20)
        tidy(ax,f"{'ABCD'[j]}  Fire {fid}","Calendar date", "Fraction of reconstructed area" if j==0 else None)
        ax.set_ylim(0,1.1)
        if j==0:ax.legend(fontsize=7,loc="center right")
        label=f"{int(row.observation_count)} observations / {int(row.duration_days)} calendar days\n{row.catalog_area_km2:.1f} km²; {row.start_date.year}"
        glyph(axes[1,j],g,label)
    fig.suptitle("From dated growth observations to developmental morphology",fontsize=15)
    fig.supxlabel("Ring radius = √(reconstructed cumulative area / reconstructed total). Gray bands = unobserved dates, not zero growth.",fontsize=9)
    return fig


def figure2(d,slices,read):
    p=d[d.primary_eligible]
    ev=read("pca_variance");loading=read("pca_loadings")
    fig=plt.figure(figsize=(11,7),layout="constrained")
    grid=fig.add_gridspec(2,2)
    a=fig.add_subplot(grid[0,0]); h=a.hexbin(p.shape_PC1,p.shape_PC2,gridsize=40,mincnt=1,bins="log",cmap="Blues")
    tidy(a,f"A  Shape-only occupancy (n = {len(p):,})",f"PC1 ({ev.explained_variance.iloc[0]:.1%})",f"PC2 ({ev.explained_variance.iloc[1]:.1%})")
    fig.colorbar(h,ax=a,label="Fires per bin",shrink=.75)
    a=fig.add_subplot(grid[0,1]);t=np.arange(len(loading))/len(loading)+.5/len(loading)
    for pc,color in [("PC1",BLUE),("PC2",TEAL)]:a.plot(t,loading[pc],label=pc,color=color)
    a.axhline(0,color=GRAY,lw=.5);tidy(a,"B  Axis interpretation","Relative calendar time","Loading on growth-allocation bin");a.legend()
    a=fig.add_subplot(grid[1,0]);cats=["One observation","Two observations","≥3 with gaps","Primary ≥3 consecutive"]
    counts=[d.observation_count.eq(1).sum(),d.observation_count.eq(2).sum(),((d.observation_count>=3)&~d.consecutive).sum(),len(p)]
    a.barh(cats[::-1],counts[::-1],color=[TEAL,GRAY,GRAY,GRAY]);a.tick_params(axis="y",labelsize=8)
    a.set_xticks([0,50000,100000,150000],["0","50k","100k","150k"])
    tidy(a,"C  Observation support","Number of fires")
    nested=grid[1,1].subgridspec(1,3)
    for i,fid in enumerate(example_ids(d)[:3]):
        ax=fig.add_subplot(nested[0,i]);glyph(ax,slices[slices.fire_id.eq(fid)].sort_values("timestamp"),f"{'D  ' if i==0 else ''}Fire {fid}")
    fig.suptitle("The developmental morphospace: shape first, external attributes afterward",fontsize=14)
    fig.supxlabel(f"Five axes summarize {ev.cumulative_variance.iloc[4]:.1%}. Observation-threshold and null tests: Figure S2.",fontsize=9)
    return fig


def figure3(d,read):
    p=d[d.primary_eligible & d.weather_complete]
    fig,axes=plt.subplots(1,2,figsize=(11,4.8),layout="constrained",gridspec_kw={"width_ratios":[1,1.15]})
    a=axes[0];h=a.hexbin(p.shape_PC1,p.shape_PC2,C=p.mean_vpd_kpa,reduce_C_function=np.median,gridsize=28,mincnt=5,cmap="viridis")
    fig.colorbar(h,ax=a,label="Median event-mean VPD (kPa)",shrink=.8)
    tidy(a,"A  Weather projected onto shape","Shape PC1","Shape PC2")
    a=axes[1];ci=read("event_uncertainty")
    responses=["front_loaded_fraction","late_growth_fraction","peak_timing","normalized_entropy","pulse_count","shape_PC1_fold"]
    for i,(block,color) in enumerate(zip(BLOCKS,[BLUE,TEAL,GOLD])):
        g=ci[(ci.kind==block)&(ci.predictor_set=="core_plus_max")&(ci.resampling=="fire_id")].set_index("response").reindex(responses)
        y=np.arange(len(g))+(i-1)*.18
        a.errorbar(g.r2,y,xerr=[np.maximum(g.r2-g.r2_low,0),np.maximum(g.r2_high-g.r2,0)],fmt="o",ms=4,color=color,label=BLOCK_LABELS[block])
    a.axvline(0,color=GRAY,lw=.6);a.set_yticks(np.arange(len(responses)),[LABELS[r] for r in responses]);a.invert_yaxis()
    tidy(a,"B  Limited, response-specific predictability","Held-out R², core means + maximum VPD")
    a.legend(fontsize=7,loc="lower right")
    fig.suptitle(f"How weather maps onto morphology | primary maps and models: n = {len(p):,}",fontsize=14)
    fig.supxlabel("Weather does not define the axes. Adjusted associations, nested controls and selection diagnostics remain supplementary.",fontsize=8)
    return fig


def figure4(read):
    ci=read("state_uncertainty");perf=read("state_performance")
    fig,axes=plt.subplots(2,2,figsize=(11,7.5),layout="constrained")
    models=["mean_only","persistence","autoregressive","weather_only","state_plus_weather","state_weather_interactions"]
    labels=["Training mean","Current-growth persistence","Autoregressive state","Day-t weather only","State + weather","State × weather"]
    for ax,column,lo,hi,title in [(axes[0,0],"r2","r2_low","r2_high","A  Total skill (context)"),
                                (axes[0,1],"delta_r2","delta_low","delta_high","B  Increment above autoregressive state")]:
        shown=models if column=="r2" else models[2:3]+models[4:]
        shown_labels=labels if column=="r2" else labels[2:3]+labels[4:]
        for i,(block,color) in enumerate(zip(BLOCKS,[BLUE,TEAL,GOLD])):
            g=ci[(ci.kind==block)&(ci.resampling=="fire_id")].set_index("predictor_set").reindex(shown)
            ax.errorbar(g[column],np.arange(len(shown))+(i-1)*.18,
                xerr=[np.maximum(g[column]-g[lo],0),np.maximum(g[hi]-g[column],0)],fmt="o",ms=4,color=color,label=BLOCK_LABELS[block])
        ax.axvline(0,color=GRAY,lw=.6);ax.set_yticks(np.arange(len(shown)),shown_labels);ax.invert_yaxis()
        tidy(ax,title,"R²" if column=="r2" else "ΔR²; paired fire-bootstrap interval")
    axes[0,0].legend(fontsize=7)
    a=axes[1,0];g=read("state_spatial_exposure_sensitivity")
    for i,(model,label,color) in enumerate([("active_day_weather","Day-t growth centroid",TEAL),("final_centroid_weather","Final-event centroid (retrospective)",GRAY)]):
        sub=g[g.predictor_set.eq(model)]
        a.scatter(sub.delta_r2,np.arange(len(sub))+.13*i,label=label,color=color)
    a.set_yticks([.065,1.065],["Region holdout","Year-block holdout"]);a.axvline(0,color=GRAY,lw=.5)
    tidy(a,"C  Spatial-exposure sensitivity","ΔR² above the same state baseline");a.legend(fontsize=7)
    a=axes[1,1];g=read("state_subgroup_sensitivity")
    g=g[(g.kind=="region_block")&(g.predictor_set=="state_plus_weather")&(g.stratum=="season")]
    a.errorbar(g.delta_r2,np.arange(len(g)),xerr=[np.maximum(g.delta_r2-g.delta_low,0),np.maximum(g.delta_high-g.delta_r2,0)],fmt="o",color=TEAL)
    a.axvline(0,color=GRAY,lw=.5);a.set_yticks(np.arange(len(g)),g.value)
    tidy(a,"D  Seasonal sensitivity","ΔR² from adding day-t weather")
    fig.suptitle("Developmental state and subsequent calendar-day growth",fontsize=15)
    fig.supxlabel(f"Shared AR cohort: {int(perf.n.max()):,} transitions. Day-specific geometry; end-of-day covariates. Reconstructed-data benchmark, not causation or a live forecast.",fontsize=8)
    return fig


def figure5(d,read):
    summary=read("matching_sensitivity");perm=read("matching_permutation");examples=read("matched_examples")
    fig,axes=plt.subplots(2,2,figsize=(11,7.5),layout="constrained")
    g=summary[(summary.k==10)&(summary.metric=="euclidean")]
    a=axes[0,0];a.bar(g.space,g.matched_fraction,color=[BLUE,TEAL]);a.set_ylim(0,1.13);a.set_yticks(np.arange(0,1.01,.2))
    tidy(a,"A  Fraction with a unique acceptable partner",ylabel="Matched fires / eligible complete fires")
    a.text(.03,.98,"RMS z-distance ≤ 0.5\nSame region, season, duration and count\nArea ratio ≤ 2; no partner reuse",transform=a.transAxes,va="top",fontsize=8)
    a=axes[0,1]
    for i,space in enumerate(["weather","morphology"]):
        vals=perm[perm.matching_space.eq(space)].mismatch_gt1_fraction
        a.boxplot([vals],positions=[i],widths=.35)
        a.scatter(i,g[g.space.eq(space)].mismatch_gt1_fraction,s=60,color=TEAL,zorder=4)
    a.set_xticks([0,1],["Weather-matched","Morphology-matched"])
    a.set_ylim(.37,.56)
    tidy(a,"B  Mismatch versus conditional permutations",ylabel="Fraction with other-space distance > 1")
    a.text(.03,.96,"Dots: observed; boxes: within-stratum nulls",transform=a.transAxes,va="top",fontsize=8)
    profiles=[c for c in d if c.startswith("allocation_")]
    for ax,(_,pair) in zip(axes[1],examples.iterrows()):
        for side,color in [("a",BLUE),("b",GOLD)]:
            fid=str(pair["fire_id_"+side]);row=d[d.fire_id.astype(str).eq(fid)].iloc[0]
            ax.plot(np.linspace(0,1,len(profiles)+1),np.r_[0,np.cumsum(row[profiles].to_numpy(float))],color=color,label=f"Fire {fid}")
        tidy(ax,f"{'C' if ax==axes[1,0] else 'D'}  {pair.matching_space.capitalize()}-matched example","Relative developmental time","Cumulative reconstructed fraction")
        ax.legend(fontsize=8,loc="lower right")
        ax.text(.03,.97,f"Weather distance {pair.weather_distance:.3f}\nMorphology distance {pair.morphology_distance:.3f}\nMatch caliper {pair.caliper:.2f}; k = 10",transform=ax.transAxes,va="top",fontsize=8)
    fig.suptitle("Convergent and divergent pathways: representative matched-pair diagnostics",fontsize=14)
    fig.supxlabel("Independent pairs, not a two-by-two match. Fuel continuity, terrain, active-edge exposure, ignition and suppression remain testable hypotheses.",fontsize=8)
    return fig


def supplement(read):
    fig,axes=plt.subplots(2,3,figsize=(13,8),layout="constrained")
    p=read("event_performance");p=p[(p.alpha==1)&(p.kind=="region_block")]
    table=p.pivot(index="response",columns="predictor_set",values="r2")
    a=axes[0,0];h=a.imshow(table,aspect="auto",cmap="RdBu",vmin=-.1,vmax=.1)
    a.set_xticks(np.arange(len(table.columns)),table.columns,rotation=75,ha="right",fontsize=6)
    a.set_yticks(np.arange(len(table)),[LABELS.get(v,v) for v in table.index],fontsize=7)
    tidy(a,"S1A  Full region-held-out model grid");fig.colorbar(h,ax=a,shrink=.7,label="R² (color clipped ±0.1)")
    a=axes[0,1];p=read("morphospace_sensitivity")
    short={"all_observed_histories_observation_time":"All, observation time","one_slice":"One observation",
        "two_slice":"Two observations","multi_observation_including_gaps":"≥3, including gaps",
        "primary_consecutive_ge3":"Primary consecutive ≥3","consecutive_ge5":"Consecutive ≥5",
        "consecutive_ge10":"Consecutive ≥10","legacy_features_all_mean_centered":"Legacy features, all",
        "legacy_features_primary_mean_centered":"Legacy features, primary","shape_traits_only":"Shape traits only"}
    names=[f"Primary, {int(b)} bins" if v=="primary_resolution" else short[v] for v,b in zip(p.analysis,p.bins)]
    a.barh(names,p.first_five,color=BLUE);a.tick_params(axis="y",labelsize=7);a.invert_yaxis();tidy(a,"S1B  Feature/cohort sensitivity","Five-axis explained fraction")
    a=axes[0,2];p=read("pca_bootstrap")
    a.boxplot([p[f"axis{i}_cosine"] for i in range(1,6)],tick_labels=[f"PC{i}" for i in range(1,6)])
    a.set_ylim(.95,1.002);tidy(a,"S1C  Bootstrap axis stability",ylabel="Aligned loading cosine")
    a=axes[1,0];p=read("weather_inclusion_exclusion");p=p[p.dimension=="region"]
    table=p.pivot(index="value",columns="weather_complete",values="n").fillna(0)
    table.plot.barh(stacked=True,ax=a,color=[GRAY,TEAL],legend=False);tidy(a,"S1D  Weather completeness","Number of fires")
    a.legend(["Incomplete","Complete"],fontsize=7)
    a=axes[1,1];p=read("matching_sensitivity")
    for (space,metric),g in p.groupby(["space","metric"]):a.plot(g.k,g.matched_fraction,"o-",label=f"{space}, {metric}")
    tidy(a,"S1E  Matching sensitivity","Candidate neighbors k","Fraction matched");a.legend(fontsize=6)
    a=axes[1,2];p=read("state_performance")
    for model,color in [("autoregressive",BLUE),("state_plus_weather",TEAL),("state_weather_interactions",GOLD)]:
        g=p[(p.kind=="region_block")&(p.predictor_set==model)].sort_values("alpha")
        a.plot(g.alpha,g.r2,"o-",label=model,color=color)
    a.set_xscale("log");tidy(a,"S1F  Ridge penalty sensitivity","Penalty on standardized predictors","Region-held-out R²");a.legend(fontsize=6)
    fig.suptitle("Supplementary validation and sensitivity | complete tables accompany every panel",fontsize=14)
    return fig


def validation_supplement(read):
    fig,axes=plt.subplots(2,3,figsize=(13,8),layout="constrained")
    g=read("morphospace_stability").query("comparison=='observation_threshold'")
    a=axes[0,0]
    for col,label,color in [("pair_distance_spearman","Distance rank",BLUE),("neighbor_overlap","15-neighbor overlap",TEAL),
                            ("exemplar_tail_jaccard","Extreme-tail overlap",GOLD)]:
        a.plot(g.label.astype(int),g[col],"o-",label=label,color=color)
    a.set(ylim=(0,1.05),xticks=[2,3,5,7]);tidy(a,"S2A  Observation-count robustness","Minimum consecutive observations","Similarity to ≥3 reference")
    a.legend(fontsize=7)
    null=read("null_history_replicates");names=["temporal_shuffle","dirichlet_1","dirichlet_10"]
    a=axes[0,1]
    a.boxplot([null[null.null.eq(n)].first_five for n in names],tick_labels=["Shuffle","Dirichlet 1","Dirichlet 10"])
    a.axhline(null[null.null.eq("observed")].first_five.iloc[0],color=TEAL,label="Observed (same 4,000 fires)")
    tidy(a,"S2B  Compression is not uniquely biological",ylabel="First-five-axis fraction");a.legend(fontsize=7)
    a=axes[0,2];q=read("null_history_comparison").query("null=='temporal_shuffle'")
    metrics=["front_loaded_fraction_mean","pulse_count_mean","reactivation_count_mean"]
    q=q.set_index("metric").loc[metrics];y=np.arange(3)
    a.errorbar(q.null_mean,y+.1,xerr=[q.null_mean-q.null_low,q.null_high-q.null_mean],fmt="o",color=GRAY,label="Temporal shuffle, 95% range")
    a.scatter(q.observed,y-.1,color=TEAL,label="Observed")
    a.set_yticks(y,["Front-loading fraction","Detected pulses","Reactivations"]);a.invert_yaxis()
    tidy(a,"S2C  Ordering changes developmental traits","Mean per event");a.legend(fontsize=7)
    a=axes[1,0];g=read("endpoint_projections").query("minimum_observations==3 and axis<=2")
    g=g[g.attribute.isin(["catalog_area_km2","duration_days","observation_count","peak_growth_km2_per_day"])]
    names=["catalog_area_km2","duration_days","observation_count","peak_growth_km2_per_day"]
    for i,color in [(1,BLUE),(2,TEAL)]:
        sub=g[g.axis.eq(i)].set_index("attribute").loc[names];a.scatter(sub.spearman,np.arange(4)+(i-1.5)*.2,color=color,label=f"PC{i}")
    a.axvline(0,color=GRAY,lw=.5);a.set_yticks(range(4),["Final area","Duration","Observation count","Observed daily peak"]);a.invert_yaxis()
    tidy(a,"S2D  Exclusion does not imply independence","Spearman association with external attribute");a.legend(fontsize=7)
    a=axes[1,1];g=read("adjusted_weather_associations").query("population=='primary' and year_adjusted==True and resampling=='region'")
    responses=["front_loaded_fraction","late_growth_fraction","pulse_count"]
    for i,(predictor,color,label) in enumerate([("mean_vpd_kpa",BLUE,"Mean VPD"),("mean_precipitation_mm",TEAL,"Mean precipitation")]):
        q=g[g.predictor.eq(predictor)].set_index("response").loc[responses]
        a.errorbar(q.partial_rank,np.arange(3)+(i-.5)*.2,xerr=[np.maximum(q.partial_rank-q.low,0),np.maximum(q.high-q.partial_rank,0)],fmt="o",color=color,label=label)
    a.axvline(0,color=GRAY,lw=.5);a.set_yticks(range(3),[LABELS[r] for r in responses]);a.invert_yaxis()
    tidy(a,"S2E  Associations after all coarse controls","Partial rank; conditional region intervals");a.legend(fontsize=7)
    a=axes[1,2];g=read("matching_caliper_sensitivity").query("metric=='euclidean'")
    for space,color in [("weather",BLUE),("morphology",TEAL)]:
        q=g[g.space.eq(space)];a.plot(q.caliper,q.paired_fraction,"o-",color=color,label=space)
    tidy(a,"S2F  Pairing depends on the caliper","RMS standardized match caliper","Fraction assigned unique partners");a.set_ylim(0,1);a.legend(fontsize=7)
    fig.suptitle("Second-pass validation: stable broad gradients, qualified local and environmental claims",fontsize=14)
    return fig


def interaction_supplement(read):
    fig,axes=plt.subplots(2,2,figsize=(11,8),layout="constrained")
    density=read("vpd_joint_density")
    for a,state,title in [(axes[0,0],"current_growth_log1p","S3A  VPD × current state support"),
                          (axes[0,1],"previous_growth_log1p","S3B  VPD × previous state support")]:
        q=density[density.state.eq(state)]
        table=q.pivot(index="state_bin",columns="vpd_bin",values="n")
        h=a.imshow(np.log10(table+1),origin="lower",aspect="auto",cmap="Blues")
        for row in q[~q.supported].itertuples():a.scatter(row.vpd_bin,row.state_bin,marker="x",color=GOLD,s=35)
        tidy(a,title,"VPD quantile bin (low → high)","State quantile bin (low → high)")
        fig.colorbar(h,ax=a,label="log10(transitions + 1)",shrink=.8)
    a=axes[1,0];q=read("vpd_interaction_coefficients").query("stratum in ['all','region']")
    names=["all","central","east","intermountain","west"]
    for i,(term,color,label) in enumerate([("vpd_kpa_x_current_growth_log1p",BLUE,"VPD × current"),
                                         ("vpd_kpa_x_previous_growth_log1p",TEAL,"VPD × previous")]):
        g=q[q.term.eq(term)].set_index("value").loc[names]
        a.errorbar(g.estimate,np.arange(5)+(i-.5)*.18,xerr=1.96*g.cluster_se,fmt="o",color=color,label=label)
    a.axvline(0,color=GRAY,lw=.5);a.set_yticks(range(5),["All","Central","East","Intermountain","West"]);a.invert_yaxis()
    tidy(a,"S3C  Conditional coefficient heterogeneity","Coefficient per kPa × log1p(km²)")
    a.set_ylim(5.2,-.5);a.legend(fontsize=7,loc="lower right")
    a=axes[1,1];q=read("vpd_incremental_robustness").query("stratum=='all' and resampling=='fire_id'")
    names=["random_fire","year_block","region_block","spatiotemporal"]
    for i,(comparison,color,label) in enumerate([("VPD_above_additive",BLUE,"VPD products above additive"),
        ("VPD_above_other_interactions",TEAL,"VPD products above other interactions")]):
        g=q[q.comparison.eq(comparison)].set_index("kind").loc[names]
        a.errorbar(g.delta_r2,np.arange(4)+(i-.5)*.18,xerr=[g.delta_r2-g.delta_low,g.delta_high-g.delta_r2],fmt="o",color=color,label=label)
    a.axvline(0,color=GRAY,lw=.5);a.set_yticks(range(4),["Random diagnostic","Year block","Region block","Space + time"]);a.invert_yaxis()
    tidy(a,"S3D  VPD-specific held-out improvement","Paired ΔR²; conditional fire-bootstrap interval")
    a.set_ylim(4.2,-.5);a.legend(fontsize=7,loc="lower right")
    fig.suptitle("VPD interaction: predictive support with regional and size-dependent caveats",fontsize=14)
    fig.supxlabel("Crosses: fewer than 100 transitions or 30 fires. Quantile bins can merge at tied growth values. No extrapolated response surface is shown.",fontsize=8)
    return fig


def render(root:Path,data_root:Path):
    stats=root/"analysis/v2";out=root/"figures/v2"
    def read(name):
        path=stats/f"{name}.csv"
        if not path.exists():raise FileNotFoundError(f"Statistics must be written before rendering: {path}")
        return pd.read_csv(path)
    def validation_read(name):
        return pd.read_csv(root/"analysis/scientific_validation"/f"{name}.csv")
    d=pd.read_parquet(stats/"event_analysis.parquet")
    d.fire_id=d.fire_id.astype(str)
    s=pd.read_parquet(data_root/"scratch/fire_vase_run_full/tables/vase_slices.parquet")
    s.fire_id=s.fire_id.astype(str);s.timestamp=pd.to_datetime(s.timestamp)
    set_style();mpl.rcParams.update({"svg.hashsalt":"fire-vase-v2-20260828","font.family":"DejaVu Sans","font.size":8})
    builds=[lambda:figure1(d,s),lambda:figure2(d,s,read),lambda:figure3(d,read),
            lambda:figure4(read),lambda:figure5(d,read),lambda:supplement(read),
            lambda:validation_supplement(validation_read),lambda:interaction_supplement(validation_read)]
    outputs={}
    for i,build in enumerate(builds,1):
        name=f"Figure_{i}" if i<=5 else f"Supplementary_Figure_{i-5}"
        print(f"Rendering {name}",flush=True)
        fig=build();outputs[name]=save_figure(fig,name,directory=out,dpi=220,deterministic=True);plt.close(fig)
        web=root/"docs/assets/figures/v2";web.mkdir(parents=True,exist_ok=True)
        shutil.copy2(out/f"{name}.png",web/f"{name}.png")
    (out/"figure_manifest.json").write_text(json.dumps(outputs,indent=2))
    return outputs
