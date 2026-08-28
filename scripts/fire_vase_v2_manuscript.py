"""Generate a versioned, evidence-bound manuscript, audit and reproducibility record."""
from pathlib import Path
from functools import partial
import html
import json
import re
import numpy as np
import pandas as pd
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,PageBreak,Image
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib.pagesizes import letter
from fire_vase_v2_inputs import sha256


def mdtable(frame):
    cols=list(frame.columns)
    def fmt(x):
        if isinstance(x,(float,np.floating)):return "NA" if not np.isfinite(x) else f"{x:.3f}"
        return str(x)
    return "| "+" | ".join(cols)+" |\n| "+" | ".join(["---"]*len(cols))+" |\n"+"\n".join("| "+" | ".join(fmt(x) for x in row)+" |" for row in frame.itertuples(index=False,name=None))


def build(root):
    out=root/"analysis/v2"
    read=lambda name:pd.read_csv(out/f"{name}.csv")
    load=lambda name:json.loads((out/f"{name}.json").read_text())
    semantic,audit,transition=load("semantic_summary"),load("input_audit"),load("transition_audit")
    ev=read("pca_variance");boot=read("pca_bootstrap");null=read("null_tests")
    event=read("event_performance");state=read("state_performance");ci=read("state_uncertainty")
    matches=read("matching_sensitivity").query("k==10 and metric=='euclidean'").set_index("space")
    perm=read("matching_permutation");stability=read("pca_geographic_year_stability")
    n=int(event.cohort_n.max())
    features=pd.read_parquet(out/"event_analysis.parquet")
    sensitivity=read("morphospace_sensitivity").set_index("analysis")
    associations=read("adjusted_associations")
    precip=associations[(associations.predictor=="mean_precipitation_mm")&(associations.response=="pulse_count")].iloc[0]
    def val(model,response,kind="region_block",column="r2",table=event):
        return float(table[(table.alpha==1)&(table.kind==kind)&(table.predictor_set==model)&(table.response==response)][column].iloc[0])
    state_rows=state[(state.alpha==1)&state.kind.isin(["region_block","year_block","spatiotemporal"])&state.predictor_set.isin(["autoregressive","state_plus_weather","state_weather_interactions"])]
    state_table=state_rows[["kind","predictor_set","r2","delta_r2"]]
    event_responses=["front_loaded_fraction","late_growth_fraction","peak_timing","normalized_entropy","pulse_count","reactivation_count","shape_PC1_fold"]
    event_table=event[(event.alpha==1)&(event.kind=="region_block")&event.response.isin(event_responses)&event.predictor_set.isin(["core_means","core_plus_max","comprehensive_means","comprehensive_plus_max"])].pivot(index="response",columns="predictor_set",values="r2").reset_index()
    captions={
    1:"From daily growth to morphology. Four verified FIRED events connect observed daily area increments (blue bars), their reconstructed cumulative sum (gold), and VASE rings. Horizontal dates and vertical ring spacing use elapsed calendar time. The fourth event intentionally exposes observation gaps: shaded dates are unobserved, not zero-growth days. Radius is the square root of normalized cumulative area; catalog area is an external annotation, not the profile denominator. Source IDs, dates, counts, and areas appear in the panel and event audit table.",
    2:f"The developmental morphospace. (A) Occupancy of {semantic['primary_n']:,} histories with at least three consecutive dated observations, projected from 20 normalized growth-allocation bins. (B) Signed PCA loadings locate the relative-time contrasts defining the axes. (C) One- and two-observation events and gappy multi-observation events remain separate. (D) Ordinary mean-centered, standardized PCA explains {ev.cumulative_variance.iloc[4]:.1%} on five axes. (E) The same 4,000 real-event counts and durations support observed and randomized-allocation comparisons, with 100 realizations per null. Representative glyphs are real events, not inferred natural classes. Null results depend on the allocation model; they do not establish a unique physical wedge.",
    3:f"How weather maps onto morphology. (A-B) Median event-mean VPD and precipitation in occupied shape-space bins (at least five fires per bin); weather never defines the axes. (C) Unadjusted and partial rank associations for precipitation, after duration, observation count, catalog area, region and month adjustment in the broader complete multi-observation cohort. Region-resampling intervals hold the nuisance fit fixed. (D) Separate held-out R-squared values for individual responses, using core means plus maximum VPD on the identical {n:,}-event primary population. Bars are fire-resampling intervals for fixed held-out predictions. Region/year resampling, all nested predictor comparisons, every response and penalty are in the supplementary tables; Figure S1 shows the full regional comparison. Negative values are retained. PCA response preprocessing is fitted inside each training fold.",
    4:f"Developmental state and subsequent growth. The response is log(1 + next calendar-day area in km2), for {transition['shared_AR_cohort_rows']:,} transitions from {transition['shared_AR_cohort_fires']:,} fires sharing complete t-1, t and t+1 growth and day-t weather. (A) Mean, persistence, autoregressive state, weather-only, additive and interaction models. (B) Paired incremental R-squared above autoregressive state is the main comparison. (C) Active-day and final-centroid exposure comparisons use the same rows. (D) Seasonal checks use region-held-out predictions and fire-cluster uncertainty. Daily newly burned-area centroids use no final-event geometry. These are end-of-day covariates from retrospectively reconstructed observations, not an operational forecast or causal estimate. All fire slices remain together; spatiotemporal folds exclude both the test region and test year block from training.",
    5:"Convergent and divergent pathways. (A) Fraction assigned a unique nearest-neighbor partner under RMS standardized distance <= 0.5, exact region, season, duration and observation count, and catalog-area ratio <= 2. Each fire is used at most once in each matching analysis. (B) The fraction with other-space distance > 1 is compared with 100 conditional permutations within region, season, duration, count and log2-area strata. This threshold is a descriptive diagnostic, not a biological boundary. (C-D) Two independent examples nearest the median mismatch; no adversarial maximum is selected and no two-by-two match is claimed. Full dates, areas, counts, standardized distances, calipers, variables and IDs are in matched_examples.csv. Missing mechanistic covariates make these hypothesis-generating diagnostics, not causal evidence.",
    }
    manuscript=f"""# Fire VASE represents developmental morphology before meteorological exposure

Research manuscript draft | Second-generation methodological reanalysis | 28 August 2026

Authors and affiliations: to be confirmed.

## Abstract

Fire VASE converts dated growth observations into developmental morphology. We reanalyzed {semantic['n']:,} FIRED events without defining their structure by weather, final size, duration, or observation count. The primary analysis contains {semantic['primary_n']:,} events with at least three consecutive daily observations; shorter and gappy histories are separate sensitivity populations. A mean-centered PCA of normalized growth allocation explains {ev.explained_variance.iloc[0]:.1%} on its first axis and {ev.cumulative_variance.iloc[4]:.1%} on five axes. This compression is useful but is not uniquely biological: duration-preserving randomized histories also have low-dimensional structure. Event-level meteorological associations vary by response and validation block, and the earlier median held-out R-squared of 0.349 is withdrawn. Exact calendar-day state models use day-specific newly burned-area centroids and compare weather against an autoregressive baseline. Caliper-constrained, non-reused matched pairs quantify convergence and divergence without selecting extreme counterexamples. Morphology is the primary contribution; weather is an external demonstration, and mismatches motivate mechanistic hypotheses rather than causal attribution.

## Introduction

Final area and duration describe endpoints, not the allocation of growth over a fire's observed history. FIRED reconstructs fire events and their daily burned footprints from satellite burned-area records [1,2]. Fire VASE encodes these dated increments as a developmental object: elapsed time orders rings, and ring radius represents the square root of normalized cumulative area. The representation is retrospective. An observation gap is not a documented pause or a zero-growth day.

The scientific distinction is between a representation and an explanation. Shared morphological coordinates allow histories to be compared without weather entering the coordinate construction. Daily gridMET conditions [3] are the first external layer projected onto that representation. Associations do not establish which environmental or management process generated a trajectory.

## Results

### Corrected semantics and observation support

The pilot trait labeled peak growth was catalog area divided by catalog duration for all {semantic['n']:,} events. Replacing it with the largest observed daily increment changes {semantic['peak_changed_n']:,} event values. That is an observed daily peak, not an instantaneous or hourly maximum. Reconstructed and catalog totals differ by at most {semantic['max_area_relative_discrepancy']:.2g} in relative magnitude in these cached events. Normalizing entropy to the sum of observed increments fixes the implementation, but changes no current entropy value within numerical tolerance.

Of {audit['rows']:,} cached observations, {audit['one_day_transitions']:,} adjacent pairs are exactly one calendar day apart and {audit['longer_gaps']:,} span longer gaps. Missing and duplicate dates number {audit['missing_dates']} and {audit['duplicate_date_rows']}. There are {int(features.observation_count.eq(1).sum()):,} one-observation events, {int(features.observation_count.eq(2).sum()):,} two-observation events and {int((features.observation_count.ge(3)&~features.consecutive).sum()):,} gappy events with at least three observations. Only {semantic['primary_n']:,} events satisfy the primary consecutive-history criterion. This restriction favors short, continuously observed histories; it is a scientific scope limit, not a claim to represent every wildfire.

The old neighborhood branch assigned {semantic['old_multi_pulse_without_three_pulses']:,} fires to a multi-pulse label without the branch's nominal three detected pulses. The new rules require actual local maxima. Labels are interpretive landmarks and never inputs to PCA or discovered natural classes (Figures 1-2).

### A shared coordinate system, without a universal restricted-wedge claim

The primary 20-bin space explains {ev.explained_variance.iloc[0]:.1%}, {ev.explained_variance.iloc[1]:.1%}, and {ev.explained_variance.iloc[2]:.1%} on its first three axes. Its first-five-axis fraction is {ev.cumulative_variance.iloc[4]:.1%}, compared with 96.3% in the older mixed-scale, median-centered SVD. These numbers refer to different feature definitions and cohorts, not interchangeable estimates. Mean-centering the unchanged legacy feature space alone lowers its first-axis fraction from 81.0% to 72.9%. The v2 effective dimension (inverse squared variance-share sum) is {1/np.sum(ev.explained_variance**2):.2f}.

Bootstrap five-dimensional subspace overlap has median {boot.subspace_overlap.median():.3f} and 2.5-97.5 percentiles {boot.subspace_overlap.quantile(.025):.3f}-{boot.subspace_overlap.quantile(.975):.3f}. Axis/loadings and region/year checks are exported separately. Restricting to at least ten consecutive observations leaves {int(sensitivity.loc['consecutive_ge10','n']):,} fires and reduces five-axis coverage to {sensitivity.loc['consecutive_ge10','first_five']:.1%}; interpolation at 10 or 40 bins also changes compression. Thus dimensionality is not independent of temporal support or resolution.

On an identical 4,000-fire sample, observed five-axis coverage is {null.query("metric=='first_five'").observed.iloc[0]:.3f}. The corresponding mean is {null.query("metric=='first_five' and null=='within_fire_permutation'").null_mean.iloc[0]:.3f} after reordering each observed allocation, {null.query("metric=='first_five' and null=='dirichlet_1'").null_mean.iloc[0]:.3f} for uniform-simplex allocations, and {null.query("metric=='first_five' and null=='dirichlet_10'").null_mean.iloc[0]:.3f} for more even allocations. Observed ordering carries structure, but low dimensionality alone is not evidence for a physically restricted developmental universe. The previous universal wedge interpretation is removed.

### Weather is an external, response-dependent association

All primary event-model comparisons use the same {n:,} complete fires. Core event means exclude maximum VPD; explicit nested additions include maximum VPD in both core and comprehensive sets. Means, the 90th VPD quantile and fixed-threshold exceedance fractions are distinguished from record-length-dependent extremes. Duration and count are adjustment variables only; their inclusion cannot be used to claim prediction of duration itself.

Region-held-out R-squared values are shown below; other blocks, penalties, intervals, and every response remain in machine-readable tables. No cross-response median is the primary result.

{mdtable(event_table)}

The low regional recoverability of fold-trained shape PC1 ({val('core_plus_max','shape_PC1_fold'):.3f} for core plus maximum VPD) contrasts with the old 0.349 median across heterogeneous outcomes. Increased model size does not have a uniform benefit or cost across responses. Fixed-duration and fixed-count strata, length-only versus length-plus-maximum VPD models, and the broader gappy cohort test exposure opportunity explicitly. Maximum VPD is not retained as a deterministic explanation of shape (Figure 3).

Precipitation associations also change after adjustment. In the broader {int(precip.n):,} complete multi-observation fires, its raw rank correlation with detected pulses is {precip.raw_spearman:.3f} and its partial rank correlation is {precip.partial_rank:.3f} after duration, count, area, region and month adjustment. These values are descriptive, not causal effects. Longer records offer more opportunity to contain precipitation, large extremes and repeated local maxima. Weather completeness is geographically selective, especially outside gridMET's CONUS coverage; the inclusion table reports region, year, area, duration and morphology rather than assuming missingness is random.

### Subsequent growth is evaluated against known developmental state

The state analysis uses exactly dated one-day transitions and an autoregressive baseline containing current growth, previous-calendar-day growth, cumulative observed area and elapsed time. The common cohort contains {transition['shared_AR_cohort_rows']:,} transitions from {transition['shared_AR_cohort_fires']:,} fires. Requiring the previous calendar day for every comparator removes first observations and transitions following gaps equally from all models. Day-t weather is sampled at that day's newly burned-area centroid, not a final-fire centroid. Daily polygons are projected before centroid calculation and points outside the weather grid are excluded.

{mdtable(state_table)}

Incremental rather than total skill is the relevant weather comparison. Fire-, year- and region-resampling intervals and region, season, area and observation-quality sensitivity estimates accompany Figure 4. These intervals condition on fitted held-out predictions and do not include model-refitting or remote-sensing error. Interactions are statistical associations. End-of-day weather and reconstructed burned area should not be called information demonstrably available to a real-time system; satellite latency, retrospective FIRED event delineation and daily time-zone alignment remain unresolved.

### Representative convergence and divergence

Weather-space matching assigns unique acceptable partners to {matches.loc['weather','matched_fraction']:.1%} of eligible complete primary fires; morphology-space matching assigns {matches.loc['morphology','matched_fraction']:.1%}. The fraction with standardized other-space distance greater than one is {matches.loc['weather','mismatch_gt1_fraction']:.1%} among weather matches and {matches.loc['morphology','mismatch_gt1_fraction']:.1%} among morphology matches. This is an explicitly chosen diagnostic threshold, not a natural class boundary. Conditional permutation distributions and candidate-neighbor/metric sensitivity quantify how much mismatch is expected under nuisance-matched allocation.

The conditional permutation mean mismatch fractions are {perm.loc[perm.matching_space.eq('weather'),'mismatch_gt1_fraction'].mean():.1%} for weather matches and {perm.loc[perm.matching_space.eq('morphology'),'mismatch_gt1_fraction'].mean():.1%} for morphology matches. The observed fractions are compatible with these permutation distributions; the diagnostic does not establish excess mismatch beyond the declared reference. The displayed examples are nearest the median population mismatch, not maxima among a selected neighborhood. They are independent matched pairs, not a two-by-two arrangement asserting both row and column matches. The full pair table prints event IDs, dates, area, duration, count, region, season, predictor values, standardized distances, and calipers. Fuel continuity, terrain, active-edge heterogeneity, ignition context and suppression histories are plausible hypotheses, not explanations established by this diagnostic (Figure 5).

## Methods

### Data provenance and exclusions

All observations come from the materialized v0.1 FIRED/gridMET data lake; no synthetic fallback is permitted. Every cached daily increment is joined by event ID and date to the original daily GeoPackage and must agree within 1e-9 km2. Catalog areas must match the original event GeoPackage. The raw daily file contains {audit['raw_daily_rows']:,} rows, {audit['source_rows_absent_from_cache']:,} more than the lakehouse; unmatched rows and their catalog membership are enumerated in source_row_exclusions.csv. Cached dates span 2 November 2000 to 1 May 2021, despite the source filename. Missing dates, duplicate dates, nonfinite or negative increments, zero reconstructed totals and calendar gaps are explicitly checked. None is imputed as zero. Source and weather-cache hashes, code versions and output hashes are recorded.

### Growth and shape coordinates

For nonnegative daily increments g_i, reconstructed area is S = sum(g_i), distinct from catalog area A. Growth probabilities are p_i = g_i/S. Shannon entropy is -sum(p_i log p_i), with zero-probability terms omitted; normalized entropy divides by log(n) for n > 1. A positive one-slice history has entropy zero and no internal shape information. Zero-total or incomplete growth is undefined, not assigned high or low entropy.

In the primary consecutive cohort, each daily increment occupies one equal-width relative-time interval. Linear interpolation of cumulative mass at 21 fixed edges followed by differencing produces 20 nonnegative bin masses summing to one. It does not create additional observations. Gappy histories appear only in the explicitly observation-time sensitivity; their missing calendar days are not reconstructed. The primary PCA uses only these allocation bins. Catalog area, duration, count, absolute peak, mean growth and slenderness are excluded. Shape-oriented traits are projected afterward and provide a separate trait-only sensitivity, avoiding duplicated profile/trait weighting in the primary space.

PCA subtracts training means, divides by training standard deviations, and eigendecomposes the covariance matrix. Near-constant columns receive scale one. Loadings use a deterministic sign convention. Bootstrap comparisons optimally align five loading axes and also report subspace overlap; individual axes can rotate when eigenvalues are close. Nulls retain each sampled event's observation count and relative-time support: within-fire permutations preserve increments; symmetric Dirichlet allocations with concentration 1 and 10 test two alternative allocation universes. They are simulation controls, never presented as observed fires. Hull fill is convex-hull area after clipping scores to their 1st-99th percentile rectangle and rescaling to a unit box; occupancy is the fraction of a 20-by-20 score grid occupied. Neither is a formal proof of biological constraint. Empirical tails use (1 + exceedances)/(1 + replicates); multiple metrics are descriptive and not multiplicity-adjusted.

### Landmarks and pulses

Rules are evaluated in exported priority order. Invalid growth, one observation, two observations and gappy/undated histories are classified first. On eligible histories, at least two local maxima with prominence >= 20% of the observed peak define the multiple-detected-pulses landmark. Endpoints are eligible by padding the series with zeros; a flat plateau counts once. Reactivation requires a return above 25% of peak after at least two consecutively observed subthreshold days. Late peak requires normalized peak-bin midpoint >= 2/3; front-loaded taper requires >= 75% area by relative time 0.5 and final/peak growth <= 0.35. All others are distributed growth. These thresholds are declared interpretive rules, not validated ecological classes.

### Weather, prediction and uncertainty

Daily gridMET variables comprise maximum/minimum temperature, VPD, wind speed, precipitation, relative/specific humidity, 100/1000-hour fuel-moisture indices, energy release component, burning index, reference/potential evapotranspiration and solar radiation. The latter indices are modeled products, not direct measurements of local fuel loads. Event means use all observed dates and require complete values for every variable on every observed row. VPD exceedance is > 2 kPa; wet fraction is precipitation > 0.1 mm/day. Quantiles and fractions do not monotonically increase by construction with record length, but still have record-length-dependent sampling uncertainty. No event-sample anomaly is called climatology.

Ridge models use penalties 0.01, 1 and 100 on standardized predictors with an unpenalized intercept. Penalty 1 is prespecified, not chosen by test performance; all penalties are reported. Training-only scaling is mandatory. When predicting shape PCs, the PCA is refitted inside each training fold, scores are scaled by training score standard deviation, and pooled evaluation subtracts each held-out fold's observed score mean from both target and prediction to prevent arbitrary fold offsets inflating the denominator. Axis sign conventions are local; fold-level values and loading variation are authoritative. Outcomes already present as predictors are explicitly excluded from predictive reporting.

Validation leaves out each coarse geographic region, contiguous five-year blocks beginning in 2000 (last block 2020-2021), or each region-by-year-block intersection. For the crossed scheme, training excludes the entire test region AND the entire test year block, a stricter transfer task than hashing region-year identifiers. All rows of a fire share its ignition-year block. Random-fire hashing is diagnostic only. Models share a complete cohort determined by the union of requested predictors and outcomes. Held-out R-squared uses all valid predictions and retains negatives; the reference mean is trained, not calculated from test outcomes. Paired fire/year/region cluster resampling of fixed out-of-fold errors uses 200 draws; few regional clusters limit precision. No causal interpretation follows from predictive improvement.

### Matching and reproducibility

Matching uses core event means in weather space or 20 allocation bins in morphology space, standardized across the declared complete primary matching cohort. Candidate edges are the k nearest neighbors within exact region, season, duration and count strata. Edges exceeding an area ratio of two or RMS z-distance 0.5 are rejected. Remaining edges are sorted by match distance and ID order, and selected greedily without reusing either member; mismatch outcomes do not influence selection. This is disjoint nearest-neighbor graph matching, not globally optimal matching. Both the fraction with an eligible candidate and the fraction actually paired are exported. Sensitivities use k = 1, 5, 10 and 20 and Euclidean/RMS versus cityblock/mean-absolute standardized distance. Nulls permute the other-space vectors within exact nuisance strata plus floor(log2(area)); singleton strata cannot randomize and constrain the reference. Models and matching remain observational.

## Limitations and conclusions

Fire VASE supplies a transparent representation and a shared coordinate system, not a universal set of fire types. Dimensionality depends on observation support, resolution and the normalized-curve constraints themselves. The strict primary cohort is small relative to the source population and does not establish transfer to long or intermittently observed fires. Weather is a useful external layer, but the earlier 0.349 median was not a defensible general headline. Duration, count and maxima must remain disentangled, especially for pulse and reactivation opportunity.

Day-specific geometry removes one identifiable spatial look-ahead pathway, but this does not establish operational availability of reconstructed fire histories or causal weather effects. Nearest-cell daily exposures miss spatial heterogeneity, directional winds and active-edge conditions. GridMET nominal days use Mountain Standard Time; FIRED dates and satellite burn-date uncertainty may not align perfectly. Fuel load/continuity, terrain and slope, ignition, suppression and independent operational validation are not included. Source land-cover labels alone cannot substitute for those mechanisms. Matched mismatches generate questions for those next layers; they are not unexplained residuals that by themselves prove contingency or causal control.

## Supplementary inventory

Figure S1 covers complete regional model grids, alternative feature/cohort spaces, bootstrap axes, missingness, matching sensitivity and penalty sensitivity. Machine-readable tables include PCA loadings/variance, all bootstrap loadings, year/region stability, null realizations/tests, every landmark rule and branch count, every event's semantic audit, source-row exclusions, weather inclusion/exclusion, predictor dictionaries, complete model grids and folds, all preprocessing parameters, cluster intervals, fixed-length strata, gappy-cohort sensitivity, legacy-outcome cohort comparisons, spatial-exposure/state-subgroup sensitivities, complete unique pairs, representative examples, matching nulls and output manifests. Large row-level tables are compressed CSV or regenerable Parquet; the latter remain local and ignored by Git.

## References and reuse

[1] Balch et al. (2020). FIRED (Fire Events Delineation): An Open, Flexible Algorithm and Database of US Fire Events Derived from the MODIS Burned Area Product (2001-2019). Remote Sensing 12, 3498. https://doi.org/10.3390/rs12213498

[2] Country-level fire perimeter datasets (2001-2021). Scientific Data (2022). https://doi.org/10.1038/s41597-022-01572-3

[3] Climatology Lab. gridMET product documentation. https://www.climatologylab.org/gridmet.html (accessed 28 August 2026). Daily meteorological data, approximately 4-km resolution; gridMET is public-domain/CC0 as described by the provider. Upstream FIRED reuse and citation requirements remain attached to the source package; this reanalysis does not relicense the data.

## AI assistance and verification

Codex assisted with code, methodological auditing, statistical regeneration, tests, figures and manuscript drafting in this repository. Results were computed from the identified real inputs. Human scientific review remains necessary, especially for estimand choice, remote-sensing uncertainty and ecological interpretation. The audit and verification records disclose limitations rather than substituting computational reproduction for scientific validation.
"""
    dest=root/"docs/manuscripts/fire_vase_developmental_morphology/manuscript_v2.md"
    dest.write_text(manuscript)
    legends="\n\n".join(f"## Figure {i}\n\n{caption}" for i,caption in captions.items())
    (root/"figures/v2/figure_legends.md").write_text("# V2 figure legends\n\n"+legends)
    render_pdf(manuscript,captions,root)
    audit_rows=[
        ["Peak versus mean","Confirmed",f"{semantic['peak_changed_n']} changed peaks","Catalog area/duration called peak","Maximum observed daily increment","Scale-free PCA unaffected by absolute units; legacy mixed-space claims replaced"],
        ["Entropy probabilities","Implementation confirmed; current values unchanged","Normalize by observed increment sum","Catalog-based denominator","0 changed within tolerance","Incomplete-reconstruction failure mode fixed; observed entropy values survive"],
        ["Pulse branch","Confirmed",f"{semantic['old_multi_pulse_without_three_pulses']} count-only assignments","Count >=6 could imply multi-pulse","Actual prominent local maxima; branch table exported","Natural-class interpretation removed"],
        ["Date transitions","Confirmed",f"{audit['longer_gaps']} longer gaps","313726 modeled adjacent rows","Exact calendar transitions; shared AR cohort","Old next-day interpretation removed"],
        ["PCA centering and scale","Confirmed","Mean-centered profile-only PCA","PC1 .810; first five .963",f"PC1 {ev.explained_variance.iloc[0]:.6f}; first five {ev.cumulative_variance.iloc[4]:.6f}","Compression survives, universal restricted wedge does not"],
        ["Weather predictor/cohort comparison","Confirmed","Nested sets; one cohort; fixed-length sensitivities","Median .349348",f"Response-specific; PC1 region/core+max {val('core_plus_max','shape_PC1_fold'):.6f}","Median headline withdrawn; heterogeneous associations remain"],
        ["Final-geometry state leakage","Confirmed","Day-t growth-centroid extraction; same-row exposure comparison","Final-event centroid; no calendar-gap filter",f"{transition['shared_AR_cohort_rows']} shared AR transitions","Prospective covariate design, but operational availability unresolved"],
        ["Adversarial matching","Confirmed","Greedy disjoint nearest pairs with calipers and conditional permutations","Maximum other-space discordance among neighbors",f"Weather matched {matches.loc['weather','matched_fraction']:.6f}; morphology matched {matches.loc['morphology','matched_fraction']:.6f}","Representative mismatch survives only as a diagnostic; no causal mechanism inferred"],
    ]
    audit_frame=pd.DataFrame(audit_rows,columns=["Issue","Finding","Correction/evidence","Old","New","Scientific consequence"])
    audit_frame.to_csv(out/"issue_audit.csv",index=False)
    report=f"""# Fire VASE v2 audit

Legacy values were reproduced to <1e-15 in archived event/state model tables and all five legacy figures were regenerated before corrections. Reproduction is not methodological validation.

{mdtable(audit_frame)}

## Important remaining limitations

- The primary population is only {semantic['primary_n']:,} consecutive histories, {n:,} weather-complete. Intermittent observations are not zero growth and are analyzed only under explicitly separate assumptions.
- Normalized-profile geometry and observation count themselves induce dimensionality; null conclusions are model-dependent. No universal wedge claim survives.
- Weather uncertainty intervals resample fixed held-out errors, not the complete training/fitting process. Four main CONUS region clusters and small state/season subsets limit precision.
- Day-specific geometry is available and used; FIRED's retrospective reconstruction and gridMET daily timing still prevent an operational-availability claim.
- Matching is a declared greedy disjoint procedure, not optimal allocation. Conditional permutations contain sparse/singleton strata. No two-by-two display or causal attribution is claimed.
- Complete model grids include duration as an external outcome, but configurations containing duration as a predictor are marked excluded_known_outcome and cannot count as predictive skill.

## Evidence and commands

Inputs and outputs are indexed by run_manifest.json, input_hashes.json, day_t_weather_manifest.json and publication_manifest.json. Code, configuration, seeds, rows and exclusions accompany the statistics. Execute the normal pipeline:

```sh
PYTHONPATH=src:scripts OPENBLAS_NUM_THREADS=1 MPLCONFIGDIR=/tmp/fire-vase-v2-mpl .venv/bin/python manuscript_figures/00_run_all.py --generation v2 --data-lake data_lake/fire-vase-data-lake-v0.1
.venv/bin/python -m pytest tests/test_analysis_v2.py -q
```

The original source tables and prior manuscript/figures remain unchanged. The old standalone analysis scripts are explicitly legacy; only the v2 normal pipeline produces current conclusions. No external data were downloaded for analysis.
"""
    (out/"audit_report.md").write_text(report)
    artifact_paths=[dest,root/"output/pdf/fire_vase_v2_manuscript.pdf",out/"issue_audit.csv",out/"audit_report.md"]
    artifact_paths+=list((root/"figures/v2").glob("*"))
    manifest={"artifacts":{str(p.relative_to(root)):sha256(p) for p in sorted(artifact_paths) if p.is_file()},
        "statistics_hashes":{p.name:sha256(p) for p in sorted(out.glob("*.csv"))},
        "figure_code_sha256":sha256(root/"scripts/figures/make_figures_v2.py"),
        "manuscript_code_sha256":sha256(Path(__file__))}
    (out/"publication_manifest.json").write_text(json.dumps(manifest,indent=2))


