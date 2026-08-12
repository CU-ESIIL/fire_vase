#!/usr/bin/env python3
"""Generate the expanded AI transparency report from repository evidence.

The repository does not currently contain a raw, line-by-line chat transcript.
This generator therefore summarizes the auditable project record that was
created from prompt-assisted work: the AI transparency statement, archived
formal reviews, citation/compliance audits, analysis reports, tests, figures,
schemas, notebooks, and reproducibility metadata.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/fire_vase_matplotlib")

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
REPORT = REPO_ROOT / "docs" / "manuscripts" / "fire_vase_developmental_morphology" / "ai_transparency_report.md"
ASSET_DIR = REPO_ROOT / "docs" / "assets" / "ai_transparency"
SOURCE_STATEMENT = REPO_ROOT / "docs" / "manuscripts" / "fire_vase_developmental_morphology" / "ai_transparency_statement.md"


@dataclass(frozen=True)
class Category:
    name: str
    keywords: tuple[str, ...]
    description: str


CATEGORIES = (
    Category(
        "Code and data engineering",
        (
            "script",
            "scripts",
            "python",
            "lakehouse",
            "cache",
            "caches",
            "parquet",
            "schema",
            "schemas",
            "pipeline",
            "infrastructure",
            "ingestion",
            "table",
            "tables",
            "data",
            "gridmet",
            "fired",
        ),
        "Building scripts, schemas, caches, and data-lake/lakehouse workflows.",
    ),
    Category(
        "Analysis and statistics",
        ("analysis", "pca", "model", "null", "bootstrap", "blocked", "r2", "morphospace", "validation", "statistics"),
        "Morphospace construction, statistical summaries, null checks, prediction baselines, and validation tables.",
    ),
    Category(
        "Visualization and figures",
        (
            "figure",
            "figures",
            "plot",
            "visual",
            "visualizations",
            "climate-color",
            "color",
            "mapping",
            "panel",
            "png",
            "svg",
            "pdf",
            "render",
            "vase",
            "hero",
            "atlas",
            "atlases",
            "animations",
            "demos",
            "illustrative",
            "synthetic",
            "rings",
        ),
        "Manuscript figures, visual QA, VASE renders, panels, and website graphics.",
    ),
    Category(
        "Manuscript drafting and revision",
        ("manuscript", "draft", "abstract", "introduction", "discussion", "revision", "science-style", "narrative"),
        "Drafting and revising manuscript text, figure legends, and submission-facing narrative.",
    ),
    Category(
        "Review, critique, and response",
        ("review", "reviewer", "editor", "decision", "major revision", "response", "recommendation", "critique"),
        "Simulated/editorial review rounds, response planning, and revision guardrails.",
    ),
    Category(
        "Citations and compliance",
        ("citation", "doi", "reference", "literature", "guideline", "compliance", "author", "journal"),
        "Citation searching/auditing, reference placement, and author-guideline checks.",
    ),
    Category(
        "Testing and reproducibility",
        ("test", "pytest", "reproduc", "checksum", "pixel", "smoke", "qc", "quality", "audit"),
        "Tests, reproducibility checks, checksums, figure pixel comparisons, and quality-control reports.",
    ),
    Category(
        "Documentation and handoff",
        (
            "docs",
            "documentation",
            "readme",
            "vignette",
            "notebook",
            "website",
            "cyverse",
            "handoff",
            "archive",
            "transparency",
            "logs",
            "manifests",
            "examples",
            "development notes",
        ),
        "Documentation, website pages, notebooks, collaboration guides, archives, and public handoff notes.",
    ),
)


PROMPT_BASIS_HEADING = "## Prompt-log basis"


def read_text(path: Path) -> str:
    return path.read_text(errors="ignore")


def prompt_basis_items(statement_path: Path) -> list[str]:
    """Extract bullet items from the existing prompt-log basis section."""
    text = read_text(statement_path)
    if PROMPT_BASIS_HEADING not in text:
        return []
    section = text.split(PROMPT_BASIS_HEADING, 1)[1]
    section = section.split("\n## ", 1)[0]
    return [line[2:].strip() for line in section.splitlines() if line.startswith("- ")]


def markdown_evidence_files() -> list[Path]:
    roots = [
        REPO_ROOT / "analysis",
        REPO_ROOT / "archive" / "manuscript_history",
        REPO_ROOT / "docs",
        REPO_ROOT / "figures",
        REPO_ROOT / "manuscript_figures",
        REPO_ROOT / "scripts",
    ]
    files: list[Path] = []
    for root in roots:
        if root.exists():
            files.extend(path for path in root.rglob("*") if path.suffix.lower() in {".md", ".txt"})
    return sorted(set(files))


def classify_text(text: str) -> Counter[str]:
    """Count category hits in a piece of project evidence."""
    lowered = text.lower()
    counts: Counter[str] = Counter()
    for category in CATEGORIES:
        counts[category.name] = sum(len(re.findall(rf"\b{re.escape(keyword.lower())}\b", lowered)) for keyword in category.keywords)
    return counts


def classify_prompt_basis(items: list[str]) -> pd.DataFrame:
    rows = []
    for item in items:
        counts = classify_text(item)
        matches = [name for name, value in counts.items() if value > 0]
        if not matches:
            matches = ["Unclassified"]
        for match in matches:
            rows.append({"item": item, "category": match, "hits": counts.get(match, 1) or 1})
    return pd.DataFrame(rows)


def classify_evidence_files(files: list[Path]) -> pd.DataFrame:
    rows = []
    for path in files:
        text = read_text(path)
        counts = classify_text(text)
        total_hits = sum(counts.values())
        dominant = max(counts, key=counts.get) if total_hits else "Unclassified"
        rows.append(
            {
                "path": path.relative_to(REPO_ROOT).as_posix(),
                "words": len(re.findall(r"\w+", text)),
                "dominant_category": dominant,
                **{category.name: counts[category.name] for category in CATEGORIES},
            }
        )
    return pd.DataFrame(rows)


def artifact_inventory() -> pd.DataFrame:
    groups = {
        "Python scripts": ["scripts/**/*.py", "manuscript_figures/**/*.py", "src/**/*.py", "examples/**/*.py"],
        "Tests": ["tests/test_*.py"],
        "Documentation pages": ["docs/**/*.md", "README.md", "scripts/README.md", "manuscript_figures/README.md"],
        "Archived review/audit docs": ["archive/manuscript_history/**/*.md"],
        "Analysis reports": ["analysis/*.md", "analysis/*.txt"],
        "Schemas/configs": ["schemas/*.json", "config/*.yml", "config/*.yaml"],
        "Figures and visual assets": ["figures/**/*.png", "figures/**/*.svg", "figures/**/*.pdf", "docs/assets/**/*.png"],
        "Notebooks": ["notebooks/*.ipynb"],
        "Manuscript/PDF/DOCX outputs": ["output/pdf/*.pdf", "output/docx/*.docx"],
    }
    rows = []
    for label, patterns in groups.items():
        paths: set[Path] = set()
        for pattern in patterns:
            paths.update(REPO_ROOT.glob(pattern))
        paths = {path for path in paths if path.is_file() and ".venv" not in path.parts and "data_lake" not in path.parts}
        rows.append({"artifact_group": label, "count": len(paths)})
    return pd.DataFrame(rows)


def review_inventory() -> pd.DataFrame:
    patterns = {
        "Formal review rounds": ["archive/manuscript_history/**/formal_reviews*.md"],
        "Citation audits": ["archive/manuscript_history/**/*citation_audit*.md", "docs/manuscripts/**/*citation_check*.md"],
        "Compliance checks": ["archive/manuscript_history/**/*compliance*.md"],
        "Claim/analysis audit reports": ["analysis/*audit*.md", "analysis/*report*.md", "analysis/*decision*.md"],
        "Reproducibility reports": ["analysis/reproducibility_check*.json"],
        "Figure validation tables": ["figures/main/derived_stats/*.csv", "analysis/claim_audit_stats/*.csv"],
    }
    rows = []
    for label, globs in patterns.items():
        paths: set[Path] = set()
        for pattern in globs:
            paths.update(REPO_ROOT.glob(pattern))
        rows.append({"vetting_record": label, "count": len([path for path in paths if path.is_file()])})
    return pd.DataFrame(rows)


def test_inventory() -> pd.DataFrame:
    rows = []
    for path in sorted((REPO_ROOT / "tests").glob("test_*.py")):
        text = read_text(path)
        test_count = len(re.findall(r"^\s*def\s+test_", text, flags=re.MULTILINE))
        if "lakehouse" in path.name or "climate" in path.name:
            area = "Data/lakehouse and climate"
        elif "figure" in path.name or "plot" in path.name or "viewer" in path.name or "viz" in path.name or "panel" in path.name:
            area = "Visualization/rendering"
        elif "vase" in path.name or "hull" in path.name or "fire" in path.name:
            area = "Fire VASE geometry/API"
        else:
            area = "General"
        rows.append({"file": path.relative_to(REPO_ROOT).as_posix(), "test_count": test_count, "area": area})
    return pd.DataFrame(rows)


def reproducibility_summary() -> dict[str, object]:
    report_path = REPO_ROOT / "analysis" / "reproducibility_check_latest.json"
    if not report_path.exists():
        return {"available": False}
    try:
        report = json.loads(report_path.read_text())
    except json.JSONDecodeError:
        return {"available": False, "error": "Could not parse reproducibility_check_latest.json"}

    def nested(*keys: str) -> object:
        current: object = report
        for key in keys:
            if not isinstance(current, dict):
                return None
            current = current.get(key)
        return current

    return {
        "available": True,
        "data_lake_status": nested("data_lake", "status"),
        "derived_stats_status": nested("derived_stats", "status"),
        "figures_pixel_status": nested("figures", "pixel_status"),
        "raw_keys": sorted(report.keys()),
    }


def save_bar_chart(df: pd.DataFrame, label_col: str, value_col: str, output: Path, title: str, color: str = "#d85228") -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    plot_df = df.sort_values(value_col, ascending=True).tail(12)
    fig, ax = plt.subplots(figsize=(8, max(3.5, 0.42 * len(plot_df))), dpi=180)
    ax.barh(plot_df[label_col], plot_df[value_col], color=color)
    ax.set_title(title, loc="left", fontweight="bold")
    ax.set_xlabel("Count")
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.grid(axis="x", alpha=0.18)
    fig.tight_layout()
    fig.savefig(output, bbox_inches="tight")
    plt.close(fig)


def write_outputs(
    prompt_df: pd.DataFrame,
    evidence_df: pd.DataFrame,
    artifacts_df: pd.DataFrame,
    reviews_df: pd.DataFrame,
    tests_df: pd.DataFrame,
    reproducibility: dict[str, object],
    output_dir: Path,
) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        "prompt_type_chart": output_dir / "prompt_type_breakdown.png",
        "artifact_chart": output_dir / "artifact_inventory.png",
        "vetting_chart": output_dir / "vetting_records.png",
        "test_chart": output_dir / "tests_by_area.png",
        "summary_json": output_dir / "ai_transparency_summary.json",
        "prompt_csv": output_dir / "prompt_type_breakdown.csv",
        "evidence_csv": output_dir / "evidence_file_classification.csv",
        "artifacts_csv": output_dir / "artifact_inventory.csv",
        "vetting_csv": output_dir / "vetting_records.csv",
        "tests_csv": output_dir / "tests_by_area.csv",
    }

    prompt_summary = prompt_df.groupby("category", as_index=False).size().rename(columns={"size": "count"})
    evidence_summary = evidence_df.groupby("dominant_category", as_index=False).size().rename(
        columns={"dominant_category": "category", "size": "count"}
    )
    test_summary = tests_df.groupby("area", as_index=False)["test_count"].sum()

    save_bar_chart(prompt_summary, "category", "count", outputs["prompt_type_chart"], "Prompt-log basis: documented assistance categories")
    save_bar_chart(artifacts_df, "artifact_group", "count", outputs["artifact_chart"], "Repository artifacts touched by AI-assisted work", "#496044")
    save_bar_chart(reviews_df, "vetting_record", "count", outputs["vetting_chart"], "Recorded vetting and review evidence", "#2c6f84")
    save_bar_chart(test_summary.rename(columns={"area": "category", "test_count": "count"}), "category", "count", outputs["test_chart"], "Implemented tests by area", "#f2b84b")

    prompt_summary.to_csv(outputs["prompt_csv"], index=False)
    evidence_df.to_csv(outputs["evidence_csv"], index=False)
    artifacts_df.to_csv(outputs["artifacts_csv"], index=False)
    reviews_df.to_csv(outputs["vetting_csv"], index=False)
    test_summary.to_csv(outputs["tests_csv"], index=False)

    payload = {
        "generated_on": date.today().isoformat(),
        "source_basis": "Repository-recorded AI/prompt-assisted project record; no raw chat transcript file was found.",
        "prompt_basis_item_count": int(prompt_df["item"].nunique()) if not prompt_df.empty else 0,
        "prompt_type_counts": dict(zip(prompt_summary["category"], prompt_summary["count"], strict=False)),
        "evidence_file_count": int(len(evidence_df)),
        "evidence_dominant_category_counts": dict(zip(evidence_summary["category"], evidence_summary["count"], strict=False)),
        "artifact_counts": dict(zip(artifacts_df["artifact_group"], artifacts_df["count"], strict=False)),
        "vetting_counts": dict(zip(reviews_df["vetting_record"], reviews_df["count"], strict=False)),
        "test_file_count": int(len(tests_df)),
        "test_function_count": int(tests_df["test_count"].sum()) if not tests_df.empty else 0,
        "tests_by_area": dict(zip(test_summary["area"], test_summary["test_count"], strict=False)),
        "reproducibility": reproducibility,
        "output_files": {key: path.relative_to(REPO_ROOT).as_posix() for key, path in outputs.items()},
    }
    outputs["summary_json"].write_text(json.dumps(payload, indent=2) + "\n")
    return {key: path.relative_to(REPO_ROOT).as_posix() for key, path in outputs.items()}


def markdown_table(df: pd.DataFrame, max_rows: int | None = None) -> str:
    if max_rows is not None:
        df = df.head(max_rows)
    if df.empty:
        return "_No records found._"

    def cell(value: object) -> str:
        text = "" if pd.isna(value) else str(value)
        return text.replace("|", "\\|").replace("\n", "<br>")

    columns = list(df.columns)
    header = "| " + " | ".join(columns) + " |"
    divider = "| " + " | ".join("---" for _ in columns) + " |"
    rows = ["| " + " | ".join(cell(row[column]) for column in columns) + " |" for _, row in df.iterrows()]
    return "\n".join([header, divider, *rows])


def write_report(
    items: list[str],
    prompt_df: pd.DataFrame,
    evidence_df: pd.DataFrame,
    artifacts_df: pd.DataFrame,
    reviews_df: pd.DataFrame,
    tests_df: pd.DataFrame,
    reproducibility: dict[str, object],
    outputs: dict[str, str],
    report_path: Path,
) -> None:
    prompt_summary = prompt_df.groupby("category", as_index=False).size().rename(columns={"size": "count"})
    prompt_summary = prompt_summary.sort_values("count", ascending=False)
    evidence_summary = evidence_df.groupby("dominant_category", as_index=False).agg(files=("path", "count"), words=("words", "sum"))
    evidence_summary = evidence_summary.rename(columns={"dominant_category": "category"}).sort_values("files", ascending=False)
    test_summary = tests_df.groupby("area", as_index=False)["test_count"].sum().sort_values("test_count", ascending=False)

    reproducibility_line = "No current reproducibility report was available."
    if reproducibility.get("available"):
        reproducibility_line = (
            f"Latest recorded checks: data lake `{reproducibility.get('data_lake_status')}`, "
            f"derived statistics `{reproducibility.get('derived_stats_status')}`, "
            f"figure pixels `{reproducibility.get('figures_pixel_status')}`."
        )

    text = f"""# Expanded AI Transparency Report

