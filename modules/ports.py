"""Module 4: Port activity via IMF PortWatch dataset on HDX.

Free, no API key. Daily port calls + incoming/outgoing shipment volumes
(metric tons) for ALL 75 Indonesian ports, Jan 2019 to present, weekly updates.
Raw values only - no clipping, no winsorizing (base effects explained in text).

Outputs:
  port_activity.csv - every port x month: calls, import/export/volume MT, YoY
  port_national.csv - Indonesia totals per month + YoY
  port_rankings.csv - per-port totals, latest month values + YoY windows
  port_vessel_mix.csv - monthly national totals per vessel type
  port_dow.csv - average daily calls by weekday, all ports pooled
"""
import os
import time
import logging

import pandas as pd
import requests

log = logging.getLogger(__name__)

TYPES = ["container", "dry_bulk", "general_cargo", "roro", "tanker", "cargo"]


def download_portwatch(cfg, max_age_days=None):
    """Download the PortWatch CSV to the raw cache; reuse if fresh enough."""
    pc = cfg["portwatch"]
    max_age_days = pc.get("refresh_days") if max_age_days is None else max_age_days
    path = pc["raw_cache"]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.exists(path):
        age_days = (time.time() - os.path.getmtime(path)) / 86400
        if max_age_days is not None and age_days < max_age_days:
            log.info("PortWatch cache fresh (%.1f days old), reusing %s", age_days, path)
            return path
    log.info("Downloading PortWatch CSV (~33 MB) ...")
    r = requests.get(pc["csv_url"], timeout=300)
    r.raise_for_status()
    tmp = path + ".part"
    with open(tmp, "wb") as f:
        f.write(r.content)
    os.replace(tmp, path)
    return path


def load_portwatch(cfg, refresh=False):
    """Load daily data. refresh=False reuses cache younger than refresh_days."""
    max_age = None if refresh else cfg["portwatch"].get("refresh_days")
    path = download_portwatch(cfg, max_age_days=max_age)
    df = pd.read_csv(path)
    df["date"] = pd.to_datetime(df["date"], utc=True).dt.tz_localize(None)
    return df


def aggregate_ports(df):
    """Monthly per-port totals for ALL ports. Raw values, no clipping."""
    d = df.copy()
    d["month"] = d["date"].dt.to_period("M")
    g = d.groupby(["portname", "month"]).agg(
        calls=("portcalls", "sum"),
        import_mt=("import", "sum"),
        export_mt=("export", "sum"),
    ).reset_index().rename(columns={"portname": "port"})
    g["volume_mt"] = g["import_mt"] + g["export_mt"]
    g = g.sort_values(["port", "month"]).reset_index(drop=True)
    g["calls_yoy"] = g.groupby("port")["calls"].pct_change(12) * 100
    g["volume_yoy"] = g.groupby("port")["volume_mt"].pct_change(12) * 100
    return g[["port", "month", "calls", "import_mt", "export_mt",
              "volume_mt", "calls_yoy", "volume_yoy"]]


def national_totals(monthly):
    """Indonesia-wide monthly sums + YoY from summed levels."""
    n = monthly.groupby("month").agg(
        calls=("calls", "sum"), import_mt=("import_mt", "sum"),
        export_mt=("export_mt", "sum"), volume_mt=("volume_mt", "sum"),
        n_ports=("port", "nunique")).reset_index().sort_values("month")
    n["calls_yoy"] = n["calls"].pct_change(12) * 100
    n["volume_yoy"] = n["volume_mt"].pct_change(12) * 100
    return n


def rankings(monthly):
    """Per-port totals + latest-month snapshot with 1M/12M YoY context."""
    tot = monthly.groupby("port").agg(
        total_calls=("calls", "sum"), total_volume_mt=("volume_mt", "sum"),
        months=("month", "nunique")).reset_index()
    last_month = monthly["month"].max()
    last = monthly[monthly["month"] == last_month][
        ["port", "calls", "volume_mt", "calls_yoy", "volume_yoy"]]
    prev = monthly[monthly["month"] == last_month - 1][["port", "calls", "volume_mt"]]
    prev = prev.rename(columns={"calls": "prev_calls", "volume_mt": "prev_volume"})
    out = tot.merge(last, on="port", how="left").merge(prev, on="port", how="left")
    out["last_month"] = str(last_month)
    out["calls_mom"] = (out["calls"] / out["prev_calls"] - 1) * 100
    out["volume_mom"] = (out["volume_mt"] / out["prev_volume"] - 1) * 100
    return out.sort_values("total_volume_mt", ascending=False).reset_index(drop=True)


def vessel_mix(df):
    """Monthly national tonnage/call totals per vessel type (descriptive)."""
    d = df.copy()
    d["month"] = d["date"].dt.to_period("M").astype(str)
    out = d.groupby("month").agg(
        **{f"calls_{t}": (f"portcalls_{t}", "sum") for t in TYPES},
        **{f"mt_{t}": (f"import_{t}", "sum") for t in TYPES}).reset_index()
    for t in TYPES:
        out[f"mt_{t}"] = out[f"mt_{t}"] + d.groupby("month")[f"export_{t}"].sum().values
    return out.sort_values("month").reset_index(drop=True)


def dow_table(df):
    """Average daily calls by weekday, all ports pooled (descriptive)."""
    d = df.copy()
    d["dow"] = d["date"].dt.day_name()
    out = d.groupby("dow")["portcalls"].mean().reindex(
        ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"])
    return out.reset_index().rename(columns={"portcalls": "avg_daily_calls"})


def run(cfg):
    df = load_portwatch(cfg)
    monthly = aggregate_ports(df)
    nat = national_totals(monthly)
    rank = rankings(monthly)
    mix = vessel_mix(df)
    dow = dow_table(df)
    os.makedirs("data/processed", exist_ok=True)
    monthly.to_csv("data/processed/port_activity.csv", index=False)
    nat.to_csv("data/processed/port_national.csv", index=False)
    rank.to_csv("data/processed/port_rankings.csv", index=False)
    mix.to_csv("data/processed/port_vessel_mix.csv", index=False)
    dow.to_csv("data/processed/port_dow.csv", index=False)
    log.info("Wrote port_activity (%d rows, %d ports), national (%d), rankings (%d)",
             len(monthly), monthly["port"].nunique(), len(nat), len(rank))
    return monthly, nat, rank


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    import yaml
    cfg = yaml.safe_load(open("config.yaml"))
    m, n, r = run(cfg)
    print("ports:", m["port"].nunique(), "| months:", m["month"].nunique())
    print(n.tail(3).to_string())
    print(r.head(8)[["port", "total_volume_mt", "calls_yoy", "volume_yoy"]].to_string())
