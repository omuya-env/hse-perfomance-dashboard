"""Clean and validate the synthetic HSE incident log."""

from __future__ import annotations

import pandas as pd

import src.config as cfg


def load_raw_log(path=cfg.RAW_LOG) -> pd.DataFrame:
    """Load the raw incident log CSV with parsed dates and booleans."""
    # keep_default_na=False stops pandas turning the 'None' body-part label into NaN
    df = pd.read_csv(path, parse_dates=["date"], keep_default_na=False)
    df["contractor_flag"] = (
        df["contractor_flag"].astype(str).str.upper().isin(["TRUE", "1"])
    )
    return df


def clean_log(df: pd.DataFrame) -> pd.DataFrame:
    """Standardise categories, strip whitespace, enforce canonical label sets."""
    df = df.copy()

    for col in ["shift", "department", "event_type", "body_part",
                "immediate_cause", "root_cause"]:
        df[col] = df[col].astype(str).str.strip()

    df = df.rename(columns={
        "shift": "Shift",
        "department": "Department",
        "event_type": "Event Type",
        "body_part": "Body Part",
        "immediate_cause": "Immediate Cause",
        "root_cause": "Root Cause",
        "days_lost": "Days Lost",
        "contractor_flag": "Contractor",
    })

    df["Days Lost"] = df["Days Lost"].astype(int)
    df["Contractor"] = df["Contractor"].map({True: "Yes", False: "No"})

    df = df.sort_values(["date", "incident_id"]).reset_index(drop=True)
    df["incident_id"] = [f"INC-{i:04d}" for i in range(1, len(df) + 1)]
    return df


def validate_log(df: pd.DataFrame) -> None:
    """Raise ValueError if the log breaks any data-dictionary rule."""
    problems = []

    if df["incident_id"].duplicated().any():
        problems.append("duplicate incident_id values")

    if df["date"].isna().any():
        problems.append("missing dates")

    allowed = {
        "Shift": set(cfg.SHIFTS),
        "Department": set(cfg.DEPARTMENTS),
        "Event Type": set(cfg.EVENT_TYPES),
        "Body Part": set(cfg.BODY_PARTS),
        "Immediate Cause": set(cfg.IMMEDIATE_CAUSES),
        "Root Cause": set(cfg.ROOT_CAUSES),
    }
    for col, ok in allowed.items():
        bad = set(df[col]) - ok
        if bad:
            problems.append(f"{col}: unexpected values {sorted(bad)}")

    bad_dates = df[(df["date"] < "2025-01-01") | (df["date"] > "2026-06-30")]
    if not bad_dates.empty:
        problems.append(f"{len(bad_dates)} rows outside the study period")

    mask = df["Event Type"].isin([cfg.NEAR_MISS, cfg.FIRST_AID])
    if (df.loc[mask, "Days Lost"] != 0).any():
        problems.append("Near Miss or First Aid rows with days lost")

    lti = df["Event Type"] == cfg.LOST_TIME_INJURY
    if (df.loc[lti, "Days Lost"] < 1).any():
        problems.append("LTI rows without lost days")

    if not df.loc[~lti & ~mask, "Days Lost"].eq(0).all():
        problems.append("Medical Treatment rows with days lost")

    if problems:
        raise ValueError("Validation failed: " + "; ".join(problems))


def add_derived_flags(df: pd.DataFrame) -> pd.DataFrame:
    """Add month, year and KPI classification flags used downstream."""
    df = df.copy()
    df["Month"] = df["date"].dt.to_period("M").astype(str)
    df["Year"] = df["date"].dt.year
    df["Recordable"] = df["Event Type"].isin(cfg.RECORDABLE_EVENTS)
    df["LTI"] = df["Event Type"] == cfg.LOST_TIME_INJURY
    df["Near Miss"] = df["Event Type"] == cfg.NEAR_MISS
    df["Has Days Lost"] = df["Days Lost"] > 0
    return df


def run_prep() -> pd.DataFrame:
    """Load, clean, validate and save the processed incident log."""
    df = load_raw_log()
    df = clean_log(df)
    validate_log(df)
    df = add_derived_flags(df)

    cfg.DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    df.to_csv(cfg.CLEAN_LOG, index=False)

    print(f"Cleaned log: {len(df)} rows -> {cfg.CLEAN_LOG.name}")
    print(f"  date range: {df['date'].min().date()} to {df['date'].max().date()}")
    print(f"  event mix: {df['Event Type'].value_counts(normalize=True).mul(100).round(1).to_dict()}")
    return df


if __name__ == "__main__":
    run_prep()
