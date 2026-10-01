"""Generate notebooks/hse_analysis.ipynb programmatically (then execute with nbconvert)."""

from __future__ import annotations

from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "notebooks" / "hse_analysis.ipynb"

nb = nbf.v4.new_notebook()
cells = []

cells.append(nbf.v4.new_markdown_cell(
    "# HSE Performance Analysis\n"
    "\n"
    "Pandas reproduction of every KPI in the Excel dashboard, plus the SPC, Pareto and "
    "heatmap figures used in the monthly memo.\n"
    "\n"
    "**Data:** `data/processed/incident_log_clean_SYNTHETIC.csv` - synthetic incident log for "
    "one site, Jan 2025 to Jun 2026. Not real incident records."
))

cells.append(nbf.v4.new_code_cell(
    "import sys\n"
    "from pathlib import Path\n"
    "\n"
    "root = Path.cwd()\n"
    "while not (root / \"src\").exists() and root != root.parent:\n"
    "    root = root.parent\n"
    "sys.path.insert(0, str(root))\n"
    "\n"
    "import pandas as pd\n"
    "import numpy as np\n"
    "import matplotlib.pyplot as plt\n"
    "\n"
    "import src.config as cfg\n"
    "import src.kpi as K\n"
    "\n"
    "plt.rcParams.update({\"figure.dpi\": 110, \"axes.spines.top\": False,\n"
    "                     \"axes.spines.right\": False, \"axes.grid\": True,\n"
    "                     \"grid.alpha\": 0.3})\n"
    "log = pd.read_csv(cfg.CLEAN_LOG, parse_dates=[\"date\"])\n"
    "log.head()"
))

cells.append(nbf.v4.new_markdown_cell("## 1. Data overview\nQuick profile of the cleaned log."))
cells.append(nbf.v4.new_code_cell(
    "print(f\"rows: {len(log)}, months: {log['Month'].nunique()}, \"\n"
    "      f\"departments: {log['Department'].nunique()}\")\n"
    "log[\"Event Type\"].value_counts()"
))

cells.append(nbf.v4.new_markdown_cell(
    "## 2. Monthly KPI reproduction\n"
    "Same formulas as the Excel dashboard:\n"
    "\n"
    "- **LTIF** = lost time injuries x 1,000,000 / man-hours\n"
    "- **TRIR** = recordables x 200,000 / man-hours\n"
    "- **Severity rate** = days lost x 1,000,000 / man-hours\n"
    "- **Near-miss ratio** = near misses / total events x 100"
))
cells.append(nbf.v4.new_code_cell("kpi = K.kpis_by_month(log)\nkpi.head(6)"))
cells.append(nbf.v4.new_code_cell(
    "cols = [\"Month\", \"Man-Hours\", \"Near Miss\", \"Recordables\",\n"
    "        \"Lost Time Injury\", \"Days Lost\", \"LTIF\", \"TRIR\", \"Severity Rate\"]\n"
    "kpi[cols].round(2)"
))

cells.append(nbf.v4.new_markdown_cell("## 3. Trend chart with targets"))
cells.append(nbf.v4.new_code_cell(
    "fig, ax = plt.subplots(figsize=(11, 4.5))\n"
    "ax.plot(kpi[\"Month\"], kpi[\"TRIR\"], marker=\"o\", label=\"TRIR\")\n"
    "ax.plot(kpi[\"Month\"], kpi[\"LTIF\"], marker=\"s\", label=\"LTIF\")\n"
    "ax.axhline(cfg.TARGETS[\"TRIR\"], ls=\"--\", lw=1, color=\"grey\", label=\"target\")\n"
    "ax.axvspan(5.5, 8.5, color=\"red\", alpha=0.08, label=\"bad quarter\")\n"
    "ax.set_title(\"Monthly TRIR and LTIF vs target\")\n"
    "ax.tick_params(axis=\"x\", rotation=45)\n"
    "ax.legend()\n"
    "plt.show()"
))

cells.append(nbf.v4.new_markdown_cell(
    "## 4. SPC control chart on TRIR\n"
    "Mean + 2-sigma limits answer: **is the bad quarter a real signal or noise?** "
    "Points outside the limits (or long runs) suggest a special cause."
))
cells.append(nbf.v4.new_code_cell(
    "values = kpi[\"TRIR\"].to_numpy(float)\n"
    "mean, sigma = values.mean(), values.std(ddof=0)\n"
    "ucl, lcl = mean + 2 * sigma, max(mean - 2 * sigma, 0)\n"
    "print(f\"mean={mean:.2f}  sigma={sigma:.2f}  UCL={ucl:.2f}  LCL={lcl:.2f}\")\n"
    "\n"
    "fig, ax = plt.subplots(figsize=(11, 4.5))\n"
    "ax.plot(kpi[\"Month\"], values, marker=\"o\")\n"
    "ax.axhline(mean, color=\"green\", label=f\"mean {mean:.2f}\")\n"
    "ax.axhline(ucl, color=\"red\", ls=\"--\", label=f\"UCL {ucl:.2f}\")\n"
    "ax.axhline(lcl, color=\"red\", ls=\"--\", label=f\"LCL {lcl:.2f}\")\n"
    "ax.axvspan(5.5, 8.5, color=\"red\", alpha=0.08)\n"
    "ax.set_title(\"SPC control chart: monthly TRIR\")\n"
    "ax.tick_params(axis=\"x\", rotation=45)\n"
    "ax.legend(loc=\"upper right\", fontsize=8)\n"
    "plt.show()\n"
    "\n"
    "out = [(str(m), round(v, 2)) for m, v in zip(kpi[\"Month\"], values) if v > ucl]\n"
    "print(\"Months above UCL:\", out if out else \"none\")"
))

