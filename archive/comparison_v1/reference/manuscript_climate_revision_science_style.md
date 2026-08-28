# Climate Organizes but Does Not Determine Wildfire Development

Authors: Author names and affiliations to be added.

Correspondence: Corresponding author email to be added.

## One-Sentence Summary

Climate shifts wildfire developmental opportunity without prescribing a single developmental path.

## Abstract

Wildfire risk is commonly summarized by final burned area, duration, or spread rate, but fires can reach similar endpoints through distinct growth histories. We introduce Fire VASE, a developmental representation that converts daily FIRED events into comparable profiles and projects gridMET climate onto them. Across 278,569 U.S. events, 237,235 have complete centroid climate exposure from 2000 to 2021. Fire histories occupy recurring gradients of timing, persistence, pulse structure, reactivation, and termination. Hot, dry, low-fuel-moisture, and high-fire-danger conditions shift the prevalence of these forms, but blocked prediction and matched examples show that centroid climate does not uniquely determine them. Fire VASE reframes climate as shifting developmental opportunity: the growth histories a fire is more or less likely to follow.

## Introduction

Climate is a first-order constraint on wildfire activity, especially through warming, drying, and rising atmospheric demand (1-3). Recent work has also sharpened attention on fire growth itself: the fastest-growing events account for disproportionate damage, and daily expansion can matter as much as final area for hazard and response (4). Yet continental analyses still commonly summarize fires by final burned area, duration, or average spread rate. Those summaries are indispensable, but they flatten development. A fire can reach the same final size through an early burst, steady accumulation, late surge, repeated pulses, or reactivation after quiescence.

Fire VASE was designed to preserve that missing developmental information. It maps developmental time to vertical position and cumulative burned area to ring width, producing a comparable object for every observed daily fire history. The underlying fire histories come from MODIS burned-area event delineation and FIRED perimeter products (5-7). Daily climate exposure comes from gridMET, a high-resolution gridded meteorological data set for ecological applications across the conterminous United States (8). Conceptually, Fire VASE draws from morphometrics, functional data analysis, and dimension reduction: it represents a history as a shape, compares shapes in a shared coordinate system, and then asks what external conditions shift the distribution of those shapes (9-11).

Here we ask how climate organizes wildfire developmental opportunity, defined as the distribution of growth histories made more or less likely under a given set of conditions. The paper makes two separable contributions. First, it defines a developmental representation that is estimated from fire histories before climate is considered. Second, it projects a comprehensive but centroid-based daily climate table onto that representation. The revised population table includes daily centroid maximum temperature, minimum temperature, vapor pressure deficit (VPD), wind speed, precipitation, relative humidity, specific humidity, 100-hour and 1000-hour fuel moisture, energy release component, burning index, reference evapotranspiration, potential evapotranspiration, and solar radiation for 237,235 climate-complete fires. Perimeter, active-burned-area, and perimeter-extension attribution remain a separate exposure product and are treated according to their actual coverage. The contribution is not a deterministic spread-rate predictor; it is a coordinate system for asking how climate shifts the probability of developmental forms and where centroid climate explanation reaches its limits.

## Results

### Fire VASE preserves developmental differences hidden by final outcomes

Figure 1 establishes the problem. Real fires with simple final summaries can have sharply different daily growth histories. Some accumulate most area early, others grow steadily, others surge late, and others develop through multiple pulses. The corresponding VASEs preserve these temporal differences in one visual grammar. This is the starting point for the climate analysis: climate should be evaluated against the whole developmental history, not only against final size or duration.

### Wildfire histories vary along recurring developmental gradients

Figure 2 shows that observed fires occupy recurring developmental neighborhoods, but those neighborhoods lie along continuous gradients rather than forming isolated types. Labels such as skinny persistent, compact steady, late surge, front-loaded plateau, and multi-pulse complex are descriptive landmarks. The high prevalence of the single-flash neighborhood reflects the short duration of many mapped events, not a claim that most fires share a single mechanism. The quantitative result is a coordinate system for timing, persistence, concentration of growth, pulse structure, reactivation, and termination. Because this space is built from fire histories alone, climate can be projected afterward as an external correlate rather than baked into the axes.

### Climate shifts the probability of developmental forms

