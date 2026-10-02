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
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.properties import PageSetupProperties

import src.config as cfg
from src.kpi import kpis_by_month

# ============================================================
# BRAND PALETTE
# ============================================================

NAVY = "1F4E79"       # primary brand blue: section bands, headers, tab colour
NAVY_DARK = "14314F"  # title text
LIGHT = "D9E1F2"      # table header band and filter tiles
PAPER = "F2F6FB"      # panel and banded-row background
INK = "1F2933"        # body text
GREEN, AMBER, RED = "C6EFCE", "FFEB9C", "FFC7CE"
RAG_FONTS = {"Green": "006100", "Amber": "9C6500", "Red": "9C0006"}

FILL_NAVY = PatternFill("solid", fgColor=NAVY)
FILL_LIGHT = PatternFill("solid", fgColor=LIGHT)
FILL_PAPER = PatternFill("solid", fgColor=PAPER)
RAG_FILLS = {"Green": PatternFill("solid", fgColor=GREEN),
             "Amber": PatternFill("solid", fgColor=AMBER),
             "Red": PatternFill("solid", fgColor=RED)}

FONT_TITLE = Font(bold=True, size=18, color=NAVY_DARK)
FONT_SUB = Font(italic=True, size=10, color="595959")
FONT_BAND = Font(bold=True, size=10, color="FFFFFF")
FONT_BODY = Font(size=10, color=INK)
FONT_BOLD = Font(bold=True, size=10, color=INK)
FONT_LABEL = Font(bold=True, size=9, color=NAVY_DARK)
FONT_TILE = Font(bold=True, size=11, color=NAVY_DARK)
FONT_NOTE = Font(size=8, color=INK)

CENTER = Alignment(horizontal="center", vertical="center")


def _box(color: str) -> Border:
    """Return a thin box border in one colour."""
    side = Side(style="thin", color=color)
    return Border(left=side, right=side, top=side, bottom=side)


BORDER_GRID = Border(bottom=Side(style="thin", color=LIGHT))
BORDER_BOX = _box("BFBFBF")
BORDER_CARD = _box("FFFFFF")

# ============================================================
# DASHBOARD LAYOUT GRID
# ============================================================

# The dashboard uses two column blocks: B..K (KPI table and charts) and L..O
# (filter panel, live snapshot, support tables). Charts snap to a band row and
# either the left or the right slot of that band, so the page stays aligned.
GRID_LEFT, GRID_RIGHT = "B", "L"
GRID_RIGHT_COL, GRID_RIGHT_LAST_COL = 12, 15
BAND_ROWS = 22          # rows reserved for one chart band
CHART_WIDE = (20, 8)    # (width, height) in cm
CHART_NARROW = (14, 8)
CHART_STYLE = 2
CARD_COLS = (2, 4, 6, 8)
DASH_WIDTHS = {1: 2, 2: 11, 3: 12, 4: 12, 5: 12, 6: 12, 7: 11, 8: 12, 9: 10,
               10: 11, 11: 11, 12: 26, 13: 13, 14: 11, 15: 11}


def _rag_fills(ws, column_letter: str, first_row: int, last_row: int) -> None:
    """Apply green/amber/red fills to a RAG text column."""
    for row in range(first_row, last_row + 1):
        fill = RAG_FILLS.get(ws[f"{column_letter}{row}"].value)
        if fill:
            ws[f"{column_letter}{row}"].fill = fill


def _section(ws, row: int, first_col: int, last_col: int, text: str) -> None:
    """Write a brand-coloured section band across a column span."""
    cell = ws.cell(row=row, column=first_col, value=text)
    cell.font = FONT_BAND
    cell.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    for col in range(first_col, last_col + 1):
        ws.cell(row=row, column=col).fill = FILL_NAVY
    ws.merge_cells(start_row=row, start_column=first_col, end_row=row, end_column=last_col)
    ws.row_dimensions[row].height = 18


