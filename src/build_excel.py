"""Build the Excel KPI dashboard workbook (Config, Incident Log, Monthly KPIs, Dashboard)."""

from __future__ import annotations

from collections import Counter

import pandas as pd
from openpyxl import Workbook
from openpyxl.chart import BarChart, LineChart, Reference, ScatterChart, Series
from openpyxl.chart.trendline import Trendline
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

import src.config as cfg
from src.kpi import kpis_by_department_month, kpis_by_month

GREEN = PatternFill("solid", fgColor="C6EFCE")
AMBER = PatternFill("solid", fgColor="FFEB9C")
RED = PatternFill("solid", fgColor="FFC7CE")
NAVY = PatternFill("solid", fgColor="1F4E79")
LIGHT = PatternFill("solid", fgColor="D9E1F2")
BOLD = Font(bold=True)
WHITE_BOLD = Font(bold=True, color="FFFFFF")
THIN = Border(bottom=Side(style="thin"))
RAG_MAP = {"Green": GREEN, "Amber": AMBER, "Red": RED}


def _rag_fills(ws, column_letter: str, first_row: int, last_row: int) -> None:
    """Apply green/amber/red fills to a RAG text column."""
    for row in range(first_row, last_row + 1):
        value = ws[f"{column_letter}{row}"].value
        fill = RAG_MAP.get(value)
        if fill:
            ws[f"{column_letter}{row}"].fill = fill


def _write_table(ws, df: pd.DataFrame, widths: dict[int, int] | None = None) -> None:
    """Write a dataframe as a styled table starting at A1."""
    ws.append(list(df.columns))
    for cell in ws[1]:
        cell.font = WHITE_BOLD
        cell.fill = NAVY
        cell.alignment = Alignment(horizontal="center")
    for record in df.itertuples(index=False):
        ws.append(list(record))
    for col in range(1, len(df.columns) + 1):
        letter = get_column_letter(col)
        width = (widths or {}).get(col, max(11, len(str(df.columns[col - 1])) + 3))
        ws.column_dimensions[letter].width = width
    ws.freeze_panes = "A2"


def build_config_sheet(wb: Workbook) -> None:
    """Write site profile, targets and RAG rules on the Config sheet."""
    ws = wb.create_sheet("Config")
    ws["A1"] = "HSE DASHBOARD CONFIG"
    ws["A1"].font = Font(bold=True, size=14)

    ws["A3"], ws["B3"] = "Site employees", cfg.EMPLOYEES
    ws["A4"], ws["B4"] = "Hours per shift", cfg.HOURS_PER_SHIFT
    ws["A5"], ws["B5"] = "Study period", f"{cfg.PERIOD_START} to {cfg.PERIOD_END}"
    ws["A6"], ws["B6"] = "Note", "Man-hours = employees x hours x working days per month"

    ws["A8"] = "KPI TARGETS"
    ws["A8"].font = BOLD
    ws["A9"], ws["B9"], ws["C9"] = "KPI", "Target", "Direction"
    for cell in ws[9]:
        if cell.value:
            cell.font = BOLD
            cell.fill = LIGHT
    rows = [
        ("TRIR", cfg.TARGETS["TRIR"], "<= target"),
        ("LTIF", cfg.TARGETS["LTIF"], "<= target"),
        ("Severity Rate", cfg.TARGETS["Severity Rate"], "<= target"),
        ("Near Miss Ratio", cfg.TARGETS["Near Miss Ratio"], ">= target"),
    ]
    for i, row in enumerate(rows, start=10):
        ws[f"A{i}"], ws[f"B{i}"], ws[f"C{i}"] = row

    ws["A15"] = "RAG RULES"
    ws["A15"].font = BOLD
    ws["A16"], ws["B16"] = "Green", "meets target"
    ws["A17"], ws["B17"] = "Amber", "within 20% of target"
    ws["A18"], ws["B18"] = "Red", "outside 20% of target"
    ws.column_dimensions["A"].width = 22
    ws.column_dimensions["B"].width = 40
    ws.column_dimensions["C"].width = 14


def build_log_sheet(wb: Workbook, log: pd.DataFrame) -> None:
    """Write the full cleaned incident log with a filterable header row."""
    ws = wb.create_sheet("Incident Log")
    cols = ["incident_id", "date", "Shift", "Department", "Event Type", "Body Part",
            "Immediate Cause", "Root Cause", "Days Lost", "Contractor"]
    out = log[cols].copy()
    out["date"] = out["date"].dt.strftime("%Y-%m-%d")
    _write_table(ws, out)
    ws.auto_filter.ref = ws.dimensions


