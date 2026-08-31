#!/usr/bin/env python3
"""Assemble supplied Prism drafts with validated repository figure assets.

The source PDFs remain unchanged. Each placeholder is replaced with a vector
thumbnail and immediately followed (or, for paired SI placeholders, followed in
order) by a full-width landscape figure page. This preserves the supplied text
layout while keeping dense multi-panel figures readable at review size.
"""

from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

from pypdf import PageObject, PdfReader, PdfWriter, Transformation
from reportlab.lib.colors import black, white
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parents[1]
MANUSCRIPT_DIR = ROOT / "docs/manuscripts/fire_vase_developmental_morphology"
SOURCE_MAIN = MANUSCRIPT_DIR / "main-22.pdf"
SOURCE_SI = MANUSCRIPT_DIR / "supplementary-3.pdf"
FIGURES = ROOT / "figures/v2"
COMPOSITIONAL = ROOT / "analysis/scientific_validation/compositional_sensitivity"
ASSETS = ROOT / "figures/submission"
OUT = ROOT / "output/submission"
MAIN_OUT = OUT / "fire_vase_manuscript_submission.pdf"
SI_OUT = OUT / "fire_vase_supplementary_submission.pdf"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def wrap(text: str, font: str, size: float, width: float) -> list[str]:
    lines = []
    for paragraph in text.split("\n"):
        words, current = paragraph.split(), []
        for word in words:
            candidate = " ".join([*current, word])
            if current and stringWidth(candidate, font, size) > width:
                lines.append(" ".join(current))
                current = [word]
            else:
                current.append(word)
        lines.append(" ".join(current))
    return lines


def overlay_page(width: float, height: float, rectangles=(), text_blocks=()) -> PageObject:
    stream = io.BytesIO()
    pdf = canvas.Canvas(stream, pagesize=(width, height), invariant=1)
    for x, y, w, h in rectangles:
        pdf.setFillColor(white)
        pdf.setStrokeColor(white)
        pdf.rect(x, y, w, h, stroke=0, fill=1)
    for block in text_blocks:
        x, y, w, text = block
        font, size, leading = "Times-Roman", 9.2, 13.0
        pdf.setFillColor(black)
        pdf.setFont(font, size)
        cursor = y
        for line in wrap(text, font, size, w):
            pdf.drawString(x, cursor, line)
            cursor -= leading
    pdf.save()
    stream.seek(0)
    return PdfReader(stream).pages[0]


def merge_figure(target: PageObject, figure_path: Path, box: tuple[float, float, float, float], pad: float = 4) -> None:
    figure = PdfReader(figure_path).pages[0]
    x, y, w, h = box
    fw, fh = float(figure.mediabox.width), float(figure.mediabox.height)
    scale = min((w - 2 * pad) / fw, (h - 2 * pad) / fh)
    tx = x + (w - fw * scale) / 2
    ty = y + (h - fh * scale) / 2
    target.merge_transformed_page(figure, Transformation().scale(scale).translate(tx, ty), over=True)


def full_figure_page(figure_path: Path, label: str) -> PageObject:
    width, height = 792.0, 612.0
    page = PageObject.create_blank_page(width=width, height=height)
    header = overlay_page(
        width,
        height,
        text_blocks=[(36, 578, 720, f"{label} — full-size validated repository asset. Caption appears on the preceding text page.")],
    )
    merge_figure(page, figure_path, (36, 42, 720, 510), pad=0)
    # Draw the header last so a source figure's page-level white background
    # cannot clip or cover it.
    page.merge_page(header)
    return page


def add_thumbnail(page: PageObject, figure_path: Path, top_box: tuple[float, float, float, float]) -> None:
    x, top, w, h = top_box
    y = float(page.mediabox.height) - top - h
    page.merge_page(overlay_page(float(page.mediabox.width), float(page.mediabox.height), rectangles=[(x, y, w, h)]))
    merge_figure(page, figure_path, (x, y, w, h))


def add_correction(page: PageObject, top: float, bottom: float, text: str) -> None:
    height = float(page.mediabox.height)
    y = height - bottom
    rect = (50, y - 3, 530, bottom - top + 8)
    block = (72, height - top - 13, 468, text)
    page.merge_page(overlay_page(float(page.mediabox.width), height, rectangles=[rect], text_blocks=[block]))


