#!/usr/bin/env python3
"""Freeze an evidence-bound audit, claims and editorial handoff; no model fitting."""
from pathlib import Path
import json
import subprocess
import numpy as np
import pandas as pd
from fire_vase_v2_inputs import sha256

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"analysis/scientific_validation"
BASE=ROOT/"analysis/v2"


def table(d):
    def fmt(x):
        return f"{x:.4f}" if isinstance(x,(float,np.floating)) else str(x).replace("|","/").replace("\n"," ")
    return "| "+" | ".join(d.columns)+" |\n| "+" | ".join(["---"]*len(d.columns))+" |\n"+"\n".join(
        "| "+" | ".join(fmt(v) for v in row)+" |" for row in d.itertuples(index=False,name=None))


def build(root=ROOT):
    read=lambda n:pd.read_csv(OUT/f"{n}.csv")
    old=lambda n:pd.read_csv(BASE/f"{n}.csv")
    pop=json.loads((OUT/"population_audit.json").read_text())
    sha=subprocess.check_output(["git","rev-parse","HEAD"],cwd=root,text=True).strip()
    stability=read("morphospace_stability");threshold=stability.query("comparison=='observation_threshold'").set_index("label")
    threshold.index=threshold.index.astype(int)
    null=read("null_history_comparison");shuffle=null[null.null.eq("temporal_shuffle")].set_index("metric")
    assoc=read("adjusted_weather_associations").query("population=='primary' and year_adjusted==True and resampling=='region'")
    vpd=read("vpd_incremental_robustness").query("stratum=='all' and resampling=='fire_id'")
    coeff=read("vpd_interaction_coefficients").query("stratum=='all'")
    mismatch=read("mismatch_null_comparison")
    state=old("state_performance").query("alpha==1")
    event=old("event_performance").query("alpha==1")
    matches=read("matching_caliper_sensitivity").query("caliper==0.5 and metric=='euclidean'").set_index("space")
    def assocrow(p,r):return assoc[(assoc.predictor==p)&(assoc.response==r)].iloc[0]
    summary=dict(repository_sha=sha,primary_n=pop["primary"],event_n=pop["primary_weather_complete"],
        ge7_n=int(threshold.loc[7,"n"]),ge7_first_five=float(threshold.loc[7,"first_five"]),
        ge7_distance=float(threshold.loc[7,"pair_distance_spearman"]),ge7_neighbors=float(threshold.loc[7,"neighbor_overlap"]),
        shuffle_front_observed=float(shuffle.loc["front_loaded_fraction_mean","observed"]),
        shuffle_front_null=float(shuffle.loc["front_loaded_fraction_mean","null_mean"]),
        shuffle_pulses_observed=float(shuffle.loc["pulse_count_mean","observed"]),
        shuffle_pulses_null=float(shuffle.loc["pulse_count_mean","null_mean"]),
        shuffle_reactivation_observed=float(shuffle.loc["reactivation_count_mean","observed"]),
        shuffle_reactivation_null=float(shuffle.loc["reactivation_count_mean","null_mean"]),
        null_first_five=float(shuffle.loc["first_five","observed"]),
        null_shuffle_first_five=float(shuffle.loc["first_five","null_mean"]),
        null_dirichlet1=float(null.query("null=='dirichlet_1' and metric=='first_five'").null_mean.iloc[0]),
        null_dirichlet10=float(null.query("null=='dirichlet_10' and metric=='first_five'").null_mean.iloc[0]),
        precip_pulses=assocrow("mean_precipitation_mm","pulse_count").to_dict(),
        vpd_late=assocrow("mean_vpd_kpa","late_growth_fraction").to_dict(),
        vpd_classification="SUPPORTED WITH CAVEATS",
        vpd_region_delta=float(vpd.query("kind=='region_block' and comparison=='VPD_above_other_interactions'").delta_r2.iloc[0]),
        vpd_current_coefficient=float(coeff[coeff.term.eq("vpd_kpa_x_current_growth_log1p")].estimate.iloc[0]),
        vpd_previous_coefficient=float(coeff[coeff.term.eq("vpd_kpa_x_previous_growth_log1p")].estimate.iloc[0]),
        verdict="CENTRAL REPRESENTATION ROBUST BUT ENVIRONMENTAL STORY WEAK")
    (OUT/"validated_summary.json").write_text(json.dumps(summary,indent=2))
    audit_rows=[
        ("Mean mislabeled as peak","Catalog area/duration called peak","Separate mean_catalog growth attribute; old label retired","CORRECTLY IMPLEMENTED","analysis/v2/event_semantic_audit.csv.gz","test_peak_is_not_mean","All 278569 old peaks equal the catalog mean; 108214 observed peaks differ."),
        ("True peak","No direct daily maximum","Maximum observed dated increment","CORRECTLY IMPLEMENTED","analysis/v2/semantic_summary.json","test_peak_is_not_mean","Observed daily maximum only, never instantaneous/hourly peak."),
        ("Entropy","Catalog denominator could fail if reconstruction incomplete","Normalize to actual increment sum; undefined zero/missing totals","CORRECTLY IMPLEMENTED","analysis/v2/semantic_summary.json","entropy and invalid-growth tests","Current entropy unchanged; defensive correction is material."),
        ("Area totals","Reconstruction equality assumed","Source join and per-event discrepancy audit","CORRECTLY IMPLEMENTED","analysis/v2/input_audit.json","source join assertions","Maximum relative discrepancy 6.46e-16; 931 orphan source rows remain documented exclusions."),
        ("Pulse and landmark logic","Observation count could trigger multi-pulse","Actual prominence-based peaks; ordered interpretive rules","CORRECTLY IMPLEMENTED","analysis/v2/neighborhood_rules.csv","test_pulses_require_detected_maxima_not_observation_count","Labels are not natural classes; gappy pulse traits remain sequence-based sensitivity only."),
        ("Exact dates","Adjacent rows interpreted as next day","One-calendar-day response before completeness filtering","CORRECTLY IMPLEMENTED","analysis/scientific_validation/population_audit.json","calendar and duplicate-date tests","150922 longer gaps are not next-day transitions. Second pass also invalidates ambiguous duplicate prior-day state; no current rows affected."),
        ("Shape-only PCA","Mixed-scale median-centered SVD","Mean-centered standardized 20 normalized allocation masses","CORRECTLY IMPLEMENTED","analysis/v2/pca_loadings.csv","mass conservation and PCA replay","PC1 34.1%, five axes 89.4%, not the legacy 81.0/96.3%."),
        ("Endpoint removal","Area/duration/count/growth entered axes","Only allocation bins enter primary PCA","CORRECTLY IMPLEMENTED","analysis/scientific_validation/endpoint_projections.csv","verify_fire_vase_v2.py","Exclusion is not independence; moderate external associations persist."),
        ("Observation-count handling","Single-slice events mixed with rich histories","Primary >=3 consecutive; 1/2/gappy strata separate","CORRECTLY IMPLEMENTED","analysis/scientific_validation/observation_counts.csv","actual population assertions","Second pass adds >=2/3/5/7 common-anchor stability; local structure less stable than broad gradients."),
        ("Null histories","No adequate constraint baseline","Permutation and two Dirichlet nulls with fixed counts","PARTIALLY IMPLEMENTED","analysis/scientific_validation/null_history_comparison.csv","test_nulls_preserve_real_total_and_observation_count","v2 checked PCA geometry only; second pass adds actual-total conservation, trait/distance/landmark distributions."),
        ("Predictor nesting","Different sets mixed maximum VPD inclusion","Explicit core/full/maximum/length/quantile sets","CORRECTLY IMPLEMENTED","analysis/v2/event_predictors.csv","predictor nesting test","Effects are response-specific, not a cross-response median."),
        ("Common cohorts and folds","Feature and cohort changes confounded","Union-complete cohort, training-only preprocessing and fold PCA","CORRECTLY IMPLEMENTED","analysis/scientific_validation/event_fold_replay.csv","targeted alpha=1 numerical replay","9212 fires, identical cohort and folds. Fold-PCs are local statistical targets, not guaranteed identical biological axes."),
        ("Maximum VPD opportunity","Extreme exposure interpreted without record-length control","Nested length controls and fixed-length strata","CORRECTLY IMPLEMENTED","analysis/scientific_validation/maximum_vpd_increment.csv","same-cohort model replay","Most extra max-VPD shape skill attenuates with opportunity controls; attenuation does not prove purely mechanical causation."),
        ("Geographic/seasonal/year confounding","Bivariate relations emphasized","v2 partial ranks control length, area, region, month but omit year","PARTIALLY IMPLEMENTED","analysis/scientific_validation/adjusted_weather_associations.csv","test_partial_rank_projects_both_outcomes_off_same_nuisance","Second pass adds categorical year and primary-cohort results; broad rain-pulse story weakens."),
        ("Weather selection","Complete fires treated as broadly representative","Region/year/size/morphology inclusion table","PARTIALLY IMPLEMENTED","analysis/scientific_validation/weather_selection_traits.csv","population census","Second pass adds explicit observation count and standardized differences; selection exactly excludes Alaska/Hawaii here."),
        ("State estimand","Adjacent-observation next growth","log1p exact next-calendar-day km2; common t-1,t,t+1 cohort","CORRECTLY IMPLEMENTED","analysis/scientific_validation/state_population.csv","state cohort hash/date assertions","87944 transitions from 31700 fires, not all 196611 eligible transitions."),
        ("Spatial look-ahead","Final-event centroid exposure","Day-t newly burned-area centroid from raw geometry","CORRECTLY IMPLEMENTED","analysis/v2/day_t_weather_manifest.json","test_no_final_geometry_or_future_geometry_in_prospective_models","Removes final-geometry pathway, not retrospective reconstruction or timing limitations."),
        ("Autoregression","Weather totals without strong state comparator","Current/prior growth, cumulative area and elapsed time baseline","CORRECTLY IMPLEMENTED","analysis/scientific_validation/state_incremental_skill.csv","state replay","Most total skill is state-only; additive weather increment is about .005 R2."),
        ("VPD x state uncertainty/support","Visually emphasized interaction","v2 validates eight weather products jointly, not VPD specifically","PARTIALLY IMPLEMENTED","analysis/scientific_validation/vpd_incremental_robustness.csv","coefficient fixture and held-out ablations","Second pass isolates two VPD products; qualified positive average increment, heterogeneous coefficients."),
        ("Mismatch matching","Most-discordant neighbor selected","Outcome-blind greedy disjoint kNN graph with calipers","CORRECTLY IMPLEMENTED","analysis/scientific_validation/matching_balance.csv","exact pair replay and uniqueness assertions","Null-compatible mismatch; good-match existence is only within candidate graph."),
        ("Matching sensitivity","No representative prevalence design","v2 k/metric sensitivity, but no caliper variation","PARTIALLY IMPLEMENTED","analysis/scientific_validation/matching_caliper_sensitivity.csv","actual caliper/ID assertions","Second pass adds .25/.5/.75/1 sensitivity; paired fraction is design-dependent, not ecological prevalence."),
        ("Figure redesign","Legacy climate-centered panels","Five morphology-first figures","PARTIALLY IMPLEMENTED","analysis/scientific_validation/figure_claim_audit.csv","PDF/PNG visual QA","Second pass simplifies Figures 2/3, moves diagnostics to S2 and adds VPD-specific S3."),
        ("Manuscript numbers","Legacy headlines and overclaims","Versioned generated manuscript with corrected evidence","CORRECTLY IMPLEMENTED","docs/manuscripts/fire_vase_developmental_morphology/manuscript_v2.md","source/table checks and PDF QA","Second pass inserts stability/null/adjustment/interaction qualifications; archival values remain explicitly retired."),
        ("Tests and reproducibility","Legacy numerical reproduction alone","Invariant tests, numerical replays and deterministic rendering","PARTIALLY IMPLEMENTED","analysis/scientific_validation/reproducibility.json","dedicated and repository pytest commands","Two pre-existing test modules cannot collect: missing tests.helpers.contracts. Not claimed fully green."),
        ("Configuration integrity","Some declared thresholds silently ignored","Actual fixed defaults happen to match recorded settings","PARTIALLY IMPLEMENTED","scripts/fire_vase_v2.py","test_fixed_protocol_rejects_silent_threshold_override","Second pass rejects unsupported overrides. No current numerical value changes."),
    ]
    audit=pd.DataFrame(audit_rows,columns=["issue","previous implementation","new implementation","status","evidence file","tests","scientific consequence"])
    audit.to_csv(OUT/"second_pass_audit.csv",index=False)
    figures=pd.DataFrame([
        ["1","What does VASE encode?","Four real dated events","Observed increments, cumulative mass and elapsed-time rings","Encoding preserves ordering and makes gaps explicit","No causal mechanism or population prevalence","vase_slices.parquet; event_analysis.parquet; example_ids()","PASS: IDs and dates checked; visual review"],
        ["2","What shape structure is represented?","10246 consecutive >=3 histories","20-bin PCA; first two loading contrasts; observation census; real glyphs","Shared broad developmental gradients without endpoint inputs","Not independence from endpoints, natural classes, or a biological wedge","pca_variance.csv; pca_loadings.csv; event_analysis.parquet","PASS: numerical PCA replay and threshold stress tests"],
        ["3","Does external weather map to shape predictably?","9212 common complete primary fires","Binned mean VPD and per-response blocked prediction","Weak, heterogeneous association with morphology","No uniform explanatory power, causation, or all-fire generality","event_uncertainty.csv; event_analysis.parquet","PASS: same cohort/folds; simplified to two panels"],
        ["4","What does weather add above recent state?","87944 transitions / 31700 fires","Six comparators; paired deltas; exposure/season checks","Small reproducible improvement above strong AR baseline","Not a VPD-specific curve, uniform subgroup skill, or live forecast","state_uncertainty.csv; state_spatial_exposure_sensitivity.csv; state_subgroup_sensitivity.csv","PASS: exact dates, hashes and numerical replay; VPD specifics in S3"],
        ["5","How much mismatch remains under declared matching?","9212 eligible fires; 3710 weather and 3145 morphology pairs","Unique caliper pairs; conditional permutations; two independent median examples","Observed mismatch is compatible with this null; pairs are study candidates","No excess mismatch, ecological prevalence, 2x2 matching, or mechanism","matched_pairs.csv; matching_permutation.csv; matched_examples.csv","PASS: exact ID/order reproduction, balance, k/metric/caliper checks"],
    ],columns=["FIGURE","SCIENTIFIC QUESTION","DATA","ANALYSIS","CLAIM","WHAT THE FIGURE DOES NOT SHOW","DEPENDENCIES","VALIDATION STATUS"])
    figures.to_csv(OUT/"figure_claim_audit.csv",index=False)
    claims=pd.DataFrame([
        ["A","Observed histories contain developmental information beyond endpoint summaries.","SUPPORTED","Dated normalized allocations encode internal ordering, including measured front/late growth and pulses.",10246,"event_analysis.parquet; null_history_comparison.csv","Information content, not proven extra ecological/causal mechanism."],
        ["B","A shape-only morphospace exists without endpoint variables defining axes.","SUPPORTED","Only allocation_00 through allocation_19 are fitted; PCA reproduced.",10246,"analysis/v2/pca_loadings.csv; endpoint_projections.csv","No claim of statistical independence from duration or size."],
        ["C","Main developmental gradients persist among well-observed fires.","SUPPORTED WITH CAVEATS",f">=7 distance rho {summary['ge7_distance']:.3f}, neighbor overlap {summary['ge7_neighbors']:.3f}; first axes stable.",1171,"morphospace_stability.csv","Common primary anchors, not independent external validation; higher axes, exemplars and local neighborhoods change."],
        ["D","Observed histories contain organization beyond null normalized histories.","SUPPORTED WITH CAVEATS",f"Mean front loading {summary['shuffle_front_observed']:.3f} vs shuffle {summary['shuffle_front_null']:.3f}; pulses {summary['shuffle_pulses_observed']:.3f} vs {summary['shuffle_pulses_null']:.3f}.",4000,"null_history_comparison.csv","Ordering-specific evidence; dimensionality also arises under positive-allocation constraints and observation selection."],
        ["E","Continuous gradients rather than discrete natural fire types.","NOT YET SUPPORTED","Coordinates are continuous and landmark labels are rules, but absence of natural classes was not tested.",10246,"analysis/v2/neighborhood_rules.csv; Figure_2","Do not equate a continuous coordinate system with evidence against all latent classes."],
        ["F","Weather is associated with developmental morphology.","SUPPORTED WITH CAVEATS","Selected responses have weak positive blocked skill; peak timing and fold PCs are poorly recovered.",9212,"weather_response_validation.csv","Model-, response-, population- and blocking-dependent."],
        ["G","Important associations survive coarse geography/season/length controls.","SUPPORTED WITH CAVEATS",f"Mean VPD/late-growth partial rho {summary['vpd_late']['partial_rank']:.3f}; most associations are small after year/region/month/size/length controls.",9212,"adjusted_weather_associations.csv","Survival does not imply a large or causal relationship; precipitation/pulses is weak."],
        ["H","Weather does not uniquely determine individual morphology.","SUPPORTED WITH CAVEATS","Measured event weather and tested ridge models leave much shape variation unrecovered; matched pairs differ.",9212,"weather_response_validation.csv; matched_distance_distributions.csv","Not proof that every possible weather representation/model is nondeterministic."],
        ["I","Recent state provides a strong autoregressive baseline.","SUPPORTED WITH CAVEATS","Pooled AR R2 .448 in regional/space-time holdouts, .458 in year/random holdouts.",87944,"state_incremental_skill.csv","Pooled across 31700 fires; some small-area strata have poor absolute skill."],
        ["J","Weather adds reproducible information beyond recent state.","SUPPORTED WITH CAVEATS","Additive delta about .005; all-weather products .015-.018 across blocks.",87944,"state_incremental_skill.csv","Small conditional improvement; fixed-prediction intervals, four regions, reconstructed end-of-day benchmark."],
        ["K","VPD x state is reproducible and empirically supported.","SUPPORTED WITH CAVEATS",f"Two VPD products add .006-.012 over other interactions; region delta {summary['vpd_region_delta']:.4f}; dense central quantile cells.",87944,"vpd_incremental_robustness.csv; vpd_interaction_coefficients.csv; vpd_joint_density.csv","Year edges, region and size coefficients vary; not a universal curve or causal effect."],
        ["L","Mismatch structure exceeds a reasonable null.","NOT SUPPORTED","49.7% vs null 50.4% (weather matches); 39.5% vs 40.2% (morphology matches).",9212,"mismatch_null_comparison.csv","Declared distance>1 threshold and sparse-stratum reference only; no excess detected."],
        ["M","Matched counterexamples identify mechanistic study candidates.","SUPPORTED WITH CAVEATS","Two independently validated median-mismatch pairs have explicit IDs and calipers.",4,"analysis/v2/matched_examples.csv; matching_balance.csv","Candidates, not extreme cases or evidence identifying the missing mechanism."],
    ],columns=["claim_id","claim","status","evidence","sample_size","analysis_artifact","major_caveat"])
    claims.to_csv(OUT/"final_claim_matrix.csv",index=False)
    (OUT/"final_claim_matrix.md").write_text("# Final claim matrix\n\n"+table(claims)+"\n")
    headlines=[]
    def headline(result,old_value,new_value,n,status,reason,consequence,source):
        headlines.append(dict(result=result,old_value=old_value,new_value=new_value,sample_size=n,
            analysis_version="v2 + scientific-validation-1",status=status,reason_for_change=reason,
            manuscript_consequence=consequence,source_file=source))
    for key in ["events","slices","weather_complete"]:
        headline(key,pop[key],pop[key],pop[key],"CONFIRMED","Source/derived population audit","Retain with population label","population_audit.json")
    for label,oldv,newv in [("PCA PC1",.8098926,threshold.loc[3,"pc1"]),("PCA first five",.9627472,threshold.loc[3,"first_five"])]:
        headline(label,oldv,newv,10246,"RETIRED","Legacy features/centering/cohort replaced; not same estimand","Retire old headline; identify both generations","analysis/v2/morphospace_sensitivity.csv")
    headline("Median heterogeneous event-weather R2",.3493478298,"not a valid aggregate headline",9212,"RETIRED","Nested common cohorts and per-response validation","Do not reuse .349 as general skill","weather_response_validation.csv")
    headline("Old adjacent-slice state R2",.3533341326,"not comparable to exact-day AR estimand",87944,"RETIRED","Dates, exposure and state comparator changed","Use incremental exact-day results","state_incremental_skill.csv")
    for row in read("observation_counts").itertuples(index=False):
        headline(f"Observation count {row.observations}",row.all_events,row.consecutive,row.all_events,"SCOPE_CLARIFIED","All vs consecutive histories, not event loss","Always report 1/2-slice events too","observation_counts.csv")
    for row in old("neighborhood_rules").itertuples(index=False):
        headline(f"Landmark occupancy: {row.landmark}","legacy rule definitions retired",row.n,pop["events"],
            "RULE_REPLACED","New priority-ordered count/date/actual-pulse rules","Interpretive landmarks, not natural types","analysis/v2/neighborhood_rules.csv")
    for row in old("morphospace_sensitivity").itertuples(index=False):
        if row.analysis.startswith("legacy_features"):
            headline(f"Mean-centered legacy features: {row.analysis}; first five",.9627472,row.first_five,row.n,
                "COMPARISON_ONLY","Separates centering/cohort effects from feature definition","Not the primary shape-only space","analysis/v2/morphospace_sensitivity.csv")
    for row in event.itertuples(index=False):
        headline(f"Event R2: {row.response}; {row.predictor_set}; {row.kind}",row.r2,row.r2,row.n,
            "EXCLUDED_KNOWN_OUTCOME" if row.status=="excluded_known_outcome" else "CONFIRMED",
            "Prespecified alpha=1 replay; unchanged v2 cohort and folds","Report individual response; local fold-PC caveat","weather_response_validation.csv")
    for row in state.itertuples(index=False):
        headline(f"State {row.predictor_set}; {row.kind}",row.r2,row.r2,row.n,"CONFIRMED","Same exact-day cohort",
            f"Delta R2 above AR {row.delta_r2:.6f}","state_incremental_skill.csv")
    for row in mismatch.itertuples(index=False):
        headline(f"Mismatch {row.space}; {row.metric}",row.observed,row.observed,row.pairs,"CONFIRMED",
            "Pair ID replay and null audit",f"Null mean {row.null_mean:.6f}; no excess","mismatch_null_comparison.csv")
    for row in null.itertuples(index=False):
        headline(f"Expanded null {row.null}; {row.metric}","not previously evaluated on this sample",row.observed,row.n,"VALIDATED",
            "Separate recorded 4000-event sample adds trait/distance/landmark tests",f"Reference mean {row.null_mean:.6f}","null_history_comparison.csv")
    for row in assoc.itertuples(index=False):
        headline(f"Association {row.predictor}; {row.response}",row.raw_spearman,row.partial_rank,row.n,"ADJUSTED",
            "Primary cohort, year/region/month/duration/count/area controls","Small associations; not causal","adjusted_weather_associations.csv")
    pd.DataFrame(headlines).to_csv(OUT/"headline_results_comparison.csv",index=False,float_format="%.12g")
    story=f"""# Validated scientific story

## PRIMARY DISCOVERY

The unchanged normalized-growth representation gives stable broad developmental gradients among consecutively observed multi-slice FIRED events, and their ordering is not interchangeable with random permutations of the same increments. This is a representation of observed development, not a universal physical typology. At >=7 observations, five-axis distance ranks correlate {summary['ge7_distance']:.3f} with the primary reference, while five-axis coverage falls to {summary['ge7_first_five']:.1%} and local-neighbor overlap to {summary['ge7_neighbors']:.1%}.

## SECONDARY RESULTS

Real sequences allocate a mean {summary['shuffle_front_observed']:.1%} of growth to the first half versus {summary['shuffle_front_null']:.1%} after within-fire shuffling; detected pulses average {summary['shuffle_pulses_observed']:.3f} versus {summary['shuffle_pulses_null']:.3f}. Weather associations are weak and response-specific. Recent state is a substantially stronger predictor than weather alone. Additive weather adds about .005 R2; weather-state products add about .015-.018 above AR. VPD-specific ablations support a small average improvement, with important coefficient heterogeneity.

## NEGATIVE RESULTS

Low dimensionality alone is not evidence of biological restriction: random positive allocations can compress more than observed histories. Rain-pulse associations attenuate and are weak in the primary population after controls. A median .349 weather headline is retired. Mismatch does not exceed the declared conditional-permutation reference. Neither a universal VPD curve nor absence of latent natural classes has been established.

## IMPORTANT CAVEATS

Only {pop['primary']:,}/{pop['events']:,} events define primary shape axes; 161073 events have one observation. All weather-complete fires here are CONUS; Alaska/Hawaii are wholly excluded. Shape still correlates with size, duration and count. Stability metrics evaluate refitted coordinates on fixed primary anchors, not independent generalization. Null tests are descriptive and not multiplicity-adjusted. Daily reconstruction and timing uncertainty remain; coefficient covariance and held-out error bootstrap condition on fitted design/predictions. Four region clusters and sparse large-fire/edge-year subsets limit uncertainty. Small-size state strata can have negative absolute R2 despite a positive incremental difference.

## WHAT THE PAPER SHOULD NOT CLAIM

No natural fire types, biological wedge, weather-defined axes, morphology-endpoint independence, uniform weather predictability, causal interactions, fully prospective operation, excess mismatch, ecological mismatch prevalence, or inferred fuel/suppression mechanism. Candidate-neighbor coverage is not exhaustive good-match existence. The two example pairs do not form a two-by-two match.

## MOST IMPORTANT NEXT DATA LAYER

Independently validated active-edge fuel continuity and terrain, aligned to dated observed growth, are the most useful next mechanistic layer; suppression/ignition context and improved burn-date uncertainty are also needed. This is a future research priority, not an explanation established by current residuals. No such data were ingested here.
"""
    (OUT/"scientific_story.md").write_text(story)
    audit_text=f"""# Second-pass scientific audit

Candidate baseline: `{sha}`. The preceding v2 closeout reproduced 60 numerical/publication artifact hashes in a saved-statistics render replay and reviewed all 12 manuscript pages. Targeted second-pass numerical replay validates primary event models at the prespecified penalty, three principal state models across all four blocks, the PCA, and exact matching IDs/order. See replay JSON files. This is not a blind rerun of archived/gappy/penalty grids.

## Correction audit

Statuses assess how completely the **preceding pass** implemented each correction. The last column distinguishes second-pass additions. All statuses use the requested vocabulary.

{table(audit)}

## Observation-time semantics

There are {pop['adjacent_observed_pairs']:,} adjacent observed pairs: {pop['exactly_one_day']:,} one-day, {pop['exactly_two_days']:,} two-day and {pop['greater_than_two_days']:,} longer than two days. Missing dates, duplicates and zero-growth observations are all zero in these inputs. Missing days are never inserted as zero. The 931 raw daily rows not linked to the event catalog remain exclusions, not silently added events.

| Quantity | Time basis | Permitted interpretation |
| --- | --- | --- |
| Pulse and reactivation counts | Observation sequence; consecutive daily only in primary | Low observed increments, not documented suppression or dormancy; gappy counts sensitivity-only |
| First/second differences | Fixed 20-bin normalized relative-time density | Dimensionless roughness, not km2/day velocity or acceleration |
| Next growth | Exact t to t+1 calendar day; AR also requires t-1 | Subsequent observed daily increment, conditioned on an observed transition |
| Duration | Catalog hours / 24; calendar span retained separately | Endpoint attribute, never PCA input |
| Allocation interpolation | Relative calendar time for consecutive histories; index time for gappy sensitivity | Mass-conserving rebinning, not additional observations |
| State weather | Day-t newly burned polygon centroid | Forward-dated response with retrospectively reconstructed end-of-day exposure; no final geometry |

One/two-observation and gappy events remain in the data narrative and separate sensitivity PCA fits. They do not define primary axes and are not silently projected as fully observed multi-day forms. This pass explicitly projects excluded endpoint attributes onto primary scores, not excluded events into the primary cohort.

## Stability interpretation

{table(stability.query("comparison=='observation_threshold'")[["label","n","first_five","subspace_overlap","pair_distance_spearman","neighbor_overlap","exemplar_tail_jaccard"]])}

All fits use unchanged 20-bin features. Each comparison is evaluated on the same recorded 1000 primary-event anchors and 20000 sampled index pairs (self-pairs removed), using five unwhitened score axes. Assignment/sign alignment tests axes; Procrustes allows rotation and global scale; distance rank and 15-neighbor overlap test geometry; top/bottom 2% anchor-tail Jaccard tests exemplar stability. Repeated/tied profiles can affect neighbor identities. Bootstrap, >=2/3/5/7, region and year results are all exported. Regions/years with fewer than 30 primary events do not define a fit. Higher axes and local identity are less stable than leading gradients.

## Null interpretation

The second-pass seeded 4000-event sample is explicitly stored and differs from the original v2 null sample. Do not mix their observed baselines. Shuffle preserves count, true reconstructed total and the entire increment multiset; both Dirichlet nulls preserve count and total. Entropy is unchanged under shuffle, a useful negative control. Per-replicate trait quantiles, distance quantiles in a fixed primary-standardized metric, landmark proportions, dimensionality and concentration are exported. One hundred replicates give descriptive tail resolution 1/101; these are not multiplicity-adjusted significance declarations. Lower pulse/reactivation counts and higher front loading show nonrandom observed ordering, not a unique ecological cause.

## Weather, state and matching limitations

`weather_response_validation.csv` contains all individual responses, sets, blocks and three resampling units; its wide companion is convenience only. Known duration outcomes in length-predictor models are excluded. Fold PCA is trained without test data; axes are fold-local and metrics must not be interpreted as prediction of a universal PC1. Maximum VPD is more associated with duration than mean VPD; above-core max-VPD increments attenuate sharply with length controls. Fixed-length strata are retained as separate sensitivity tables, not quietly pooled.

Year-adjusted primary associations replace the gappy-inclusive main association narrative. Exact collinearity of duration/count in primary histories is handled by least-squares projection; it prevents estimating two distinct opportunity effects. Weather completeness is exactly geographic in this materialized input, so missingness is not ignorable. There are no weather data to validate Alaska/Hawaii transfer.

VPD interaction classification: **SUPPORTED WITH CAVEATS**. Full-sample product coefficients use original units and fire-cluster sandwich standard errors conditional on the ridge design/penalty. Per-year/region/season/size and training-fold refits test heterogeneity; VPD-product ablations test incremental held-out performance. Joint support is reported for both current and prior state; quantile bins merge where growth values tie. Central 1-99% VPD range is 0.19-3.48 kPa. A dense coarse cell does not license tail extrapolation or prove conditional positivity after every nuisance variable. Partial 2000/2021 years and small-size refits can change coefficient signs. No fitted response surface is shown.

Matching uses global matching-cohort scales, exact region/season/duration/count, RMS or mean-absolute z-distance, area ratio <=2, and no reuse within an analysis. Balance tables report absolute paired differences, not merely signed means that could cancel. The candidate graph is limited to k neighbors before area filtering; `candidate_fraction` is not exhaustive existence. Singleton permutation strata contain 2.79% of eligible events. Null results condition on declared strata, not a proof of universal independence. Both independent examples verify their own matching-space caliper; no two-by-two assertion remains.

## Figure-to-claim audit

{table(figures)}

## Reproducibility and remaining implementation issues

Two safe guard corrections affect no current observations: reject declared fixed-protocol configuration overrides that would otherwise be ignored, and invalidate an ambiguous duplicate prior-day state. The current inputs have no duplicate dates. Full test collection still lacks `tests.helpers.contracts` in two pre-existing modules; this unrelated package-testing gap is recorded, not silently patched or reported as covered. The final reproducibility record distinguishes byte-identical regenerated tables/publications from reused v2 source/statistics hashes. The old v2 run manifest is historical provenance; the new validation/publication freeze supersedes stale publication hashes within it without rewriting history.
"""
    (OUT/"audit_report.md").write_text(audit_text)
    selected=event.query("predictor_set=='core_plus_max'").pivot(index="response",columns="kind",values="r2").reset_index()
    state_selected=state[state.predictor_set.isin(["autoregressive","state_plus_weather","state_weather_interactions"])][["kind","predictor_set","r2","delta_r2"]]
    final=f"""# Final scientific validation report

1. Repository baseline SHA: `{sha}`; subsequent working-tree code and output hashes are in the freeze manifest.
2. Previous pass reproduced: 60-file render replay; PCA, primary alpha=1 event/state models, cohorts/folds and unique pair IDs reproduced. Historical v1 event/state tables reproduced to <1e-15 in the preceding pass. No claim of rerunning every archived sensitivity.
3. Remaining implementation errors: no known numerical error affecting these data. Two guard defects corrected (ignored fixed-protocol overrides and ambiguous duplicate prior state). Pre-existing full-test collection gap remains. Event-year/month are fire-level, not observation-level seasonal effects.
4. Primary population: 10246 valid >=3 consecutive histories; 9212 complete primary weather fires. Matching uses the same 9212; state analysis is a different explicitly identified transition cohort.
5. Observation distribution: 161073 one-slice, 47950 two-slice, 69546 >=3, 30538 >=5, 15036 >=7. Consecutive >=3/5/7 counts: 10246/2887/1171. Threshold rows overlap; do not sum them.
6. Exact-day transitions: 196611 of 347533 adjacent pairs; 81940 two-day and 68982 longer gaps. Common AR cohort: 87944 transitions, 31700 fires. Missing/duplicate dates and observed zero increments: zero.
7. Morphospace: mean-centered standardized PCA of 20 mass-conserving normalized growth-allocation bins; five-axis geometry, not a new feature search.
8. Excluded inputs: final area, duration, observation count, absolute peak/mean growth, slenderness and weather. They are external attributes only.
9. Observation-threshold stability: >=7 PC1/2 common-anchor correlations {threshold.loc[7,'axis1_correlation']:.3f}/{threshold.loc[7,'axis2_correlation']:.3f}, distance rho {summary['ge7_distance']:.3f}; local neighbors {summary['ge7_neighbors']:.3f}, exemplar-tail overlap {threshold.loc[7,'exemplar_tail_jaccard']:.3f}. Five-axis coverage falls to {summary['ge7_first_five']:.1%}. Full bootstrap/year/region results are in `morphospace_stability.csv`.
10. Null result: observed first-half allocation {summary['shuffle_front_observed']:.3f} versus shuffle {summary['shuffle_front_null']:.3f}; pulses {summary['shuffle_pulses_observed']:.3f} versus {summary['shuffle_pulses_null']:.3f}; reactivation {summary['shuffle_reactivation_observed']:.3f} versus {summary['shuffle_reactivation_null']:.3f}. Ordering differs; compression alone is not uniquely biological.
11. Endpoint relationship: PC1 Spearman area -.308, duration/count -.185, true peak -.332; PC2 area .259, duration/count .256. Excluded variables remain moderately associated with shape.
12. Strongest adjusted associations: mean VPD versus late allocation rho {summary['vpd_late']['partial_rank']:.3f}; mean VPD/front loading +.050, precipitation/late allocation +.041. Primary precipitation/pulses falls from {summary['precip_pulses']['raw_spearman']:.3f} to {summary['precip_pulses']['partial_rank']:.3f}, with region interval crossing zero. All are small; no causal claim.
13. Per-response weather performance: table below uses core means + maximum VPD; all nested sets and fire/year/region intervals are in `weather_response_validation.csv`. Stronger response skill lies in roughness/taper/entropy than peak timing or fold PCs. The latter are training-fold-local targets.
14. Weather selection: 237235 complete CONUS events; all 41279 Alaska and 55 Hawaii events incomplete. Complete mean duration 3.34 vs 2.35 days and mean count 2.32 vs 1.82; standardized entropy difference .309. Geography and observation process restrict generality.
15. State-only performance: pooled AR R2 .448 regional and crossed space-time; .458 random/year. Small-fire absolute performance is weaker and can be negative.
16. Incremental weather: additive about .005 R2; all weather-state products .015-.018 over AR. Table below and `state_incremental_skill.csv` contain all blocks and paired uncertainty.
17. VPD x state: SUPPORTED WITH CAVEATS. VPD products add .006-.012 over the other interaction products; global current/prior coefficients {summary['vpd_current_coefficient']:.3f}/{summary['vpd_previous_coefficient']:.3f}. Blocked average increments are positive, but region/size and edge-year coefficient heterogeneity precludes a universal curve.
18. Matching: 9212 eligible; 3710 weather pairs (80.5% paired), 3145 morphology pairs (68.3% paired). Candidate-graph coverage 91.2%/81.3%. Caliper .25-1 changes paired coverage to 59.8-85.7% / 54.0-77.9%.
19. Mismatch/null: observed >1 fractions .497 vs null .504 and .395 vs .402, within conditional permutation ranges. No excess mismatch detected. Not an ecological prevalence estimate.
20. Strongest conclusion: broad shape geometry and nonrandom ordering among adequately observed histories; representation precedes environmental explanation.
21. Most important negative result: low dimensionality does not establish biological restriction; measured event weather has weak heterogeneous shape skill, and mismatch is null-compatible.
22. Largest limitation: observation-process selection and timing uncertainty; only 3.68% of catalog events enter primary shape training. Missing mechanistic covariates and retrospective exposure further limit environmental interpretation.
23. Main figures changed: Figures 2 and 3 simplified; Figures 1, 4 and 5 retain their main analytical design. New S2 holds stability/null/adjustment/caliper checks; S3 holds VPD support/coefficients/ablation. Full figure-to-claim audit accompanies them.
24. Claims changed: strengthen ordering evidence and bounded VPD incremental support; qualify local neighborhood/long-history stability; weaken rain/pulses and broad weather predictability; remove excess mismatch, biological wedge and untested absence-of-types claims.
25. Prism handoff: `analysis/scientific_validation/PRISM_HANDOFF.md`.
26. Final manuscript PDF: `output/pdf/fire_vase_v2_manuscript.pdf`; source: `docs/manuscripts/fire_vase_developmental_morphology/manuscript_v2.md`.

## Individual weather responses

{table(selected)}

## State comparator results

{table(state_selected)}

## Claims A-M

{table(claims[['claim_id','status','evidence','major_caveat']])}

## Verdict

{summary['verdict']}

This verdict reflects stable representation and temporal-order evidence alongside weak, selected, noncausal event-weather associations. It does not deny the modest reproducible state-weather increment. See `reproducibility.json` for exact verification scope and the full-test collection limitation.
"""
    (OUT/"final_report.md").write_text(final)
    handoff=f"""# Prism handoff - validated evidence, not a request to reanalyze

1. **Primary claim:** normalized observed-growth allocation provides stable broad developmental gradients among 10246 consecutively observed >=3-slice FIRED events; ordering carries information beyond shuffled increments. Scope is the observation-supported population, not every wildfire.
2. **Secondary claims:** weak response-dependent weather associations; strong pooled autoregression; small additional weather/state-interaction skill; validated pairs as follow-up candidates.
3. **Removed:** universal biological wedge; .349 median weather headline; excess mismatch over null; proven natural fire classes or proven absence of classes; causal weather/fuel/suppression conclusions; operational prospective claims.
4. **Weakened:** precise local neighborhood/exemplar identity, long-history transfer, precipitation-pulse association, weather as a general morphology predictor, universal VPD response curve.
5. **Strengthened:** actual-total/multiset-preserving order null; common-anchor geometry metrics; explicit year adjustment; VPD-specific held-out ablation plus support/heterogeneity checks; matching balance and caliper sensitivity.
6. **Headlines:** legacy PC1/five-axis 81.0/96.3% RETIRED; current 34.1/89.4% on 10246. >=7:1171 and74.2% five-axis. All events278569/slices626102/weather-complete237235; primary weather9212. Exact pairs196611; AR87944/31700fires. Regional AR .4476, additive delta .0050, all-products delta .0181; VPD-pair ablation delta .0118 over other products. Match >1 fractions49.7/39.5% vsnull50.4/40.2%. `headline_results_comparison.csv` is the exhaustive machine-readable source.
7. **Figures:** 1 encoding and gaps; 2 morphology and observation support; 3 weak heterogeneous external weather mapping; 4 incremental skill above state, not a VPD curve; 5 null-compatible matched diagnostics, two independent pairs. S2/S3 carry scientific validation.
8. **Use:** developmental morphology; normalized allocation; observed daily peak; consecutive dated observations; relative developmental time; interpretive landmarks; exact subsequent-calendar-day observed growth; retrospectively reconstructed end-of-day covariates; conditional uncertainty; candidate-graph coverage.
9. **Avoid:** climate when meaning daily weather; physical velocity/acceleration for normalized differences; daily for gappy-sequence traits; information available operationally at day t; deterministic explanation; unexplained causal mismatch; population prevalence; two-by-two match.
10. **Limitations:** primary3.68% of events, many one-slice fires; complete-case CONUS-only selection; moderate endpoint associations; partial edge years; four region clusters; fixed-prediction bootstrap; retrospective fire reconstruction/grid timing; tied profiles; arbitrary pulse/caliper thresholds; missing active-edge fuel/terrain and management data. Small-size state strata have weak absolute prediction. See claim-specific caveats.
11. **Supplement only:** complete loadings/grids/penalties, null distributions, missingness, alternate cohorts/resolution, full coefficient/support checks, matching balance/k/metric/caliper, exact provenance and tests.
12. **Editorial work still needed:** tighten Introduction and Discussion for journal audience using the supplied `main-16.pdf`; consolidate Results without elevating weather to primary mechanism; preserve all caveats and the quantitative Abstract updates; confirm funding/contributions, target-journal reference style and a domain review of FIRED/gridMET timing. The reference's supplied title and author block are retained; `reference_manuscript_audit.md` reconciles its 27 pages without restoring superseded claims. No numerical reinterpretation or additional analysis is delegated to Prism. `final_claim_matrix.md`, `scientific_story.md`, and `final_report.md` are the controlling evidence summary.

Verdict: {summary['verdict']}.
"""
    (OUT/"PRISM_HANDOFF.md").write_text(handoff)
    (OUT/"README.md").write_text("# Scientific validation package\n\nStart with [final_report.md](final_report.md), [audit_report.md](audit_report.md), [final_claim_matrix.md](final_claim_matrix.md), and [PRISM_HANDOFF.md](PRISM_HANDOFF.md). Tables are generated by `scripts/validate_fire_vase_science.py`; prose and claims by `scripts/finalize_fire_vase_science.py`. The v2 candidate statistics remain separately identified. Run `PYTHONPATH=src:scripts MPLBACKEND=Agg MPLCONFIGDIR=/tmp/fire-vase-v2-mpl OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/validate_fire_vase_science.py`, then the normal figure pipeline with `--render-only`. The full normal pipeline also invokes this validation stage.\n\nNo new external observational data were ingested. Null simulations are labeled reference distributions. CSVs use fixed seeds and 12-digit serialization; the freeze manifest records hashes. Reused full v2 sensitivity grids are not mislabeled newly rerun.\n")


if __name__=="__main__":build()