def build_kpi_sheet(wb: Workbook, kpi: pd.DataFrame) -> None:
    """Write the monthly KPI table and colour the RAG columns."""
    ws = wb.create_sheet("Monthly KPIs")
    _write_table(ws, kpi, widths={1: 10, 2: 13})
    header = [c.value for c in ws[1]]
    for name in ["RAG TRIR", "RAG LTIF", "RAG Severity", "RAG Near Miss"]:
        col = get_column_letter(header.index(name) + 1)
        _rag_fills(ws, col, 2, len(kpi) + 1)
    ws.auto_filter.ref = ws.dimensions


def build_dashboard_sheet(wb: Workbook, kpi: pd.DataFrame, log: pd.DataFrame) -> None:
    """Create the dashboard: KPI cards, YTD-vs-target boxes, charts and RAG formatting."""
    ws = wb.create_sheet("Dashboard")
    ws.sheet_view.showGridLines = False
    ws.column_dimensions["A"].width = 2

    ws["B2"] = "HSE PERFORMANCE DASHBOARD"
    ws["B2"].font = Font(bold=True, size=18, color="1F4E79")
    ws["B3"] = f"Synthetic site log, {cfg.PERIOD_START} to {cfg.PERIOD_END}, {cfg.EMPLOYEES} employees"
    ws["B3"].font = Font(italic=True, size=10)

    ytd = kpi.iloc[-1]
    year = ytd["Month"][:4]
    ytd_rows = kpi[kpi["Month"].str.startswith(year)]

    # ---- KPI cards -----------------------------------------------------
    cards = [
        ("YTD TRIR", ytd_rows["Recordables"].sum() * 200_000 / ytd_rows["Man-Hours"].sum(),
         cfg.TARGETS["TRIR"], "2.22"),
        ("YTD LTIF", ytd_rows["Lost Time Injury"].sum() * 1_000_000 / ytd_rows["Man-Hours"].sum(),
         cfg.TARGETS["LTIF"], "2.22"),
        ("YTD Severity", ytd_rows["Days Lost"].sum() * 1_000_000 / ytd_rows["Man-Hours"].sum(),
         cfg.TARGETS["Severity Rate"], "2.22"),
        ("YTD Near Miss %", ytd_rows["Near Miss"].sum() * 100 / ytd_rows["Total Incidents"].sum(),
         cfg.TARGETS["Near Miss Ratio"], "2.22"),
    ]
    card_cols = [2, 4, 6, 8]
    for (label, value, target, fmt), col in zip(cards, card_cols):
        status = cfg.rag_status(value, target, higher_is_better="Near Miss" in label)
        fill = RAG_MAP[status]
        for r, text in [(5, label), (6, round(value, 2)), (7, f"target {'>=' if 'Near Miss' in label else '<='} {target}")]:
            cell = ws.cell(row=r, column=col, value=text)
            cell.font = Font(bold=(r == 6), size=(14 if r == 6 else 10))
            cell.fill = fill
        ws.merge_cells(start_row=5, start_column=col, end_row=5, end_column=col + 1)
        ws.merge_cells(start_row=6, start_column=col, end_row=6, end_column=col + 1)
        ws.merge_cells(start_row=7, start_column=col, end_row=7, end_column=col + 1)

    # ---- Monthly KPI mini table (chart data source) ---------------------
    start = 10
    ws.cell(row=start - 1, column=2, value="MONTHLY KPIS").font = BOLD
    headers = ["Month", "TRIR", "LTIF", "Severity Rate", "Near Miss %", "Near Miss",
               "Inspections", "Injuries", "RAG TRIR", "RAG LTIF"]
    for j, h in enumerate(headers, start=2):
        cell = ws.cell(row=start, column=j, value=h)
        cell.font = WHITE_BOLD
        cell.fill = NAVY
        cell.alignment = Alignment(horizontal="center")
    for i, row in kpi.iterrows():
        r = start + 1 + i
        ws.cell(row=r, column=2, value=row["Month"])
        for j, key in enumerate(["TRIR", "LTIF", "Severity Rate", "Near Miss Ratio"],
                                start=3):
            ws.cell(row=r, column=j, value=round(float(row[key]), 2))
        ws.cell(row=r, column=7, value=int(row["Near Miss"]))
        ws.cell(row=r, column=8, value=int(row["Inspections"]))
        ws.cell(row=r, column=9, value=int(row["First Aid"] + row["Medical Treatment"] + row["Lost Time Injury"]))
        ws.cell(row=r, column=10, value=row["RAG TRIR"])
        ws.cell(row=r, column=11, value=row["RAG LTIF"])
        ws.cell(row=r, column=10).fill = RAG_MAP[row["RAG TRIR"]]
        ws.cell(row=r, column=11).fill = RAG_MAP[row["RAG LTIF"]]
    first, last = start + 1, start + len(kpi)

    # ---- Charts ---------------------------------------------------------
    line = LineChart()
    line.title = "TRIR and LTIF monthly trend (18 months)"
    line.y_axis.title = "Rate per exposure base"
    line.x_axis.title = "Month"
    line.height, line.width = 8, 20
    data = Reference(ws, min_col=3, max_col=4, min_row=start, max_row=last)
    cats = Reference(ws, min_col=2, min_row=first, max_row=last)
    line.add_data(data, titles_from_data=True)
    line.set_categories(cats)
    ws.add_chart(line, f"B{last + 3}")

    bar = BarChart()
    bar.type, bar.grouping = "col", "stacked"
    bar.overlap = 100
    bar.title = "Leading vs lagging indicators (stacked monthly)"
    bar.y_axis.title = "Count"
    bar.height, bar.width = 8, 20
    lead = Reference(ws, min_col=7, max_col=8, min_row=start, max_row=last)
    bar.add_data(lead, titles_from_data=True)
    bar.set_categories(cats)
    ws.add_chart(bar, f"L{last + 3}")

    injuries = BarChart()
    injuries.type = "col"
    injuries.title = "Monthly injuries by event type"
    injuries.y_axis.title = "Count"
    injuries.height, injuries.width = 8, 20
    inj = Reference(ws, min_col=9, max_col=9, min_row=start, max_row=last)
    injuries.add_data(inj, titles_from_data=True)
    injuries.set_categories(cats)
    ws.add_chart(injuries, f"B{last + 21}")

    # ---- Department Pareto ---------------------------------------------
    dept_counts = Counter(log["Department"])
    p_row = last + 39
    ws.cell(row=p_row - 1, column=2, value="DEPARTMENT PARETO (18 MONTHS)").font = BOLD
    ws.cell(row=p_row, column=2, value="Department").font = BOLD
    ws.cell(row=p_row, column=3, value="Incidents").font = BOLD
    ws.cell(row=p_row, column=4, value="Cumulative %").font = BOLD
    ordered = dept_counts.most_common()
    total = sum(dept_counts.values())
    cum = 0
    for i, (dept, n) in enumerate(ordered, start=1):
        cum += n
        ws.cell(row=p_row + i, column=2, value=dept)
        ws.cell(row=p_row + i, column=3, value=n)
        ws.cell(row=p_row + i, column=4, value=round(cum * 100 / total, 1))

    pareto = BarChart()
    pareto.type = "col"
    pareto.title = "Department Pareto of incidents"
    pareto.y_axis.title = "Incidents"
    pareto.height, pareto.width = 8, 14
    pareto.add_data(Reference(ws, min_col=3, min_row=p_row, max_row=p_row + len(ordered)),
                    titles_from_data=True)
    pareto.set_categories(Reference(ws, min_col=2, min_row=p_row + 1, max_row=p_row + len(ordered)))
    ws.add_chart(pareto, f"G{p_row + 1}")

    cum_line = ScatterChart()
    cum_line.title = "Pareto cumulative percentage"
    cum_line.y_axis.title = "Cumulative %"
    cum_line.height, cum_line.width = 8, 14
    cum_line.y_axis.scaling.min, cum_line.y_axis.scaling.max = 0, 100
    cum_line.series = [Series(
        Reference(ws, min_col=4, min_row=p_row + 1, max_row=p_row + len(ordered)),
        xvalues=Reference(ws, min_col=2, min_row=p_row + 1, max_row=p_row + len(ordered)),
        title="Cumulative %",
    )]
    ws.add_chart(cum_line, f"N{p_row + 1}")

    # ---- Days-lost histogram --------------------------------------------
    lti_days = log.loc[log["Event Type"] == cfg.LOST_TIME_INJURY, "Days Lost"]
    h_row = p_row + len(ordered) + 4
    ws.cell(row=h_row - 1, column=2, value="DAYS LOST DISTRIBUTION (LTI CASES)").font = BOLD
    bins = [1, 3, 5, 7, 10, 15]
    labels = ["1-2", "3-4", "5-6", "7-9", "10-14", "15+"]
    counts = [0] * len(bins)
    for d in lti_days:
        for i, b in enumerate(bins):
            if d <= b:
                counts[i] += 1
                break
        else:
            counts[-1] += 1
    ws.cell(row=h_row, column=2, value="Bucket").font = BOLD
    ws.cell(row=h_row, column=3, value="Cases").font = BOLD
    for i, (lab, n) in enumerate(zip(labels, counts), start=1):
        ws.cell(row=h_row + i, column=2, value=lab)
        ws.cell(row=h_row + i, column=3, value=n)

    hist = BarChart()
    hist.type = "col"
    hist.title = "Days lost histogram (LTI cases)"
    hist.y_axis.title = "Cases"
    hist.height, hist.width = 8, 14
    hist.add_data(Reference(ws, min_col=3, min_row=h_row, max_row=h_row + len(labels)),
                  titles_from_data=True)
    hist.set_categories(Reference(ws, min_col=2, min_row=h_row + 1, max_row=h_row + len(labels)))
    ws.add_chart(hist, f"G{h_row + 1}")

    # ---- YTD vs target boxes (live Excel formulas) -----------------------
    # Column letters resolved from the Monthly KPIs sheet layout
    # (A Month, B Phase, C Man-Hours, D Near Miss, ... G LTI, H Recordables,
    #  I Total Incidents, J Days Lost).
    f_row = h_row + len(labels) + 4
    ws.cell(row=f_row - 1, column=2, value=f"YTD {year} VS TARGET").font = BOLD
    kpi_sheet = "'Monthly KPIs'"
    y0 = int(kpi.index[kpi["Month"].str.startswith(year)][0]) + 2
    y1 = len(kpi) + 1
    boxes = [
        ("TRIR (target <= 3.0)",
         f"=SUM({kpi_sheet}!H{y0}:H{y1})*200000/SUM({kpi_sheet}!C{y0}:C{y1})"),
        ("LTIF (target <= 3.0)",
         f"=SUM({kpi_sheet}!G{y0}:G{y1})*1000000/SUM({kpi_sheet}!C{y0}:C{y1})"),
        ("Severity (target <= 15)",
         f"=SUM({kpi_sheet}!J{y0}:J{y1})*1000000/SUM({kpi_sheet}!C{y0}:C{y1})"),
        ("Near Miss % (target >= 80)",
         f"=SUM({kpi_sheet}!D{y0}:D{y1})/SUM({kpi_sheet}!I{y0}:I{y1})*100"),
    ]
    for i, (label, formula) in enumerate(boxes):
        r = f_row + i
        ws.cell(row=r, column=2, value=label)
        cell = ws.cell(row=r, column=3, value=formula)
        cell.number_format = "0.00"
        cell.font = BOLD
        cell.border = THIN

    # ---- SPC-style scatter with trend line -------------------------------
    spc = ScatterChart()
    spc.title = "TRIR scatter (mean trend)"
    spc.y_axis.title = "TRIR"
    spc.x_axis.title = "Month index"
    spc.height, spc.width = 8, 20
    spc.series = [Series(
        Reference(ws, min_col=3, min_row=first, max_row=last),
        xvalues=Reference(ws, min_col=2, min_row=first, max_row=last),
        title="TRIR",
    )]
    spc.series[0].trendline = Trendline(trendlineType="linear")
    ws.add_chart(spc, f"L{last + 21}")

    ws.cell(row=f_row + len(boxes) + 2, column=2,
            value="SYNTHETIC DATA: generated for portfolio demonstration, not real incident records.").font = Font(italic=True, size=9)
    return {"f_row": f_row, "year": year}


def build_workbook() -> None:
    """Generate the full workbook from the processed data."""
    log = pd.read_csv(cfg.CLEAN_LOG, parse_dates=["date"])
    kpi = kpis_by_month(log)

    wb = Workbook()
    wb.remove(wb.active)

    build_config_sheet(wb)
    build_log_sheet(wb, log)
    build_kpi_sheet(wb, kpi)
    build_dashboard_sheet(wb, kpi, log)

    cfg.EXCEL_DIR.mkdir(parents=True, exist_ok=True)
    wb.save(cfg.WORKBOOK)
    print(f"Workbook saved: {cfg.WORKBOOK}")
    print(f"  sheets: {wb.sheetnames}")


if __name__ == "__main__":
    build_workbook()
