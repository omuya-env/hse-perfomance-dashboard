"""Compute monthly HSE KPIs and department-level analysis tables."""

from __future__ import annotations

import pandas as pd

import src.config as cfg


def kpis_by_month(log: pd.DataFrame) -> pd.DataFrame:
    """Build the monthly KPI table (exposure, counts, ratios, leading indicator)."""
    hours = cfg.monthly_man_hours()
    inspections = cfg.monthly_inspections()
    months = hours.index

    rows = []
    for m in months:
        key = str(m)
        sub = log[log["Month"] == key]
        man_hours = float(hours.loc[m])
        lti = int(sub["LTI"].sum())
        recordables = int(sub["Recordable"].sum())
        near_miss = int(sub["Near Miss"].sum())
        days_lost = int(sub["Days Lost"].sum())

        rows.append({
            "Month": key,
            "Phase": cfg.phase_of(m),
            "Man-Hours": man_hours,
            "Near Miss": near_miss,
            "First Aid": int((sub["Event Type"] == cfg.FIRST_AID).sum()),
            "Medical Treatment": int((sub["Event Type"] == cfg.MEDICAL_TREATMENT).sum()),
            "Lost Time Injury": lti,
            "Recordables": recordables,
            "Total Incidents": int(len(sub)),
            "Days Lost": days_lost,
            "Inspections": int(inspections.loc[m]),
            "LTIF": lti * 1_000_000 / man_hours,
            "TRIR": recordables * 200_000 / man_hours,
            "Severity Rate": days_lost * 1_000_000 / man_hours,
            "Near Miss Ratio": near_miss * 100 / len(sub) if len(sub) else 0.0,
        })

    kpi = pd.DataFrame(rows)
    kpi["RAG TRIR"] = [cfg.rag_status(v, cfg.TARGETS["TRIR"]) for v in kpi["TRIR"]]
    kpi["RAG LTIF"] = [cfg.rag_status(v, cfg.TARGETS["LTIF"]) for v in kpi["LTIF"]]
    kpi["RAG Severity"] = [
        cfg.rag_status(v, cfg.TARGETS["Severity Rate"]) for v in kpi["Severity Rate"]
    ]
    kpi["RAG Near Miss"] = [
        cfg.rag_status(v, cfg.TARGETS["Near Miss Ratio"], higher_is_better=True)
        for v in kpi["Near Miss Ratio"]
    ]
    return kpi


def kpis_by_department_month(log: pd.DataFrame) -> pd.DataFrame:
    """Build the department x month table with recordables, LTIs, days lost and TRIR."""
    rows = []
    for m in cfg.month_list():
        key = str(m)
        dept_hours = cfg.department_man_hours(m)
        sub = log[log["Month"] == key]
        for dept, hours in dept_hours.items():
            d = sub[sub["Department"] == dept]
            rows.append({
                "Month": key,
                "Department": dept,
                "Man-Hours": hours,
                "Incidents": int(len(d)),
                "Recordables": int(d["Recordable"].sum()),
                "LTI": int(d["LTI"].sum()),
                "Days Lost": int(d["Days Lost"].sum()),
                "TRIR": int(d["Recordable"].sum()) * 200_000 / hours,
            })
    return pd.DataFrame(rows)


def ytd_summary(kpi: pd.DataFrame) -> dict:
    """Summarise year-to-date exposure, incidents and KPIs for the latest month."""
    last = kpi.iloc[-1]
    ytd = kpi[kpi["Month"].str.startswith(last["Month"][:4])]

    man_hours = float(ytd["Man-Hours"].sum())
    lti = int(ytd["Lost Time Injury"].sum())
    recordables = int(ytd["Recordables"].sum())
    near_miss = int(ytd["Near Miss"].sum())
    total = int(ytd["Total Incidents"].sum())
    days_lost = int(ytd["Days Lost"].sum())

    return {
        "year": last["Month"][:4],
        "month": last["Month"],
        "man_hours": man_hours,
        "lti": lti,
        "recordables": recordables,
        "near_miss": near_miss,
        "total": total,
        "days_lost": days_lost,
        "ltif": lti * 1_000_000 / man_hours,
        "trir": recordables * 200_000 / man_hours,
        "severity": days_lost * 1_000_000 / man_hours,
        "near_miss_ratio": near_miss * 100 / total if total else 0.0,
        "inspections": int(ytd["Inspections"].sum()),
    }


def worst_department(dept_month: pd.DataFrame, year: str) -> tuple[str, pd.DataFrame]:
    """Find the department with the highest YTD recordable rate."""
    ytd = dept_month[dept_month["Month"].str.startswith(year)]
    rate = (
        ytd.groupby("Department")
        .agg(Recordables=("Recordables", "sum"), ManHours=("Man-Hours", "sum"))
        .assign(TRIR=lambda x: x["Recordables"] * 200_000 / x["ManHours"])
    )
    return str(rate["TRIR"].idxmax()), rate


def run_kpi() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Compute all KPI tables from the processed log and save the monthly table."""
    log = pd.read_csv(cfg.CLEAN_LOG, parse_dates=["date"])
    kpi = kpis_by_month(log)
    dept = kpis_by_department_month(log)

    cfg.DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    kpi.to_csv(cfg.MONTHLY_KPI_FILE, index=False)

    print(f"Monthly KPI table: {len(kpi)} months -> {cfg.MONTHLY_KPI_FILE.name}")
    print(kpi[["Month", "Man-Hours", "Recordables", "LTIF", "TRIR", "RAG TRIR"]]
          .to_string(index=False, float_format=lambda v: f"{v:.2f}"))
    return kpi, dept


if __name__ == "__main__":
    run_kpi()
