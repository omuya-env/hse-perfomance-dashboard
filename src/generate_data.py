"""
Generate a synthetic HSE incident log for the HSE Performance Dashboard project.

Output:
    data/synthetic/incident_log_SYNTHETIC.csv

The dataset represents one industrial site over 18 months.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd


# ============================================================
# CONFIGURATION
# ============================================================

RANDOM_SEED = 42

START_DATE = "2025-01-01"
MONTHS = 18

EMPLOYEES = 500
BASE_MAN_HOURS = 25_000

OUTPUT_FILE = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "synthetic"
    / "incident_log_SYNTHETIC.csv"
)


# ============================================================
# CATEGORIES
# ============================================================

DEPARTMENTS = [
    "Production",
    "Maintenance",
    "Logistics",
    "Warehouse",
]

SHIFTS = [
    "Day",
    "Evening",
    "Night",
]

EVENT_TYPES = [
    "Near Miss",
    "First Aid",
    "Medical Treatment",
    "Lost Time Injury",
]

BODY_PARTS = [
    "None",
    "Head",
    "Eye",
    "Hand",
    "Arm",
    "Back",
    "Leg",
    "Foot",
    "Multiple",
]

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
# HELPER FUNCTIONS
# ============================================================

def choose(rng: np.random.Generator, values: List[str], probabilities=None) -> str:
    """Choose one value using optional probabilities."""
    return rng.choice(values, p=probabilities)


def get_month_phase(month_number: int) -> str:
    """
    Classify each month into one of three performance phases.

    Months 1–6: improvement
    Months 7–9: bad quarter
    Months 10–18: recovery
    """
    if month_number <= 6:
        return "Improvement"
    elif month_number <= 9:
        return "Bad Quarter"
    return "Recovery"


def monthly_activity_multiplier(month_number: int) -> float:
    """
    Control overall incident activity by month.

    The first six months gradually improve.
    Months 7–9 deteriorate.
    Months 10–18 gradually recover.
    """

    # Gradual improvement
    improvement = {
        1: 1.15,
        2: 1.10,
        3: 1.06,
        4: 1.02,
        5: 0.98,
        6: 0.94,
    }

    # Deliberate bad quarter
    bad_quarter = {
        7: 1.20,
        8: 1.45,
        9: 1.55,
    }

    # Recovery
    recovery = {
        10: 1.35,
        11: 1.20,
        12: 1.10,
        13: 1.02,
        14: 0.96,
        15: 0.92,
        16: 0.89,
        17: 0.86,
        18: 0.84,
    }

    multipliers = {**improvement, **bad_quarter, **recovery}

    return multipliers[month_number]


def department_probabilities(month_number: int) -> Dict[str, float]:
    """
    Department distribution.

    Maintenance receives increased incident activity during
    the bad quarter to create a meaningful deterioration pattern.
    """

    if 7 <= month_number <= 9:
        return {
            "Production": 0.32,
            "Maintenance": 0.38,
            "Logistics": 0.17,
            "Warehouse": 0.13,
        }

    return {
        "Production": 0.37,
        "Maintenance": 0.29,
        "Logistics": 0.19,
        "Warehouse": 0.15,
    }


def event_type_probabilities(month_number: int) -> List[float]:
    """
    Target approximately:
        85% Near Miss
        10% First Aid
        4% Medical Treatment
        1% Lost Time Injury

    During the bad quarter, increase the relative likelihood
    of more serious events slightly.
    """

    if 7 <= month_number <= 9:
        return [0.79, 0.11, 0.07, 0.03]

    return [0.85, 0.10, 0.04, 0.01]


def immediate_cause_probabilities(
    department: str,
    month_number: int,
) -> List[float]:
    """
    Department-specific immediate-cause probabilities.
    """

    # Default distribution
    probabilities = np.array([
        0.17,  # Unsafe Act
        0.15,  # Unsafe Condition
        0.12,  # Equipment Failure
        0.08,  # Inadequate PPE
        0.10,  # Poor Housekeeping
        0.10,  # Manual Handling
        0.08,  # Slips/Trips
        0.07,  # Vehicle/Traffic
        0.04,  # Chemical Exposure
        0.05,  # Electrical
        0.04,  # Other
    ])

    if department == "Maintenance":
        probabilities[2] += 0.12   # Equipment Failure
        probabilities[9] += 0.04   # Electrical
        probabilities[0] -= 0.08
        probabilities[1] -= 0.04
        probabilities[10] -= 0.04

    elif department == "Logistics":
        probabilities[7] += 0.12   # Vehicle/Traffic
        probabilities[6] += 0.04   # Slips/Trips
        probabilities[0] -= 0.10
        probabilities[10] -= 0.06

    elif department == "Warehouse":
        probabilities[5] += 0.08   # Manual Handling
        probabilities[4] += 0.05   # Housekeeping
        probabilities[0] -= 0.08
        probabilities[10] -= 0.05

    elif department == "Production":
        probabilities[0] += 0.06   # Unsafe Act
        probabilities[1] += 0.04   # Unsafe Condition
        probabilities[4] += 0.02
        probabilities[2] -= 0.06
        probabilities[10] -= 0.06

    # Extra equipment problems in the bad quarter
    if department == "Maintenance" and 7 <= month_number <= 9:
        probabilities[2] += 0.08
        probabilities[1] += 0.03
        probabilities[0] -= 0.07
        probabilities[10] -= 0.04

    probabilities = np.clip(probabilities, 0, None)

    # Normalize so probabilities sum to 1
    probabilities = probabilities / probabilities.sum()

    return probabilities.tolist()


def root_cause_probabilities(
    department: str,
    immediate_cause: str,
) -> List[float]:
    """
    Generate a root cause using a relationship with the
    immediate cause rather than choosing it independently.
    """

    probabilities = np.array([
        0.13,  # Inadequate Procedure
        0.13,  # Inadequate Training
        0.11,  # Poor Supervision
        0.12,  # Equipment Maintenance
        0.12,  # Risk Assessment Gap
        0.08,  # Housekeeping Management
        0.06,  # PPE Management
        0.08,  # Workload/Staffing
        0.08,  # Communication
        0.05,  # Environmental Conditions
        0.04,  # Other
    ])

    cause_index = {
        "Unsafe Act": [1, 2],
        "Unsafe Condition": [4, 8],
        "Equipment Failure": [3],
        "Inadequate PPE": [6],
        "Poor Housekeeping": [5],
        "Manual Handling": [1, 7],
        "Slips/Trips": [5, 4],
        "Vehicle/Traffic": [4, 2],
        "Chemical Exposure": [0, 4],
        "Electrical": [3, 1],
        "Other": [0, 10],
    }

    for idx in cause_index.get(immediate_cause, []):
        probabilities[idx] += 0.08

    # Maintenance naturally receives more equipment-maintenance root causes
    if department == "Maintenance":
        probabilities[3] += 0.10

    probabilities = probabilities / probabilities.sum()

    return probabilities.tolist()


def choose_body_part(
    rng: np.random.Generator,
    event_type: str,
) -> str:
    """
    Near misses normally have no injury/body part.
    Injury events have an affected body part.
    """

    if event_type == "Near Miss":
        return "None"

    injury_parts = [
        "Head",
        "Eye",
        "Hand",
        "Arm",
        "Back",
        "Leg",
        "Foot",
        "Multiple",
    ]

    probabilities = [
        0.08,
        0.08,
        0.25,
        0.10,
        0.15,
        0.14,
        0.14,
        0.06,
    ]

    return choose(rng, injury_parts, probabilities)


def generate_days_lost(
    rng: np.random.Generator,
    event_type: str,
) -> int:
    """
    Only Lost Time Injury events generate lost workdays.
    """

    if event_type != "Lost Time Injury":
        return 0

    # Most LTIs cause a relatively small number of lost days,
    # with occasional more severe cases.
    days = int(rng.poisson(lam=3) + 1)

    return max(days, 1)


# ============================================================
# MAIN GENERATOR
# ============================================================

def generate_incident_log() -> pd.DataFrame:

    rng = np.random.default_rng(RANDOM_SEED)

    month_starts = pd.date_range(
        start=START_DATE,
        periods=MONTHS,
        freq="MS",
    )

    records = []

    incident_number = 1

    for month_number, month_start in enumerate(month_starts, start=1):

        phase = get_month_phase(month_number)
        activity_multiplier = monthly_activity_multiplier(month_number)

        # Base incident volume.
        # Poisson variation prevents every month from having
        # exactly the same number of events.
        expected_incidents = 16 * activity_multiplier

        incident_count = rng.poisson(expected_incidents)

        # Make sure every month has enough activity for analysis.
        incident_count = max(incident_count, 8)

        department_names = list(
            department_probabilities(month_number).keys()
        )

        department_probs = list(
            department_probabilities(month_number).values()
        )

        event_probs = event_type_probabilities(month_number)

        # Generate dates within the month.
        month_end = month_start + pd.offsets.MonthEnd(1)

        available_days = pd.date_range(
            month_start,
            month_end,
            freq="D",
        )

        for _ in range(incident_count):

            incident_date = rng.choice(available_days)

            department = choose(
                rng,
                department_names,
                department_probs,
            )

            event_type = choose(
                rng,
                EVENT_TYPES,
                event_probs,
            )

            shift = choose(
                rng,
                SHIFTS,
                [0.58, 0.27, 0.15],
            )

            cause_probs = immediate_cause_probabilities(
                department,
                month_number,
            )

            immediate_cause = choose(
                rng,
                IMMEDIATE_CAUSES,
                cause_probs,
            )

            root_probs = root_cause_probabilities(
                department,
                immediate_cause,
            )

            root_cause = choose(
                rng,
                ROOT_CAUSES,
                root_probs,
            )

            body_part = choose_body_part(
                rng,
                event_type,
            )

            days_lost = generate_days_lost(
                rng,
                event_type,
            )

            # Contractors are somewhat more represented in
            # Logistics and Maintenance.
            contractor_probability = {
                "Production": 0.12,
                "Maintenance": 0.24,
                "Logistics": 0.32,
                "Warehouse": 0.20,
            }[department]

            contractor_flag = bool(
                rng.random() < contractor_probability
            )

            records.append(
                {
                    "incident_id": f"INC-{incident_number:04d}",
                    "date": incident_date,
                    "shift": shift,
                    "department": department,
                    "event_type": event_type,
                    "body_part": body_part,
                    "immediate_cause": immediate_cause,
                    "root_cause": root_cause,
                    "days_lost": days_lost,
                    "contractor_flag": contractor_flag,
                    "_phase": phase,
                }
            )

            incident_number += 1

    df = pd.DataFrame(records)

    # --------------------------------------------------------
    # Sort and clean basic formatting
    # --------------------------------------------------------

    df["date"] = pd.to_datetime(df["date"])

    df = df.sort_values(
        ["date", "incident_id"]
    ).reset_index(drop=True)

    # Remove the internal modelling column before export.
    df = df.drop(columns=["_phase"])

    return df


# ============================================================
# VALIDATION
# ============================================================

def validate_dataset(df: pd.DataFrame) -> None:
    """Run basic checks before saving the dataset."""

    required_columns = [
        "incident_id",
        "date",
        "shift",
        "department",
        "event_type",
        "body_part",
        "immediate_cause",
        "root_cause",
        "days_lost",
        "contractor_flag",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {missing_columns}"
        )

    if df["incident_id"].duplicated().any():
        raise ValueError("Duplicate incident IDs found.")

    if df["date"].isna().any():
        raise ValueError("Missing incident dates found.")

    if (df["days_lost"] < 0).any():
        raise ValueError("Negative days lost found.")

    # Near Miss and First Aid should have no lost days.
    invalid_no_lost_time = df[
        df["event_type"].isin(
            ["Near Miss", "First Aid"]
        )
        & (df["days_lost"] != 0)
    ]

    if not invalid_no_lost_time.empty:
        raise ValueError(
            "Near Miss / First Aid records contain lost days."
        )

    # Lost Time Injury must have at least one lost day.
    invalid_lti = df[
        (df["event_type"] == "Lost Time Injury")
        & (df["days_lost"] < 1)
    ]

    if not invalid_lti.empty:
        raise ValueError(
            "Lost Time Injury records without lost days found."
        )


# ============================================================
# SUMMARY
# ============================================================

def print_summary(df: pd.DataFrame) -> None:
    """Print a useful summary after generation."""

    print("\n" + "=" * 60)
    print("HSE SYNTHETIC INCIDENT LOG GENERATED")
    print("=" * 60)

    print(f"\nTotal incidents: {len(df):,}")
    print(f"Employees represented: {EMPLOYEES:,}")
    print(f"Study period: {df['date'].min().date()} → {df['date'].max().date()}")

    print("\nEvent type distribution:")
    event_distribution = (
        df["event_type"]
        .value_counts(normalize=True)
        .mul(100)
        .round(2)
    )

    for event_type, percentage in event_distribution.items():
        print(f"  {event_type:<20} {percentage:>6.2f}%")

    print("\nDepartment distribution:")
    department_distribution = (
        df["department"]
        .value_counts(normalize=True)
        .mul(100)
        .round(2)
    )

    for department, percentage in department_distribution.items():
        print(f"  {department:<20} {percentage:>6.2f}%")

    print("\nLost days:")
    print(f"  Total: {df['days_lost'].sum():,}")
    print(
        f"  LTI cases: "
        f"{(df['event_type'] == 'Lost Time Injury').sum():,}"
    )

    print("\nSaved to:")
    print(f"  {OUTPUT_FILE}")

    print("=" * 60 + "\n")


# ============================================================
# SCRIPT ENTRY POINT
# ============================================================

def main() -> None:

    # Generate
    df = generate_incident_log()

    # Validate
    validate_dataset(df)

    # Make sure output directory exists
    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # Export
    df.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    # Summary
    print_summary(df)


if __name__ == "__main__":
    main()