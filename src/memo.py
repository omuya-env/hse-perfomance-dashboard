"""Build the one-page monthly HSE report memo (PDF via reportlab)."""

from __future__ import annotations

import argparse

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (HRFlowable, Image, PageBreak, Paragraph,
                                SimpleDocTemplate, Spacer, Table, TableStyle)

import src.config as cfg
from src.kpi import kpis_by_department_month, kpis_by_month, ytd_summary, worst_department

# ============================================================
# PAGE GEOMETRY AND BRAND STYLE
# ============================================================

PAGE_W, PAGE_H = A4
MARGIN_X, MARGIN_TOP, MARGIN_BOTTOM = 18 * mm, 16 * mm, 16 * mm
FRAME_W = PAGE_W - 2 * MARGIN_X

NAVY = colors.HexColor("#1f4e79")
RULE = colors.HexColor("#c8d3de")
GRID = colors.HexColor("#d6dde6")
MUTED = colors.HexColor("#5a6672")
BAND = colors.HexColor("#f4f7fb")
RAG_TINT = {"Green": colors.HexColor("#e8f5e9"),
            "Amber": colors.HexColor("#fff8e1"),
            "Red": colors.HexColor("#ffebee")}

# Height cap for embedded charts: 74mm is the largest height that keeps two wide
# figures plus the tables and text on a single page.
MAX_CHART_H = 74 * mm

ACTION_LIBRARY = {
    "Equipment Maintenance":
        "Accelerate the planned-maintenance backlog review and require supervisor "
        "sign-off on equipment isolation before restart.",
    "Inadequate Procedure":
        "Review and reissue the affected work procedures with crew briefings this month.",
    "Inadequate Training":
        "Run targeted toolbox training for the affected crew and verify competence records.",
    "Poor Supervision":
        "Increase supervisor presence on shift and audit permit-to-work compliance.",
    "Risk Assessment Gap":
        "Reassess the risk assessments for the affected tasks and update control measures.",
    "Housekeeping Management":
        "Launch a weekly housekeeping walk-down with published scores per area.",
    "PPE Management":
        "Audit PPE stock, fit and usage in the affected area and re-brief the crew.",
    "Workload/Staffing":
        "Review shift staffing and overtime during high-risk maintenance windows.",
    "Communication":
        "Reinforce shift handover standards and brief the findings at the next toolbox talk.",
    "Environmental Conditions":
        "Review lighting and floor conditions in the affected areas and fix defects found.",
    "Other":
        "Conduct a dedicated incident-review meeting and agree corrective actions with owners.",
}

CHART_CHOICES = [
    ("trend", "trir_ltif_trend.png"),
    ("spc", "spc_trir_control_chart.png"),
    ("pareto", "department_pareto.png"),
    ("heatmap", "dept_event_heatmap.png"),
    ("histogram", "days_lost_histogram.png"),
    ("leading", "leading_vs_lagging.png"),
    ("rag", "trir_rag_monthly.png"),
]


def choose_actions(log: pd.DataFrame, year: str, worst: str, n: int = 2) -> list[str]:
    """Pick the n most frequent root causes for the worst department's YTD recordables."""
    ytd = log[log["Month"].str.startswith(year)]
    focus = ytd[(ytd["Department"] == worst) & ytd["Recordable"]]
    counts = focus["Root Cause"].value_counts()
    actions = [ACTION_LIBRARY.get(rc, ACTION_LIBRARY["Other"]) for rc in counts.index]
    return actions[:n] if actions else [ACTION_LIBRARY["Other"]]


def rag_color(value: float, target: float, higher_is_better: bool = False) -> colors.Color:
    """Map a KPI value to a RAG colour for the memo tables."""
    status = cfg.rag_status(value, target, higher_is_better)
    return {"Green": colors.HexColor("#2e7d32"),
            "Amber": colors.HexColor("#f9a825"),
            "Red": colors.HexColor("#c62828")}[status]


