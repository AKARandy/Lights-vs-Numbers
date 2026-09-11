"""Build the github.io static mirror of the Streamlit dashboard.

Reads the committed CSVs only (no network, no keys) and writes a
self-contained site to public/. Runs in CI with pandas + plotly + pyyaml.

    python scripts/build_pages.py
"""
import os
import shutil
import sys

import pandas as pd
import plotly.express as px

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "dashboard"))
from palette import RYO, SIGNAL, plotly_sequence  # noqa: E402

PROC = os.path.join("data", "processed")
RAW = os.path.join("data", "raw")
OUT = "public"
DATA_OUT = os.path.join(OUT, "data")

BLUE = RYO["blue"]
NAVY = RYO["navy"]
SLATE = RYO["slate"]
BLACK = RYO["black"]
FIRST = {"cdn_done": False}


def fig_html(fig, height=420):
    """Plotly div; plotly.js CDN included once on the first chart."""
    fig.update_layout(height=height, plot_bgcolor="white",
                      paper_bgcolor="white", font=dict(color="black"),
                      xaxis=dict(gridcolor="#D4DCF2"),
                      yaxis=dict(gridcolor="#D4DCF2"), legend_title_text="")
    inc = "cdn" if not FIRST["cdn_done"] else False
    FIRST["cdn_done"] = True
    return fig.to_html(full_html=False, include_plotlyjs=inc)


def annotate(fig, x, y, text):
    fig.add_annotation(x=x, y=y, text=text, showarrow=True, arrowhead=2,
                       bgcolor=RYO["yellow"], font=dict(color="black", size=11))
    return fig


def table_html(df, digits=4):
    d = df.copy()
    for c in d.select_dtypes(include="number").columns:
        d[c] = d[c].round(digits)
    return d.fillna("").to_html(index=False, border=0, classes="tbl")


def need(*names):
    return all(os.path.exists(os.path.join(PROC, n)) for n in names)


def sec1_ntl(parts):
    parts.append("<h2>1 - Nighttime lights (VIIRS, quarterly)</h2>")
    parts.append('<p class="note">Illustrative sample data (live feed planned).</p>')
    if not need("ntl_quarterly.csv"):
        return
    ntl = pd.read_csv(os.path.join(PROC, "ntl_quarterly.csv"))
    fig = px.line(ntl, x="quarter", y="ntl_mean",
                  title="Mean radiance (sample data: flat until live feed)",
                  color_discrete_sequence=[SIGNAL["ntl"]])
    parts.append(fig_html(fig))
    fig = px.line(ntl, x="quarter", y="ntl_yoy",
                  title="YoY growth (sample data: flat until live feed)",
                  color_discrete_sequence=[SIGNAL["ntl"]])
    parts.append(fig_html(fig))
    parts.append(table_html(ntl))


def sec2_elec(parts):
    parts.append("<h2>2 - Electricity vs manufacturing GDP (BPS, quarterly)</h2>")
    parts.append('<p class="note">Illustrative sample data (live feed planned).</p>')
    if not need("elec_mfg.csv"):
        return
    em = pd.read_csv(os.path.join(PROC, "elec_mfg.csv"))
    m = em[["quarter", "elec_yoy", "mfg_yoy"]].melt(
        "quarter", var_name="series", value_name="v")
    m["series"] = m["series"].map({"elec_yoy": "Electricity",
                                   "mfg_yoy": "Manufacturing GDP"})
    fig = px.line(m.dropna(subset=["v"]).sort_values("quarter"),
                  x="quarter", y="v", color="series",
                  labels={"v": "% YoY", "quarter": "quarter"},
                  title="Growth overlaid: electricity vs manufacturing (%)",
                  color_discrete_map={"Electricity": SIGNAL["elec"],
                                      "Manufacturing GDP": SIGNAL["mfg"]})
    parts.append(fig_html(fig))
    fig = px.line(em, x="quarter", y="ratio",
                  title="Elec/mfg growth ratio (plain number)",
                  color_discrete_sequence=[SIGNAL["elec"]])
    parts.append(fig_html(fig))
    parts.append(table_html(em))


