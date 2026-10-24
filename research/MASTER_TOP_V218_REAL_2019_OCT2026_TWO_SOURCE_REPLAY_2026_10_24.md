# V2.1.8 real historical+Forward 2019–2026-10 data reuse — 2026-10-24

This corrects the previous answer saying existing data were insufficient **to run any real historical replay**. Both user-owned inputs were indeed available:

* `US_DAILY_2019-01_to_2026-03.parquet`, 361,249,091 bytes, 23,816,047 genuine bars, 47,480 historical ticker strings; **2019-01-02–2026-03-31**, 1,821 market sessions.
* `MARKETPARQUET_FORWARD_2026-04-01_to_2026-10-09.zip`, 133 dated **Stock** partitions, 888,409 real bars, 7,512 symbols; **2026-04-01–2026-10-09**.
* Original saved price and 2Y Treasury two-gate work from PR #21 provides the 1M/6M rate and ^GSPC series; frozen original V2.1.8 math is unchanged.

## ACTUALLY EXECUTED

Full original 23.8M-bar prices read for per-symbol last 252 prior closes and Forward-history bootstrap; every one of 133 private Stock partitions ingested, no invented price. Dataset joined: **1,954 distinct contiguous market sessions** in date-range Jan2019–Oct9 2026 (the market calendar has trading-day weekends/holidays, not daily date continuity). Applied frozen H/L persistence20, H/L gate75, TopRatio>=.95, threshold55 and 126-market-session event lock. A separate independent mathematical receipt rechecked every recorded score and the 126-session event dedup.

* Historical mixed security universe: **11 tentative alert dates, one provisional episode starting 2021-12-07 (72.46393)**. The realized ^GSPC 12-month post-event path maximum drawdown is **−25.42510%** (not a causal effectiveness proof).
* 2026 Forward Stock partition *bootstrapped from historical mixed-source tickers*: **16 tentative alert dates, one provisional episode starting 2026-09-18 (69.52510)**. As of Forward ZIP end 2026-10-09, the 12m outcome is **censored**, and the observed post-event path MDD to archive cutoff is −1.45737%, NOT a 12m bear prediction verification.
* Total **27 tentative alert-days / 2 provisional deduplicated episodes**. By year: 2019 0, 2020 0 (COVID miss), 2021 11, 2022 0, 2023 0, 2024 0, 2025 0, Jan–Oct2026 16.
* At Forward first session **5,601 of 6,763** valid 252-close mature tickers; last session **5,684 of 6,490**. **729 of 7,512** Forward tickers have no preceding historical ticker at all.
* **263** initial source-switch ticker price comparisons differ by >2× or <0.5×; a separate conservative QA variant quarantines **359** histories for 2× discontinuity OR >90-calendar-day source gap. This can alter signals: on **2026-09-17**, frozen raw-input score=0 whereas the source QA sensitivity version=67.23758, giving a full-day earlier signal. **This conservative QA filter is NOT a frozen model rule**. It highlights cross-provider source insecurity.
* 22,190 historical ticker **strings** have their last row before 2026; they are plausible now-inactive/delisted coverage, **not proof of 22,190 delisted companies**. The data include ETFs, OTC, other instruments, security ticker reuse and no independent daily permanent security IDs. Also the 2024-11-13 slice is corrupted; provider adjustments across the 2026-03/04 bridge are unverified. Hence **none of the 27 candidate days can be labeled a certified historical frozen common-stock PIT signal**, despite using actual prices. The 2000–2018 stock history is not present.

## Evidence/artifact lineage

* Local executable `stitch_2019_2026_actual_prices_v218.py`: actual historical+Forward raw-price ingestion and analysis, no source fabrications.
* Independent `verify_2019_2026_stitched.py`: confirms 1,954 dates, 27 candidate alert days, 2 episodes, model formula, per-year counts, and **censored 2026 event**.
* Local full daily derived data (no stock-level raw vendor prices in public repo): `v218_real_2019_2026_10_stitched_exploratory_scores.csv`, `v218_2019_2026_10_bridge_receipt.json`, `v218_stitched_verification_2026_10_24/independent_check_receipt.json`. Available to user as zip attachment in conversation.
* Frozen production `main`, dashboard and active signal **unchanged**. Research code/results have not been promoted to verified PIT.

**Conclusion: YES — both real user-provided date-ranged data sources can and already HAVE been run together for a 2019–Oct 2026 exploratory replay. NO — having historically inactive names in the input does not certify complete delisted security membership or the frozen common-stock universe.** Keep the experimental result but do not merge into production as formal V2.1.8 backtest.