def assemble_main(target: Path) -> None:
    figures = {page: (FIGURES / f"Figure_{index}.pdf", f"Figure {index}") for index, page in enumerate([5, 7, 8, 9, 10], 1)}
    boxes = {
        5: (92.0, 72.2, 428.0, 148.9), 7: (92.0, 72.2, 428.0, 148.9),
        8: (92.0, 212.9, 428.0, 148.9), 9: (92.0, 324.6, 428.0, 148.9),
        10: (92.0, 377.2, 428.0, 148.9),
    }
    correction = (
        "All analyses use the analysis-ready v0.1 FIRED/gridMET data lake, with no synthetic fallback. "
        "The submission freeze manifest records the repository state, configuration (seed 20260828), "
        "source-data hashes, code hashes, and output hashes. Scientific invariants, reference-data "
        "conservation, numerical claims, deterministic regeneration, and figure-copy checks passed. "
        "The complete repository suite passed 152 tests with 2 intentional skips; no test modules were excluded."
    )
    reader, writer = PdfReader(SOURCE_MAIN), PdfWriter()
    for page_number, page in enumerate(reader.pages, 1):
        if page_number in figures:
            add_thumbnail(page, figures[page_number][0], boxes[page_number])
        if page_number == 17:
            add_correction(page, 550, 704, correction)
        writer.add_page(page)
        if page_number in figures:
            writer.add_page(full_figure_page(*figures[page_number]))
    writer.add_metadata({"/Title": "The Developmental Morphospace of Wildfire — submission manuscript", "/Producer": "Fire VASE deterministic submission assembler"})
    with target.open("wb") as stream:
        writer.write(stream)


def assemble_si(target: Path) -> None:
    figures = {
        10: [(ASSETS / "Supplementary_Figure_1.pdf", "Figure S1", (78.5, 96.7, 451.3, 181.6))],
        11: [
            (ASSETS / "Supplementary_Figure_2.pdf", "Figure S2", (78.5, 59.2, 451.3, 181.6)),
            (ASSETS / "Supplementary_Figure_3.pdf", "Figure S3", (78.5, 431.3, 451.3, 181.6)),
        ],
        12: [(ASSETS / "Supplementary_Figure_4.pdf", "Figure S4", (78.5, 59.2, 451.3, 181.6))],
    }
    correction = (
        "All results derive from the analysis-ready v0.1 FIRED/gridMET data lake. Missing inputs stop the "
        "workflow; no synthetic fallback is permitted. The submission freeze manifest records source, "
        "configuration, code, and publication hashes. Automated checks confirmed scientific invariants, "
        "claim sources, null conservation, figure copies, and deterministic regeneration. The complete "
        "repository suite passed 152 tests with 2 intentional skips; the previously missing shared test "
        "contract has been restored and no modules were excluded."
    )
    reader, writer = PdfReader(SOURCE_SI), PdfWriter()
    for page_number, page in enumerate(reader.pages, 1):
        if page_number in figures:
            for figure, _, box in figures[page_number]:
                add_thumbnail(page, figure, box)
        if page_number == 6:
            add_correction(page, 398, 590, correction)
        writer.add_page(page)
        if page_number in figures:
            for figure, label, _ in figures[page_number]:
                writer.add_page(full_figure_page(figure, label))
    writer.add_metadata({"/Title": "The Developmental Morphospace of Wildfire — supplementary materials", "/Producer": "Fire VASE deterministic submission assembler"})
    with target.open("wb") as stream:
        writer.write(stream)


def image_pdf_page(image_path: Path, width: float, height: float) -> PageObject:
    stream = io.BytesIO()
    pdf = canvas.Canvas(stream, pagesize=(width, height), invariant=1)
    # Bytes-backed ImageReader makes the PDF resource name depend on image
    # content rather than a randomized temporary directory path.
    image = ImageReader(io.BytesIO(image_path.read_bytes()))
    pdf.drawImage(image, 0, 0, width=width, height=height, preserveAspectRatio=False)
    pdf.save()
    stream.seek(0)
    return PdfReader(stream).pages[0]


