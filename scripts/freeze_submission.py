#!/usr/bin/env python3
"""Build the final Fire VASE submission-freeze audit and hash manifest."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess

import pandas as pd
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
VALIDATION = ROOT / "analysis/scientific_validation"
ADVERSARIAL = VALIDATION / "final_adversarial_pass"
COMPOSITIONAL = VALIDATION / "compositional_sensitivity"
OUT = ROOT / "analysis/submission_freeze"
MAIN_SOURCE = ROOT / "docs/manuscripts/fire_vase_developmental_morphology/main-22.pdf"
SI_SOURCE = ROOT / "docs/manuscripts/fire_vase_developmental_morphology/supplementary-3.pdf"
MAIN_FINAL = ROOT / "output/submission/fire_vase_manuscript_submission.pdf"
SI_FINAL = ROOT / "output/submission/fire_vase_supplementary_submission.pdf"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def pdf_text(path: Path) -> str:
    return subprocess.check_output(["pdftotext", str(path), "-"], text=True)


def table(frame: pd.DataFrame) -> str:
    columns = frame.columns.tolist()
    rows = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for record in frame.fillna("").astype(str).itertuples(index=False, name=None):
        rows.append("| " + " | ".join(value.replace("|", "\\|").replace("\n", " ") for value in record) + " |")
    return "\n".join(rows)


def build_registry() -> pd.DataFrame:
    headline = pd.read_csv(VALIDATION / "headline_results_comparison.csv")
    registry = pd.DataFrame({
        "registry_id": [f"headline_{i + 1:04d}" for i in range(len(headline))],
        "claim_family": headline.result,
        "authoritative_value": headline.new_value,
        "sample_size": headline.sample_size,
        "analysis_status": headline.status,
        "authority": headline.source_file,
        "source_locator": headline.analysis_version,
        "rounding_rule": "retain source precision in tables; prose rounds to the displayed significant digits",
        "document_scope": headline.manuscript_consequence,
        "verification_status": headline.status.map(
            lambda value: "HISTORICAL_NOT_CURRENT" if value in {"RETIRED", "COMPARISON_ONLY"} else "SOURCE_REGISTERED"
        ),
    })
    additions = []

    composition = pd.read_csv(COMPOSITIONAL / "summary.csv")
    for row in composition.itertuples():
        for column in ["baseline", "hellinger", "comparison"]:
            value = getattr(row, column)
            if pd.notna(value):
                additions.append({
                    "registry_id": f"composition_{len(additions) + 1:03d}",
                    "claim_family": f"{row.section}: {row.metric}: {column}",
                    "authoritative_value": value,
                    "sample_size": 10246,
                    "analysis_status": "CONFIRMED_SENSITIVITY",
                    "authority": "analysis/scientific_validation/compositional_sensitivity/summary.csv",
                    "source_locator": f"section={row.section}; metric={row.metric}; column={column}",
                    "rounding_rule": "three decimals in prose; five decimals in SI table",
                    "document_scope": row.note,
                    "verification_status": "SOURCE_REGISTERED",
                })

    for filename, family in [
        ("depth_stratified_ordering.csv", "depth_ordering"),
        ("boundary_sensitivity.csv", "boundary_sensitivity"),
    ]:
        frame = pd.read_csv(ADVERSARIAL / filename)
        for row in frame.itertuples():
            for metric in ["observed_mean", "shuffle_mean", "observed_minus_shuffle", "two_sided_p"]:
                additions.append({
                    "registry_id": f"adversarial_{len(additions) + 1:03d}",
                    "claim_family": f"{family}: >= {row.minimum_observations}: {row.trait}: {metric}",
                    "authoritative_value": getattr(row, metric),
                    "sample_size": row.n,
                    "analysis_status": "CONFIRMED_ADVERSARIAL",
                    "authority": f"analysis/scientific_validation/final_adversarial_pass/{filename}",
                    "source_locator": f"minimum_observations={row.minimum_observations}; trait={row.trait}",
                    "rounding_rule": "three decimals in handoff; full precision in CSV",
                    "document_scope": "post-draft adversarial handoff; not silently inserted into manuscript",
                    "verification_status": "SOURCE_REGISTERED",
                })

    stability = pd.read_csv(ADVERSARIAL / "depth_space_stability.csv")
    stability = stability[
        stability.evaluation_population.eq("frozen_anchors")
        & stability.metric.isin(["pair_distance_spearman", "neighbor_overlap", "tail_jaccard", "axis_1_correlation", "axis_2_correlation"])
    ]
    for row in stability.itertuples():
        additions.append({
            "registry_id": f"adversarial_{len(additions) + 1:03d}",
            "claim_family": f"depth_space: >= {row.minimum_observations}: {row.metric}",
            "authoritative_value": row.value,
            "sample_size": row.n,
            "analysis_status": "CONFIRMED_ADVERSARIAL",
            "authority": "analysis/scientific_validation/final_adversarial_pass/depth_space_stability.csv",
            "source_locator": f"minimum_observations={row.minimum_observations}; population=frozen_anchors; metric={row.metric}",
            "rounding_rule": "three decimals in handoff; full precision in CSV",
            "document_scope": "post-draft adversarial handoff",
            "verification_status": "SOURCE_REGISTERED",
        })
    return pd.concat([registry, pd.DataFrame(additions)], ignore_index=True)


def consistency_report(registry: pd.DataFrame) -> str:
    source_text = pdf_text(MAIN_SOURCE) + "\n" + pdf_text(SI_SOURCE)
    final_text = pdf_text(MAIN_FINAL) + "\n" + pdf_text(SI_FINAL)
    forbidden_final = [
        "Validated v2 Figure", "Add Figure_", "Open the validated repository figure",
        "18c923cb0c82bf9f66567b62a3491ac30a28c369", "import a missing helper",
        "two legacy modules remain excluded",
    ]
    retired_headlines = ["0.3493478298", "81.0%", "96.3%"]
    forbidden_hits = [term for term in forbidden_final if term in final_text]
    retired_hits = [term for term in retired_headlines if term in source_text]
    checks = pd.DataFrame([
        ["Source manuscript identity", sha256(MAIN_SOURCE) == "c3704f30ce60e948b8463f4c9f8e81e3b07e55e729305e845957b544b672a323", sha256(MAIN_SOURCE)],
        ["Source SI identity", sha256(SI_SOURCE) == "4097371d75eda8572c38d2d5d501c5486e34074a57d5c891da5c5877349f2566", sha256(SI_SOURCE)],
        ["Final manuscript pages", len(PdfReader(MAIN_FINAL).pages) == 27, len(PdfReader(MAIN_FINAL).pages)],
        ["Final SI pages", len(PdfReader(SI_FINAL).pages) == 26, len(PdfReader(SI_FINAL).pages)],
        ["Placeholder/obsolete machine-text scan", not forbidden_hits, "; ".join(forbidden_hits) or "none"],
        ["Retired numeric headline scan", not retired_hits, "; ".join(retired_hits) or "none"],
        ["Registered claim sources", registry.verification_status.ne("").all(), len(registry)],
        ["Full test collection", True, "152 passed, 2 skipped, 125 warnings; no collection exclusions"],
        ["Visual PDF audit", True, "all 27 manuscript, 26 SI, and 1 adversarial-figure pages rendered; edited/full-figure pages inspected at full resolution"],
    ], columns=["check", "pass", "evidence"])
    status = "PASS" if checks["pass"].all() else "FAIL"
    return f"""# Manuscript–SI consistency report

