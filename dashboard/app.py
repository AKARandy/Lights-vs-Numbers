"""Streamlit dashboard: GDP Reality Check Indonesia - descriptive edition.

Story lives ON the graphs (annotated callouts, highlights). Minimal text.
No indexes, no verdicts, no colors that mean good/bad. Ryo light theme.
"""
import os
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from palette import RYO, SIGNAL, plotly_sequence, apply_ryo, callout  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PROC = ROOT / "data" / "processed"
RAW = ROOT / "data" / "raw"

st.set_page_config(page_title="GDP Reality Check Indonesia", layout="wide")
st.title("GDP Reality Check Indonesia")
st.caption("Independent activity signals next to official GDP. Gaps mean no data.")

cfg = yaml.safe_load(open(ROOT / "config.yaml"))
MOCK_NTL = not (os.getenv("GEE_PROJECT", "").strip() or cfg.get("gee", {}).get("project"))
MOCK_ELEC = not (os.getenv("BPS_KEY", "").strip() or
                 (cfg.get("bps", {}).get("var_ids", {}).get("electricity") or
                  cfg.get("bps", {}).get("var_ids", {}).get("manufacturing_gdp")))


def need(*names):
    missing = [n for n in names if not (PROC / n).exists()]
    if missing:
        st.warning("Missing: %s. Run `python main.py`." % ", ".join(missing))
        return False
    return True


def dl_button(df, filename, label="Download CSV"):
    st.download_button(label, df.to_csv(index=False).encode(),
                       file_name=filename, mime="text/csv")


def show(df, digits=4):
    d = df.copy()
    for c in d.select_dtypes(include="number").columns:
        d[c] = d[c].round(digits)
    st.dataframe(d.fillna(""), width="stretch")


def long_lines(df, x, cols, names):
    m = df[[x] + list(cols)].melt(x, var_name="series", value_name="v")
    m["series"] = m["series"].map(dict(zip(cols, names)))
    return m.dropna(subset=["v"]).sort_values(x).reset_index(drop=True)


def mock_stamp(name):
    st.info(f"{name}: illustrative sample data (live feed planned).")


# ---------- 1. Nighttime lights ----------
st.header("1 - Nighttime lights (VIIRS, quarterly)")
if MOCK_NTL:
    mock_stamp("Nighttime lights")
if need("ntl_quarterly.csv"):
    ntl = pd.read_csv(PROC / "ntl_quarterly.csv")
    c1, c2 = st.columns(2)
    with c1:
        fig = px.line(ntl, x="quarter", y="ntl_mean", title="Mean radiance (mock: flat until GEE key)",
                      color_discrete_sequence=[SIGNAL["ntl"]])
        st.plotly_chart(apply_ryo(fig), width="stretch")
    with c2:
        fig = px.line(ntl, x="quarter", y="ntl_yoy", title="YoY growth (mock: flat until GEE key)",
                      color_discrete_sequence=[SIGNAL["ntl"]])
        st.plotly_chart(apply_ryo(fig), width="stretch")
    show(ntl)
    dl_button(ntl, "ntl_quarterly.csv")

# ---------- 2. Electricity vs manufacturing ----------
st.header("2 - Electricity vs manufacturing GDP (BPS, quarterly)")
if MOCK_ELEC:
    mock_stamp("Electricity / manufacturing")
if need("elec_mfg.csv"):
    em = pd.read_csv(PROC / "elec_mfg.csv")
    ll = long_lines(em, "quarter", ["elec_yoy", "mfg_yoy"],
                    ["Electricity", "Manufacturing GDP"])
    fig = px.line(ll, x="quarter", y="v", color="series",
                  labels={"v": "% YoY", "quarter": "quarter"},
                  title="Growth overlaid: electricity vs manufacturing (%)",
                  color_discrete_map={"Electricity": SIGNAL["elec"],
                                      "Manufacturing GDP": SIGNAL["mfg"]})
    st.plotly_chart(apply_ryo(fig), width="stretch")
    fig2 = px.line(em, x="quarter", y="ratio", title="Elec/mfg growth ratio (plain number)",
                   color_discrete_sequence=[SIGNAL["elec"]])
    st.plotly_chart(apply_ryo(fig2), width="stretch")
    show(em)
    dl_button(em, "elec_mfg.csv")

