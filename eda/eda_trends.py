"""EDA: consumption searches. All 262 weekly rows x 3 keywords get used."""
import os
import logging

import pandas as pd
import plotly.express as px

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "dashboard"))
from palette import RYO, plotly_sequence, apply_ryo  # noqa: E402

FIG = "eda/figures"
TAB = "reports/tables"


def main():
    os.makedirs(FIG, exist_ok=True)
    os.makedirs(TAB, exist_ok=True)
    kw = pd.read_csv("data/raw/trends_consumption_raw.csv", index_col="date", parse_dates=True)
    print(f"LEDGER in: weeks={len(kw)}, keywords={list(kw.columns)}")

    long = kw.reset_index().melt("date", var_name="keyword", value_name="value")
    fig = px.line(long, x="date", y="value", color="keyword",
                  title="Consumption keyword histories (0-100, weekly)",
                  color_discrete_sequence=plotly_sequence(3))
    apply_ryo(fig).write_image(f"{FIG}/fig_t01_keywords.png", scale=2)

    desc = kw.describe().T[["mean", "std", "min", "max"]]
    desc.to_csv(f"{TAB}/trends_keyword_summary.csv")
    peaks = kw.stack().reset_index()
    peaks.columns = ["date", "keyword", "value"]
    peaks = peaks.sort_values("value", ascending=False).head(10).reset_index(drop=True)
    peaks.to_csv(f"{TAB}/trends_top_weeks.csv", index=False)

    m = pd.read_csv("data/processed/trends_consumption.csv")
    fig = px.line(m, x="month", y="consumption_index",
                  title="Consumption index (monthly)",
                  color_discrete_sequence=[RYO["navy"]])
    apply_ryo(fig).write_image(f"{FIG}/fig_t02_index.png", scale=2)
    print(f"LEDGER out: summary={len(desc)}, peaks=10, months={len(m)}")
    print("EDA trends done.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