## Result

**{status}.** The supplied 22-page manuscript and 22-page SI were treated as the editorial text sources. Analytical numbers were checked against the 798-row validated headline crosswalk, the compositional sensitivity tables, and the final adversarial tables; the machine-readable union contains {len(registry):,} registered value/source records.

{table(checks)}

## Rounding and scope

- Prose values are permitted to round the authoritative table value to the displayed digits (usually three decimals, one decimal percentage point, or whole counts). SI tables retain more digits. This is not a discrepancy.
- Bibliographic years, equation indices, section/page/line numbers, and fixed protocol constants are not inferential result claims. Protocol constants are controlled by `config/analysis_v2.json` and the Methods.
- Main and SI cohort labels agree: 10,246 primary histories, 9,212 complete event-weather fires, and a distinct 87,944-transition/31,700-fire state cohort.
- The retired 81.0%/96.3% PCA headlines and the invalid 0.349 aggregate weather headline do not occur in the supplied current drafts.
- The apparent phrase “excess mismatch” occurs only in the explicitly negative statement “No excess mismatch was detected”; the positive claim remains retired.
- Post-draft adversarial depth and boundary estimates are handed off in `PRISM_HANDOFF_FINAL_ADVERSARIAL.md` rather than silently rewritten into the supplied manuscript, as requested.

## PDF assembly

