# GDP Reality Check Indonesia - PLAN.MD

## 0. Status and Decision Log

| Date | Ruling | Status |
|---|---|---|
| 2026-09-11 | Full 4-signal MVP, `venv+pip`, secrets in `.env`, mock-first (no keys) | Built |
| 2026-09-11 | MarineTraffic dropped (enterprise-only since Jan 2025), PortWatch on HDX primary | Built, live |
| 2026-09-11 | `stadata` primary for BPS; `pytrends` for MVP (Apify later) | Built (mock until key) |
| 2026-09-11 | **Stress search panel REMOVED permanently**, keyword rot / concept drift | Removed |
| 2026-09-11 | **RAI composite REMOVED**, no index, no weights, no verdicts | Deleted |
| 2026-09-11 | Slop banned, science welcome: economist-made composites allowed with adopted recipe | Policy |
| 2026-09-11 | **All 75 ports**, full history, plain numbers, no judgment colors | Built |
| 2026-09-11 | Ryo light theme (`ryoPorto.jpg`: #5276C6 / #FAE965 / #000000 on white) | Built |
| 2026-09-11 | EDA program, every row used, numbered findings, zero invented metrics | Built |
| 2026-09-11 | `pip cache purge` (456.9 MB reclaimed) | Done |
| 2026-09-11 | **Dash purge: em dashes and en dashes removed from all project text** | Done |
| 2026-09-11 | **Incident: dash-purge script bug emptied 23 code/doc files** (data, figures, venv untouched). All rebuilt from record | Recovered |
| 2026-09-11 | **Story lives ON graphs** (annotated callouts, highlights), no story-text, minimal words | Built |

**Build status (2026-09-11, descriptive rebuild COMPLETE, self-QA in progress):**
- `combine.py` descriptive join to `overview.csv` (35 quarters x 14 cols); `pytest` 5/5.
- Ports all 75: `port_activity.csv` 6,601 rows raw, `port_national.csv` 92 months,
  `port_rankings.csv` 75 ports, plus `port_vessel_mix.csv` and `port_dow.csv`.
- EDA: 15 figures, 12 tables, `FINDINGS.md` (12 numbered finds).
- Dashboard: 6 descriptive sections, Ryo light theme, MOCK stamps, downloads,
  annotated story callouts, bars/areas/heatmap alongside lines.
- Self-QA screenshots `reports/01-10_*.png`; AppTest 0 exceptions required.

---

## 1. Goal

Show lots of simple descriptive data analysis of Indonesian economic activity
next to official GDP. Blend nothing. The story is told ON the graphs
(annotated callouts pinned to data points, highlights, reference shapes) with
minimal words. A 9-year-old should get the point from the pictures.

---

## 2. Project Layout (Target)

```
Lights vs Numbers/
├── requirements.txt
├── config.yaml
├── .env.example
├── .gitignore
├── main.py
├── PLAN.MD
├── README.md
├── ryoPorto.jpg                # theme reference (do not delete)
├── modules/
│   ├── __init__.py
│   ├── nightlights.py          # GEE VIIRS, mock fallback
│   ├── electricity.py          # BPS via stadata, mock fallback, plain ratio
│   ├── trends.py               # consumption panel ONLY
│   ├── ports.py                # PortWatch, ALL 75 ports + national + mix + dow
│   ├── combine.py              # descriptive quarterly join, no index
│   └── palette.py              # (in dashboard/) Ryo palette, single source
├── scripts/
│   └── discover_bps_vars.py
├── tests/
│   └── test_descriptive.py     # join math, gap policy, ports aggregation
├── data/
│   ├── raw/                    # caches + labeled mocks
│   └── processed/              # per-signal files + national/rankings/mix/dow/overview
├── dashboard/
│   ├── app.py                  # 6 sections, story callouts, Ryo light
│   └── palette.py
├── .streamlit/
│   └── config.toml             # light theme tokens
├── eda/
│   ├── eda_ports.py
│   ├── eda_trends.py
│   ├── eda_cross.py
│   └── figures/                # numbered output charts
└── reports/
    ├── tables/                 # every aggregation as downloadable CSV
    ├── FINDINGS.md             # numbered finds with figure + row counts
    ├── 01-10_*.png             # dashboard QA screenshots
    └── template.html           # reserved for Phase-2 PDF
```

Deleted in the RAI purge: `modules/scoring.py`, `tests/test_scoring.py`,
`data/processed/rai_score.csv`, `data/processed/rai_weights.csv`,
`data/processed/trends_stress.csv`. `data/raw/trends_stress_raw.csv` stays on
disk as archive, never read.

---

## 3. Dependencies (`requirements.txt`)

earthengine-api, geemap, pandas>=2.0, numpy, requests, pytrends, stadata,
datasets, streamlit, plotly, pyyaml, schedule, python-dotenv, pytest, jinja2,
kaleido (figure export). No sklearn/scipy: nothing is estimated.

---

## 4. Configuration (`config.yaml` + `.env`)

`.env`: `GEE_PROJECT`, `BPS_KEY` (both empty until obtained).
`config.yaml`: gee project, BPS base_url + var_ids (null until discovery),
portwatch HDX IDs + csv_url + raw_cache + refresh_days + spotlight list
(dashboard defaults only, all 75 processed regardless), trends geo/timeframe +
consumption keywords, official_gdp quarters. NO scoring section. Ever.

---

## 5. Module 1 - Nighttime Lights

VIIRS VNP46A2 via GEE, band Gap_Filled_DNB_BRDF_Corrected_NTL, quarterly
server-side means, `ntl_yoy = pct_change(4)*100`. No key: labeled mock.
Output `ntl_quarterly.csv`: quarter, ntl_mean, ntl_yoy.

## 6. Module 2 - Electricity vs Manufacturing

stadata primary, raw requests fallback, labeled mock fallback. Output
`elec_mfg.csv`: quarter, elec, mfg, elec_yoy, mfg_yoy, ratio (plain number,
no flags).

## 7. Module 3 - Consumption Searches

pytrends, retries, 7-day cache. `build_consumption_index` to
`trends_consumption.csv` (month, consumption_index). Stress panel deleted
permanently (concept drift). Live, no key.

## 8. Module 4 - Ports, All 75

PortWatch HDX CSV (262,088 daily rows, 75 ports, 2019-01-01 to 2026-08-28,
zero nulls, 6 vessel splits + import/export splits). Verified names:
"Tanjung Priok" (port514), "Surabaya" = Tanjung Perak (port1237), "Belawan"
(port139). Outputs: per-port monthly (raw, never clipped), national totals,
rankings (totals + latest + MoM/YoY), vessel mix, weekday table. Live, no key.

## 9. Module 5 - Descriptive Join (`combine.py`)

Joins 5 inputs to quarterly `overview.csv` (14 cols). Only YoY math + official
mapping. Gaps stay gaps. `main.py` runs 4 fetchers + combine with per-module
isolation.

## 10. Dashboard (Ryo light, story on graphs)

`.streamlit/config.toml` forces light base. `palette.py`: RYO swatches
(blue #5276C6, yellow #FAE965, black, white, navy #2B4B9B, slate #555B63,
periwinkle #7E97D8) + blue ramp + `callout()` yellow story boxes.
Sections: 1 NTL, 2 electricity, 3 consumption (+ keyword chart with Lebaran
peak callout, top-10 weeks), 4 ports (national + cliff callout on weakest
month, vessel-mix area, Sunday bars, seasonality heatmap, top-8, 75-port
picker with yellow highlight, winners/losers bars, rankings), 5 official-GDP
overlays (black official line), 6 big table. Downloads on every table.
MOCK stamps stay (short honesty badges). No story-text sections.

## 11. EDA Program

Rules: counts, sums, means, medians, min/max, %, YoY/MoM/QoQ, ranks, labeled
rolling windows, shared-axis overlays. Forbidden: indexes, weights, verdicts,
thresholds, judgment colors, gap-filling. Every output states rows-in to
rows-out. Scripts: ports deep dive (mix, balance, DOW, seasonality, outliers,
concentration), trends (histories, peaks), cross (overlays + observed
co-movement with n). Outputs: `eda/figures/`, `reports/tables/`, FINDINGS.md.

## 12. Data Provenance

PortWatch daily: REAL. Trends raw: REAL. NTL + electricity: MOCK until keys.
Official GDP dataset: data/raw/official_gdp_quarterly.csv, 42 rows 2016Q1
to 2026Q2, YoY full, QoQ missing only 2016Q1-Q2 (pending), every row with
its source URL. combine.load_official() is the only reader.
Stress raw: ARCHIVED, never read.

## 13. Verification and QA Loop

pytest, main.py exit 0, AppTest 0 exceptions, browser screenshots of every
section, self-check first (fix, re-shoot), user is final evaluator per picture.

## 14. Storage Notes

Repo about 834 MB (.venv 803 MB + data 31 MB). OneDrive tree 5.1 GB vs 5 GB
free quota (project tipped a full box). No duplicates. pip cache purged.
.venv stays in OneDrive per user scope.

## 15. Banned List (Permanent)

**Banned is SLOP, not science.** Economist-made composites with an adopted
recipe are welcome (see 16). Banned forever: author-invented blends, verdicts,
invented thresholds, judgment colors, stress panel, clipped stored data,
gap-filling, causal claims, em/en dashes in project text. Violations reverted.

## 16. Open Items Needing a Human

1. `GEE_PROJECT` (free signup) to un-mock NTL.
2. `BPS_KEY` + discovery script to un-mock electricity.
3. Verify all four `official_gdp` values against BPS.
4. Composite recipe ruling when ready: (a) real economists sign off,
   (b) cited-paper weights, or (c) equal weights. Until then descriptive-only.
