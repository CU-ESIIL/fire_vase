# Website evidence-trail audit

Date: 2026-09-03

This audit maps the current manuscript, supplementary material, validation
evidence, notebooks, and AI-use record before the guided-storytelling pass. The
28 August 2026 v2 manuscript and validated v2 outputs remain the quantitative
authority. No repository asset is moved or replaced by this pass.

## Manuscript figures

| Figure | Scientific question and supported finding | Validation that challenges it | Reproduction route | Manuscript location | Public location before this pass |
|---|---|---|---|---|---|
| Figure 1 | What does a Fire VASE encode? Ordered growth and gaps remain visible. | Source/date audit; cube integrity; real-event ID/date checks | Canonical reproduction notebook; `01_figure_1.py`; `vase_slices.parquet`, `event_analysis.parquet` | Introduction; Results: corrected semantics and observation support | Homepage, Approach, figure gallery, corrected evidence |
| Figure 2 | Can histories share developmental coordinates? Broad continuous gradients are supported. | Observation-depth refits; temporal/allocation nulls; Hellinger geometry; bootstrap, region, and year stability | Canonical notebook; `02_figure_2.py`; PCA tables in `analysis/v2/` | Results: shared coordinate system; SI S3-S5, S10-S11 | Developmental-pathways finding, figure gallery, corrected evidence |
| Figure 3 | How well does measured weather map onto morphology? Associations are weak and response-dependent. | Common-cohort blocked folds; adjustment/selection checks; climate attribution; external gridMET check | Canonical notebook; `03_figure_3.py`; event predictor/performance/uncertainty tables | Results: weather is an external association; SI S6, S12 | Figure gallery and corrected evidence only |
| Figure 4 | What does weather add above recent state? State supplies most next-day predictive skill; weather adds a small increment. | Exact-day/date audit; day-specific geometry; spatial-exposure and seasonal sensitivity; VPD ablation and subgroup refits | Canonical notebook; `04_figure_4.py`; state performance/uncertainty tables | Results: subsequent growth; SI S7, S13 | Weather-and-state finding, figure gallery, corrected evidence |
| Figure 5 | What remains unexplained by weather or morphology matching? Pairs are study candidates; mismatch is null-compatible. | Unique-pair replay; balance; conditional permutations; candidate, metric, and caliper sensitivity | Canonical notebook; `05_figure_5.py`; matched-pair and permutation tables | Results: convergence and divergence; SI S8, S14 | Mismatched-fires finding, figure gallery, corrected evidence |

## Validation figures

| Figure | Threat tested | What would worry us | Published result | Finding challenged |
|---|---|---|---|---|
| Supplementary Figure 2 | Observation depth, constrained geometry, arbitrary temporal order, endpoint association, weather controls, matching caliper | Broad axes vanish; observed ordering resembles shuffles; conclusions depend entirely on one support threshold or caliper | Broad gradients persist; local structure changes; ordering-sensitive traits differ; compression and matching require qualification | Figures 2, 3, and 5; Findings 1, 2, and 4 |
| Supplementary Figure 4 | Choice of compositional geometry | Leading developmental meaning disappears under Hellinger geometry | Global organization and early-versus-late gradient persist; neighborhoods and tails are less invariant | Figure 2; Finding 1 |
| FIRED geometry and hull sensitivity | Polygon simplification and directional support | Operational simplification materially changes area or invalidates geometry | Event 20657 changes cumulative area by 0.254% at 125 m; aggressive stress tests change more | Representation and geometry implementation |
| gridMET time and polygon attribution | Wrong day/cell or hidden exposure definition | Recomputed daily values disagree, dates are missing, or attribution method is silently substituted | Date/value replay is exact for the sample; alternative spatial attribution differs and stays explicit | Figures 3 and 4; Finding 3 |
| Cube/HTML integrity and expected-failure controls | Permuted axes, dates, or displayed values | Corruptions pass or HTML no longer maps to source cells | Clean source-to-view contract passes; latitude reversal, time scrambling, and a dropped day are rejected | Implementation credibility across figures |
| External sources | Cached inputs disagree with independent/upstream representations | gridMET raw cells or FIRED event/daily geometry disagree | Published sample agrees within declared numerical tolerances | Weather and source-data credibility |

## AI transparency artifacts

| Artifact | Location | What it documents | Limitation |
|---|---|---|---|
| Concise AI statement | `docs/manuscripts/fire_vase_developmental_morphology/ai_transparency_statement.md` | Actual assistance categories, human responsibility, observational-data boundary | Prepared 22 July 2026; concise rather than artifact-level |
| Expanded report | `docs/manuscripts/fire_vase_developmental_morphology/ai_transparency_report.md` | Generated inventory of prompts, artifacts, vetting records, tests, and reproducibility status | Describes documented repository evidence, not every private prompt |
| Prompt and implementation log | `PROMPT_LOG.md` | Major requests, implementation scope, correction and validation history | Reconstructed for some work; not a line-by-line transcript |
| Machine-readable transparency assets | `docs/assets/ai_transparency/` | Counts and charts behind the expanded report | Counts are snapshots and must be regenerated after repository changes |
| Scientific validation and freeze records | `analysis/scientific_validation/`, `analysis/submission_freeze/` | Claim matrices, numerical replay, hashes, test status, human-only decisions | Computational reproduction does not replace scientific judgment review |

## Story-to-evidence gaps addressed by this pass

- Add a guided walkthrough of all five current manuscript figures.
- Add concise, reusable “How to read this figure,” “Look here,” challenge, and
  evidence-trail components to finding pages.
- Put validation figures and counterfactual failure conditions on the public
  validation page while retaining detailed module pages.
- Add a human-readable AI accountability landing page and link it from the
  homepage, Paper, Validation, and Reproduce.
- Keep all four notebooks first-class and at their current paths.
