"""Module 2: Electricity vs Manufacturing GDP via BPS WebAPI.

Primary: stadata.Client (key from .env BPS_KEY). Fallback: raw requests.
Without a key or discovered var IDs, falls back to the labeled mock
data/raw/mock_elec_mfg.csv so the pipeline keeps running offline.
"""
import os
import re
import logging

import pandas as pd

log = logging.getLogger(__name__)

MOCK = "data/raw/mock_elec_mfg.csv"


def _bps_key():
    return os.getenv("BPS_KEY", "").strip()


def _view_via_stadata(key, domain, var):
    from stadata import Client
    client = Client(key)
    res = client.view_dynamictable(domain=domain, var=var)
    if res is None:
        raise RuntimeError("stadata returned None for domain=%s var=%s" % (domain, var))
    return res


def _view_via_requests(key, domain, var, base_url):
    url = (f"{base_url}/list/model/data/perpage/100000/lang/ind/"
           f"domain/{domain}/key/{key}/keyword//page/1/var/{var}")
    import requests
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    j = r.json()
    if j.get("status") != "OK":
        raise RuntimeError(f"BPS API status: {j}")
    return j


_Q_RE = re.compile(r"(\d{4})\s*[Qq.](\d)")
_Y_RE = re.compile(r"^(\d{4})$")


def _to_quarterly(view_df, value_label=None):
    """Normalize a BPS view (columns = period labels, rows = vars) to (quarter, value).

    Handles labels like '2018-Q1', '2018 Q1', 'Q1 2018' and annual '2018'.
    """
    rows = []
    cols = [str(c) for c in view_df.columns]
    data_cols = []
    for c in cols:
        m = _Q_RE.search(c)
        if m:
            data_cols.append((c, f"{m.group(1)}Q{m.group(2)}"))
        elif _Y_RE.match(c.strip()):
            data_cols.append((c, f"{c.strip()}Q1"))  # annual: attach to Q1 (approx)
    if not data_cols:
        raise ValueError("No period columns recognized: %s" % cols)
    for i, row in view_df.iterrows():
        label = value_label or str(view_df.index.name or "")
        for c, q in data_cols:
            v = row[c]
            try:
                v = float(str(v).replace(".", "").replace(",", "."))
            except (ValueError, TypeError):
                continue
            rows.append({"quarter": q, "value": v})
    out = pd.DataFrame(rows)
    if out.empty:
        raise ValueError("No numeric values parsed from BPS view")
    return out[["quarter", "value"]]


def _load_one(key, base_url, vid_cfg, domain_default="0052"):
    if not vid_cfg:
        return None
    domain = str(vid_cfg.get("domain", domain_default))
    var = vid_cfg.get("var")
    if not var:
        return None
    try:
        view = _view_via_stadata(key, domain, var)
        return _to_quarterly(view, vid_cfg.get("label"))
    except Exception as e:
        log.warning("stadata failed (%s), trying raw requests", e)
    view = _view_via_requests(key, domain, var, base_url)
    datacontent = view["datacontent"]
    df = pd.DataFrame(list(datacontent.items()), columns=["key", "value"])
    # raw API keys look like "<vervar><var><turvar><th>"; fall back to period labels in 'tahun'
    tahun = {t["val"]: t["label"] for t in view.get("tahun", [])}
    rows = []
    for _, r in df.iterrows():
        k = str(r["key"])
        for code, label in tahun.items():
            if k.endswith(code):
                try:
                    rows.append({"quarter": label, "value": float(str(r["value"]).replace(",", "."))})
                except ValueError:
                    pass
                break
    return pd.DataFrame(rows, columns=["quarter", "value"]).dropna() if rows else None


def get_electricity_and_mfg(cfg):
    key = _bps_key()
    bps = cfg["bps"]
    var_ids = bps.get("var_ids") or {}
    elec = mfg = None
    if key and (var_ids.get("electricity") or var_ids.get("manufacturing_gdp")):
        try:
            elec = _load_one(key, bps["base_url"], var_ids.get("electricity") or {}, "0052")
            mfg = _load_one(key, bps["base_url"], var_ids.get("manufacturing_gdp") or {}, "0007")
        except Exception as e:
            log.warning("BPS fetch failed: %s", e)
    if elec is None or mfg is None:
        if os.path.exists(MOCK):
            log.warning("Using MOCK electricity/manufacturing data (no BPS key or var IDs configured)")
            mock = pd.read_csv(MOCK)
            if elec is None:
                elec = mock[["quarter", "elec"]].rename(columns={"elec": "value"})
            if mfg is None:
                mfg = mock[["quarter", "mfg"]].rename(columns={"mfg": "value"})
        else:
            raise FileNotFoundError("No BPS credentials AND no mock at %s" % MOCK)
    df = elec.merge(mfg, on="quarter", suffixes=("_elec", "_mfg"))
    df = df.rename(columns={"value_elec": "elec", "value_mfg": "mfg"}).sort_values("quarter").reset_index(drop=True)
    df["elec_yoy"] = df["elec"].pct_change(4) * 100
    df["mfg_yoy"] = df["mfg"].pct_change(4) * 100
    # ratio is a plain number. No flags, no thresholds (PLAN.MD 15).
    df["ratio"] = df["elec_yoy"] / df["mfg_yoy"]
    return df


def run(cfg):
    df = get_electricity_and_mfg(cfg)
    out = "data/processed/elec_mfg.csv"
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
