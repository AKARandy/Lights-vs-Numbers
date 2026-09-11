"""Discover BPS WebAPI variable/table IDs for electricity + manufacturing GDP.

Usage:
    python scripts/discover_bps_vars.py --keyword listrik
    python scripts/discover_bps_vars.py --keyword pertumbuhan --domain 0007

Requires BPS_KEY in .env (register at https://webapi.bps.go.id/developer/).
Prints candidate table IDs to pin into config.yaml:bps.var_ids.
"""
import argparse
import os
import sys

import requests
from dotenv import load_dotenv

load_dotenv()
BASE = "https://webapi.bps.go.id/v1/api"


def list_tables(key, domain="0000", keyword="", pages=3):
    hits = []
    for page in range(1, pages + 1):
        url = (f"{BASE}/list/model/statictable/perpage/100/lang/ind/"
               f"domain/{domain}/key/{key}/keyword/{keyword}/page/{page}")
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        j = r.json()
        if j.get("status") != "OK":
            print("BPS status:", j)
            break
        for row in j.get("data", []):
            hits.append(row)
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keyword", default="listrik")
    ap.add_argument("--domain", default="0000")
    ap.add_argument("--pages", type=int, default=3)
    args = ap.parse_args()

    key = os.getenv("BPS_KEY", "").strip()
    if not key:
        print("No BPS_KEY in .env. Register at https://webapi.bps.go.id/developer/ and set BPS_KEY=...")
        sys.exit(1)

    hits = list_tables(key, domain=args.domain, keyword=args.keyword, pages=args.pages)
    if not hits:
        print("No tables matched keyword=%r domain=%r" % (args.keyword, args.domain))
        return
    for h in hits:
        print("-", {k: h.get(k) for k in ("id", "domain", "judul", "title", "var") if k in h})


if __name__ == "__main__":
    main()