Figure 3 projects climate onto Fire VASE space. Climate-colored morphospace maps show that maximum temperature, VPD, fuel moisture, and wind emphasize different portions of the developmental space, while composite VASEs show that low-, middle-, and high-VPD fires differ in where normalized growth is allocated through developmental time. Developmental-neighborhood prevalence shifts across VPD groups, and effect-size summaries show that maximum temperature, VPD, relative humidity, fuel moisture, precipitation, and fire-danger indices relate to different developmental responses. These associations are coherent with the broader literature linking warming, aridity, and fuel dryness to fire activity (1-3), but the VASE analysis resolves the outcome as a developmental distribution rather than a single aggregate burned-area response.

The predictive limit is equally important. In conservative blocked validation, which summarizes transfer across year, region, and region-year blocks rather than random-fire splits alone, the best transferable event-level representation is core event means, with median held-out R2 of 0.349 across developmental responses. Region-season anomaly diagnostics do not outperform core event means, comprehensive event means do not outperform core event means, and temporally resolved exposure summaries do not outperform core event means in the median blocked comparison. This does not mean that humidity, fuel moisture, precipitation, or fire danger are unimportant. It means that, in these correlated daily centroid summaries and linear blocked baselines, adding more climate descriptors did not improve transfer beyond the core atmospheric variables. Modest blocked R2 is therefore a bound on deterministic prediction, not a rejection of the distributional result. The claim is probabilistic: climate redistributes fires across developmental possibilities. It does not assign a unique developmental form.

### Developmental state changes how climate is expressed through growth

The same daily climate exposure can occur before a fire begins rapid expansion, during the largest growth episode, or after growth has already tapered. We therefore modeled next-day growth as a function of climate, current developmental state, and their interaction. To avoid leakage, state was defined only from information available at day t: elapsed day, current daily growth, current cumulative area, and current acceleration. Final duration, final area fraction, and future VASE coordinates were not used.

State-containing models outperform climate-only baselines for next-day growth (Fig. 4). The best conservative state model is core climate-state interaction, with median held-out R2 of 0.353. Core climate-state interactions survive the predeclared blocked-transfer margin. Because state predictors include current growth and acceleration, this gain is partly autoregressive. The result shows that recent fire state conditions the interpretation of near-term climate-growth associations; it does not show that the model has identified causal state-dependent climate control.

### Climate organizes opportunity without uniquely determining outcome

Figure 5 asks where climate explanation fails. Pairs of fires with similar limited centroid summaries can have divergent VASE morphologies, and pairs with similar morphology can occur under contrasting climate pathways. These pairs are not matched on complete weather trajectories, active-edge exposure, or within-perimeter heterogeneity. That limitation is the point: mismatches define the scientific boundary of the current analysis. Climate describes opportunity. Which opportunity is realized likely also depends on active-edge exposure, local fuels, topography, vegetation, suppression, ignition context, human access, wind direction, and gusts. Prior work shows that human ignitions reshape the spatial and seasonal fire niche (12), active-fire studies show why daily fire progression can require spatially explicit growth tracking (13), and environmental controls such as fuels, vegetation, and topography shape fire occurrence, spread, boundaries, and transferability across landscapes (14-16). Those factors belong in the next version of the database, not in an overclaim from centroid climate alone.

## Discussion

Fire VASE makes a common wildfire abstraction visible: final size is an endpoint, not a life history. Once the life history is represented directly, climate appears as a probabilistic shift in developmental opportunity. Hot, dry, high-VPD, low-fuel-moisture, and high-fire-danger conditions shift where fires fall in developmental space and when growth is allocated. But even expanded centroid climate does not collapse wildfire development into a deterministic sequence.

This framing changes how climate-fire relationships should be read. Event means are informative but blunt. Daily exposure, extreme-day fractions, and developmental timing sharpen interpretation, yet transfer across years and regions remains weak. Expanded centroid climate adds moisture, fuel, and fire-danger context, but it does not remove the need for spatially resolved exposure. Scaling perimeter and active-edge attribution, adding independent local climate normals, and integrating topography, vegetation, suppression, ignition context, wind direction, and gusts are the next necessary steps.