Date generated: {date.today().isoformat()}

This document expands the short manuscript AI transparency statement into a
repository-auditable report. It is generated by
[`scripts/generate_ai_transparency_report.py`](https://github.com/CU-ESIIL/fire_vase/blob/main/scripts/generate_ai_transparency_report.py)
from the project record: the existing prompt-log-basis statement, archived
formal reviews, citation/compliance audits, analysis reports, tests, schemas,
figure outputs, notebooks, and reproducibility metadata.

## Scope And Limitation

The repository currently preserves a prompt-log-derived project record, but it
does not include a raw, line-by-line private chat transcript as a standalone
file. The statistics below therefore quantify **documented AI-assisted work
preserved in the repository**, not every private prompt ever typed during the
project. If a raw prompt log is added later, rerun the generator and extend its
source list so these counts can become transcript-level rather than
artifact-level.

## Manuscript-Ready Statement

OpenAI Codex/ChatGPT was used as an AI-assisted coding, analysis,
visualization, documentation, and editorial tool during development of Fire
VASE. AI assistance included data-lake and lakehouse scripting, climate
attribution workflows, morphospace and validation analyses, figure rendering,
website and notebook documentation, manuscript drafting and revision, simulated
review, citation auditing, and reproducibility checks. The AI system did not
originate the underlying FIRED, MODIS burned-area, gridMET, PRISM, or other
observational data; did not make final scientific judgments independently; and
is not listed as an author. Human investigators directed the analyses, selected
the scientific claims, reviewed code and outputs, verified calculations and
citations where reported, and remain responsible for the integrity,
interpretation, and final manuscript.

## What AI Was Used To Do

The current prompt-log basis contains **{len(items)} documented assistance
items**. Items can map to more than one category, because a single prompt may
combine, for example, figure generation, testing, and manuscript revision.

![Prompt type breakdown](../../assets/ai_transparency/prompt_type_breakdown.png)

{markdown_table(prompt_summary)}

## What The Work Produced

AI-assisted work is visible in repository artifacts rather than only in prose.
The inventory below counts current tracked project products by broad type. Some
artifacts were created directly with AI assistance; others were generated or
organized through AI-assisted scripts and documentation workflows.

![Artifact inventory](../../assets/ai_transparency/artifact_inventory.png)

{markdown_table(artifacts_df.sort_values("count", ascending=False))}

## How AI Use Was Vetted

The project record includes review, audit, reproducibility, and validation
artifacts that constrain what AI-generated or AI-assisted work could be used
for. These records include formal simulated review rounds, citation audits,
author-guideline checks, claim audits, reproducibility reports, and figure
validation tables.

![Vetting records](../../assets/ai_transparency/vetting_records.png)

{markdown_table(reviews_df.sort_values("count", ascending=False))}

{reproducibility_line}

## Tests Implemented

The repository currently contains **{int(tests_df['test_count'].sum()) if not tests_df.empty else 0}
test functions** across **{len(tests_df)} test files**. The tests emphasize the
Fire VASE geometry/API surface, rendering behavior, lakehouse/cache contracts,
and real-data smoke checks.

![Tests by area](../../assets/ai_transparency/tests_by_area.png)

{markdown_table(test_summary)}

## Evidence Categories In Repository Text

The generator classified **{len(evidence_df)} Markdown/TXT evidence files** by
dominant keyword category. This is a coarse but reproducible proxy for where the
AI-assisted record is concentrated.

{markdown_table(evidence_summary)}

## Prompt-Log Basis Items

The existing AI transparency statement preserved the following documented
prompt-log basis items:

{chr(10).join(f'- {item}' for item in items)}

## Responsibility Boundary

AI assistance was used to accelerate implementation, synthesis, drafting,
review, and quality control. It was not used as an autonomous author, data
source, or final scientific authority. Human investigators remain responsible
for study design, data selection, analytic choices, interpretation, citation
accuracy, and all claims in the final manuscript.

## Refresh Instructions

Regenerate this report after major prompt-log, manuscript, analysis, figure, or
testing updates:

```bash
uv run python scripts/generate_ai_transparency_report.py
```

Machine-readable outputs:

- Summary JSON: `{outputs['summary_json']}`
- Prompt category table: `{outputs['prompt_csv']}`
- Evidence classification table: `{outputs['evidence_csv']}`
- Artifact inventory: `{outputs['artifacts_csv']}`
- Vetting records: `{outputs['vetting_csv']}`
- Test inventory: `{outputs['tests_csv']}`
"""
    report_path.write_text(text)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=REPORT)
    parser.add_argument("--asset-dir", type=Path, default=ASSET_DIR)
    args = parser.parse_args()

    items = prompt_basis_items(SOURCE_STATEMENT)
    prompt_df = classify_prompt_basis(items)
    evidence_df = classify_evidence_files(markdown_evidence_files())
    artifacts_df = artifact_inventory()
    reviews_df = review_inventory()
    tests_df = test_inventory()
    reproducibility = reproducibility_summary()
    outputs = write_outputs(prompt_df, evidence_df, artifacts_df, reviews_df, tests_df, reproducibility, args.asset_dir)
    write_report(items, prompt_df, evidence_df, artifacts_df, reviews_df, tests_df, reproducibility, outputs, args.report)
    print(f"Wrote {args.report}")
    print(f"Wrote assets under {args.asset_dir}")


if __name__ == "__main__":
    main()