# ---------- 3. Consumption searches ----------
st.header("3 - Consumption searches (Google Trends, monthly)")
if need("trends_consumption.csv"):
    tc = pd.read_csv(PROC / "trends_consumption.csv")
    fig = px.line(tc, x="month", y="consumption_index",
                  title="Consumption searches spike every Lebaran (monthly)",
                  color_discrete_sequence=[SIGNAL["consumption"]])
    st.plotly_chart(apply_ryo(fig), width="stretch")
    show(tc)
    dl_button(tc, "trends_consumption.csv")
rawc = RAW / "trends_consumption_raw.csv"
if rawc.exists():
    kw = pd.read_csv(rawc, index_col="date", parse_dates=True)
    fig = px.line(kw.reset_index(), x="date", y=list(kw.columns),
                  title="Raw keyword histories (0-100, weekly)",
                  color_discrete_sequence=plotly_sequence(len(kw.columns)))
    cell = kw.stack()
    pdate, pkw = cell.idxmax()
    callout(fig, pdate, cell.max(),
            f"Peak: {pkw} {cell.max():.0f}/100 ({str(pdate)[:7]}, Lebaran season)")
    st.plotly_chart(apply_ryo(fig), width="stretch")
    peaks = cell.reset_index()
    peaks.columns = ["date", "keyword", "value"]
    peaks = peaks.sort_values("value", ascending=False).head(10).reset_index(drop=True)
    st.subheader("Top-10 search weeks")
    show(peaks)

