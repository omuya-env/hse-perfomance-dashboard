# HSE Performance Dashboard

## Project Overview

An HSE analytics project that transforms workplace incident data into monthly HSE performance indicators, an Excel management dashboard, statistical analysis, and a one-page management report.

The dashboard reproduces the monthly reporting pack a site HSE analyst would produce: clean the incident log, compute the KPIs, build the Excel dashboard, run the statistical charts, and write the one-page memo a site manager can act on.

## Synthetic Data Statement

All incident data in this project is **synthetic** and was generated for portfolio demonstration purposes. It does not represent any real company's incident records, and the findings must not be presented as real HSE statistics.

- File: `data/synthetic/incident_log_SYNTHETIC.csv` (18 months, Jan 2025 to Jun 2026, 337 events, one site)
- Generator: `src/generate_data.py` (seeded, reproducible)
- Generation assumptions: [docs/assumptions.md](docs/assumptions.md)
- Field definitions and validation rules: [docs/data_dictionary.md](docs/data_dictionary.md)

The monthly safety-inspection series used as a leading indicator is also synthetic and is generated in `src/config.py`.

## KPI Formula Sheet

| KPI | Formula | What it measures | Target |
| --- | ------- | ---------------- | ------ |
| LTIF | Lost time injuries x 1,000,000 / man-hours | Fatalities and lost-time injuries per million hours worked | <= 3.0 |
| TRIR | Recordable injuries x 200,000 / man-hours | Recordable injuries (medical treatment + LTI) per 200,000 hours (100 full-time workers per year) | <= 3.0 |
| Severity Rate | Days lost x 1,000,000 / man-hours | Workdays lost per million hours worked | <= 15 |
| Near-Miss Ratio | Near misses / total events x 100 | Share of reported events that are near misses; higher means stronger proactive reporting culture | >= 80% |

**Leading indicators** (predict future harm): near-miss reports, safety inspections.
**Lagging indicators** (record past harm): first aid cases, medical treatment cases, lost time injuries, days lost.

**Recordable injury:** an injury requiring medical treatment beyond first aid (includes lost time injuries).

**Exposure basis:** man-hours = 500 employees x 8-hour shifts x working days per month (about 86,800 hours/month). This realistic basis keeps TRIR in the range real manufacturing sites report.

## Repository Structure

```
├── data/
│   ├── synthetic/                # raw generated log (SYNTHETIC)
│   └── processed/                # cleaned log + monthly KPI table (SYNTHETIC)
├── docs/
│   ├── assumptions.md            # generation assumptions
│   └── data_dictionary.md        # field definitions and validation rules
├── src/
│   ├── config.py                 # paths, site profile, targets, RAG rules, man-hours
│   ├── generate_data.py          # synthetic log generator (seed 42)
│   ├── prep.py                   # clean + validate + derive flags
│   ├── kpi.py                    # monthly and department KPI tables
│   ├── build_excel.py            # Excel dashboard workbook builder
│   ├── make_figures.py           # matplotlib figures incl. SPC chart
│   └── memo.py                   # one-page PDF memo builder
├── excel/
│   └── hse_kpi_dashboard.xlsx    # Config, Incident Log, Monthly KPIs, Dashboard
├── figures/                      # PNG figures used in memo and portfolio
├── notebooks/
│   └── hse_analysis.ipynb        # pandas reproduction + SPC/Pareto/heatmap
├── reports/
│   └── monthly_hse_report_memo.pdf
├── sas/
│   └── hse_charts.sas            # optional SAS module (SAS OnDemand)
└── tools/
    └── make_notebook.py          # regenerates the notebook structure
```

## How to Run

Requires Python 3.12+ and the packages in `requirements.txt`.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python -m src.generate_data      # 1. regenerate the synthetic log (seed 42)
python -m src.prep               # 2. clean, validate, derive flags
python -m src.kpi                # 3. compute monthly KPIs
python -m src.build_excel        # 4. build the Excel dashboard
python -m src.make_figures       # 5. render all figures
python -m src.memo               # 6. build the one-page memo PDF
jupyter nbconvert --to notebook --execute --inplace notebooks/hse_analysis.ipynb
```

Memo options: `python -m src.memo --month 2025-09 --charts spc pareto` (any month in the study period; chart choices: trend, spc, pareto, heatmap, histogram, leading, rag).

## The Excel Dashboard

`excel/hse_kpi_dashboard.xlsx` has four sheets:

- **Config** - site profile, KPI targets, RAG rules
- **Incident Log** - the cleaned log with filters
- **Monthly KPIs** - 18-month KPI table with red/amber/green status columns
- **Dashboard** - KPI cards, 12+ month TRIR/LTIF trend, leading vs lagging split, department Pareto, days-lost histogram, and live YTD-vs-target boxes driven by Excel formulas

RAG rules: green = meets target, amber = within 20% of target, red = beyond. Edit targets on the Config sheet and in `src/config.py`.

## Manual Steps

1. Open `excel/hse_kpi_dashboard.xlsx` in Excel and review the Dashboard sheet (openpyxl charts render slightly differently in Excel; adjust styling to taste).
2. SAS OnDemand: upload `data/processed/incident_log_clean_SYNTHETIC.csv`, set the `%LET inpath` in `sas/hse_charts.sas`, and run it (PROC MEANS KPIs, PROC SGPLOT trend, Pareto and heatmap).
3. Review `reports/monthly_hse_report_memo.pdf` and re-run `python -m src.memo` for other months.
4. Browse `notebooks/hse_analysis.ipynb` for the pandas reproduction and the SPC interpretation.

## Scope

One site, 18 months, monthly granularity. No training matrices, no permit-to-work system, no multi-site rollup. The memo is one page.

## Tools

Python, Pandas, NumPy, Matplotlib, openpyxl, reportlab, Jupyter, SAS (optional).
