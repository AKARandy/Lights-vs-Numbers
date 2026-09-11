"""EDA: ports excavation. Every one of the 262k daily rows gets used.

Outputs: eda/figures/fig_p*.png, reports/tables/port_*.csv, row ledger on stdout.
Descriptive only: counts, sums, shares, %, YoY/MoM, ranks, labeled windows.
"""
import os
import logging

import pandas as pd
import plotly.express as px

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "dashboard"))
from palette import RYO, BLUE_RAMP, apply_ryo  # noqa: E402

log = logging.getLogger(__name__)
FIG = "eda/figures"
TAB = "reports/tables"
TYPES = ["container", "dry_bulk", "general_cargo", "roro", "tanker", "cargo"]


def main():
    os.makedirs(FIG, exist_ok=True)
    os.makedirs(TAB, exist_ok=True)
    df = pd.read_csv("data/raw/portwatch_indonesia_daily.csv",
                     parse_dates=["date"])
    print(f"LEDGER in: daily rows={len(df)}, ports={df['portname'].nunique()}, "
          f"span={df['date'].min().date()}->{df['date'].max().date()}, nulls={int(df.isna().sum().sum())}")

    df["month"] = df["date"].dt.to_period("M").astype(str)

    # 1. national monthly levels + YoY
    nat = df.groupby("month").agg(calls=("portcalls", "sum"),
                                  volume_mt=("import", "sum")).reset_index()
    nat["volume_mt"] = nat["volume_mt"] + df.groupby("month")["export"].sum().values
    nat = nat.sort_values("month")
    nat["calls_yoy"] = nat["calls"].pct_change(12) * 100
    nat["volume_yoy"] = nat["volume_mt"].pct_change(12) * 100
    nat.to_csv(f"{TAB}/port_national_monthly.csv", index=False)
    for col, title in [("calls", "National port calls (monthly)"),
                       ("volume_mt", "National shipment volume MT (monthly)")]:
        fig = px.line(nat, x="month", y=col, title=title,
                      color_discrete_sequence=[RYO["blue"]])
        apply_ryo(fig).write_image(f"{FIG}/fig_p01_{col}.png", scale=2)

    # 2. vessel-type mix shares over time (monthly, national)
    mix_c = df.groupby("month")[[f"portcalls_{t}" for t in TYPES]].sum()
    mix_c.columns = TYPES
    mix_c = mix_c.div(mix_c.sum(axis=1), axis=0).reset_index()
    mix_c.to_csv(f"{TAB}/port_vessel_mix_calls.csv", index=False)
    fig = px.area(mix_c, x="month", y=TYPES, title="Call mix by vessel type (share)",
                  color_discrete_sequence=BLUE_RAMP)
    apply_ryo(fig).write_image(f"{FIG}/fig_p02_mix_calls.png", scale=2)
    mix_v = df.groupby("month")[[f"import_{t}" for t in TYPES]].sum()
    mix_v.columns = TYPES
    mix_v = mix_v.div(mix_v.sum(axis=1), axis=0).reset_index()
    mix_v.to_csv(f"{TAB}/port_vessel_mix_import.csv", index=False)
    fig = px.area(mix_v, x="month", y=TYPES, title="Import tonnage mix by vessel type (share)",
                  color_discrete_sequence=BLUE_RAMP)
    apply_ryo(fig).write_image(f"{FIG}/fig_p03_mix_import.png", scale=2)

    # 3. import vs export balance
    bal = df.groupby("month").agg(imp=("import", "sum"), exp=("export", "sum")).reset_index()
    bal["balance_mt"] = bal["exp"] - bal["imp"]
    bal.to_csv(f"{TAB}/port_impex_balance.csv", index=False)
    fig = px.line(bal, x="month", y=["imp", "exp"],
                  labels={"value": "MT", "imp": "Import", "exp": "Export"},
                  title="Import vs export tonnage (monthly MT)",
                  color_discrete_sequence=[RYO["blue"], RYO["navy"]])
    apply_ryo(fig).write_image(f"{FIG}/fig_p04_impex.png", scale=2)

    # 4. day-of-week effects (daily grain)
    df["dow"] = df["date"].dt.day_name()
    dow = df.groupby("dow")["portcalls"].mean().reindex(
        ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"])
    dow.to_csv(f"{TAB}/port_dow.csv", header=True)
    fig = px.bar(dow.reset_index(), x="dow", y="portcalls",
                 labels={"dow": "", "portcalls": "avg daily calls"},
                 title="Day-of-week effect (avg daily calls, all ports)",
                 color_discrete_sequence=[RYO["blue"]])
    apply_ryo(fig).write_image(f"{FIG}/fig_p05_dow.png", scale=2)

    # 5. month x year seasonality heatmap (national monthly calls)
    piv = nat.copy()
    piv["y"] = piv["month"].str[:4]
    piv["m"] = piv["month"].str[5:]
    heat = piv.pivot(index="m", columns="y", values="calls")
    heat.to_csv(f"{TAB}/port_seasonality.csv")
    fig = px.imshow(heat, labels=dict(x="year", y="month", color="calls"),
                    title="Seasonality: national monthly calls",
                    color_continuous_scale=["#D4DCF2", "#5276C6", "#1E3A8A"])
    apply_ryo(fig).write_image(f"{FIG}/fig_p06_season.png", scale=2)

    # 6. outlier log: top-20 single-day port-days by calls + biggest MoM jumps with bases
    top_days = df.nlargest(20, "portcalls")[["date", "portname", "portcalls"]]
    top_days.to_csv(f"{TAB}/port_top_days.csv", index=False)
    m = pd.read_csv("data/processed/port_activity.csv")
    m["month"] = pd.to_datetime(m["month"].astype(str))
    m = m.sort_values(["port", "month"])
    m["mom"] = m.groupby("port")["calls"].pct_change(1) * 100
    jumps = m.nlargest(20, "mom")[["port", "month", "calls", "mom", "calls_yoy"]]
    jumps.to_csv(f"{TAB}/port_top_jumps.csv", index=False)
    print(f"LEDGER out: months={len(nat)}, heat_cells={int(heat.size)}, "
          f"top_days=20, jumps=20")

    # 7. concentration: top-5/10 share of national calls + tonnage over time
    pm = m.copy()
    pm["month"] = pm["month"].astype(str)
    tot = pm.groupby("month")[["calls", "volume_mt"]].sum()
    conc = []
    for mo, g in pm.groupby("month"):
        g = g.sort_values("volume_mt", ascending=False)
        conc.append({"month": mo,
                     "top5_calls": g.head(5)["calls"].sum() / tot.loc[mo, "calls"],
                     "top10_calls": g.head(10)["calls"].sum() / tot.loc[mo, "calls"],
                     "top5_vol": g.head(5)["volume_mt"].sum() / tot.loc[mo, "volume_mt"],
                     "top10_vol": g.head(10)["volume_mt"].sum() / tot.loc[mo, "volume_mt"]})
    conc = pd.DataFrame(conc)
    conc.to_csv(f"{TAB}/port_concentration.csv", index=False)
    fig = px.line(conc, x="month", y=["top5_calls", "top10_calls", "top5_vol", "top10_vol"],
                  title="Concentration: top ports' share of national traffic",
                  color_discrete_sequence=[RYO["blue"], RYO["navy"], "#7E97D8", "#555B63"])
    apply_ryo(fig).write_image(f"{FIG}/fig_p07_concentration.png", scale=2)
    print("EDA ports done.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
