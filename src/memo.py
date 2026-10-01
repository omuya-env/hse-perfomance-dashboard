"""Build the one-page monthly HSE report memo (PDF via reportlab)."""

from __future__ import annotations

import argparse

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (Image, PageBreak, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle)

import src.config as cfg
from src.kpi import kpis_by_department_month, kpis_by_month, ytd_summary, worst_department

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

    styles = getSampleStyleSheet()
    small = ParagraphStyle("small", parent=styles["Normal"], fontSize=8, leading=10)
    h1 = ParagraphStyle("h1x", parent=styles["Title"], fontSize=15, spaceAfter=2)

    story = [
        Paragraph("Monthly HSE Performance Report", h1),
        Paragraph(
            f"Site: Demo Industrial Facility (synthetic data) | Reporting month: "
            f"{ytd['month']} | Prepared by: HSE Analyst | For: Site Manager",
            small,
        ),
        Spacer(1, 4 * mm),
    ]

    # ---- Headline KPI table ------------------------------------------------
    headline = [
        ["Indicator", "YTD " + ytd["year"], "Target", "Status"],
        ["TRIR", f"{ytd['trir']:.2f}", "<= 3.0", ""],
        ["LTIF", f"{ytd['ltif']:.2f}", "<= 3.0", ""],
        ["Severity rate (days lost x 1M / hours)", f"{ytd['severity']:.1f}", "<= 15", ""],
        ["Near-miss ratio", f"{ytd['near_miss_ratio']:.1f}%", ">= 80%", ""],
    ]
    rag_vals = [
        (ytd["trir"], cfg.TARGETS["TRIR"], False),
        (ytd["ltif"], cfg.TARGETS["LTIF"], False),
        (ytd["severity"], cfg.TARGETS["Severity Rate"], False),
        (ytd["near_miss_ratio"], cfg.TARGETS["Near Miss Ratio"], True),
    ]
    status_texts = []
    for value, target, hib in rag_vals:
        status_texts.append(cfg.rag_status(value, target, hib))
        headline[len(status_texts)][3] = status_texts[-1]

    table = Table(headline, colWidths=[70 * mm, 25 * mm, 25 * mm, 22 * mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f4e79")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        *[("TEXTCOLOR", (3, i), (3, i), rag_color(v, t, h))
          for i, (v, t, h) in enumerate(rag_vals, start=1)],
    ]))
    story += [table, Spacer(1, 3 * mm)]

    # ---- Narrative ----------------------------------------------------------
    worst, dept_table = worst_department(dept, ytd["year"])
    narrative = (
        f"<b>Headline:</b> Through {ytd['month']} the site recorded {ytd['recordables']} "
        f"recordable injuries and {ytd['lti']} lost time injuries over "
        f"{ytd['man_hours']:,.0f} man-hours (YTD TRIR {ytd['trir']:.2f}, LTIF "
        f"{ytd['ltif']:.2f}). {ytd['near_miss']} near misses were reported "
        f"({ytd['near_miss_ratio']:.0f}% of all events). "
        f"<b>Focus area:</b> {worst} carries the highest year-to-date recordable rate. "
        f"<b>Requested actions:</b> the two actions below go to the {worst} superintendent."
    )
    story.append(Paragraph(narrative, styles["Normal"]))

    actions = choose_actions(log, ytd["year"], worst)
    story.append(Spacer(1, 2 * mm))
    for i, action in enumerate(actions, start=1):
        story.append(Paragraph(f"<b>Action {i}:</b> {action}", styles["Normal"]))
        story.append(Spacer(1, 1 * mm))

    story.append(Spacer(1, 3 * mm))

    # ---- Charts -------------------------------------------------------------
    chart_map = dict(CHART_CHOICES)
    picks = charts or ["trend", "spc"]
    for pick in picks:
        filename = chart_map[pick]
        path = cfg.FIGURES_DIR / filename
        if path.exists():
            img = Image(str(path), width=170 * mm, height=77 * mm)
            img._restrictSize(170 * mm, 77 * mm)
            story.append(img)
        story.append(Spacer(1, 2 * mm))

    # ---- One-page discipline -------------------------------------------------
    if len(picks) > 2:
        story.append(PageBreak())

    story.append(Paragraph(
        "SYNTHETIC DATA: all figures derive from a generated demonstration dataset, "
        "not real incident records. Man-hours are derived from 500 employees x 8-hour "
        "shifts x working days.", small))
    story.append(Paragraph(
        "Formulas: LTIF = LTI x 1,000,000 / man-hours; TRIR = recordables x 200,000 / "
        "man-hours; severity rate = days lost x 1,000,000 / man-hours.", small))

    cfg.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(cfg.MEMO_PDF), pagesize=A4,
        topMargin=12 * mm, bottomMargin=12 * mm, leftMargin=15 * mm, rightMargin=15 * mm,
        title="Monthly HSE Performance Report",
    )
    doc.build(story)
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