def sec3_trends(parts):
    parts.append("<h2>3 - Consumption searches (Google Trends, monthly)</h2>")
    if not need("trends_consumption.csv"):
        return
    tc = pd.read_csv(os.path.join(PROC, "trends_consumption.csv"))
    fig = px.line(tc, x="month", y="consumption_index",
                  title="Consumption searches spike every Lebaran (monthly)",
                  color_discrete_sequence=[SIGNAL["consumption"]])
    parts.append(fig_html(fig))
    parts.append(table_html(tc))
    rawc = os.path.join(RAW, "trends_consumption_raw.csv")
    if os.path.exists(rawc):
        kw = pd.read_csv(rawc, index_col="date", parse_dates=True)
        fig = px.line(kw.reset_index(), x="date", y=list(kw.columns),
                      title="Raw keyword histories (0-100, weekly)",
                      color_discrete_sequence=plotly_sequence(len(kw.columns)))
        cell = kw.stack()
        pdate, pkw = cell.idxmax()
        annotate(fig, pdate, cell.max(),
                 f"Peak: {pkw} {cell.max():.0f}/100 ({str(pdate)[:7]}, Lebaran season)")
        parts.append(fig_html(fig))
        peaks = cell.reset_index()
        peaks.columns = ["date", "keyword", "value"]
        peaks = peaks.sort_values("value", ascending=False).head(10)
        parts.append("<h3>Top-10 search weeks</h3>")
        parts.append(table_html(peaks.reset_index(drop=True)))


def sec4_ports(parts):
    parts.append("<h2>4 - Ports (PortWatch, monthly, all 75)</h2>")
    if not need("port_national.csv", "port_activity.csv", "port_rankings.csv"):
        return
    nat = pd.read_csv(os.path.join(PROC, "port_national.csv"))
    pa = pd.read_csv(os.path.join(PROC, "port_activity.csv"))
    rk = pd.read_csv(os.path.join(PROC, "port_rankings.csv"))
    parts.append("<h3>Indonesia totals</h3>")
    fig = px.line(nat, x="month", y="calls",
                  title="National port calls (monthly)",
                  color_discrete_sequence=[BLUE])
    parts.append(fig_html(fig, 360))
    fig = px.line(nat, x="month", y="volume_mt",
                  title="National shipment volume, MT (monthly)",
                  color_discrete_sequence=[NAVY])
    parts.append(fig_html(fig, 360))
    m = nat[["month", "calls_yoy", "volume_yoy"]].melt(
        "month", var_name="series", value_name="v")
    m["series"] = m["series"].map({"calls_yoy": "Calls", "volume_yoy": "Volume"})
    worst = nat.loc[nat["volume_yoy"].idxmin()]
    fig = px.line(m.dropna(subset=["v"]).sort_values("month"),
                  x="month", y="v", color="series",
                  labels={"v": "% YoY", "month": "month"},
                  title=f"Weakest month ({worst['month']}): volume "
                        f"{worst['volume_yoy']:.1f}% (calls {worst['calls_yoy']:.1f}%)",
                  color_discrete_map={"Calls": BLUE, "Volume": NAVY})
    annotate(fig, worst["month"], worst["volume_yoy"],
             f"{worst['month']}: weakest month on record")
    parts.append(fig_html(fig))
    mixp = os.path.join(PROC, "port_vessel_mix.csv")
    if os.path.exists(mixp):
        parts.append("<h3>What the ships carry</h3>")
        mix = pd.read_csv(mixp)
        mtypes = [c for c in mix.columns if c.startswith("mt_")]
        mlong = mix[["month"] + mtypes].melt("month", var_name="t", value_name="mt")
        mlong["t"] = mlong["t"].str.replace("mt_", "")
        mtot = mlong.groupby("month")["mt"].transform("sum")
        mlong["share"] = mlong["mt"] / mtot
        fig = px.area(mlong, x="month", y="share", color="t",
                      title="Cargo mix by vessel type (share of tonnage)",
                      color_discrete_sequence=plotly_sequence(6))
        parts.append(fig_html(fig))
    dowp = os.path.join(PROC, "port_dow.csv")
    if os.path.exists(dowp):
        dow = pd.read_csv(dowp)
        fig = px.bar(dow, x="dow", y="avg_daily_calls",
                     labels={"dow": "", "avg_daily_calls": "avg daily calls"},
                     title="Ports rest on Sunday (avg daily calls, all ports, 2019-2026)",
                     color_discrete_sequence=[BLUE])
        sun = dow.loc[dow["dow"] == "Sunday", "avg_daily_calls"].iloc[0]
        mon = dow.loc[dow["dow"] == "Monday", "avg_daily_calls"].iloc[0]
        annotate(fig, "Sunday", sun,
                 f"Sunday {sun:.2f}/day vs Monday {mon:.2f} "
                 f"({(1 - sun / mon) * 100:.0f}% weekend dip)")
        parts.append(fig_html(fig, 360))
    heat = nat.copy()
    heat["y"] = heat["month"].str[:4]
    heat["m"] = heat["month"].str[5:]
    hp = heat.pivot(index="m", columns="y", values="calls")
    fig = px.imshow(hp, labels=dict(x="year", y="month", color="calls"),
                    title="Seasonality: national monthly calls (darker = busier)",
                    color_continuous_scale=["#D4DCF2", "#5276C6", "#1E3A8A"])
    parts.append(fig_html(fig))
    parts.append("<h3>Top 8 ports by volume</h3>")
    top8 = rk.head(8)["port"].tolist()
    sel = pa[pa["port"].isin(top8)]
    fig = px.line(sel, x="month", y="volume_yoy", color="port",
                  title="Top 8 ports: who fell hardest last month?",
                  color_discrete_sequence=plotly_sequence(8))
    last_m = sel["month"].max()
    late = sel[sel["month"] == last_m].dropna(subset=["volume_yoy"])
    if len(late):
        w = late.loc[late["volume_yoy"].idxmin()]
        annotate(fig, w["month"], w["volume_yoy"],
                 f"{w['port']} {w['volume_yoy']:.1f}% YoY ({last_m})")
    parts.append(fig_html(fig))
    parts.append("<h3>Winners and losers (tons vs same month last year)</h3>")
    mv = rk.copy()
    mv["den"] = 1 + mv["volume_yoy"] / 100
    mv = mv[(mv["volume_mt"] > 0) & mv["volume_yoy"].notna() & (mv["den"] > 0)]
    mv["tons_vs_last_year"] = mv["volume_mt"] - mv["volume_mt"] / mv["den"]
    top = mv.nlargest(5, "tons_vs_last_year")[["port", "tons_vs_last_year"]]
    bot = mv.nsmallest(5, "tons_vs_last_year")[["port", "tons_vs_last_year"]]
    fig = px.bar(top, x="tons_vs_last_year", y="port", orientation="h",
                 text_auto=".2s", title="Top 5 gainers (tons)",
                 color_discrete_sequence=[BLUE])
    parts.append(fig_html(fig, 300))
    fig = px.bar(bot, x="tons_vs_last_year", y="port", orientation="h",
                 text_auto=".2s", title="Top 5 losers (tons)",
                 color_discrete_sequence=[NAVY])
    parts.append(fig_html(fig, 300))
    parts.append("<h3>Rankings - all 75 ports</h3>")
    parts.append("<p>Small ports swing wildly in % terms (tiny denominators). "
                 "Read % columns next to the level columns.</p>")
    parts.append(table_html(rk))


