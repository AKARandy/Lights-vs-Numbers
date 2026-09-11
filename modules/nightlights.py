"""Module 1: Nighttime lights (VIIRS VNP46A2) via Google Earth Engine.

Quarterly mean of Gap_Filled_DNB_BRDF_Corrected_NTL over Indonesia, 2018Q1+.
Quarter-level server-side aggregation (NOT per-image map) to avoid timeouts.
Without GEE_PROJECT, falls back to labeled mock data/raw/mock_ntl_quarterly.csv.
"""
import os
import logging

import pandas as pd

log = logging.getLogger(__name__)

MOCK = "data/raw/mock_ntl_quarterly.csv"
BAND = "Gap_Filled_DNB_BRDF_Corrected_NTL"
VNP46A2 = "NASA/VIIRS/002/VNP46A2"
GEO = "FAO/GAUL_SIMPLIFIED_500m/2015/level0"


def init_gee(project):
    import ee
    ee.Initialize(project=project)


def get_ntl_quarterly(cfg, start="2018-01-01", end=None):
    import ee

    end = end or pd.Timestamp.today().strftime("%Y-%m-%d")
    indo = ee.FeatureCollection(GEO).filter(ee.Filter.eq("ADM0_NAME", "Indonesia"))
    viirs = (ee.ImageCollection(VNP46A2)
             .select(BAND)
             .filterDate(start, end)
             .filterBounds(indo))

    quarters = pd.period_range(start, end, freq="Q")
    rows = []
    for q in quarters:
        img = viirs.filterDate(str(q.start_time.date()), str(q.end_time.date())).mean()
        red = img.reduceRegion(ee.Reducer.mean(), indo, scale=500, maxPixels=1e13).getInfo()
        rows.append({"quarter": str(q), "ntl_mean": red.get(BAND)})
    df = pd.DataFrame(rows)
    df["ntl_yoy"] = df["ntl_mean"].pct_change(4) * 100
    return df


def get_ntl_mock():
    mock = pd.read_csv(MOCK)
    mock["ntl_yoy"] = mock["ntl_mean"].pct_change(4) * 100
    log.warning("Using MOCK nighttime lights data (no GEE_PROJECT configured)")
    return mock


def run(cfg):
    project = os.getenv("GEE_PROJECT", "").strip() or cfg.get("gee", {}).get("project", "")
    df = None
    if project:
        try:
            init_gee(project)
            df = get_ntl_quarterly(cfg)
        except Exception as e:
            log.warning("GEE extraction failed: %s", e)
    if df is None or df.empty:
        if os.path.exists(MOCK):
            df = get_ntl_mock()
        else:
            raise FileNotFoundError("No GEE_PROJECT and no mock at %s" % MOCK)
    out = "data/processed/ntl_quarterly.csv"
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
