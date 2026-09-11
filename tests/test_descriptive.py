import pandas as pd
import numpy as np
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modules import combine, ports  # noqa: E402

CFG = {"official_gdp": {"2025Q1": 5.0, "2025Q2": 5.1}}


def _inputs():
    ntl = pd.DataFrame({"quarter": ["2024Q1", "2024Q2", "2025Q1", "2025Q2"],
                        "ntl_mean": [50.0, 51.0, 52.0, 53.0],
                        "ntl_yoy": [np.nan, np.nan, 4.0, 3.9]})
    elec = pd.DataFrame({"quarter": ["2024Q1", "2024Q2", "2025Q1", "2025Q2"],
                         "elec": [50.0, 51.0, 53.0, 54.0],
                         "mfg": [60.0, 61.0, 63.0, 64.0],
                         "elec_yoy": [np.nan, np.nan, 6.0, 5.9],
                         "mfg_yoy": [np.nan, np.nan, 5.0, 4.9],
                         "ratio": [np.nan, np.nan, 1.2, 1.2]})
    trends = pd.DataFrame({"month": ["2025-01", "2025-02", "2025-03", "2025-04"],
                           "consumption_index": [0.1, 0.2, 0.3, 0.4]})
    pn = pd.DataFrame({"month": ["2025-01", "2025-02", "2025-03", "2025-04"],
                       "calls": [800, 810, 820, 830],
                       "volume_mt": [3_000_000] * 4})
    return ntl, elec, trends, pn


def test_overview_columns_and_official_mapping():
    df = combine.build_overview(*_inputs(), CFG)
    assert list(df.columns) == ["quarter", "ntl_mean", "ntl_yoy", "elec", "mfg",
                                "elec_yoy", "mfg_yoy", "ratio", "consumption_index",
                                "calls", "volume_mt", "calls_yoy", "volume_yoy",
                                "official_gdp", "gdp_qoq"]
    row = df[df["quarter"] == "2025Q1"].iloc[0]
    assert row["official_gdp"] == 5.0
    assert pd.isna(row["gdp_qoq"])  # cfg-dict path carries YoY only
    assert row["ratio"] == 1.2
    assert row["consumption_index"] == pytest.approx(0.2)  # mean of Jan-Mar


def test_gaps_stay_gaps():
    df = combine.build_overview(*_inputs(), CFG)
    # 2024 quarters predate YoY base and have no official value
    r = df[df["quarter"] == "2024Q1"].iloc[0]
    assert pd.isna(r["ntl_yoy"]) and pd.isna(r["official_gdp"])
    # no verdict/ratio-flag columns may appear
    assert "verdict" not in df.columns and "flag" not in df.columns


def test_quarterly_port_yoy_from_sums():
    ntl, elec, trends, pn = _inputs()
    df = combine.build_overview(ntl, elec, trends, pn, CFG)
    r = df[df["quarter"] == "2025Q2"].iloc[0]
    assert r["calls"] == 830  # April only
    assert pd.isna(r["calls_yoy"])  # no year-ago quarter in fixture


def test_ports_all_ports_and_national():
    dates = pd.date_range("2024-01-01", "2025-02-01", freq="MS")
    rows = []
    for port, base in [("Alpha", 100), ("Beta", 10)]:
        for d in dates:
            rows.append({"date": d, "portname": port, "portcalls": base,
                         "import": base * 1000, "export": base * 2000})
    df = pd.DataFrame(rows)
    m = ports.aggregate_ports(df)
    assert set(m["port"].unique()) == {"Alpha", "Beta"}
    n = ports.national_totals(m)
    jan25 = n[n["month"] == "2025-01"].iloc[0]
    assert jan25["calls"] == 110
    assert jan25["volume_mt"] == 110 * 3000
    assert jan25["n_ports"] == 2
    r = ports.rankings(m)
    assert r.iloc[0]["port"] == "Alpha"
    assert "calls_mom" in r.columns and "volume_mom" in r.columns


def test_ports_no_clipping():
    dates = pd.date_range("2024-01-01", "2025-01-01", freq="MS")
    rows = [{"date": d, "portname": "Tiny", "portcalls": 1 if d.year == 2024 else 10,
             "import": 100, "export": 200} for d in dates]
    m = ports.aggregate_ports(pd.DataFrame(rows))
    v = m[m["month"] == "2025-01"]["calls_yoy"].iloc[0]
    assert v == 900.0  # raw spike preserved, not clipped


def test_official_gdp_dataset():
    off = combine.load_official()
    assert off is not None
    assert off["quarter"].is_unique
    assert len(off) == 42  # 2016Q1 to 2026Q2
    r = off[off["quarter"] == "2026Q2"].iloc[0]
    assert r["gdp_yoy"] == 5.29 and r["gdp_qoq"] == 3.73
    r = off[off["quarter"] == "2020Q2"].iloc[0]
    assert r["gdp_yoy"] == -5.32 and r["gdp_qoq"] == -4.19
    r = off[off["quarter"] == "2016Q1"].iloc[0]
    assert r["gdp_yoy"] == 4.94 and pd.isna(r["gdp_qoq"])  # pending, stays gap
    # every row carries its provenance
    assert off["yoy_source"].str.startswith("http").all()
    assert off.loc[off["gdp_qoq"].notna(), "qoq_source"].str.startswith("http").all()


def test_official_gdp_csv_structure():
    import csv
    with open("data/raw/official_gdp_quarterly.csv", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    assert rows[0] == ["quarter", "gdp_yoy", "yoy_source",
                       "gdp_qoq", "qoq_source", "note"]
    bad = [(i, len(r)) for i, r in enumerate(rows[1:], 1) if len(r) != 6]
    assert not bad, f"ragged rows shift columns silently: {bad}"
