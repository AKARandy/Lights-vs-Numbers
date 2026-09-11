"""EDA: cross-signal overlays. Shared axes only - no blending, no index.

Co-movement table reports plain Pearson r on quarterly YoY series, labeled
OBSERVED (moves together), never causal. n stated per pair.
"""
import os
import logging

import pandas as pd
import plotly.express as px

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "dashboard"))
from palette import RYO, apply_ryo  # noqa: E402

FIG = "eda/figures"
TAB = "reports/tables"

PAIRS = [("ntl_yoy", "Nighttime lights"), ("elec_yoy", "Electricity"),
         ("calls_yoy", "Port calls (national)"), ("volume_yoy", "Port volume"),
         ("consumption_index", "Consumption idx")]


def main():
    os.makedirs(FIG, exist_ok=True)
    os.makedirs(TAB, exist_ok=True)
    ov = pd.read_csv("data/processed/overview.csv")
    print(f"LEDGER in: quarters={len(ov)}")

    rows = []
    for i, (col, name) in enumerate(PAIRS):
        show = ov[["quarter", "official_gdp", col]].dropna(subset=[col])
        fig = px.line(show, x="quarter", y=["official_gdp", col],
                      labels={"value": "", "official_gdp": "Official GDP", col: name},
                      title=f"Official GDP vs {name} (quarterly)",
                      color_discrete_sequence=[RYO["black"], RYO["blue"]])
        apply_ryo(fig).write_image(f"{FIG}/fig_c{i:02d}_{col}.png", scale=2)
        both = ov[["official_gdp", col]].dropna()
        r = both["official_gdp"].corr(both[col]) if len(both) >= 3 else float("nan")
        rows.append({"signal": name, "n_quarters": len(both),
                     "pearson_r_observed": round(float(r), 3) if pd.notna(r) else None})
    pd.DataFrame(rows).to_csv(f"{TAB}/cross_comovement.csv", index=False)
    print(pd.DataFrame(rows).to_string(index=False))
    print("EDA cross done.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
