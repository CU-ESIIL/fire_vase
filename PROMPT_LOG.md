# Prompt and implementation log

## 2026-08-28 - Methodological correction (v2)

Request: rebuild Fire VASE around developmental morphology, correct peak/mean and entropy semantics, audit dates, remove endpoints from the primary PCA, use common weather cohorts and grouped validation, compare weather with autoregression, and replace adversarial examples with unique caliper matching. Preserve real inputs and legacy results; regenerate figures and manuscript.

Implementation at `18c923cb0c82bf9f66567b62a3491ac30a28c369`: `src/cubedynamics/analysis_v2.py`, `scripts/fire_vase_v2*.py`, `config/analysis_v2.json`, `analysis/v2/`, `figures/v2/`, and the versioned manuscript. The old numerical analysis is isolated in `archive/comparison_v1/`. See `analysis/v2/audit_report.md` and `legacy_dependency_audit.md`. This log was reconstructed from the preceding request and committed implementation; it is not a contemporaneous record of every command.

Closeout: scientific invariants and saved-statistics figure/manuscript replay are checked by `scripts/verify_fire_vase_v2.py`. Full test collection has a pre-existing missing `tests.helpers.contracts` import in two test modules; the remaining tests and dedicated v2 tests are run separately. Reproduction is not scientific validation.

## 2026-08-28 - Second-pass scientific validation

Request: resume and finish v2 verification, then audit rather than restart it. Stress-test unchanged shape features, null histories, observation support, endpoint projections, weather confounding/selection, incremental state skill, specifically VPD interactions, and matching quality. Freeze defensible claims and produce a Prism handoff, targeted manuscript/figure updates, and a reproducibility record.

Scope: new validation outputs live in `analysis/scientific_validation/`; v2 statistics remain the explicitly identified candidate baseline. Only unresolved tests are recomputed, plus targeted numerical replays. No new external data, feature search, or causal claims. The final audit, claim matrix, and reproducibility record document outcomes and remaining limitations.

Additional user guidance: inspect the manuscript PDF called “main.pdf”. Located remotely as `docs/manuscripts/fire_vase_developmental_morphology/main-16.pdf`; read all 27 pages without changing the original. The corrected version uses its title, supplied authorship and representation-first framing. `analysis/scientific_validation/reference_manuscript_audit.md` records its hash and section-by-section reconciliation. Its old .349, mixed-PCA, adjacent-slice and unqualified interaction claims were not reintroduced.