The present analyses are associational baselines. They do not isolate causal climate effects, suppression decisions, or fuel continuity. They also use daily centroid climate as the main population exposure, so they can miss within-perimeter heterogeneity, directional wind effects, and the climate experienced by newly burning edges. A stronger mechanistic account would need complete active-edge and newly burned-area climate, local climate normals, topography, vegetation, suppression, ignition context, wind direction, and gusts. Fire VASE supplies the coordinate system for that next layer of work: it shows that wildfire development occupies recurring forms, that climate shifts the probability of those forms, and that the realized path remains contingent on fire state and landscape context.

## Materials and Methods

### Reproducible data package and execution environment

Analyses were run from the Fire VASE repository using the versioned data-lake package defined in config/data_release.yml. The data lake contains the upstream FIRED caches, cached gridMET NetCDF files, Parquet lakehouse tables, derived analysis tables, figure inputs, schemas, manifests, and rendered manuscript products. Collaborators can reproduce the manuscript figures from a restored data lake with the command uv run python manuscript_figures/00_run_all.py --data-lake PATH_TO_FIRE_VASE_DATA_LAKE; individual numbered scripts in manuscript_figures/ regenerate each main figure and the validation supplement. The complete rebuild order from upstream source caches is recorded in config/data_release.yml and uses scripts/cache_gridmet_years.py, scripts/fire_vase_lakehouse_pilot.py, scripts/fire_vase_build_climate_tables.py, scripts/fire_vase_build_perimeter_climate_tables.py, scripts/fire_vase_developmental_morphology_analysis.py, and scripts/fire_vase_climate_revision.py. Random sampling, model folds, representative-fire selection, and figure examples use fixed seeds declared in those scripts, primarily 20260722.

### Fire source data and VASE slice construction

Fire histories were derived from the FIRED CONUS plus Alaska event and daily perimeter caches. The event table supplies fire identity, ignition and final dates, event duration, final burned area, and event geometry. The daily table supplies event id, date, event day, daily newly burned area (dy_ar_km2), and cumulative burned area (tot_ar_km2). Event centroids were calculated from event geometries after projection to EPSG:5070 and then transformed back to longitude and latitude for climate extraction. Daily records were sorted by fire id, date, and event day, and a zero-based slice_index was assigned within each fire.