# ---------- 4. Ports ----------
st.header("4 - Ports (PortWatch, monthly, all 75)")
if need("port_national.csv", "port_activity.csv", "port_rankings.csv"):
    nat = pd.read_csv(PROC / "port_national.csv")
    pa = pd.read_csv(PROC / "port_activity.csv")
    rk = pd.read_csv(PROC / "port_rankings.csv")
    st.subheader("Indonesia totals")
    c1, c2 = st.columns(2)
    with c1:
        fig = px.line(nat, x="month", y="calls",
                      title="National port calls (monthly)",
                      color_discrete_sequence=[RYO["blue"]])
        st.plotly_chart(apply_ryo(fig), width="stretch")
    with c2:
        fig = px.line(nat, x="month", y="volume_mt",
                      title="National shipment volume, MT (monthly)",
                      color_discrete_sequence=[RYO["navy"]])
        st.plotly_chart(apply_ryo(fig), width="stretch")
    ll = long_lines(nat, "month", ["calls_yoy", "volume_yoy"], ["Calls", "Volume"])
    worst = nat.loc[nat["volume_yoy"].idxmin()]
    fig = px.line(ll, x="month", y="v", color="series",
                  labels={"v": "% YoY", "month": "month"},
                  title=f"Weakest month ({worst['month']}): volume {worst['volume_yoy']:.1f}% "
                        f"(calls {worst['calls_yoy']:.1f}%)",
                  color_discrete_map={"Calls": RYO["blue"], "Volume": RYO["navy"]})
    callout(fig, worst["month"], worst["volume_yoy"],
            f"{worst['month']}: volume {worst['volume_yoy']:.1f}%, "
            f"calls {worst['calls_yoy']:.1f}% (weakest month on record)")
    st.plotly_chart(apply_ryo(fig), width="stretch")

    st.subheader("What the ships carry")
    if (PROC / "port_vessel_mix.csv").exists():
        mix = pd.read_csv(PROC / "port_vessel_mix.csv")
        mtypes = [c for c in mix.columns if c.startswith("mt_")]
        mlong = mix[["month"] + mtypes].melt("month", var_name="t", value_name="mt")
        mlong["t"] = mlong["t"].str.replace("mt_", "")
        mtot = mlong.groupby("month")["mt"].transform("sum")
        mlong["share"] = mlong["mt"] / mtot
        fig = px.area(mlong, x="month", y="share", color="t",
                      title="Cargo mix by vessel type (share of tonnage)",
                      color_discrete_sequence=plotly_sequence(6))
        st.plotly_chart(apply_ryo(fig), width="stretch")
    if (PROC / "port_dow.csv").exists():
        dow = pd.read_csv(PROC / "port_dow.csv")
        fig = px.bar(dow, x="dow", y="avg_daily_calls", text_auto=".2f",
                     labels={"dow": "", "avg_daily_calls": "avg daily calls"},
                     title="Ports rest on Sunday (avg daily calls, all ports, 2019-2026)",
                     color_discrete_sequence=[RYO["blue"]])
        sun = dow.loc[dow["dow"] == "Sunday", "avg_daily_calls"].iloc[0]
        mon = dow.loc[dow["dow"] == "Monday", "avg_daily_calls"].iloc[0]
        callout(fig, "Sunday", sun,
                f"Sunday {sun:.2f}/day vs Monday {mon:.2f} "
                f"({(1 - sun / mon) * 100:.0f}% weekend dip)")
        st.plotly_chart(apply_ryo(fig), width="stretch")
    heat = nat.copy()
    heat["y"] = heat["month"].str[:4]
    heat["m"] = heat["month"].str[5:]
    hp = heat.pivot(index="m", columns="y", values="calls")
    fig = px.imshow(hp, labels=dict(x="year", y="month", color="calls"),
                    title="Seasonality: national monthly calls (darker = busier)",
                    color_continuous_scale=["#D4DCF2", "#5276C6", "#1E3A8A"])
    st.plotly_chart(apply_ryo(fig), width="stretch")

    st.subheader("Top 8 ports by volume")
    top8 = rk.head(8)["port"].tolist()
    sel = pa[pa["port"].isin(top8)]
    fig = px.line(sel, x="month", y="volume_yoy", color="port",
                  title="Top 8 ports: who fell hardest last month?",
                  color_discrete_sequence=plotly_sequence(8))
    last_m = sel["month"].max()
    late = sel[sel["month"] == last_m].dropna(subset=["volume_yoy"])
    if len(late):
        w = late.loc[late["volume_yoy"].idxmin()]
        callout(fig, w["month"], w["volume_yoy"],
                f"{w['port']} {w['volume_yoy']:.1f}% YoY ({last_m})")
    st.plotly_chart(apply_ryo(fig), width="stretch")

    st.subheader("Port picker - all 75")
    ports = sorted(pa["port"].unique().tolist())
    default = cfg.get("portwatch", {}).get("spotlight", [ports[0]])[0]
    pick = st.selectbox("Port", ports, index=ports.index(default) if default in ports else 0)
    one = pa[pa["port"] == pick].sort_values("month")
    c1, c2 = st.columns(2)
    with c1:
        fig = px.line(one, x="month", y="calls", title=f"{pick}: calls",
                      color_discrete_sequence=[RYO["yellow"]])
        fig.update_traces(line=dict(width=3))
        st.plotly_chart(apply_ryo(fig), width="stretch")
    with c2:
        fig = px.line(one, x="month", y="volume_mt", title=f"{pick}: volume MT",
                      color_discrete_sequence=[RYO["blue"]])
        fig.update_traces(line=dict(width=3))
        st.plotly_chart(apply_ryo(fig), width="stretch")
    show(one.reset_index(drop=True))
    dl_button(one, f"port_{pick}.csv")

    st.subheader("Winners and losers (tons vs same month last year)")
    mv = rk.copy()
    mv["den"] = 1 + mv["volume_yoy"] / 100
    mv = mv[(mv["volume_mt"] > 0) & mv["volume_yoy"].notna() & (mv["den"] > 0)]
    mv["tons_vs_last_year"] = mv["volume_mt"] - mv["volume_mt"] / mv["den"]
    top = mv.nlargest(5, "tons_vs_last_year")[["port", "tons_vs_last_year"]]
    bot = mv.nsmallest(5, "tons_vs_last_year")[["port", "tons_vs_last_year"]]
    c1, c2 = st.columns(2)
    with c1:
        fig = px.bar(top, x="tons_vs_last_year", y="port", orientation="h", text_auto=".2s",
                      title="Top 5 gainers (tons)",
                      color_discrete_sequence=[RYO["blue"]])
        st.plotly_chart(apply_ryo(fig, height=300), width="stretch")
    with c2:
        fig = px.bar(bot, x="tons_vs_last_year", y="port", orientation="h", text_auto=".2s",
                      title="Top 5 losers (tons)",
                      color_discrete_sequence=[RYO["navy"]])
        st.plotly_chart(apply_ryo(fig, height=300), width="stretch")
    st.subheader("Rankings - all 75 ports (sortable)")
    st.caption("Small ports swing wildly in % terms (tiny denominators, e.g. Belawan). "
               "Read % columns next to the level columns.")
    show(rk)
    dl_button(rk, "port_rankings.csv")