def _table_header(ws, row: int, first_col: int, headers: list[str]) -> None:
    """Write a navy header row starting at a given column."""
    for offset, name in enumerate(headers):
        cell = ws.cell(row=row, column=first_col + offset, value=name)
        cell.font = Font(bold=True, size=10, color="FFFFFF")
        cell.fill = FILL_NAVY
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.row_dimensions[row].height = 20


def _label(ws, row: int, col: int, text: str) -> None:
    """Write a small field label."""
    cell = ws.cell(row=row, column=col, value=text)
    cell.font = FONT_LABEL
    cell.alignment = Alignment(horizontal="left", vertical="center")


def _tile(ws, ref: str, value, number_format: str = "@") -> None:
    """Style a cell as a slicer-style filter tile."""
    cell = ws[ref]
    cell.value = value
    cell.font = FONT_TILE
    cell.fill = FILL_LIGHT
    cell.alignment = CENTER
    cell.border = BORDER_BOX
    cell.number_format = number_format


def _place_chart(ws, chart, row: int, slot: str = "left", size: tuple | None = None) -> None:
    """Anchor a chart on the dashboard grid, left or right slot of a band."""
    width, height = size or CHART_WIDE
    chart.width, chart.height, chart.style = width, height, CHART_STYLE
    ws.add_chart(chart, f"{GRID_LEFT if slot == 'left' else GRID_RIGHT}{row}")


def _write_table(ws, df: pd.DataFrame, widths: dict[int, int] | None = None,
                 formats: dict[int, str] | None = None) -> None:
    """Write a dataframe as a banded table with a frozen navy header."""
    ws.append(list(df.columns))
    for cell in ws[1]:
        cell.font = Font(bold=True, size=10, color="FFFFFF")
        cell.fill = FILL_NAVY
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.row_dimensions[1].height = 22
    for i, record in enumerate(df.itertuples(index=False)):
        ws.append(list(record))
        for cell in ws[i + 2]:
            cell.font = FONT_BODY
            if i % 2:
                cell.fill = FILL_PAPER
            fmt = (formats or {}).get(cell.column)
            if fmt:
                cell.number_format = fmt
    for col in range(1, len(df.columns) + 1):
        ws.column_dimensions[get_column_letter(col)].width = (
            (widths or {}).get(col, max(11, len(str(df.columns[col - 1])) + 3)))
    ws.freeze_panes = "A2"


def build_config_sheet(wb: Workbook) -> None:
    """Write site profile, KPI targets, RAG rules and the amber thresholds."""
    ws = wb.create_sheet("Config")
    ws.sheet_properties.tabColor = "808080"
    ws["A1"] = "HSE DASHBOARD CONFIG"
    ws["A1"].font = FONT_TITLE
    ws["A2"] = "Edit values here: the dashboard reads targets and amber limits from this sheet."
    ws["A2"].font = FONT_SUB

    for row, (label, value) in enumerate([
        ("Site employees", cfg.EMPLOYEES),
        ("Hours per shift", cfg.HOURS_PER_SHIFT),
        ("Study period", f"{cfg.PERIOD_START} to {cfg.PERIOD_END}"),
        ("Man-hours basis", "employees x hours x working days per month"),
    ], start=4):
        ws.cell(row=row, column=1, value=label).font = FONT_BOLD
        ws.cell(row=row, column=2, value=value).font = FONT_BODY

    _section(ws, 9, 1, 4, "KPI TARGETS AND RAG THRESHOLDS")
    _table_header(ws, 10, 1, ["KPI", "Target", "Direction", "Amber limit", "Red above"])
    rules = [("TRIR", False), ("LTIF", False), ("Severity Rate", False), ("Near Miss Ratio", True)]
    for i, (name, higher) in enumerate(rules, start=11):
        ws.cell(row=i, column=1, value=name).font = FONT_BODY
        cell = ws.cell(row=i, column=2, value=cfg.TARGETS[name])
        cell.font = FONT_BOLD
        cell.number_format = "0.0"
        ws.cell(row=i, column=3, value=">= target" if higher else "<= target").font = FONT_BODY
        amber = ws.cell(row=i, column=4, value=round(cfg.amber_limit(name), 2))
        amber.number_format = "0.0"
        ws.cell(row=i, column=5, value="outside amber").font = FONT_BODY
        for col in range(1, 6):
            ws.cell(row=i, column=col).border = BORDER_GRID
    ws.cell(row=16, column=1, value=f"Amber band: within +/-{cfg.AMBER_BAND:.0%} of target. "
                                    "Green meets the target, red falls outside the band.").font = FONT_NOTE
    ws.column_dimensions["A"].width = 22
    ws.column_dimensions["B"].width = 40
    ws.column_dimensions["C"].width = 14
    ws.column_dimensions["D"].width = 14
    ws.column_dimensions["E"].width = 15