cells.append(nbf.v4.new_markdown_cell("## 5. Department Pareto"))
cells.append(nbf.v4.new_code_cell(
    "counts = log[\"Department\"].value_counts()\n"
    "cum = counts.cumsum() * 100 / counts.sum()\n"
    "\n"
    "fig, ax = plt.subplots(figsize=(8, 4.5))\n"
    "ax.bar(counts.index, counts.values, color=\"#1f4e79\")\n"
    "ax2 = ax.twinx()\n"
    "ax2.plot(counts.index, cum.values, marker=\"o\", color=\"#c62828\")\n"
    "ax2.set_ylim(0, 105)\n"
    "ax2.grid(False)\n"
    "ax.set_title(\"Department Pareto of incidents\")\n"
    "ax.set_ylabel(\"Incidents\")\n"
    "ax2.set_ylabel(\"Cumulative %\")\n"
    "plt.show()\n"
    "\n"
    "pd.DataFrame({\"incidents\": counts, \"cum_pct\": cum.round(1)})"
))

cells.append(nbf.v4.new_markdown_cell(
    "## 6. Department x event-type heatmap\n"
    "Maintenance should dominate equipment-related serious events, especially in the bad quarter."
))
cells.append(nbf.v4.new_code_cell(
    "table = pd.crosstab(log[\"Department\"], log[\"Event Type\"]).reindex(\n"
    "    index=cfg.DEPARTMENTS, columns=cfg.EVENT_TYPES)\n"
    "\n"
    "fig, ax = plt.subplots(figsize=(8, 4))\n"
    "im = ax.imshow(table.values, cmap=\"Blues\")\n"
    "ax.set_xticks(range(len(table.columns)), table.columns, rotation=20, ha=\"right\")\n"
    "ax.set_yticks(range(len(table.index)), table.index)\n"
    "for i in range(table.shape[0]):\n"
    "    for j in range(table.shape[1]):\n"
    "        ax.text(j, i, table.iloc[i, j], ha=\"center\", va=\"center\",\n"
    "                color=\"white\" if table.iloc[i, j] > table.values.max() * 0.6 else \"black\")\n"
    "fig.colorbar(im, ax=ax, label=\"Incidents\")\n"
    "ax.set_title(\"Incident heatmap: department x event type\")\n"
    "plt.show()\n"
    "\n"
    "bad = log[log[\"Month\"].isin([\"2025-07\", \"2025-08\", \"2025-09\"])]\n"
    "print(\"Bad quarter recordables by department:\")\n"
    "print(bad[bad[\"Recordable\"]].groupby(\"Department\").size())"
))

cells.append(nbf.v4.new_markdown_cell(
    "## 7. Parity check: notebook vs pipeline\n"
    "The notebook must reproduce the pipeline's monthly KPI table exactly."
))
cells.append(nbf.v4.new_code_cell(
    "pipeline = pd.read_csv(cfg.MONTHLY_KPI_FILE)\n"
    "check = kpi.drop(columns=[\"RAG TRIR\", \"RAG LTIF\", \"RAG Severity\", \"RAG Near Miss\"])\n"
    "match = np.allclose(check.select_dtypes(\"number\"),\n"
    "                    pipeline[check.select_dtypes(\"number\").columns])\n"
    "assert match, \"KPI table does not match the pipeline output\"\n"
    "print(\"Parity check PASSED: notebook KPIs == pipeline KPIs\")"
))

cells.append(nbf.v4.new_markdown_cell(
    "## 8. YTD summary and worst department\nLatest-month YTD view, as used in the memo."
))
cells.append(nbf.v4.new_code_cell(
    "ytd = K.ytd_summary(kpi)\n"
    "print({k: round(v, 2) if isinstance(v, float) else v for k, v in ytd.items()})\n"
    "\n"
    "dept = K.kpis_by_department_month(log)\n"
    "worst, table = K.worst_department(dept, ytd[\"year\"])\n"
    "print(f\"\\nWorst department by YTD TRIR: {worst}\")\n"
    "table.round(2)"
))

nb["cells"] = cells
OUT.parent.mkdir(parents=True, exist_ok=True)
nbf.write(nb, OUT)
print(f"Notebook written: {OUT}")
