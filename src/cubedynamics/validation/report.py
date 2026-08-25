"""Collate modular Fire VASE QA artifacts into one inspectable PDF."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from .core import QAResult


def _footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#59636b"))
    canvas.drawString(0.7 * inch, 0.42 * inch, "Fire VASE validation report")
    canvas.drawRightString(7.8 * inch, 0.42 * inch, f"page {doc.page}")
    canvas.restoreState()


def _metric_rows(metrics: dict, cell_style: ParagraphStyle) -> list[list[Paragraph]]:
    rows = [[Paragraph("metric", cell_style), Paragraph("value", cell_style)]]
    for key, value in metrics.items():
        if isinstance(value, dict):
            rendered = ", ".join(f"{subkey}={subvalue}" for subkey, subvalue in value.items())
        elif isinstance(value, list):
            rendered = ", ".join(str(item) for item in value)
        else:
            rendered = str(value)
        rows.append(
            [
                Paragraph(str(key).replace("_", " "), cell_style),
                Paragraph(rendered.replace("&", "&amp;"), cell_style),
            ]
        )
    return rows


def build_validation_pdf(results: Iterable[QAResult], output_path: str | Path) -> Path:
    """Build a stable, figure-forward PDF from module result objects."""

    results = list(results)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="ReportTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=24,
            leading=28,
            textColor=colors.HexColor("#24343d"),
            alignment=TA_CENTER,
            spaceAfter=16,
        )
    )
    cell_style = ParagraphStyle(
        "TableCell",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=7.6,
        leading=9.2,
        textColor=colors.black,
        wordWrap="CJK",
    )
    header_cell_style = ParagraphStyle(
        "TableHeaderCell",
        parent=cell_style,
        fontName="Helvetica-Bold",
        textColor=colors.white,
    )
    styles.add(
        ParagraphStyle(
            name="Section",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=17,
            leading=20,
            textColor=colors.HexColor("#24343d"),
            spaceAfter=8,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Small",
            parent=styles["BodyText"],
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor("#4b555b"),
        )
    )

    doc = SimpleDocTemplate(
        output.as_posix(),
        pagesize=letter,
        rightMargin=0.65 * inch,
        leftMargin=0.65 * inch,
        topMargin=0.62 * inch,
        bottomMargin=0.62 * inch,
        title="Fire VASE Validation Report",
        author="Fire VASE project",
    )
    story = [
        Spacer(1, 0.45 * inch),
        Paragraph("Fire VASE Validation Report", styles["ReportTitle"]),
        Paragraph(
            "Independent, rerunnable QA for the CubeDynamics grammar, GridMET streaming and attribution, FIRED polygon-to-hull construction, and upstream source consistency.",
            ParagraphStyle("Lead", parent=styles["BodyText"], fontSize=12, leading=17, alignment=TA_CENTER, textColor=colors.HexColor("#46545c")),
        ),
        Spacer(1, 0.35 * inch),
    ]
    status_rows = [
        [
            Paragraph("module", header_cell_style),
            Paragraph("status", header_cell_style),
            Paragraph("purpose", header_cell_style),
        ]
    ]
    for result in results:
        status_rows.append(
            [
                Paragraph(result.module, cell_style),
                Paragraph(result.status.upper(), cell_style),
                Paragraph(result.summary, cell_style),
            ]
        )
    summary_table = Table(status_rows, colWidths=[1.05 * inch, 0.75 * inch, 5.25 * inch], repeatRows=1)
    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#24343d")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (1, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("LEADING", (0, 0), (-1, -1), 11),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#b7c0c5")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f5f6")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.extend(
        [
            summary_table,
            Spacer(1, 0.25 * inch),
            Paragraph(
                f"Generated {datetime.now(timezone.utc).replace(microsecond=0).isoformat()}. Each module also writes CSV/JSON evidence beside its plot; this PDF is a collation, not the only QA record.",
                styles["Small"],
            ),
            PageBreak(),
        ]
    )

    for index, result in enumerate(results, start=1):
        story.append(Paragraph(f"{index}. {result.module.replace('_', ' ').title()} validation", styles["Section"]))
        status_color = "#2d6a4f" if result.status == "pass" else "#9b2226"
        story.append(
            Paragraph(
                f'<font color="{status_color}"><b>{result.status.upper()}</b></font> - {result.summary}',
                styles["BodyText"],
            )
        )
        story.append(Spacer(1, 0.12 * inch))
        plot_path = Path(result.artifacts.get("plot", ""))
        if plot_path.exists():
            image = Image(plot_path.as_posix())
            max_width, max_height = 7.2 * inch, 5.55 * inch
            scale = min(max_width / image.imageWidth, max_height / image.imageHeight)
            image.drawWidth = image.imageWidth * scale
            image.drawHeight = image.imageHeight * scale
            story.append(image)
            story.append(Spacer(1, 0.1 * inch))
        table = Table(_metric_rows(result.metrics, cell_style), colWidths=[2.55 * inch, 4.45 * inch], repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dce7eb")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 7.6),
                    ("LEADING", (0, 0), (-1, -1), 9.2),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#bcc5c9")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f6f8f8")]),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]
            )
        )
        story.append(table)
        if index < len(results):
            story.append(PageBreak())

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return output


__all__ = ["build_validation_pdf"]