def build_log_sheet(wb: Workbook, log: pd.DataFrame) -> None:
    """Write the full cleaned incident log with a filterable header row."""
    ws = wb.create_sheet("Incident Log")
    ws.sheet_properties.tabColor = LIGHT
    cols = ["incident_id", "date", "Shift", "Department", "Event Type", "Body Part",
            "Immediate Cause", "Root Cause", "Days Lost", "Contractor"]
    out = log[cols].copy()
    out["date"] = out["date"].dt.strftime("%Y-%m-%d")
    _write_table(ws, out)
    ws.auto_filter.ref = ws.dimensions


def build_kpi_sheet(wb: Workbook, kpi: pd.DataFrame) -> None:
    """Write the monthly KPI table and colour the RAG columns."""
    ws = wb.create_sheet("Monthly KPIs")
    ws.sheet_properties.tabColor = LIGHT
    formats = {3: "#,##0", 12: "0.00", 13: "0.00", 14: "0.0", 15: "0.0"}
    _write_table(ws, kpi, widths={1: 10, 2: 13}, formats=formats)
    header = [c.value for c in ws[1]]
    for name in ["RAG TRIR", "RAG LTIF", "RAG Severity", "RAG Near Miss"]:
        _rag_fills(ws, get_column_letter(header.index(name) + 1), 2, len(kpi) + 1)
    ws.auto_filter.ref = ws.dimensions


def _kpi_card(ws, row: int, col: int, label: str, value: float, target: float,
              higher_is_better: bool) -> None:
    """Write one RAG-coloured KPI card across two merged columns and three rows."""
    status = cfg.rag_status(value, target, higher_is_better)
    fill = RAG_FILLS[status]
    lines = [(row, label, Font(bold=True, size=9, color=RAG_FONTS[status])),
             (row + 1, round(value, 2), Font(bold=True, size=18, color=NAVY_DARK)),
             (row + 2, f"target {'>=' if higher_is_better else '<='} {target:g}",
              Font(italic=True, size=8, color="595959"))]
    for grid_row, text, font in lines:
        cell = ws.cell(row=grid_row, column=col, value=text)
        cell.font = font
        cell.alignment = CENTER
        for c in (col, col + 1):
            ws.cell(row=grid_row, column=c).fill = fill
            ws.cell(row=grid_row, column=c).border = BORDER_CARD
        ws.merge_cells(start_row=grid_row, start_column=col, end_row=grid_row, end_column=col + 1)


def _notes(ws, row: int, first_col: int, last_col: int, lines: list[str], rows: int = 11) -> None:
    """Write a wrapped notes panel across a merged block of cells."""
    cell = ws.cell(row=row, column=first_col, value="\n".join(f"- {line}" for line in lines))
    cell.font = FONT_NOTE
    cell.fill = FILL_PAPER
    cell.border = BORDER_BOX
    cell.alignment = Alignment(wrap_text=True, vertical="top", indent=1)
    for r in range(row, row + rows):
        ws.row_dimensions[r].height = 12
        for c in range(first_col, last_col + 1):
            ws.cell(row=r, column=c).fill = FILL_PAPER
    ws.merge_cells(start_row=row, start_column=first_col, end_row=row + rows - 1, end_column=last_col)


