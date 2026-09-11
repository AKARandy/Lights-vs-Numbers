"""Module 3: Google Trends consumption signals via pytrends.

Consumption keyword panel -> z-scored row mean -> monthly consumption_index.
Raw pulls cached in data/raw (7-day TTL). No API key. pytrends is unofficial;
Apify is the Phase-2 upgrade path.

NOTE: the former stress panel was removed 2026-09-11. Search keywords rot as
slang migrates to brand/app names (concept drift) and no validated keyword
set exists. Consumption searches are kept as a coincident sentiment input.
"""
import os
import time
import logging

import pandas as pd

log = logging.getLogger(__name__)


def _cache_path(kind):
    return f"data/raw/trends_{kind}_raw.csv"


def _load_cache(kind, ttl_days=7):
    path = _cache_path(kind)
    if not os.path.exists(path):
        return None
    if (time.time() - os.path.getmtime(path)) / 86400 >= ttl_days:
        return None
    df = pd.read_csv(path, index_col="date", parse_dates=True)
    df = df.drop(columns=["isPartial"], errors="ignore")
    return df if not df.empty else None


def _save_cache(kind, df):
    path = _cache_path(kind)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df.to_csv(path)


def get_trends(keywords, cfg, kind="consumption"):
    """Pull interest_over_time for up to 5 keywords with retries.

    Returns a DataFrame indexed by date (weekly) with one column per keyword,
    or an empty DataFrame if all attempts fail.
    """
    cached = _load_cache(kind)
    if cached is not None:
        log.info("Using cached %s trends (%d rows)", kind, len(cached))
        return cached

    from pytrends.request import TrendReq

    tc = cfg["trends"]
    retries = 3
    for attempt in range(1, retries + 1):
        try:
            pt = TrendReq(hl=tc.get("hl", "id-ID"), tz=tc.get("tz", 420), timeout=(10, 30))
            pt.build_payload(keywords, cat=0, timeframe=tc["timeframe"], geo=tc["geo"])
            df = pt.interest_over_time()
            if df.empty:
                break
            df = df.drop(columns=["isPartial"], errors="ignore")
            _save_cache(kind, df)
            return df
        except Exception as e:
            wait = tc.get("retry_wait_seconds", 60)
            log.warning("trends pull attempt %d/%d failed: %s", attempt, retries, e)
            if attempt < retries:
                time.sleep(wait)
    return pd.DataFrame()


def _zscore_row_mean(df):
    if df.empty:
        return pd.Series(dtype=float)
    z = (df - df.mean()) / df.std(ddof=1).replace(0, pd.NA)
    return z.mean(axis=1)


def build_consumption_index(cfg):
    tc = cfg["trends"]
    cons = get_trends(tc["consumption_keywords"], cfg, "consumption")

    ci = _zscore_row_mean(cons)
    out = pd.DataFrame({"consumption_index": ci}).dropna()
    if out.empty:
        return out
    out["month"] = out.index.to_period("M")
    out = out.groupby("month")[["consumption_index"]].mean().reset_index()
    return out


def run(cfg):
    df = build_consumption_index(cfg)
    out = "data/processed/trends_consumption.csv"
    os.makedirs(os.path.dirname(out), exist_ok=True)
    df.to_csv(out, index=False)
    log.info("Wrote %s (%d rows)", out, len(df))
    return df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    import yaml
    cfg = yaml.safe_load(open("config.yaml"))
    res = run(cfg)
    print(res.tail())