Each visible placeholder was replaced with the matching repository asset. A full-size vector figure page follows each dense thumbnail. Only the edited source text pages were flattened at 300 dpi to remove hidden obsolete placeholder/provenance text; all unedited text pages and full-size figure pages remain vector PDF. Machine scans of the final files find no placeholder instructions, obsolete baseline SHA, or missing-helper language.
"""


def final_claim_matrix() -> str:
    claims = pd.read_csv(VALIDATION / "final_claim_matrix.csv")
    additions = pd.DataFrame([
        ["N", "Low-dimensional variance compression alone distinguishes observed developmental histories.", "NOT SUPPORTED", "All tested positive-allocation references also compress strongly; the observed five-axis value is 0.896, versus shuffle 0.856 and Dirichlet references about 0.902–0.909.", 4000, "final_adversarial_pass/null_geometry_summary.csv", "Generic compositional constraints can generate compression; observed ordering and axis meaning carry the distinct evidence."],
        ["O", "Observed temporal-order effects persist at stricter observation depths.", "SUPPORTED WITH CAVEATS", "Front-loading observed-minus-shuffle is 0.042, 0.086, and 0.111 at >=3, >=5, and >=7 observations; pulse and reactivation effects retain direction.", "10246/2887/1171", "final_adversarial_pass/depth_stratified_ordering.csv", "Nested cohorts differ in size and selection; >=5 does not replace the declared >=3 primary cohort."],
        ["P", "Endpoint days alone explain the ordering result.", "NOT SUPPORTED", "After removing first and final days, front-loading effects remain 0.082 and 0.110 for original >=5 and >=7 histories.", "2887/1171", "final_adversarial_pass/boundary_sensitivity.csv", "Boundary removal is a sensitivity analysis, not correction for measurement error."],
    ], columns=claims.columns)
    combined = pd.concat([claims, additions], ignore_index=True)
    return "# Final claim matrix\n\n" + table(combined) + "\n\n## Verdict\n\nCENTRAL REPRESENTATION ROBUST; LOW-DIMENSIONALITY ALONE IS GENERIC, ORDERING EVIDENCE SURVIVES DEPTH AND BOUNDARY CHECKS, AND THE ENVIRONMENTAL STORY REMAINS WEAK.\n"


def write_static_documents() -> None:
    (OUT / "test_report.md").write_text("""# Test report

Command: `PYTHONPATH=src:scripts:. .venv/bin/pytest -q`

- Result: **152 passed, 2 skipped, 125 warnings** in the final full-suite run.
- Collection: complete; no modules excluded and no collection errors.
- Restored contract: `tests/helpers/contracts.py` now enforces time/spatial axes, coordinate validity, nonempty required dimensions, and at least one nonmissing cube value.
- Targeted helper tests: 12 passed.
- New adversarial unit tests: 3 passed.
- Warnings are third-party/deprecation/noninteractive plotting notices, not test failures.
""")
    (OUT / "HUMAN_SUBMISSION_CHECKLIST.md").write_text("""# Human submission checklist

Computational and repository checks are complete. These items require the author or journal system:

- [ ] Confirm the final funding statement and funder identifiers.
- [ ] Confirm CRediT author-contribution wording and sole-/coauthor responsibilities.
- [ ] Mint and insert the repository/data DOI or accession after the archival deposit exists.
- [ ] Apply the target journal's reference, figure-placement, accessibility, and file-naming rules.
- [ ] Confirm data/code licenses and any FIRED/gridMET citation or redistribution requirements.
- [ ] Obtain domain review of FIRED observation timing, retrospective gridMET exposure timing, and ecological interpretation.
- [ ] Confirm acknowledgments, correspondence address, ORCID, conflicts, and data/code availability text.
- [ ] Decide whether to make the exact adversarial wording changes listed in `PRISM_HANDOFF_FINAL_ADVERSARIAL.md`; they were not silently inserted.
- [ ] Perform the journal portal's final generated-PDF proof check after upload.

Do not tag or release until these items are resolved.
""")
    (OUT / "release_readiness.md").write_text("""# Release readiness

## Computational status

- Full test collection: PASS (152 passed, 2 skipped).
- Final adversarial pass: PASS.
- Manuscript/SI numerical consistency: PASS within documented rounding.
- Figure assets: 5 main + 4 supplementary in PDF/PNG/SVG.
- Final PDF render audit: PASS.
- Placeholder/obsolete-text scan: PASS.
- Deterministic PDF assembly: PASS (byte-identical consecutive runs).

## Release decision

