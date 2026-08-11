#!/usr/bin/env python3
"""Build a PDF summary atlas for the full fire VASE lakehouse pilot tables."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/cubedynamics-mpl-cache")

import duckdb
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Flowable,
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


PAGE_SIZE = landscape(letter)
WIDTH, HEIGHT = PAGE_SIZE
ACCENT = colors.HexColor("#b12a1c")
INK = colors.HexColor("#202124")
MUTED = colors.HexColor("#5f6368")
LIGHT = colors.HexColor("#f3f1ed")


class Rule(Flowable):
    def __init__(self, width: float, color=ACCENT, thickness: float = 1.5):
        super().__init__()
        self.width = width
        self.height = thickness + 4
        self.color = color
        self.thickness = thickness

    def draw(self) -> None:
        self.canv.setStrokeColor(self.color)
        self.canv.setLineWidth(self.thickness)
        self.canv.line(0, self.height / 2, self.width, self.height / 2)


def _styles():
    base = getSampleStyleSheet()
    base.add(
        ParagraphStyle(
            name="TitleLarge",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=28,
            leading=32,
            textColor=INK,
            alignment=TA_LEFT,
            spaceAfter=10,
        )
    )
    base.add(
        ParagraphStyle(
            name="Section",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            textColor=INK,
            spaceBefore=4,
            spaceAfter=8,
        )
    )
    base.add(
        ParagraphStyle(
            name="Small",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
            textColor=MUTED,
        )
    )
    base.add(
        ParagraphStyle(
            name="CalloutNumber",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=24,
            leading=28,
            alignment=TA_CENTER,
            textColor=ACCENT,
        )
    )
    base.add(
        ParagraphStyle(
            name="CalloutLabel",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            alignment=TA_CENTER,
            textColor=MUTED,
        )
    )
    return base


def _page(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(MUTED)
    canvas.drawString(0.45 * inch, 0.32 * inch, "CubeDynamics fire VASE population atlas")
    canvas.drawRightString(WIDTH - 0.45 * inch, 0.32 * inch, f"Page {doc.page}")
    canvas.restoreState()


def _fmt_int(value) -> str:
    return f"{int(value):,}"


def _fmt_float(value, digits=2) -> str:
    return f"{float(value):,.{digits}f}"


def _query_tables(table_root: Path) -> dict[str, pd.DataFrame]:
    con = duckdb.connect()
    traits = table_root / "fire_traits.parquet"
    catalog = table_root / "fire_catalog.parquet"
    manifest = table_root / "processing_manifest.parquet"
    return {
        "overall": con.execute(
            f"""
            select
              count(*) as n_fires,
              min(year) as min_year,
              max(year) as max_year,
              count(distinct year) as n_years,
              sum(total_area_km2) as total_area_km2,
              avg(total_area_km2) as mean_area_km2,
              median(total_area_km2) as median_area_km2,
              max(total_area_km2) as max_area_km2,
              avg(duration_hours) / 24.0 as mean_duration_days,
              median(duration_hours) / 24.0 as median_duration_days,
              max(duration_hours) / 24.0 as max_duration_days
            from '{traits}'
            """
        ).fetchdf(),
        "by_year": con.execute(
            f"""
            select year, count(*) as n, avg(total_area_km2) as mean_area_km2,
              sum(total_area_km2) as total_area_km2
            from '{traits}'
            group by year
            order by year
            """
        ).fetchdf(),
        "by_region": con.execute(
            f"""
            select region, count(*) as n, avg(total_area_km2) as mean_area_km2,
              median(total_area_km2) as median_area_km2,
              sum(total_area_km2) as total_area_km2,
              avg(duration_hours) / 24.0 as mean_duration_days
            from '{traits}'
            group by region
            order by n desc
            """
        ).fetchdf(),
        "by_region_year": con.execute(
            f"""
            select region, year, count(*) as n
            from '{traits}'
            group by region, year
            order by region, year
            """
        ).fetchdf(),
        "largest": con.execute(
            f"""
            select fire_id, region, year, total_area_km2, duration_hours / 24.0 as duration_days,
              peak_growth_km2_per_hour * 24.0 as peak_growth_km2_per_day
            from '{traits}'
            order by total_area_km2 desc
            limit 20
            """
        ).fetchdf(),
        "duration_top": con.execute(
            f"""
            select fire_id, region, year, total_area_km2, duration_hours / 24.0 as duration_days
            from '{traits}'
            order by duration_hours desc
            limit 20
            """
        ).fetchdf(),
        "status": con.execute(
            f"""
            select status, count(*) as n
            from '{manifest}'
            group by status
            order by status
            """
        ).fetchdf(),
        "catalog": con.execute(
            f"select count(*) as n_catalog from '{catalog}'"
        ).fetchdf(),
        "sample": con.execute(
            f"""
            select fire_id, region, year, total_area_km2, duration_hours / 24.0 as duration_days
            from '{traits}'
            using sample 12000 rows
            """
        ).fetchdf(),
        "quantiles": con.execute(
            f"""
            select
              quantile_cont(total_area_km2, 0.01) as area_p01,
              quantile_cont(total_area_km2, 0.10) as area_p10,
              quantile_cont(total_area_km2, 0.50) as area_p50,
              quantile_cont(total_area_km2, 0.90) as area_p90,
              quantile_cont(total_area_km2, 0.99) as area_p99,
              quantile_cont(duration_hours / 24.0, 0.01) as duration_p01,
              quantile_cont(duration_hours / 24.0, 0.10) as duration_p10,
              quantile_cont(duration_hours / 24.0, 0.50) as duration_p50,
              quantile_cont(duration_hours / 24.0, 0.90) as duration_p90,
              quantile_cont(duration_hours / 24.0, 0.99) as duration_p99
            from '{traits}'
            """
        ).fetchdf(),
    }


def _save_chart(path: Path, fig) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


def _make_charts(data: dict[str, pd.DataFrame], fig_dir: Path) -> dict[str, Path]:
    charts: dict[str, Path] = {}
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.edgecolor": "#777777",
            "axes.labelcolor": "#202124",
            "xtick.color": "#4b4b4b",
            "ytick.color": "#4b4b4b",
        }
    )

    by_year = data["by_year"]
    fig, ax = plt.subplots(figsize=(9.4, 3.1))
    ax.bar(by_year["year"], by_year["n"], color="#b12a1c", width=0.82)
    ax.set_title("Event count by ignition year", loc="left", fontsize=13, weight="bold")
    ax.set_xlabel("Year")
    ax.set_ylabel("Events")
    ax.grid(axis="y", color="#dddddd", linewidth=0.7)
    charts["year_counts"] = _save_chart(fig_dir / "year_counts.png", fig)

    by_region = data["by_region"]
    fig, ax = plt.subplots(figsize=(8.8, 3.7))
    ax.barh(by_region["region"], by_region["n"], color="#7f3b2d")
    ax.invert_yaxis()
    ax.set_title("Events by broad region", loc="left", fontsize=13, weight="bold")
    ax.set_xlabel("Events")
    ax.grid(axis="x", color="#dddddd", linewidth=0.7)
    charts["region_counts"] = _save_chart(fig_dir / "region_counts.png", fig)

    sample = data["sample"].copy()
    sample = sample[(sample["total_area_km2"] > 0) & (sample["duration_days"] > 0)]
    fig, ax = plt.subplots(figsize=(8.8, 3.6))
    ax.scatter(
        sample["total_area_km2"],
        sample["duration_days"],
        s=8,
        alpha=0.24,
        color="#1f6f78",
        edgecolors="none",
    )
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_title("Size-duration structure (sample of 12,000 events)", loc="left", fontsize=13, weight="bold")
    ax.set_xlabel("Final area (km2, log scale)")
    ax.set_ylabel("Duration (days, log scale)")
    ax.grid(color="#dddddd", linewidth=0.7)
    charts["area_duration"] = _save_chart(fig_dir / "area_duration.png", fig)

    fig, axes = plt.subplots(1, 2, figsize=(9.6, 3.4))
    axes[0].hist(np.log10(sample["total_area_km2"]), bins=52, color="#b12a1c", alpha=0.9)
    axes[0].set_title("Final area", loc="left", fontsize=12, weight="bold")
    axes[0].set_xlabel("log10 km2")
    axes[0].set_ylabel("Events")
    axes[0].grid(axis="y", color="#dddddd", linewidth=0.7)
    axes[1].hist(np.log10(sample["duration_days"]), bins=45, color="#1f6f78", alpha=0.9)
    axes[1].set_title("Duration", loc="left", fontsize=12, weight="bold")
    axes[1].set_xlabel("log10 days")
    axes[1].grid(axis="y", color="#dddddd", linewidth=0.7)
    charts["histograms"] = _save_chart(fig_dir / "histograms.png", fig)

    heat = data["by_region_year"].pivot(index="region", columns="year", values="n").fillna(0)
    fig, ax = plt.subplots(figsize=(9.6, 3.6))
    im = ax.imshow(heat.values, aspect="auto", cmap="YlOrRd")
    ax.set_yticks(range(len(heat.index)))
    ax.set_yticklabels(heat.index)
    ax.set_xticks(range(0, len(heat.columns), max(1, len(heat.columns) // 10)))
    ax.set_xticklabels([int(heat.columns[i]) for i in ax.get_xticks()])
    ax.set_title("Region-year event density", loc="left", fontsize=13, weight="bold")
    ax.set_xlabel("Ignition year")
    fig.colorbar(im, ax=ax, label="Events", fraction=0.03, pad=0.02)
    charts["region_year"] = _save_chart(fig_dir / "region_year.png", fig)

    return charts


def _table(rows, col_widths=None, font_size=8.5):
    table = Table(rows, colWidths=col_widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), font_size),
                ("LEADING", (0, 0), (-1, -1), font_size + 2),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d8d2ca")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fbfaf8")]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def _image(path: Path, width: float) -> Image:
    image = Image(str(path))
    ratio = image.imageHeight / image.imageWidth
    image.drawWidth = width
    image.drawHeight = width * ratio
    return image


def _callout(value: str, label: str, styles) -> Table:
    rows = [[value], [Paragraph(label, styles["CalloutLabel"])]]
    table = Table(rows, colWidths=[1.75 * inch], rowHeights=[0.38 * inch, 0.27 * inch])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), LIGHT),
                ("BOX", (0, 0), (-1, -1), 0.35, colors.HexColor("#d7d0c7")),
                ("FONTNAME", (0, 0), (0, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (0, 0), 22),
                ("TEXTCOLOR", (0, 0), (0, 0), ACCENT),
                ("ALIGN", (0, 0), (0, 0), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    return table


def build_pdf(table_root: Path, output_pdf: Path, work_dir: Path) -> dict:
    data = _query_tables(table_root)
    charts = _make_charts(data, work_dir / "figures")
    styles = _styles()

    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(output_pdf),
        pagesize=PAGE_SIZE,
        rightMargin=0.45 * inch,
        leftMargin=0.45 * inch,
        topMargin=0.42 * inch,
        bottomMargin=0.5 * inch,
        title="Fire VASE Population Summary Atlas",
        author="CubeDynamics",
    )

    overall = data["overall"].iloc[0]
    status = data["status"]
    quant = data["quantiles"].iloc[0]
    generated = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    story = []

    story += [
        Paragraph("Fire VASE Population Summary Atlas", styles["TitleLarge"]),
        Paragraph(
            "Full cached FIRED event source summarized from the CubeDynamics fire VASE lakehouse pilot tables. "
            "This PDF is a population atlas: rendered panels and individual VASE meshes remain derived assets, "
            "while the Parquet tables are the current data product.",
            styles["BodyText"],
        ),
        Spacer(1, 0.12 * inch),
        Rule(10.0 * inch),
        Spacer(1, 0.14 * inch),
        Table(
            [
                [
                    _callout(_fmt_int(overall["n_fires"]), "real FIRED event rows", styles),
                    _callout(f"{int(overall['min_year'])}-{int(overall['max_year'])}", "ignition years", styles),
                    _callout(_fmt_float(overall["total_area_km2"], 0), "total km2 recorded", styles),
                    _callout(_fmt_float(overall["median_area_km2"], 2), "median final km2", styles),
                    _callout(_fmt_float(overall["median_duration_days"], 1), "median duration days", styles),
                ]
            ],
            colWidths=[1.95 * inch] * 5,
        ),
        Spacer(1, 0.18 * inch),
        _image(charts["year_counts"], 9.8 * inch),
        Spacer(1, 0.10 * inch),
        Paragraph(
            f"Generated {generated}. Source tables: {table_root.as_posix()}. "
            "Rows are from the cached FIRED event GeoPackage normalized into Parquet by the lakehouse pilot.",
            styles["Small"],
        ),
        PageBreak(),
    ]

    by_region = data["by_region"]
    region_rows = [["Region", "Events", "Share", "Mean km2", "Median km2", "Total km2", "Mean days"]]
    total_n = float(overall["n_fires"])
    for row in by_region.to_dict("records"):
        region_rows.append(
            [
                row["region"],
                _fmt_int(row["n"]),
                f"{100 * row['n'] / total_n:.1f}%",
                _fmt_float(row["mean_area_km2"], 2),
                _fmt_float(row["median_area_km2"], 2),
                _fmt_float(row["total_area_km2"], 0),
                _fmt_float(row["mean_duration_days"], 1),
            ]
        )
    story += [
        Paragraph("Regional Structure", styles["Section"]),
        Table(
            [[_image(charts["region_counts"], 4.7 * inch), _table(region_rows, font_size=7.6)]],
            colWidths=[4.95 * inch, 5.05 * inch],
        ),
        PageBreak(),
    ]

    story += [
        Paragraph("Time And Region", styles["Section"]),
        _image(charts["region_year"], 9.7 * inch),
        Spacer(1, 0.12 * inch),
        Paragraph(
            "The heat map counts event records by broad centroid region and ignition year. "
            "This is a manifest-scale view, not a climate-attributed VASE rendering.",
            styles["Small"],
        ),
        PageBreak(),
    ]

    quant_rows = [
        ["Metric", "P01", "P10", "P50", "P90", "P99"],
        [
            "Final area (km2)",
            _fmt_float(quant["area_p01"], 3),
            _fmt_float(quant["area_p10"], 3),
            _fmt_float(quant["area_p50"], 3),
            _fmt_float(quant["area_p90"], 3),
            _fmt_float(quant["area_p99"], 3),
        ],
        [
            "Duration (days)",
            _fmt_float(quant["duration_p01"], 1),
            _fmt_float(quant["duration_p10"], 1),
            _fmt_float(quant["duration_p50"], 1),
            _fmt_float(quant["duration_p90"], 1),
            _fmt_float(quant["duration_p99"], 1),
        ],
    ]
    story += [
        Paragraph("Size And Duration", styles["Section"]),
        Table(
            [[_image(charts["area_duration"], 5.2 * inch), _image(charts["histograms"], 4.6 * inch)]],
            colWidths=[5.25 * inch, 4.75 * inch],
        ),
        Spacer(1, 0.12 * inch),
        _table(quant_rows, col_widths=[1.9 * inch, 1.1 * inch, 1.1 * inch, 1.1 * inch, 1.1 * inch, 1.1 * inch]),
        PageBreak(),
    ]

    largest = data["largest"]
    largest_rows = [["Fire ID", "Region", "Year", "Final area km2", "Duration days", "Peak growth km2/day"]]
    for row in largest.head(15).to_dict("records"):
        largest_rows.append(
            [
                row["fire_id"],
                row["region"],
                str(int(row["year"])),
                _fmt_float(row["total_area_km2"], 2),
                _fmt_float(row["duration_days"], 1),
                _fmt_float(row["peak_growth_km2_per_day"], 2),
            ]
        )
    story += [
        Paragraph("Largest Events", styles["Section"]),
        _table(largest_rows, col_widths=[1.0 * inch, 1.55 * inch, 0.65 * inch, 1.25 * inch, 1.1 * inch, 1.35 * inch]),
        Spacer(1, 0.12 * inch),
        Paragraph(
            "These rows are ranked from the normalized trait table, using FIRED total area and duration attributes. "
            "They are candidates for later individual VASE rendering or climate-attributed review.",
            styles["Small"],
        ),
        PageBreak(),
    ]

    long_rows = [["Fire ID", "Region", "Year", "Final area km2", "Duration days"]]
    for row in data["duration_top"].head(15).to_dict("records"):
        long_rows.append(
            [
                row["fire_id"],
                row["region"],
                str(int(row["year"])),
                _fmt_float(row["total_area_km2"], 2),
                _fmt_float(row["duration_days"], 1),
            ]
        )
    story += [
        Paragraph("Longest Duration Events", styles["Section"]),
        _table(long_rows, col_widths=[1.05 * inch, 1.65 * inch, 0.75 * inch, 1.35 * inch, 1.25 * inch]),
        Spacer(1, 0.16 * inch),
        Paragraph("Processing Status", styles["Section"]),
        _table(
            [["Status", "Rows"]]
            + [[row["status"], _fmt_int(row["n"])] for row in status.to_dict("records")],
            col_widths=[2.2 * inch, 1.2 * inch],
        ),
        Spacer(1, 0.12 * inch),
        Paragraph(
            "All rows in this atlas are at geometry_complete in the current pilot manifest. "
            "Climate, event, trait refinement, VASE slice, and render completion can advance independently as component versions mature.",
            styles["Small"],
        ),
        PageBreak(),
    ]

    story += [
        Paragraph("Provenance And Limits", styles["Section"]),
        _table(
            [
                ["Field", "Value"],
                ["PDF", output_pdf.as_posix()],
                ["Table root", table_root.as_posix()],
                ["Catalog rows", _fmt_int(data["catalog"].iloc[0]["n_catalog"])],
                ["Trait rows", _fmt_int(overall["n_fires"])],
                ["Processing status", "; ".join(f"{r.status}: {_fmt_int(r.n)}" for r in status.itertuples())],
                ["Generated", generated],
            ],
            col_widths=[1.75 * inch, 7.45 * inch],
            font_size=8.2,
        ),
        Spacer(1, 0.18 * inch),
        Paragraph(
            "Important limit: this atlas summarizes fire-event metadata and derived pilot traits for the full cached FIRED event table. "
            "It does not yet include per-fire hourly climate extraction, ring-level VASE slices, climate-colored VASE panels, or rendered meshes for every fire. "
            "Those products are designed to be written as external lakehouse assets and then registered back to the manifest.",
            styles["BodyText"],
        ),
    ]

    doc.build(story, onFirstPage=_page, onLaterPages=_page)

    return {
        "pdf": output_pdf.as_posix(),
        "table_root": table_root.as_posix(),
        "pages": 7,
        "n_fires": int(overall["n_fires"]),
        "generated_at": generated,
        "figures": {name: path.as_posix() for name, path in charts.items()},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--table-root", default="scratch/fire_vase_run_full/tables")
    parser.add_argument("--output", default="output/pdf/fire_vase_population_summary_atlas.pdf")
    parser.add_argument("--work-dir", default="tmp/pdfs/fire_vase_population_summary_atlas")
    parser.add_argument("--manifest", default="output/pdf/fire_vase_population_summary_atlas_manifest.json")
    args = parser.parse_args()

    report = build_pdf(Path(args.table_root), Path(args.output), Path(args.work_dir))
    manifest_path = Path(args.manifest)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
