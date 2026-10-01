"""Shared configuration for the HSE Performance Dashboard project."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

# ============================================================
# PATHS
# ============================================================

ROOT = Path(__file__).resolve().parent.parent

DATA_SYNTH = ROOT / "data" / "synthetic"
DATA_PROCESSED = ROOT / "data" / "processed"
FIGURES_DIR = ROOT / "figures"
EXCEL_DIR = ROOT / "excel"
REPORTS_DIR = ROOT / "reports"
SAS_DIR = ROOT / "sas"

RAW_LOG = DATA_SYNTH / "incident_log_SYNTHETIC.csv"
CLEAN_LOG = DATA_PROCESSED / "incident_log_clean_SYNTHETIC.csv"
MONTHLY_KPI_FILE = DATA_PROCESSED / "monthly_kpis_SYNTHETIC.csv"
WORKBOOK = EXCEL_DIR / "hse_kpi_dashboard.xlsx"
MEMO_PDF = REPORTS_DIR / "monthly_hse_report_memo.pdf"

# ============================================================
# SITE PROFILE
# ============================================================

EMPLOYEES = 500
HOURS_PER_SHIFT = 8
PERIOD_START = "2025-01"
PERIOD_END = "2026-06"

# Department headcount split used to allocate man-hours per department.
DEPT_HEADCOUNT = {
    "Production": 220,
    "Maintenance": 130,
    "Logistics": 80,
    "Warehouse": 70,
}

# ============================================================
# EVENT CLASSIFICATION
# ============================================================

NEAR_MISS = "Near Miss"
FIRST_AID = "First Aid"
MEDICAL_TREATMENT = "Medical Treatment"
LOST_TIME_INJURY = "Lost Time Injury"

RECORDABLE_EVENTS = [MEDICAL_TREATMENT, LOST_TIME_INJURY]
INJURY_EVENTS = [FIRST_AID, MEDICAL_TREATMENT, LOST_TIME_INJURY]

DEPARTMENTS = list(DEPT_HEADCOUNT)
SHIFTS = ["Day", "Evening", "Night"]
EVENT_TYPES = [NEAR_MISS, FIRST_AID, MEDICAL_TREATMENT, LOST_TIME_INJURY]
BODY_PARTS = ["None", "Head", "Eye", "Hand", "Arm", "Back", "Leg", "Foot", "Multiple"]
IMMEDIATE_CAUSES = [
    "Unsafe Act",
    "Unsafe Condition",
    "Equipment Failure",
    "Inadequate PPE",
    "Poor Housekeeping",
    "Manual Handling",
    "Slips/Trips",
    "Vehicle/Traffic",
    "Chemical Exposure",
    "Electrical",
    "Other",
]
ROOT_CAUSES = [
    "Inadequate Procedure",
    "Inadequate Training",
    "Poor Supervision",
    "Equipment Maintenance",
    "Risk Assessment Gap",
    "Housekeeping Management",
    "PPE Management",
    "Workload/Staffing",
    "Communication",
    "Environmental Conditions",
    "Other",
]

# ============================================================
# KPI TARGETS AND RAG RULES
# ============================================================

TARGETS = {
    "TRIR": 3.0,
    "LTIF": 3.0,
    "Severity Rate": 15.0,
    "Near Miss Ratio": 80.0,
}
HIGHER_IS_BETTER = {"Near Miss Ratio"}
AMBER_BAND = 0.20  # values within 20% of the target count as amber


def rag_status(value: float, target: float, higher_is_better: bool = False) -> str:
    """Return Green, Amber or Red for a KPI value against its target."""
    if higher_is_better:
        green = value >= target
        amber = value >= target * (1 - AMBER_BAND)
    else:
        green = value <= target
        amber = value <= target * (1 + AMBER_BAND)
    return "Green" if green else ("Amber" if amber else "Red")


# ============================================================
# TIME AND EXPOSURE
# ============================================================


def month_list() -> list[pd.Period]:
    """Return the 18 study months as monthly periods."""
    return list(pd.period_range(PERIOD_START, PERIOD_END, freq="M"))


def phase_of(month: pd.Period) -> str:
    """Classify a study month into Improvement, Bad Quarter or Recovery."""
    n = month_list().index(month) + 1
    if n <= 6:
        return "Improvement"
    if n <= 9:
        return "Bad Quarter"
    return "Recovery"


def monthly_man_hours() -> pd.Series:
    """Derive realistic man-hours per month from employees, shift hours and business days."""
    hours = []
    for p in month_list():
        start = p.start_time.strftime("%Y-%m-%d")
        end = (p + 1).start_time.strftime("%Y-%m-%d")
        work_days = np.busday_count(start, end)
        hours.append(EMPLOYEES * HOURS_PER_SHIFT * work_days)
    return pd.Series(hours, index=month_list(), name="man_hours")


def department_man_hours(month: pd.Period) -> dict[str, float]:
    """Allocate one month's man-hours across departments by headcount share."""
    start = month.start_time.strftime("%Y-%m-%d")
    end = (month + 1).start_time.strftime("%Y-%m-%d")
    work_days = np.busday_count(start, end)
    total = EMPLOYEES * HOURS_PER_SHIFT * work_days
    headcount_total = sum(DEPT_HEADCOUNT.values())
    return {d: total * n / headcount_total for d, n in DEPT_HEADCOUNT.items()}


# ============================================================
# SYNTHETIC INSPECTION PROGRAMME (leading indicator)
# ============================================================

INSPECTIONS_BY_PHASE = {"Improvement": 54, "Bad Quarter": 38, "Recovery": 50}


def monthly_inspections() -> pd.Series:
    """Generate the synthetic monthly safety-inspection counts used as a leading indicator."""
    rng = np.random.default_rng(42)
    counts = [int(rng.poisson(INSPECTIONS_BY_PHASE[phase_of(p)])) for p in month_list()]
    return pd.Series(counts, index=month_list(), name="inspections")