def _styles() -> dict[str, ParagraphStyle]:
    """Return the memo's paragraph styles."""
    base = getSampleStyleSheet()["Normal"]
    return {
        "title": ParagraphStyle("MemoTitle", parent=base, fontName="Helvetica-Bold",
                                fontSize=16, leading=19, textColor=NAVY),
        "meta": ParagraphStyle("MemoMeta", parent=base, fontSize=8, leading=10.5, textColor=MUTED),
        "h2": ParagraphStyle("MemoH2", parent=base, fontName="Helvetica-Bold", fontSize=9.8,
                             leading=12, textColor=NAVY, spaceBefore=5, spaceAfter=1),
        "body": ParagraphStyle("MemoBody", parent=base, fontSize=8.8, leading=12.2,
                               alignment=TA_JUSTIFY, spaceAfter=2.5),
        "bullet": ParagraphStyle("MemoBullet", parent=base, fontSize=8.8, leading=12.2,
                                 alignment=TA_JUSTIFY, leftIndent=13, bulletIndent=2,
                                 spaceAfter=1.5),
        "note": ParagraphStyle("MemoNote", parent=base, fontSize=7, leading=9, textColor=MUTED),
    }


def _heading(text: str, style: ParagraphStyle) -> list:
    """Return a section heading followed by a hairline rule."""
    return [Paragraph(text, style),
            HRFlowable(width="100%", thickness=0.5, color=RULE, spaceBefore=0.5, spaceAfter=3)]


def _headline_table(headline: list[list[str]], rag_vals: list[tuple]) -> Table:
    """Build the headline KPI table with banded rows and RAG status tints."""
    table = Table(headline, hAlign="LEFT",
                  colWidths=[FRAME_W - 3 * 28 * mm, 28 * mm, 28 * mm, 28 * mm])
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (1, 1), (1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.4),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("LINEBELOW", (0, 0), (-1, -2), 0.4, GRID),
        ("BOX", (0, 0), (-1, -1), 0.5, GRID),
    ]
    for i, (value, target, higher) in enumerate(rag_vals, start=1):
        status = cfg.rag_status(value, target, higher)
        style += [("BACKGROUND", (3, i), (3, i), RAG_TINT[status]),
                  ("TEXTCOLOR", (3, i), (3, i), rag_color(value, target, higher)),
                  ("FONTNAME", (3, i), (3, i), "Helvetica-Bold")]
        if i % 2 == 0:
            style.append(("BACKGROUND", (0, i), (2, i), BAND))
    table.setStyle(TableStyle(style))
    return table