def build_dashboard_sheet(wb: Workbook, kpi: pd.DataFrame, log: pd.DataFrame) -> None:
    """Create the dashboard: KPI cards, period filter, live snapshot, tables and charts."""
    ws = wb.create_sheet("Dashboard")
    ws.sheet_properties.tabColor = NAVY
    ws.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
    ws.page_setup.orientation, ws.page_setup.fitToWidth = "landscape", 1
    ws.sheet_view.showGridLines = False
    ws.sheet_view.zoomScale = 90
    for col, width in DASH_WIDTHS.items():
        ws.column_dimensions[get_column_letter(col)].width = width

    ws["B2"] = "HSE PERFORMANCE DASHBOARD"
    ws["B2"].font = FONT_TITLE
    ws["B3"] = (f"Synthetic site log | {cfg.PERIOD_START} to {cfg.PERIOD_END} | "
                f"{cfg.EMPLOYEES} employees | TRIR per 200,000 hours, LTIF and severity "
                "per 1,000,000 hours")
    ws["B3"].font = FONT_SUB
    ws.row_dimensions[2].height = 24
    ws.row_dimensions[3].height = 14

    ytd = kpi.iloc[-1]
    year = ytd["Month"][:4]
    ytd_rows = kpi[kpi["Month"].str.startswith(year)]
    ytd_hours = ytd_rows["Man-Hours"].sum()

    # ---- KPI cards (static snapshot of the latest year to date) ----------
    cards = [
        ("YTD TRIR", ytd_rows["Recordables"].sum() * 200_000 / ytd_hours,
         cfg.TARGETS["TRIR"], False),
        ("YTD LTIF", ytd_rows["Lost Time Injury"].sum() * 1_000_000 / ytd_hours,
         cfg.TARGETS["LTIF"], False),
        ("YTD Severity", ytd_rows["Days Lost"].sum() * 1_000_000 / ytd_hours,
         cfg.TARGETS["Severity Rate"], False),
        ("YTD Near Miss %", ytd_rows["Near Miss"].sum() * 100 / ytd_rows["Total Incidents"].sum(),
         cfg.TARGETS["Near Miss Ratio"], True),
    ]
    for (label, value, target, higher), col in zip(cards, CARD_COLS):
        _kpi_card(ws, 5, col, label, value, target, higher)
    for r, height in ((5, 15), (6, 24), (7, 13)):
        ws.row_dimensions[r].height = height

    # ---- Period filter (slicer-style year and month pickers) -------------
    _section(ws, 5, GRID_RIGHT_COL, GRID_RIGHT_LAST_COL, "PERIOD FILTER")
    _label(ws, 6, 12, "Year")
    _tile(ws, "M6", year)
    _label(ws, 6, 14, "Month")
    _tile(ws, "O6", "All")
    _label(ws, 7, 12, "Resolved filter")
    ws["M7"] = '=IF($O$6="All",$M$6&"-*",$M$6&"-"&$O$6)'
    ws["M7"].font = FONT_BODY
    ws["M7"].alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws.merge_cells("M7:O7")
    for c in (12, 13, 14, 15):
        ws.cell(row=7, column=c).fill = FILL_PAPER
    ws["L8"] = ("Pick a Year and a Month below or beside the cards; choose All for the year. "
                "The filtered table underneath and the statuses recalculate.")
    ws["L8"].font = FONT_NOTE
    ws["L8"].alignment = Alignment(wrap_text=False, vertical="center")
    ws.merge_cells("L8:O8")
    ws.row_dimensions[6].height = 20
    ws.row_dimensions[7].height = 16
    ws.row_dimensions[8].height = 14

    years = sorted({m[:4] for m in kpi["Month"]})
    months = ["All"] + sorted({m[5:] for m in kpi["Month"]})
    dv_year = DataValidation(type="list", formula1='"' + ",".join(years) + '"', allow_blank=False)
    dv_month = DataValidation(type="list", formula1='"' + ",".join(months) + '"', allow_blank=False)
    ws.add_data_validation(dv_year)
    ws.add_data_validation(dv_month)
    dv_year.add(ws["M6"])
    dv_month.add(ws["O6"])

    # ---- Filtered period snapshot (live Excel formulas) ------------------
    last_kpi_row = len(kpi) + 1
    kpi_ref = f"'Monthly KPIs'!$A$2:$A${last_kpi_row}"
    criteria = "$M$7"

    def total(col: str) -> str:
        """Return a SUMIFS over one Monthly KPIs column for the filtered period."""
        return f"SUMIFS('Monthly KPIs'!${col}$2:${col}${last_kpi_row},{kpi_ref},{criteria})"

    _section(ws, 10, GRID_RIGHT_COL, GRID_RIGHT_LAST_COL, "FILTERED PERIOD VS TARGET")
    _table_header(ws, 11, GRID_RIGHT_COL, ["Indicator", "Value", "Target", "Status"])
    snapshot = [
        ("Man-hours worked", f"={total('C')}", None, False, "#,##0"),
        ("Recordable injuries", f"={total('H')}", None, False, "0"),
        ("Lost time injuries", f"={total('G')}", None, False, "0"),
        ("TRIR (per 200,000 h)", f"=IFERROR({total('H')}*200000/{total('C')},\"\")", 11, False, "0.00"),
        ("LTIF (per 1,000,000 h)", f"=IFERROR({total('G')}*1000000/{total('C')},\"\")", 12, False, "0.00"),
        ("Severity rate (days/1M h)", f"=IFERROR({total('J')}*1000000/{total('C')},\"\")", 13, False, "0.0"),
        ("Near-miss ratio (%)", f"=IFERROR({total('D')}/{total('I')}*100,\"\")", 14, True, "0.0"),
    ]
    for i, (label, formula, cfg_row, higher, fmt) in enumerate(snapshot):
        row = 12 + i
        cells = {12: (label, None), 13: (formula, fmt),
                 14: (f"=Config!$B${cfg_row}" if cfg_row else "-", "0.0"),
                 15: (None, None)}
        if cfg_row:
            compare = ">=" if higher else "<="
            cells[15] = (f'=IF(M{row}{compare}N{row},"Green",'
                         f'IF(M{row}{compare}Config!$D${cfg_row},"Amber","Red"))', None)
        for col, (value, number_format) in cells.items():
            cell = ws.cell(row=row, column=col, value=value)
            cell.font = FONT_BODY
            cell.border = BORDER_GRID
            cell.alignment = CENTER if col > 12 else Alignment(vertical="center")
            if number_format:
                cell.number_format = number_format
    for status, fill in (("Green", RAG_FILLS["Green"]), ("Amber", RAG_FILLS["Amber"]),
                         ("Red", RAG_FILLS["Red"])):
        ws.conditional_formatting.add(
            f"O12:O18",
            CellIsRule(operator="equal", formula=[f'"{status}"'], fill=fill,
                       font=Font(bold=True, color=RAG_FONTS[status])))

    # ---- Monthly KPI table (chart data source, left block) ---------------
    start = 11
    _section(ws, 10, 2, 11, "MONTHLY KPIS (chart data source)")
    headers = ["Month", "TRIR", "LTIF", "Severity Rate", "Near Miss %", "Near Miss",
               "Inspections", "Injuries", "RAG TRIR", "RAG LTIF"]
    _table_header(ws, start, 2, headers)
    for i, row in kpi.iterrows():
        r = start + 1 + i
        ws.cell(row=r, column=2, value=row["Month"]).font = FONT_BODY
        for j, key in enumerate(["TRIR", "LTIF", "Severity Rate", "Near Miss Ratio"], start=3):
            cell = ws.cell(row=r, column=j, value=round(float(row[key]), 2))
            cell.font, cell.number_format, cell.alignment = FONT_BODY, "0.00", CENTER
        for j, value in ((7, int(row["Near Miss"])), (8, int(row["Inspections"])),
                         (9, int(row["First Aid"] + row["Medical Treatment"] + row["Lost Time Injury"]))):
            cell = ws.cell(row=r, column=j, value=value)
            cell.font, cell.alignment = FONT_BODY, CENTER
        for j, key in ((10, "RAG TRIR"), (11, "RAG LTIF")):
            cell = ws.cell(row=r, column=j, value=row[key])
            cell.font, cell.alignment, cell.fill = FONT_BODY, CENTER, RAG_FILLS[row[key]]
        if i % 2:
            for j in range(2, 12):
                if j not in (10, 11):
                    ws.cell(row=r, column=j).fill = FILL_PAPER
    first, last = start + 1, start + len(kpi)
    cats = Reference(ws, min_col=2, min_row=first, max_row=last)

    # ---- Support data for the Pareto and histogram charts (right block) --
    _section(ws, 20, GRID_RIGHT_COL, GRID_RIGHT_LAST_COL, "DEPARTMENT PARETO (18 MONTHS)")
    _table_header(ws, 21, GRID_RIGHT_COL, ["Department", "Incidents", "Cumulative %"])
    dept_counts = Counter(log["Department"])
    ordered = dept_counts.most_common()
    dept_total, cum = sum(dept_counts.values()), 0
    for i, (dept, n) in enumerate(ordered, start=1):
        cum += n
        ws.cell(row=21 + i, column=12, value=dept).font = FONT_BODY
        ws.cell(row=21 + i, column=13, value=n).font = FONT_BODY
        cell = ws.cell(row=21 + i, column=14, value=round(cum * 100 / dept_total, 1))
        cell.font, cell.number_format = FONT_BODY, "0.0"
        if i % 2:
            for c in (12, 13, 14):
                ws.cell(row=21 + i, column=c).fill = FILL_PAPER

    lti_days = log.loc[log["Event Type"] == cfg.LOST_TIME_INJURY, "Days Lost"]
    buckets = pd.cut(lti_days, bins=[0, 2, 4, 6, 9, 14, float("inf")],
                     labels=["1-2", "3-4", "5-6", "7-9", "10-14", "15+"])
    bucket_labels = ["1-2", "3-4", "5-6", "7-9", "10-14", "15+"]
    counts = buckets.value_counts().reindex(bucket_labels, fill_value=0)
    h_row = 28
    _section(ws, h_row - 1, GRID_RIGHT_COL, GRID_RIGHT_LAST_COL, "DAYS LOST BUCKETS (LTI CASES)")
    _table_header(ws, h_row, GRID_RIGHT_COL, ["Days lost", "Cases"])
    for i, (label, n) in enumerate(zip(bucket_labels, counts), start=1):
        ws.cell(row=h_row + i, column=12, value=label).font = FONT_BODY
        ws.cell(row=h_row + i, column=13, value=int(n)).font = FONT_BODY
        if i % 2:
            for c in (12, 13):
                ws.cell(row=h_row + i, column=c).fill = FILL_PAPER

    # ---- Chart bands -----------------------------------------------------
    def band(index: int) -> int:
        """Return the anchor row of chart band number index (0 based)."""
        return last + 3 + index * BAND_ROWS

    line = LineChart()
    line.title = "TRIR and LTIF monthly trend (18 months)"
    line.y_axis.title = "Rate per exposure base"
    line.x_axis.title = "Month"
    line.add_data(Reference(ws, min_col=3, max_col=4, min_row=start, max_row=last),
                  titles_from_data=True)
    line.set_categories(cats)
    line.legend.position = "b"
    _place_chart(ws, line, band(0), "left", CHART_WIDE)

    lead_bar = BarChart()
    lead_bar.type, lead_bar.grouping, lead_bar.overlap = "col", "stacked", 100
    lead_bar.title = "Leading vs lagging indicators (stacked monthly)"
    lead_bar.y_axis.title = "Count"
    lead_bar.add_data(Reference(ws, min_col=7, max_col=8, min_row=start, max_row=last),
                      titles_from_data=True)
    lead_bar.set_categories(cats)
    lead_bar.legend.position = "b"
    _place_chart(ws, lead_bar, band(0), "right", CHART_NARROW)

    injuries = BarChart()
    injuries.type = "col"
    injuries.title = "Monthly injuries by event type"
    injuries.y_axis.title = "Count"
    injuries.legend = None
    injuries.add_data(Reference(ws, min_col=9, min_row=start, max_row=last), titles_from_data=True)
    injuries.set_categories(cats)
    _place_chart(ws, injuries, band(1), "left", CHART_WIDE)

    spc = ScatterChart()
    spc.title = "TRIR scatter with mean trend"
    spc.y_axis.title = "TRIR"
    spc.x_axis.title = "Month index"
    spc.legend = None
    spc.series = [Series(Reference(ws, min_col=3, min_row=first, max_row=last),
                         xvalues=Reference(ws, min_col=2, min_row=first, max_row=last),
                         title="TRIR")]
    spc.series[0].trendline = Trendline(trendlineType="linear")
    _place_chart(ws, spc, band(1), "right", CHART_NARROW)

    pareto = BarChart()
    pareto.type = "col"
    pareto.title = "Department Pareto of incidents"
    pareto.y_axis.title = "Incidents"
    pareto.legend = None
    pareto.add_data(Reference(ws, min_col=13, min_row=21, max_row=21 + len(ordered)),
                    titles_from_data=True)
    pareto.set_categories(Reference(ws, min_col=12, min_row=22, max_row=21 + len(ordered)))
    _place_chart(ws, pareto, band(2), "left", CHART_WIDE)

    cum_line = ScatterChart()
    cum_line.title = "Pareto cumulative percentage"
    cum_line.y_axis.title = "Cumulative %"
    cum_line.legend = None
    cum_line.y_axis.scaling.min, cum_line.y_axis.scaling.max = 0, 100
    cum_line.series = [Series(Reference(ws, min_col=14, min_row=22, max_row=21 + len(ordered)),
                              xvalues=Reference(ws, min_col=12, min_row=22, max_row=21 + len(ordered)),
                              title="Cumulative %")]
    _place_chart(ws, cum_line, band(2), "right", CHART_NARROW)

    hist = BarChart()
    hist.type = "col"
    hist.title = "Days lost histogram (LTI cases)"
    hist.y_axis.title = "Cases"
    hist.legend = None
    hist.add_data(Reference(ws, min_col=13, min_row=h_row, max_row=h_row + len(bucket_labels)),
                  titles_from_data=True)
    hist.set_categories(Reference(ws, min_col=12, min_row=h_row + 1,
                                  max_row=h_row + len(bucket_labels)))
    _place_chart(ws, hist, band(3), "left", CHART_WIDE)

    _notes(ws, band(3), GRID_RIGHT_COL, GRID_RIGHT_LAST_COL, [
        "Filter: choose a Year and a Month (or All) in PERIOD FILTER; the FILTERED PERIOD "
        "table and its statuses recalculate.",
        "Cards show the latest year to date and stay fixed; the filtered table above is the "
        "live, switchable view.",
        "RAG: green meets the target, amber sits within "
        f"{cfg.AMBER_BAND:.0%} of it, red falls outside the band.",
        "TRIR = recordables x 200,000 / man-hours | LTIF = lost time injuries x 1,000,000 / "
        "man-hours.",
        "Severity rate = days lost x 1,000,000 / man-hours | near-miss ratio = near misses / "
        "all reported events.",
        "Excel slicers are not available in openpyxl, so the Year and Month pickers use "
        "validated drop-downs.",
        "SYNTHETIC DATA: generated for portfolio demonstration, not real incident records.",
    ])

    print(f"  dashboard grid: monthly table rows {first}-{last}, chart bands at "
          f"{', '.join(str(band(i)) for i in range(4))}")


def build_workbook() -> None:
    """Generate the full workbook from the processed data."""
    log = pd.read_csv(cfg.CLEAN_LOG, parse_dates=["date"])
    kpi = kpis_by_month(log)

    wb = Workbook()
    wb.remove(wb.active)
    wb.properties.title = "HSE Performance Dashboard (synthetic data)"
    wb.properties.creator = "HSE Analytics"
    wb.calculation.fullCalcOnLoad = True

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