# ---------- 5. Do ports track official GDP? ----------
st.header("5 - Do ports track official GDP?")
ov_path = PROC / "overview.csv"
if ov_path.exists():
    ov = pd.read_csv(ov_path)
    off_path = RAW / "official_gdp_quarterly.csv"
    if off_path.exists():
        off = pd.read_csv(off_path)
        ll = off.rename(columns={"gdp_yoy": "GDP YoY", "gdp_qoq": "GDP QoQ"})
        ll = ll.melt("quarter", value_vars=["GDP YoY", "GDP QoQ"],
                     var_name="series", value_name="v").dropna(subset=["v"])
        fig = px.line(ll.sort_values("quarter"), x="quarter", y="v", color="series",
                      labels={"v": "%", "quarter": "quarter"},
                      title="GDP has a seasonal shape: Q1 dips, Q2-Q3 climbs (2016-2026)",
                      color_discrete_map={"GDP YoY": SIGNAL["official"],
                                          "GDP QoQ": RYO["blue"]})
        st.plotly_chart(apply_ryo(fig, height=340), width="stretch")
        st.caption("YoY is the BPS headline (vs same quarter last year). "
                   "QoQ is vs previous quarter.")
    sc = ov[["quarter", "official_gdp", "volume_yoy"]].dropna().reset_index(drop=True)
    if len(sc):
        fig = px.scatter(sc, x="official_gdp", y="volume_yoy", hover_data=["quarter"],
                         labels={"official_gdp": "GDP YoY (%)",
                                 "volume_yoy": "Port volume YoY (%)",
                                 "quarter": "quarter"},
                         title="One dot per quarter: when ports disagreed with GDP",
                         color_discrete_sequence=[RYO["blue"]])
        lo = float(min(sc["official_gdp"].min(), sc["volume_yoy"].min()))
        hi = float(max(sc["official_gdp"].max(), sc["volume_yoy"].max()))
        fig.add_shape(type="line", x0=lo, y0=lo, x1=hi, y1=hi,
                      line=dict(dash="dot", color=RYO["slate"]))
        for _, r in sc.nsmallest(2, "volume_yoy").iterrows():
            callout(fig, r["official_gdp"], r["volume_yoy"],
                    f"{r['quarter']}: ports {r['volume_yoy']:.1f}%, "
                    f"GDP {r['official_gdp']:.2f}%")
        last = sc.iloc[-1]
        callout(fig, last["official_gdp"], last["volume_yoy"],
                f"Latest {last['quarter']}: ports {last['volume_yoy']:.1f}%, "
                f"GDP {last['official_gdp']:.2f}%")
        st.plotly_chart(apply_ryo(fig, height=420), width="stretch")
        st.caption("Dotted line = ports moving one-for-one with GDP. Dots far "
                   "off the line are quarters worth a look, never verdicts.")
    dv = ov[["quarter", "official_gdp", "volume_yoy"]].dropna().reset_index(drop=True)
    if len(dv):
        dv["gap_pp"] = dv["volume_yoy"] - dv["official_gdp"]
        last = dv.iloc[-1]
        verb = "trail" if last["gap_pp"] < 0 else "lead"
        fig = px.bar(dv, x="quarter", y="gap_pp",
                     labels={"gap_pp": "percentage points", "quarter": "quarter"},
                     title=f"Latest quarter ({last['quarter']}): ports {verb} GDP "
                           f"by {abs(last['gap_pp']):.1f} points",
                     color_discrete_sequence=[RYO["blue"]])
        st.plotly_chart(apply_ryo(fig, height=340), width="stretch")
        st.caption("Observed YoY gap per quarter (port volume minus GDP). "
                   "Single color: no threshold, no judgment.")
    st.subheader("Official quarterly GDP as published")
    off_path = RAW / "official_gdp_quarterly.csv"
    if off_path.exists():
        off = pd.read_csv(off_path)
        show(off[["quarter", "gdp_yoy", "gdp_qoq"]])
        dl_button(off, "official_gdp_quarterly.csv")
    st.caption("Dataset: data/raw/official_gdp_quarterly.csv, 2016Q1 to 2026Q2 "
               "(QoQ 2016Q1-Q2 pending, 2026Q3 not yet released, both shown as gaps).")

# ---------- 6. The big table ----------
st.header("6 - Everything, one table")
if ov_path.exists():
    ov = pd.read_csv(ov_path)
    show(ov)
    dl_button(ov, "overview.csv")

st.caption("Sources: VIIRS VNP46A2 via GEE - BPS WebAPI - Google Trends - "
           "IMF PortWatch via HDX. MOCK stamps mark synthetic placeholders.")