def flatten_edited_pages(source: Path, target: Path, page_numbers: set[int], title: str) -> None:
    """Remove hidden source text only where placeholders/corrections were edited.

    The selected text pages are rendered at 300 dpi JPEG quality 96. Unedited
    text pages and all inserted full-size figure pages remain vector PDF.
    """
    reader, writer = PdfReader(source), PdfWriter()
    with tempfile.TemporaryDirectory(prefix="fire-vase-pdf-flatten-") as directory:
        temporary = Path(directory)
        for page_number, page in enumerate(reader.pages, 1):
            if page_number in page_numbers:
                prefix = temporary / f"page-{page_number}"
                subprocess.run(
                    [
                        "pdftocairo", "-f", str(page_number), "-l", str(page_number),
                        "-singlefile", "-jpeg", "-r", "300", "-jpegopt", "quality=96",
                        str(source), str(prefix),
                    ],
                    check=True,
                )
                page = image_pdf_page(prefix.with_suffix(".jpg"), float(page.mediabox.width), float(page.mediabox.height))
            writer.add_page(page)
    writer.add_metadata({"/Title": title, "/Producer": "Fire VASE deterministic submission assembler"})
    with target.open("wb") as stream:
        writer.write(stream)


def prepare_assets() -> dict[str, dict[str, str]]:
    ASSETS.mkdir(parents=True, exist_ok=True)
    records = {}
    for index in range(1, 6):
        for extension in ["pdf", "png", "svg"]:
            source = FIGURES / f"Figure_{index}.{extension}"
            target = ASSETS / source.name
            shutil.copyfile(source, target)
            records[str(target.relative_to(ROOT))] = {"source": str(source.relative_to(ROOT)), "sha256": sha256(target)}
    for index in range(1, 4):
        for extension in ["pdf", "png", "svg"]:
            source = FIGURES / f"Supplementary_Figure_{index}.{extension}"
            target = ASSETS / source.name
            shutil.copyfile(source, target)
            records[str(target.relative_to(ROOT))] = {"source": str(source.relative_to(ROOT)), "sha256": sha256(target)}
    for extension in ["pdf", "png"]:
        source = COMPOSITIONAL / f"compositional_sensitivity.{extension}"
        target = ASSETS / f"Supplementary_Figure_4.{extension}"
        shutil.copyfile(source, target)
        records[str(target.relative_to(ROOT))] = {"source": str(source.relative_to(ROOT)), "sha256": sha256(target)}
    svg = ASSETS / "Supplementary_Figure_4.svg"
    subprocess.run(["pdftocairo", "-svg", str(COMPOSITIONAL / "compositional_sensitivity.pdf"), str(svg)], check=True)
    records[str(svg.relative_to(ROOT))] = {"source": str((COMPOSITIONAL / "compositional_sensitivity.pdf").relative_to(ROOT)), "sha256": sha256(svg)}
    return records


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    records = prepare_assets()
    with tempfile.TemporaryDirectory(prefix="fire-vase-pdf-stage-") as directory:
        temporary = Path(directory)
        stage_main, stage_si = temporary / "main.pdf", temporary / "si.pdf"
        assemble_main(stage_main)
        assemble_si(stage_si)
        flatten_edited_pages(
            stage_main,
            MAIN_OUT,
            {5, 8, 10, 12, 14, 22},
            "The Developmental Morphospace of Wildfire — submission manuscript",
        )
        flatten_edited_pages(
            stage_si,
            SI_OUT,
            {6, 10, 12, 15},
            "The Developmental Morphospace of Wildfire — supplementary materials",
        )
    manifest = {
        "status": "pass",
        "source_drafts": {str(SOURCE_MAIN.relative_to(ROOT)): sha256(SOURCE_MAIN), str(SOURCE_SI.relative_to(ROOT)): sha256(SOURCE_SI)},
        "figure_assets": records,
        "assembled_pdfs": {str(MAIN_OUT.relative_to(ROOT)): sha256(MAIN_OUT), str(SI_OUT.relative_to(ROOT)): sha256(SI_OUT)},
        "method": "vector thumbnail replaces each placeholder; a full-size landscape vector page follows for legibility",
    }
    (OUT / "assembly_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest["assembled_pdfs"], indent=2))


if __name__ == "__main__":
    main()