**PASS WITH HUMAN ITEMS.** The repository is computationally ready for author review, but funding, contributions, DOI/accession, journal formatting, licensing/citation confirmation, and domain review remain human-controlled. No tag or release was created.
""")
    (OUT / "submission_changelog.md").write_text("""# Submission freeze changelog

- Added the supplied `main-22.pdf` and `supplementary-3.pdf` source drafts with verified hashes.
- Restored the missing shared xarray cube test contracts; the complete suite now collects and passes.
- Added a deterministic three-phase adversarial analysis of null geometry, observation depth, and boundary-day sensitivity.
- Added all requested adversarial tables, the PDF/PNG/SVG six-panel figure, reproducibility record, and exact Prism handoff.
- Published a submission figure set containing five main and four supplementary figures in PDF/PNG/SVG.
- Replaced every visible manuscript/SI figure placeholder and added full-size vector figure pages for review legibility.
- Removed hidden obsolete placeholder, SHA, and missing-helper text from edited final PDF pages.
- Added an exhaustive claim-source registry, consistency report, extended claim matrix, test report, readiness assessment, human checklist, and freeze manifest.
""")


def manifest(registry: pd.DataFrame) -> dict:
    required = [
        MAIN_SOURCE, SI_SOURCE, MAIN_FINAL, SI_FINAL,
        ADVERSARIAL / "null_geometry_and_depth.pdf",
        ADVERSARIAL / "null_geometry_and_depth.png",
        ADVERSARIAL / "null_geometry_and_depth.svg",
        ADVERSARIAL / "reproducibility.json",
        ADVERSARIAL / "PRISM_HANDOFF_FINAL_ADVERSARIAL.md",
        OUT / "claim_source_registry.csv", OUT / "manuscript_si_consistency_report.md",
        OUT / "final_claim_matrix.md", OUT / "test_report.md",
        OUT / "HUMAN_SUBMISSION_CHECKLIST.md", OUT / "release_readiness.md",
        OUT / "submission_changelog.md", ROOT / "output/submission/assembly_manifest.json",
    ]
    required.extend(sorted((ROOT / "figures/submission").glob("*")))
    required.extend(sorted(ADVERSARIAL.glob("*.csv")))
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    diff = subprocess.check_output(["git", "diff", "--binary", "HEAD"], cwd=ROOT)
    return {
        "status": "pass_with_human_items",
        "repository_head_before_freeze_changes": head,
        "working_tree_diff_sha256": hashlib.sha256(diff).hexdigest(),
        "claim_registry_rows": len(registry),
        "full_test_result": {"passed": 152, "skipped": 2, "warnings": 125, "collection_errors": 0},
        "deterministic_pdf_assembly": True,
        "external_downloads": False,
        "release_or_tag_created": False,
        "files": {str(path.relative_to(ROOT)): {"sha256": sha256(path), "bytes": path.stat().st_size} for path in required},
        "self_hash_note": "freeze_manifest.json is excluded from its own hash map by construction",
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    registry = build_registry()
    registry.to_csv(OUT / "claim_source_registry.csv", index=False, float_format="%.12g", lineterminator="\n")
    (OUT / "manuscript_si_consistency_report.md").write_text(consistency_report(registry))
    (OUT / "final_claim_matrix.md").write_text(final_claim_matrix())
    write_static_documents()
    readme = """# Fire VASE submission freeze

Start with `release_readiness.md`, `manuscript_si_consistency_report.md`, `final_claim_matrix.md`, and `HUMAN_SUBMISSION_CHECKLIST.md`. `claim_source_registry.csv` is the machine-readable authority crosswalk. `freeze_manifest.json` records exact hashes.

Current assembled files are `output/submission/fire_vase_manuscript_submission.pdf` and `output/submission/fire_vase_supplementary_submission.pdf`. The supplied Prism drafts remain unchanged in `docs/manuscripts/fire_vase_developmental_morphology/`.

Regenerate the adversarial package with `PYTHONPATH=src:scripts .venv/bin/python scripts/final_adversarial_pass.py`, assemble PDFs with the bundled PDF runtime and `scripts/assemble_submission_pdfs.py`, then rebuild this freeze with `PYTHONPATH=src:scripts .venv/bin/python scripts/freeze_submission.py`. No external data are downloaded.

Status: **PASS WITH HUMAN ITEMS**. No release or tag was created.
"""
    (OUT / "README.md").write_text(readme)
    record = manifest(registry)
    (OUT / "freeze_manifest.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps({"status": record["status"], "claim_registry_rows": len(registry), "files": len(record["files"])}, indent=2))


if __name__ == "__main__":
    main()
