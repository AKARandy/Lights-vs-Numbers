# FINDINGS - GDP Reality Check Indonesia (descriptive, no index)

Ground: PortWatch daily 262,088 rows x 75 ports (2019-01-01 to 2026-08-28, zero
nulls) - Trends 262 weeks x 3 keywords - NTL + electricity = labeled MOCK
(33 quarters) - official GDP dataset data/raw/official_gdp_quarterly.csv:
42 rows 2016Q1 to 2026Q2, YoY full, QoQ missing only 2016Q1-Q2 (pending),
every row with its source URL. 2026Q3 not yet released.
Figures: `eda/figures/`. Tables: `reports/tables/`. Every number below is
traceable to one of them. No indexes, no verdicts.

## Ports (real data)

1. **Priok is #1 but sliding.** Tanjung Priok: 288.6M MT total (2019 to 2026),
   latest month volume YoY **-6.3%** (`port_rankings.csv`).
2. **Bunati cliff.** #2 port Bunati (254.5M MT, coal): latest volume YoY
   **-30.4%**. Single biggest red flag in the rankings.
3. **Nickel corridor visible.** Morowali Industrial Park #5 (166.2M MT);
   Tanjung Sangata #4. Bulk-export Kalimantan/Sulawesi dominate the top 5
   alongside Priok.
4. **August 2026 national cliff.** All-Indonesia: calls **-12.2% YoY**,
   volume **-21.5% YoY** (3,732 calls, 27.8M MT). Data runs to Aug 28 (nearly
   full month), a real drop, not a partial-month artifact
   (`port_national_monthly.csv`, fig_p01).
5. **Dead entries in the dataset.** Three "ports" show exactly 0 volume all-time
   (two offshore oil terminals, Muntok), dataset quirk, excluded from
   interpretation, kept in tables (`port_rankings.csv` bottom rows).
6. **Weekend dip.** Monday busiest (1.37 avg daily calls), Sunday quietest
   (1.16), about 15% weekend effect, all ports pooled (`port_dow.csv`, fig_p05).
7. **Import vs export balance** tracked monthly 2019 to 2026 (`port_impex_balance.csv`,
   fig_p04). Vessel-mix shares by type for calls and import tonnage
   (`port_vessel_mix_*.csv`, fig_p02/03).
8. **Outlier log kept raw.** Top-20 port-days and top-20 MoM jumps with base
   counts (`port_top_days.csv`, `port_top_jumps.csv`), small-port % spikes
   shown WITH denominators, never clipped.

## Consumption searches (real data)

9. **Lebaran dining surge.** All-time top search weeks are "restoran":
   100 (2022-05-01), 88/87 (April 2022), 81 (2023-04-02), Ramadan/Lebaran
   alignment, observed not modeled (`trends_top_weeks.csv`).
10. **Full keyword histories + monthly index** in fig_t01/t02; per-keyword
    mean/std/min/max in `trends_keyword_summary.csv`.

## Cross-signal (observed co-movement, n=26 real-signal quarters, WEAK, stated plainly)

11. With full BPS history (YoY 2016Q1 to 2026Q2; QoQ same range minus
    2016Q1-Q2 pending), correlations are directional hints, not evidence: port volume
    +0.378, port calls +0.105, consumption +0.313 move WITH official GDP,
    weakly; night lights -0.368 and electricity -0.293 move against it, but
    both are MOCK inputs so those two numbers mean nothing
    (`cross_comovement.csv`, fig_c00 to 04). The only honest read: real
    activity and official GDP broadly agree over 2019 to 2026, with visible
    quarterly divergences worth a look, never a verdict.
12. Official 2026Q1 5.61% sits next to: national port volume -21.5% (Aug),
    Priok -6.3%, Bunati -30.4%, elec/mfg ratio 0.10 (MOCK inputs, glass eyes).

## Row ledger

In: 262,088 daily port rows + 262x3 trend cells + 33+33 mock quarters.
Out: 92 national months, 6,601 port-months, 75 rankings, 61 trend months,
35 overview quarters, 15 figures, 12 tables. Nulls in: 0 (ports raw).
