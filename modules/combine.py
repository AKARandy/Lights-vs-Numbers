"""Module 5 (replaces scoring): descriptive quarterly join. No index, no weights.

Aligns every signal to quarters, computes YoY growth where applicable, maps
official GDP. Missing = NaN (gaps shown as gaps). Output: overview.csv.
"""
import os
import logging

import pandas as pd

log = logging.getLogger(__name__)

PROC = "data/processed"


def _q(period):
    return str(pd.Period(period, freq="Q"))


def _inputs_exist():
    return all(os.path.exists(os.path.join(PROC, f)) for f in
               ["ntl_quarterly.csv", "elec_mfg.csv", "trends_consumption.csv",
                "port_national.csv"])


def load_all():
    ntl = pd.read_csv(os.path.join(PROC, "ntl_quarterly.csv"))
    elec = pd.read_csv(os.path.join(PROC, "elec_mfg.csv"))
    trends = pd.read_csv(os.path.join(PROC, "trends_consumption.csv"))
    pn = pd.read_csv(os.path.join(PROC, "port_national.csv"))
    return ntl, elec, trends, pn


def load_official():
    """Single source of truth: data/raw/official_gdp_quarterly.csv.

    Columns: quarter, gdp_yoy, yoy_source, gdp_qoq, qoq_source, note.
    Missing quarters stay NaN downstream (gaps shown as gaps).
    """
    p = os.path.join("data", "raw", "official_gdp_quarterly.csv")
    if not os.path.exists(p):
        return None
    off = pd.read_csv(p, dtype={"quarter": str})
    off["quarter"] = off["quarter"].astype(str)
    return off


def build_overview(ntl, elec, trends, pn, cfg, official=None):
    df = ntl[["quarter", "ntl_mean", "ntl_yoy"]].copy()
    df["quarter"] = df["quarter"].map(_q)

    e = elec[["quarter", "elec", "mfg", "elec_yoy", "mfg_yoy", "ratio"]].copy()
    e["quarter"] = e["quarter"].map(_q)
    df = df.merge(e, on="quarter", how="outer")

    t = trends.copy()
    t["quarter"] = t["month"].map(_q)
    df = df.merge(t.groupby("quarter")[["consumption_index"]].mean(),
                  on="quarter", how="outer")

    p = pn.copy()
    p["quarter"] = p["month"].map(_q)
    q = p.groupby("quarter").agg(calls=("calls", "sum"),
                                 volume_mt=("volume_mt", "sum")).reset_index()
    q = q.sort_values("quarter")
    q["calls_yoy"] = q["calls"].pct_change(4) * 100
    q["volume_yoy"] = q["volume_mt"].pct_change(4) * 100
    df = df.merge(q, on="quarter", how="outer", suffixes=("", "_ports"))

    src = official if official is not None else cfg.get("official_gdp")
    if src is None:
        src = load_official()
    if isinstance(src, pd.DataFrame) and {"gdp_yoy", "gdp_qoq"}.issubset(set(src.columns)):
        m = src.set_index("quarter")
        df["official_gdp"] = df["quarter"].map(m["gdp_yoy"].astype(float))
        df["gdp_qoq"] = df["quarter"].map(m["gdp_qoq"].astype(float))
    else:
        official_map = {str(k): float(v) for k, v in (src or {}).items()}
        df["official_gdp"] = df["quarter"].map(official_map)
        df["gdp_qoq"] = float("nan")
    cols = ["quarter", "ntl_mean", "ntl_yoy", "elec", "mfg", "elec_yoy",
            "mfg_yoy", "ratio", "consumption_index", "calls", "volume_mt",
            "calls_yoy", "volume_yoy", "official_gdp", "gdp_qoq"]
    return df.sort_values("quarter").reset_index(drop=True)[cols]


def run(cfg):
    ntl, elec, trends, pn = load_all()
    df = build_overview(ntl, elec, trends, pn, cfg)
    out = os.path.join(PROC, "overview.csv")
    df.to_csv(out, index=False)
    log.info("Wrote %s (%d rows, %d cols)", out, len(df), len(df.columns))
    return df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    import yaml
    cfg = yaml.safe_load(open("config.yaml"))
    print(run(cfg).tail(8).to_string())