The canonical daily VASE table is scratch/fire_vase_run_full/tables/vase_slices.parquet. For each fire and slice, daily ring area was defined as the nonnegative daily burned-area increment, ring_area_km2 = max(dy_ar_km2, 0). Cumulative area was recomputed as the cumulative sum of daily ring area within fire. VASE width was normalized as the square root of cumulative area divided by final cumulative area, so width is proportional to radius rather than area and ranges from 0 to 1 for fires with positive mapped area. This table covers 278,569 events and 626,102 daily slices from 2 November 2000 to 1 May 2021. Companion tables include fire_catalog.parquet for cache keys and product versions, fire_traits.parquet for event-level area, duration, region, and peak-growth summaries, and processing manifest and failure tables for reproducibility and triage. Schema contracts for these products are stored in schemas/*.schema.json.

### Daily centroid climate attribution

Population climate attribution used cached daily gridMET NetCDF files and nearest-grid-cell extraction at the event centroid for each daily VASE slice. The extraction code opens each annual gridMET file with xarray, normalizes the time dimension to time when needed, selects by daily date, centroid latitude, and centroid longitude with nearest-neighbor matching, and converts maximum and minimum temperature from Kelvin to degrees C. The population centroid table includes maximum temperature, minimum temperature, VPD, wind speed, precipitation, maximum and minimum relative humidity, specific humidity, 100-hour and 1000-hour fuel moisture, energy release component, burning index, reference evapotranspiration, potential evapotranspiration, and solar radiation. Wind-present indicators use a 0.1 m s-1 threshold. A slice is marked climate-available only when all requested cached variables for that run are nonmissing; otherwise the failure reason is recorded as outside gridMET coverage or missing grid value. Complete daily centroid climate values were available for 237,235 fires.

Perimeter, active-burned-area, cumulative-burned-area, and perimeter-extension climate summaries were built as a separate companion product, vase_climate_exposures.parquet, with exposure zones and extension distances recorded in the table. Those products are retained as pilot or supplemental exposure products in this draft. The main population inference uses centroid climate because that is the complete continental-scale attribution currently available.

### Developmental feature construction

Developmental morphology was computed from the VASE slice and fire trait tables before climate was used for inference. For each fire, relative developmental time was defined from the ordered slice sequence, using a single midpoint for one-slice fires and a 0 to 1 scale for multi-slice fires. The feature set includes final area, duration, peak daily growth, observation count, peak timing, front-loaded growth fraction, late-growth fraction, terminal taper fraction, growth entropy, developmental velocity, developmental acceleration, pulse count, reactivation count, slenderness, and interpolated width and growth profiles.

Pulse count is the number of starts of major-growth periods in the daily growth sequence. A day is considered part of a major-growth period when daily growth exceeds the larger of the within-fire 75th percentile of daily growth, 25% of maximum daily growth, and a small positive floor. Reactivation count is pulse count minus one, bounded below by zero. Front-loaded growth is the cumulative growth fraction at relative developmental time 0.5. Late-growth fraction is the sum of daily growth fractions after relative time 0.75. Terminal taper is final-day daily growth divided by peak daily growth. Growth entropy is Shannon entropy of positive daily growth fractions normalized by the log of the number of observed slices. Developmental velocity and acceleration are mean absolute first and second differences of normalized VASE width. Width and growth profiles were linearly interpolated to 11 common developmental-time points, width_p00 to width_p10 and growth_p00 to growth_p10.

### Morphospace and descriptive neighborhoods

The Fire VASE morphospace was fit from geometry and developmental features only. Before principal component analysis, final area, duration, peak growth, and slenderness were log transformed; all selected features were converted to numeric values, missing values were imputed with the feature median, and features were scaled by their standard deviation. Principal components were computed with singular value decomposition, and the first five scores were retained as morph_pc1 to morph_pc5. Climate variables were attached only after this geometry-first coordinate system was defined.

Descriptive developmental neighborhoods are landmarks rather than taxonomic classes. They were assigned by transparent rules using observation count, duration, final area, pulse count, peak timing, front-loaded fraction, terminal taper, and dataset quantiles. One-slice or one-day fires are labeled single flash. Other labels include skinny persistent, broad rapid, multi-pulse complex, late surge, front-loaded plateau, and compact steady. These labels are used for figure interpretation and prevalence summaries; statistical models use the continuous developmental responses and morphospace coordinates.

### Climate summaries and developmental response variables

Event-level climate summaries were derived from daily climate-complete slices. For each gridMET variable, summaries include event mean, daily minimum, daily maximum, early/middle/late developmental-time means, and a region-month fire-season anomaly diagnostic. Early, middle, and late bins divide relative developmental time into thirds. Extreme-day fractions were computed as follows: hot days, high-VPD days, windy days, and high-ERC days use the 90th percentile of the fire-slice population; dry 1000-hour fuel-moisture days use the 10th percentile; wet days have precipitation greater than zero. The region-month anomaly is the daily value minus the median value for fires in the same broad region and calendar month. It is a fire-population contrast, not an independent climatological normal.

Developmental response variables were defined before model fitting and separated into absolute-scale outcomes, shape-normalized responses, and time-varying state variables. Event-level responses are front-loaded fraction, late-growth fraction, terminal taper fraction, growth entropy, pulse count, reactivation count, peak timing, duration, final area, and the first VASE morphospace axis. Duration, final area, pulse count, and reactivation count are modeled on a log(1 + x) scale. State-dependent slice models use next-day daily growth, log(1 + km2), as the response.

### Event-level climate models and validation

Event-level models are ridge-regularized linear baselines with penalty alpha equal to 1.0. The predictor sets are core event means, moisture and humidity, fire danger and energy, comprehensive event means, region-season anomalies, extreme days, and time-resolved exposure. Core event means include event-mean maximum temperature, minimum temperature, VPD, wind speed, and available maximum VPD summaries. Moisture and humidity include precipitation, relative humidity, specific humidity, and 100-hour and 1000-hour fuel moisture means. Fire danger and energy include energy release component, burning index, reference evapotranspiration, potential evapotranspiration, and solar radiation. Time-resolved exposure combines early, middle, and late summaries for core climate and selected moisture or fire-danger variables with extreme-day fractions.

Predictors are standardized inside each training fold and then applied to the corresponding held-out fold. Validation uses four fold definitions. Random-fire folds are deterministic hash folds and are treated as a diagnostic. Year-block folds group fires into broad time blocks. Region-block folds hold out broad geographic regions. Region-year hash folds hold out hashed region-year combinations. Reported conservative performance summarizes the blocked year, region, and region-year tests rather than the random-fire diagnostic. Held-out R2 is computed against the held-out mean baseline after concatenating fold predictions.

### State-dependent next-day growth models

State-dependent models ask whether the interpretation of daily climate depends on information available by day t. The model table is built from climate-available daily slices, sorted by fire and slice index. The response is next-day ring area, log(1 + km2), obtained by shifting ring_area_km2 one slice forward within fire. Leakage-safe state predictors are elapsed day, current daily growth log(1 + km2), current cumulative area log(1 + km2), and current growth acceleration, defined as current daily growth minus previous daily growth. Final duration, final area fraction, future growth, and VASE coordinates are not used as state predictors.

State model predictor sets are core climate only, expanded climate only, state only, core climate plus state, expanded climate plus state, and core climate-state interaction. Interaction terms multiply each core climate variable by elapsed day, current growth, and current cumulative area. These models use the same ridge estimator, within-fold standardization, and blocked validation definitions as the event-level models. Because current growth, cumulative area, and acceleration are autoregressive state variables, these analyses are associational baselines and should not be interpreted as causal estimates of climate effects.

### Composite VASEs, matched examples, and figures

Observed VASE glyphs show individual fires. Composite VASEs summarize groups by interpolating each fire's normalized width to 41 common developmental-time points and drawing the median profile with an interquartile shell. Climate-conditioned composite VASEs in the main figures use low, middle, and high terciles of event-mean daily centroid VPD among climate-complete fires. Representative fires and morphospace examples are selected deterministically from the feature table with fixed random seeds and documented scoring rules. Mismatch examples compare standardized centroid climate distances and standardized morphospace distances among sampled climate-complete fires; they illustrate limits of centroid climate attribution rather than exhaustive causal matching.

All main figures are generated from the data lake by numbered scripts in manuscript_figures/, which call the shared figure code in scripts/figures/. Validation summaries cached under analysis/claim_audit_stats/, analysis/climate_revision_stats/, and figures/main/derived_stats/ can be reused for fast rendering or recomputed with --force-validation. Figure outputs are written as PDF, PNG, and SVG so collaborators can inspect both publication and editable formats.

### Reproducibility limits

The current population inference is limited by the exposure products available at manuscript scale. Daily centroid climate does not capture within-perimeter heterogeneity, active-edge weather, directional wind exposure, gusts, fuels, vegetation, topography, suppression, ignition context, or independent local climate normals. The region-month anomaly diagnostic should therefore be read as a within-fire-population contrast. Perimeter and active-edge attribution products are included in the data lake as the next exposure layer, but they are not the basis for the main climate claim in this draft. These limits motivate the interpretation used throughout the manuscript: climate shifts developmental opportunity but does not uniquely determine the realized developmental path.

## References and Notes

1. Westerling AL, Hidalgo HG, Cayan DR, Swetnam TW. Warming and earlier spring increase western U.S. forest wildfire activity. Science. 2006;313:940-943. doi:10.1126/science.1128834.

2. Abatzoglou JT, Williams AP. Impact of anthropogenic climate change on wildfire across western US forests. Proceedings of the National Academy of Sciences. 2016;113:11770-11775. doi:10.1073/pnas.1607171113.

3. Williams AP, Abatzoglou JT, Gershunov A, Guzman-Morales J, Bishop DA, Balch JK, Lettenmaier DP. Observed impacts of anthropogenic climate change on wildfire in California. Earth's Future. 2019;7:892-910. doi:10.1029/2019EF001210.

4. Balch JK, Iglesias V, Mahood AL, Cook MC, Amaral C, DeCastro A, Leyk S, McIntosh TL, Nagy RC, St. Denis L, Tuff T, Verleye E, Williams AP, Kolden CA. The fastest-growing and most destructive fires in the US (2001 to 2020). Science. 2024;386:425-431. doi:10.1126/science.adk5737.

5. Giglio L, Boschetti L, Roy DP, Humber ML, Justice CO. The Collection 6 MODIS burned area mapping algorithm and product. Remote Sensing of Environment. 2018;217:72-85. doi:10.1016/j.rse.2018.08.005.

6. Balch JK, St. Denis LA, Mahood AL, Mietkiewicz NP, Williams TM, McGlinchy J, Cook MC. FIRED (Fire Events Delineation): an open, flexible algorithm and database of US fire events derived from the MODIS burned area product (2001-2019). Remote Sensing. 2020;12:3498. doi:10.3390/rs12213498.

7. Mahood AL, Lindrooth EJ, Cook MC, Balch JK. Country-level fire perimeter datasets (2001-2021). Scientific Data. 2022;9:458. doi:10.1038/s41597-022-01572-3.

8. Abatzoglou JT. Development of gridded surface meteorological data for ecological applications and modelling. International Journal of Climatology. 2013;33:121-131. doi:10.1002/joc.3413.

9. Bookstein FL. Morphometric Tools for Landmark Data: Geometry and Biology. Cambridge University Press; 1991.

10. Ramsay JO, Silverman BW. Functional Data Analysis. 2nd ed. Springer; 2005. doi:10.1007/b98888.

11. Jolliffe IT. Principal Component Analysis. 2nd ed. Springer; 2002. doi:10.1007/b98835.

12. Balch JK, Bradley BA, Abatzoglou JT, Nagy RC, Fusco EJ, Mahood AL. Human-started wildfires expand the fire niche across the United States. Proceedings of the National Academy of Sciences. 2017;114:2946-2951. doi:10.1073/pnas.1617394114.

13. Veraverbeke S, Sedano F, Hook SJ, Randerson JT, Jin Y, Rogers BM. Mapping the daily progression of large wildland fires using MODIS active fire data. International Journal of Wildland Fire. 2014;23:655-667. doi:10.1071/WF13015.

14. Parisien MA, Moritz MA. Environmental controls on the distribution of wildfire at multiple spatial scales. Ecological Monographs. 2009;79:127-154. doi:10.1890/07-1289.1.

15. Holsinger LM, Parks SA, Miller C. Weather, fuels, and topography impede wildland fire spread in western US landscapes. Forest Ecology and Management. 2016;380:59-69. doi:10.1016/j.foreco.2016.08.035.

16. Povak NA, Hessburg PF, Salter RB. Evidence for scale-dependent topographic controls on wildfire spread. Ecosphere. 2018;9:e02443. doi:10.1002/ecs2.2443.

## Acknowledgments

Funding: Funding information to be added before submission. Author contributions: Author contributions to be completed before submission. Competing interests: The authors declare no competing interests. Data and materials availability: The external FIRED, MODIS burned-area, and gridMET inputs are publicly available from the cited sources. Derived analysis tables, figure-generation scripts, manuscript-generation code, and the shareable Fire VASE data-lake package are organized in the Fire VASE repository. Repository DOI, CyVerse accession, or archival accession to be added before submission.

AI transparency: OpenAI Codex/ChatGPT was used as an AI-assisted coding, analysis, visualization, and editorial tool during development of this project. AI assistance included drafting and revising Python scripts for Fire VASE data ingestion, climate attribution, morphospace analysis, statistical summaries, figure generation, PDF/report production, and render-based quality checks; drafting and revising manuscript text, figure legends, response-to-review material, and simulated reviewer critiques; searching for and organizing candidate citations and author-guideline requirements; and helping maintain logs, manifests, tests, schemas, and documentation. The AI system did not originate the underlying FIRED, MODIS burned-area, gridMET, PRISM, or other observational data, did not make final scientific judgments independently, and is not listed as an author. Human investigators directed the analyses, selected the scientific claims, reviewed code and outputs, verified calculations and citations where reported, and remain responsible for the integrity, interpretation, and final content of the manuscript. Synthetic or illustrative demonstrations created during repository development are documented separately and were not used as evidentiary data for the manuscript analyses.

## Supplementary Materials

Materials and Methods

Figs. S1 to S3

Tables S1 to S4