def sec5_gdp(parts):
    parts.append("<h2>5 - Do ports track official GDP?</h2>")
    ov = pd.read_csv(os.path.join(PROC, "overview.csv"))
    offp = os.path.join(RAW, "official_gdp_quarterly.csv")
    if os.path.exists(offp):
        off = pd.read_csv(offp)
        ll = off.rename(columns={"gdp_yoy": "GDP YoY", "gdp_qoq": "GDP QoQ"})
        ll = ll.melt("quarter", value_vars=["GDP YoY", "GDP QoQ"],
                     var_name="series", value_name="v").dropna(subset=["v"])
        fig = px.line(ll.sort_values("quarter"), x="quarter", y="v", color="series",
                      labels={"v": "%", "quarter": "quarter"},
                      title="GDP has a seasonal shape: Q1 dips, Q2-Q3 climbs (2016-2026)",
                      color_discrete_map={"GDP YoY": BLACK, "GDP QoQ": BLUE})
        parts.append(fig_html(fig, 340))
        parts.append('<p class="note">YoY is the BPS headline (vs same quarter '
                     "last year). QoQ is vs previous quarter.</p>")
    sc = ov[["quarter", "official_gdp", "volume_yoy"]].dropna().reset_index(drop=True)
    if len(sc):
        fig = px.scatter(sc, x="official_gdp", y="volume_yoy", hover_data=["quarter"],
                         labels={"official_gdp": "GDP YoY (%)",
                                 "volume_yoy": "Port volume YoY (%)",
                                 "quarter": "quarter"},
                         title="One dot per quarter: when ports disagreed with GDP",
                         color_discrete_sequence=[BLUE])
        lo = float(min(sc["official_gdp"].min(), sc["volume_yoy"].min()))
        hi = float(max(sc["official_gdp"].max(), sc["volume_yoy"].max()))
        fig.add_shape(type="line", x0=lo, y0=lo, x1=hi, y1=hi,
                      line=dict(dash="dot", color=SLATE))
        for _, r in sc.nsmallest(2, "volume_yoy").iterrows():
            annotate(fig, r["official_gdp"], r["volume_yoy"],
                     f"{r['quarter']}: ports {r['volume_yoy']:.1f}%, "
                     f"GDP {r['official_gdp']:.2f}%")
        last = sc.iloc[-1]
        annotate(fig, last["official_gdp"], last["volume_yoy"],
                 f"Latest {last['quarter']}: ports {last['volume_yoy']:.1f}%, "
                 f"GDP {last['official_gdp']:.2f}%")
        parts.append(fig_html(fig))
        parts.append('<p class="note">Dotted line = ports moving one-for-one '
                     "with GDP. Dots far off the line are quarters worth a look, "
                     "never verdicts.</p>")
    dv = ov[["quarter", "official_gdp", "volume_yoy"]].dropna().reset_index(drop=True)
    if len(dv):
        dv["gap_pp"] = dv["volume_yoy"] - dv["official_gdp"]
        last = dv.iloc[-1]
        verb = "trail" if last["gap_pp"] < 0 else "lead"
        fig = px.bar(dv, x="quarter", y="gap_pp",
                     labels={"gap_pp": "percentage points", "quarter": "quarter"},
                     title=f"Latest quarter ({last['quarter']}): ports {verb} GDP "
                           f"by {abs(last['gap_pp']):.1f} points",
                     color_discrete_sequence=[BLUE])
        parts.append(fig_html(fig, 340))
        parts.append('<p class="note">Observed YoY gap per quarter (port volume '
                     "minus GDP). Single color: no threshold, no judgment.</p>")
    if os.path.exists(offp):
        parts.append("<h3>Official quarterly GDP as published</h3>")
        parts.append(table_html(off[["quarter", "gdp_yoy", "gdp_qoq"]]))
        parts.append('<p class="note">Dataset: data/raw/official_gdp_quarterly.csv, '
                     "2016Q1 to 2026Q2 (QoQ 2016Q1-Q2 pending, 2026Q3 not yet "
                     "released, both shown as gaps). "
                     '<a href="data/official_gdp_quarterly.csv">Download CSV</a>.</p>')