def render_pdf(markdown,captions,root):
    path=root/"output/pdf/fire_vase_v2_manuscript.pdf"
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name="V2Body",fontName="Times-Roman",fontSize=10.5,leading=14,spaceAfter=7))
    styles.add(ParagraphStyle(name="V2Caption",fontName="Helvetica",fontSize=8.5,leading=11,spaceAfter=6))
    story=[]
    # Tables remain complete in source/CSV; PDF renders each table as concise rows.
    for block in markdown.split("\n\n"):
        block=block.strip()
        if not block:continue
        if block.startswith("#"):
            level=len(block)-len(block.lstrip("#"))
            style=styles["Title" if level==1 else "Heading1" if level==2 else "Heading2"]
            story.append(Paragraph(html.escape(block.lstrip("# ")),style))
        elif block.startswith("|"):
            lines=block.splitlines();headers=[v.strip() for v in lines[0].strip("|").split("|")]
            for line in lines[2:]:
                values=[v.strip() for v in line.strip("|").split("|")]
                text="; ".join(f"{h}: {v}" for h,v in zip(headers,values))
                story.append(Paragraph(html.escape(text),styles["V2Caption"]))
            story.append(Spacer(1,6))
        else:
            story.append(Paragraph(html.escape(block.replace("\n"," ")),styles["V2Body"]))
    for i,caption in captions.items():
        story.append(PageBreak());story.append(Paragraph(f"Figure {i}",styles["Heading1"]))
        img=Image(str(root/f"figures/v2/Figure_{i}.png"));w=480;h=img.imageHeight*w/img.imageWidth
        story.append(Image(str(root/f"figures/v2/Figure_{i}.png"),width=w,height=h))
        story.append(Paragraph(html.escape(caption),styles["V2Caption"]))
    story.append(PageBreak());story.append(Paragraph("Supplementary Figure S1",styles["Heading1"]))
    img=Image(str(root/"figures/v2/Supplementary_Figure_1.png"));w=480
    story.append(Image(str(root/"figures/v2/Supplementary_Figure_1.png"),width=w,height=img.imageHeight*w/img.imageWidth))
    story.append(Paragraph("Complete tabular results are listed in the supplementary inventory and publication manifest.",styles["V2Caption"]))
    def footer(canvas,doc):
        canvas.setFont("Helvetica",8);canvas.drawString(60,30,"Fire VASE | v2 methodological reanalysis | 28 August 2026")
        canvas.drawRightString(552,30,str(doc.page))
    doc=SimpleDocTemplate(str(path),pagesize=letter,rightMargin=60,leftMargin=60,topMargin=48,bottomMargin=50,
        title="Fire VASE represents developmental morphology before meteorological exposure",author="Fire VASE",invariant=1)
    doc.build(story,onFirstPage=footer,onLaterPages=footer,canvasmaker=partial(Canvas,invariant=1))
