"""Generate all matplotlib analysis figures for the HSE dashboard project."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import src.config as cfg

plt.rcParams.update({
    "figure.dpi": 150,
    "savefig.bbox": "tight",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.alpha": 0.3,
})

RAG_COLORS = {"Green": "#2e7d32", "Amber": "#f9a825", "Red": "#c62828"}


def fig_trir_ltif_trend(kpi: pd.DataFrame) -> None:
    """Plot monthly TRIR and LTIF with target reference lines."""
    months = kpi["Month"]
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.plot(months, kpi["TRIR"], marker="o", label="TRIR", color="#1f4e79")
    ax.plot(months, kpi["LTIF"], marker="s", label="LTIF", color="#e07b39")
    ax.axhline(cfg.TARGETS["TRIR"], color="#1f4e79", ls="--", lw=1, alpha=0.6, label="TRIR target")
    ax.axhline(cfg.TARGETS["LTIF"], color="#e07b39", ls="--", lw=1, alpha=0.6, label="LTIF target")
    ax.axvspan(5.5, 8.5, color="#c62828", alpha=0.08, label="Bad quarter (Jul-Sep 2025)")
    ax.set_title("Monthly TRIR and LTIF, with targets")
    ax.set_ylabel("Rate")
    ax.tick_params(axis="x", rotation=45)
    ax.legend()
    fig.savefig(cfg.FIGURES_DIR / "trir_ltif_trend.png")
    plt.close(fig)


def fig_spc_chart(kpi: pd.DataFrame) -> None:
    """Plot the TRIR SPC control chart with mean and 2-sigma limits."""
    values = kpi["TRIR"].to_numpy(dtype=float)
    mean = values.mean()
    sigma = values.std(ddof=0)
    ucl, lcl = mean + 2 * sigma, max(mean - 2 * sigma, 0.0)

    fig, ax = plt.subplots(figsize=(11, 5))
    ax.plot(kpi["Month"], values, marker="o", color="#1f4e79", label="Monthly TRIR")
    ax.axhline(mean, color="#2e7d32", label=f"Mean = {mean:.2f}")
    ax.axhline(ucl, color="#c62828", ls="--", label=f"UCL (+2 sigma) = {ucl:.2f}")
    ax.axhline(lcl, color="#c62828", ls="--", label=f"LCL (-2 sigma) = {lcl:.2f}")
    ax.axvspan(5.5, 8.5, color="#c62828", alpha=0.08)
    for i, v in enumerate(values):
        if v > ucl or v < lcl:
            ax.annotate("out of control", (i, v), xytext=(0, 8),
                        textcoords="offset points", ha="center", color="#c62828", fontsize=8)
    ax.set_title("SPC control chart: monthly TRIR (mean + 2-sigma limits)")
    ax.set_ylabel("TRIR")
    ax.tick_params(axis="x", rotation=45)
    ax.legend(loc="upper right", fontsize=8)
    fig.savefig(cfg.FIGURES_DIR / "spc_trir_control_chart.png")
    plt.close(fig)


def fig_department_pareto(log: pd.DataFrame) -> None:
    """Plot the department Pareto bar chart with a cumulative-percentage line."""
    counts = log["Department"].value_counts()
    cum_pct = counts.cumsum() * 100 / counts.sum()

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(counts.index, counts.values, color="#1f4e79")
    ax.set_ylabel("Incidents")
    ax.set_title("Department Pareto of incidents (18 months)")

    ax2 = ax.twinx()
    ax2.plot(counts.index, cum_pct.values, marker="o", color="#c62828", label="Cumulative %")
    ax2.set_ylabel("Cumulative %")
    ax2.set_ylim(0, 105)
    ax2.grid(False)
    for x, y in zip(counts.index, cum_pct.values):
        ax2.annotate(f"{y:.0f}%", (x, y), xytext=(0, 8), textcoords="offset points",
                     ha="center", fontsize=8, color="#c62828")
    fig.savefig(cfg.FIGURES_DIR / "department_pareto.png")
    plt.close(fig)


def fig_dept_event_heatmap(log: pd.DataFrame) -> None:
    """Plot the department x event-type incident heatmap."""
    table = pd.crosstab(log["Department"], log["Event Type"])
    table = table.reindex(index=cfg.DEPARTMENTS, columns=cfg.EVENT_TYPES)

    fig, ax = plt.subplots(figsize=(8, 4.5))
    im = ax.imshow(table.values, cmap="Blues")
    ax.set_xticks(range(len(table.columns)), table.columns, rotation=20, ha="right")
    ax.set_yticks(range(len(table.index)), table.index)
    ax.set_title("Incident heatmap: department x event type")
    for i in range(table.shape[0]):
        for j in range(table.shape[1]):
            v = table.iloc[i, j]
            ax.text(j, i, str(v), ha="center", va="center",
                    color="white" if v > table.values.max() * 0.6 else "black", fontsize=9)
    fig.colorbar(im, ax=ax, label="Incidents")
    fig.savefig(cfg.FIGURES_DIR / "dept_event_heatmap.png")
    plt.close(fig)


def fig_days_lost_histogram(log: pd.DataFrame) -> None:
    """Plot the distribution of days lost for LTI cases."""
    days = log.loc[log["Event Type"] == cfg.LOST_TIME_INJURY, "Days Lost"]
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.hist(days, bins=range(1, int(days.max()) + 3), align="left",
            color="#1f4e79", edgecolor="white")
    ax.set_xlabel("Days lost per LTI")
    ax.set_ylabel("Cases")
    ax.set_title("Days-lost distribution (lost time injuries)")
    fig.savefig(cfg.FIGURES_DIR / "days_lost_histogram.png")
    plt.close(fig)


def fig_leading_vs_lagging(kpi: pd.DataFrame) -> None:
    """Plot leading indicators (near miss, inspections) against lagging injuries."""
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.bar(kpi["Month"], kpi["Near Miss"], color="#2e7d32", alpha=0.7, label="Near misses (leading)")
    ax.bar(kpi["Month"], kpi["Inspections"], color="#7fb3d5", alpha=0.7,
           bottom=kpi["Near Miss"], label="Inspections (leading)")
    ax.plot(kpi["Month"], kpi["First Aid"] + kpi["Medical Treatment"] + kpi["Lost Time Injury"],
            marker="o", color="#c62828", label="Injuries (lagging)")
    ax.set_title("Leading indicators vs lagging injuries")
    ax.set_ylabel("Count")
    ax.tick_params(axis="x", rotation=45)
    ax.legend()
    fig.savefig(cfg.FIGURES_DIR / "leading_vs_lagging.png")
    plt.close(fig)


def fig_rag_monthly(kpi: pd.DataFrame) -> None:
    """Plot a TRIR-by-month bar chart coloured by RAG status."""
    fig, ax = plt.subplots(figsize=(11, 4.5))
    colors = [RAG_COLORS[s] for s in kpi["RAG TRIR"]]
    ax.bar(kpi["Month"], kpi["TRIR"], color=colors)
    ax.axhline(cfg.TARGETS["TRIR"], color="black", ls="--", lw=1, label="Target 3.0")
    ax.set_title("Monthly TRIR by RAG status")
    ax.set_ylabel("TRIR")
    ax.tick_params(axis="x", rotation=45)
    ax.legend()
    fig.savefig(cfg.FIGURES_DIR / "trir_rag_monthly.png")
    plt.close(fig)


def make_all_figures() -> list:
    """Generate every figure from the processed data."""
    log = pd.read_csv(cfg.CLEAN_LOG, parse_dates=["date"])
    from src.kpi import kpis_by_month
    kpi = kpis_by_month(log)

    cfg.FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    fig_trir_ltif_trend(kpi)
    fig_spc_chart(kpi)
    fig_department_pareto(log)
    fig_dept_event_heatmap(log)
    fig_days_lost_histogram(log)
    fig_leading_vs_lagging(kpi)
    fig_rag_monthly(kpi)

    names = sorted(p.name for p in cfg.FIGURES_DIR.glob("*.png"))
    print(f"Figures written to {cfg.FIGURES_DIR}:")
    for n in names:
        print(f"  {n}")
    return names


if __name__ == "__main__":
    make_all_figures()