def _footer(canvas, doc) -> None:
    """Draw the running footer with the synthetic-data disclaimer."""
    canvas.saveState()
    canvas.setStrokeColor(RULE)
    canvas.setLineWidth(0.5)
    canvas.line(MARGIN_X, 12 * mm, PAGE_W - MARGIN_X, 12 * mm)
    canvas.setFont("Helvetica", 6.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(MARGIN_X, 8.5 * mm, "Monthly HSE Performance Report | synthetic "
                                          "demonstration data, not real incident records")
    canvas.drawRightString(PAGE_W - MARGIN_X, 8.5 * mm, f"Page {canvas.getPageNumber()}")
    canvas.restoreState()


def build_memo(month: str | None = None, charts: list[str] | None = None) -> None:
    """Generate the one-page memo PDF for the given month (default: latest)."""
    log = pd.read_csv(cfg.CLEAN_LOG, parse_dates=["date"])
    kpi = kpis_by_month(log)
    dept = kpis_by_department_month(log)

    if month:
        kpi = kpi[kpi["Month"] <= month]
        if kpi.empty:
            raise ValueError(f"No data on or before {month}")
    ytd = ytd_summary(kpi)
    st = _styles()

    # ---- Headline KPI table ------------------------------------------------
    rag_vals = [
        (ytd["trir"], cfg.TARGETS["TRIR"], False),
        (ytd["ltif"], cfg.TARGETS["LTIF"], False),
        (ytd["severity"], cfg.TARGETS["Severity Rate"], False),
        (ytd["near_miss_ratio"], cfg.TARGETS["Near Miss Ratio"], True),
    ]
    headline = [
        ["Indicator", f"YTD {ytd['year']}", "Target", "Status"],
        ["TRIR (recordables per 200,000 hours)", f"{ytd['trir']:.2f}", "<= 3.0", ""],
        ["LTIF (lost time injuries per 1,000,000 hours)", f"{ytd['ltif']:.2f}", "<= 3.0", ""],
        ["Severity rate (days lost per 1,000,000 hours)", f"{ytd['severity']:.1f}", "<= 15", ""],
        ["Near-miss ratio (% of all reported events)",
         f"{ytd['near_miss_ratio']:.1f}%", ">= 80%", ""],
    ]
    for i, (value, target, higher) in enumerate(rag_vals, start=1):
        headline[i][3] = cfg.rag_status(value, target, higher)

    story = [
        Paragraph("Monthly HSE Performance Report", st["title"]),
        HRFlowable(width="100%", thickness=1.1, color=NAVY, spaceBefore=2, spaceAfter=3.5),
        Paragraph(f"Site: Demo Industrial Facility (synthetic data) &nbsp;|&nbsp; Reporting month: "
                  f"<b>{ytd['month']}</b> &nbsp;|&nbsp; Prepared by: HSE Analyst &nbsp;|&nbsp; "
                  f"For: Site Manager", st["meta"]),
        Spacer(1, 4 * mm),
        *_heading("Headline KPIs", st["h2"]),
        _headline_table(headline, rag_vals),
        Spacer(1, 3 * mm),
    ]

    # ---- Summary and requested actions ------------------------------------
    worst, _dept_rates = worst_department(dept, ytd["year"])
    narrative = (
        f"Through <b>{ytd['month']}</b> the site recorded <b>{ytd['recordables']} recordable "
        f"injuries</b> and <b>{ytd['lti']} lost time injuries</b> over "
        f"{ytd['man_hours']:,.0f} man-hours, with {ytd['days_lost']} days lost. "
        f"{ytd['near_miss']} near misses were reported, {ytd['near_miss_ratio']:.0f}% of all "
        f"events, and {ytd['inspections']:,} safety inspections were completed. "
        f"<b>{worst}</b> carries the highest year-to-date recordable rate, so it is this "
        "month's focus area."
    )
    story += _heading(f"Summary: focus area is {worst}", st["h2"])
    story.append(Paragraph(narrative, st["body"]))
    story.append(Spacer(1, 1 * mm))
    for i, action in enumerate(choose_actions(log, ytd["year"], worst), start=1):
        story.append(Paragraph(action, st["bullet"], bulletText=f"{i}."))
    story.append(Spacer(1, 2 * mm))

    # ---- Charts -------------------------------------------------------------
    chart_map = dict(CHART_CHOICES)
    picks = charts or ["trend", "spc"]
    story += _heading("Trend detail", st["h2"])
    for pick in picks:
        path = cfg.FIGURES_DIR / chart_map[pick]
        if path.exists():
            img = Image(str(path), width=FRAME_W, height=MAX_CHART_H, kind="proportional")
            img.hAlign = "CENTER"
            story += [img, Spacer(1, 2.5 * mm)]

    # ---- One-page discipline -------------------------------------------------
    if len(picks) > 2:
        story.append(PageBreak())

    story.append(Paragraph(
        "Formulas: TRIR = recordables x 200,000 / man-hours; LTIF = lost time injuries x "
        "1,000,000 / man-hours; severity rate = days lost x 1,000,000 / man-hours; near-miss "
        "ratio = near misses / all reported events. Man-hours are 500 employees x 8-hour "
        "shifts x working days per month.", st["note"]))

    cfg.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(cfg.MEMO_PDF), pagesize=A4,
        leftMargin=MARGIN_X, rightMargin=MARGIN_X,
        topMargin=MARGIN_TOP, bottomMargin=MARGIN_BOTTOM,
        title="Monthly HSE Performance Report",
        author="HSE Analytics",
        subject="Monthly HSE performance against TRIR, LTIF, severity and near-miss targets",
        creator="hse-performance-dashboard",
    )
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    print(f"Memo written: {cfg.MEMO_PDF}")
    print(f"  month: {ytd['month']}, worst dept: {worst}, charts: {picks}")


def main() -> None:
    """CLI entry point: python -m src.memo [--month YYYY-MM] [--charts trend spc ...]."""
    parser = argparse.ArgumentParser(description="Build the one-page HSE memo PDF")
    parser.add_argument("--month", help="Reporting month as YYYY-MM (default: latest)")
    parser.add_argument("--charts", nargs="*", choices=[c for c, _ in CHART_CHOICES],
                        help="Which figures to embed (default: trend spc)")
    args = parser.parse_args()
    build_memo(month=args.month, charts=args.charts)


if __name__ == "__main__":
    main()