def sec6_table(parts):
    parts.append("<h2>6 - Everything, one table</h2>")
    ov = pd.read_csv(os.path.join(PROC, "overview.csv"))
    parts.append(table_html(ov))
    parts.append('<p class="note"><a href="data/overview.csv">Download overview.csv</a> - '
                 '<a href="data/port_rankings.csv">port_rankings.csv</a></p>')


PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Lights vs Numbers - Indonesia GDP Data Analysis</title>
<style>
body {{ font-family: -apple-system, 'Segoe UI', Roboto, sans-serif; max-width: 1100px;
margin: 0 auto; padding: 24px; background: #FFFFFF; color: #000000; }}
h1 {{ font-size: 28px; }} h2 {{ font-size: 22px; margin-top: 48px;
border-bottom: 3px solid #5276C6; padding-bottom: 6px; }}
h3 {{ font-size: 17px; margin-top: 32px; }}
.note {{ color: #555B63; font-size: 14px; }}
table.tbl {{ border-collapse: collapse; width: 100%; font-size: 13px; margin: 16px 0; }}
table.tbl th {{ background: #5276C6; color: #FFFFFF; padding: 6px 10px; text-align: left; }}
table.tbl td {{ border-bottom: 1px solid #D4DCF2; padding: 5px 10px; }}
table.tbl tr:nth-child(even) td {{ background: #F2F5FC; }}
a {{ color: #2B4B9B; }}
.footer {{ margin-top: 64px; color: #555B63; font-size: 13px;
border-top: 1px solid #D4DCF2; padding-top: 12px; }}
</style>
</head>
<body>
<h1>Lights vs Numbers</h1>
<p>Data analysis: independent activity signals next to official GDP. Gaps mean no data.
No index, no verdicts. Static mirror of the Streamlit dashboard, rebuilt on
every push. <a href="https://github.com/AKARandy/Lights-vs-Numbers">Source on GitHub</a>.</p>
{body}
<div class="footer">Sources: VIIRS VNP46A2 via GEE - BPS WebAPI - Google Trends -
IMF PortWatch via HDX. Sample-data sections are labeled.</div>
</body>
</html>
"""


def main():
    os.makedirs(DATA_OUT, exist_ok=True)
    parts = []
    sec1_ntl(parts)
    sec2_elec(parts)
    sec3_trends(parts)
    sec4_ports(parts)
    sec5_gdp(parts)
    sec6_table(parts)
    for src, dst in [("data/processed/overview.csv", "overview.csv"),
                     ("data/raw/official_gdp_quarterly.csv",
                      "official_gdp_quarterly.csv"),
                     ("data/processed/port_rankings.csv", "port_rankings.csv")]:
        if os.path.exists(src):
            shutil.copy(src, os.path.join(DATA_OUT, dst))
    html = PAGE.format(body="\n".join(parts))
    out = os.path.join(OUT, "index.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    assert os.path.exists(out) and os.path.getsize(out) > 50000, "index.html too small"
    for h in ["<h2>1 -", "<h2>4 -", "<h2>5 -", "<h2>6 -"]:
        assert h in html, f"missing section {h}"
    for f in ["overview.csv", "official_gdp_quarterly.csv", "port_rankings.csv"]:
        assert os.path.exists(os.path.join(DATA_OUT, f)), f"missing data/{f}"
    print(f"Wrote {out} ({os.path.getsize(out)} bytes)")


if __name__ == "__main__":
    main()
