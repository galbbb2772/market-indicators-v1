# Market Top NG3 — Inflation–Margin Route: research protocol

Status: HYPOTHESIS_REGISTERED / NOT VALIDATED / RESEARCH_ONLY

## Scope
New structural route for inflation-driven earnings and valuation compression. It is not legacy Route_A or Route_C recovery. Route_B remains frozen. NG1/NG2 results cannot be used to tune NG3.

## Economic hypothesis
Inflation acceleration may precede earnings-margin compression and equity drawdowns, but inflation by itself is not a sufficient equity-top signal. Separate contemporaneous stress detection from **leading** prediction. Evaluate against naive inflation-only and price-only baselines.

## Data acquisition contract (before any score)
- CPI-U all-items: BLS official monthly series CUUR0000SA0, historical release date / real-time vintage where available.
- Producer costs: BLS PPI final-demand series, only over its documented availability; do not splice a proxy silently.
- Corporate profits and margins: BEA NIPA corporate profits and gross value added; document exact table, definition, revisions, and publication lag.
- Optional independent margins proxy: S&P 500 reported/operating earnings from an attributable provider, licensed where needed. Never assume it is free.
- Equity outcome: S&P 500 price index, not total return, with dated observations and missing-day checks.
- Yield-curve/rates controls: U.S. Treasury primary series, with availability and historical publication timing documented.

## Pre-analysis audit
1. Inventory start/end dates, frequency, units, missing periods and source revision/vintage availability for every series.
2. Identify release dates and first usable trading session for each observation; default to a conservative lag if vintage timestamps are absent, flag as reconstructed rather than genuine PIT.
3. Freeze series transformations, warmup, market top-location gate, episode construction and 252-session outcome rules *before* scoring.
4. Freeze temporal development, validation and untouched holdout windows *before* reviewing outcomes. The 1968–74 and 1987 examples are hypothesis-generation examples, **not** untouched holdouts.
5. Record whether BEA profits were revised and how that affects any historical replay. Do not use revised profit observations as if they were available at the time.
6. Report coverage shortfalls; never fill absent prehistory with synthetic observations.

## Candidate feature families (NOT a frozen formula)
- Inflation acceleration: change in YoY CPI inflation over a trailing window.
- Margin squeeze: deterioration in corporate profit / value added, with correct BEA release lag.
- Cost-price divergence: producer inflation minus consumer inflation, only when comparable definitions and coverage exist.
- Market location: independently frozen 24-month-high proximity and recency gate.
These are candidate features, not validated alpha. No weights or thresholds have been selected.

## Leakage safeguards
- Any decision at equity close t uses only releases timestamped no later than t.
- Never select features based on 1968–74 or 1987 hit rates and then call those same episodes OOS.
- Distinguish detection lead time from subsequent drawdown and false-alarm frequency.
- Compare to fixed baselines and report all events, including misses and false positives.
- Fail closed on source gaps and vintage uncertainty.

## Promotion boundary
No dashboard full-pressure integration, production alert, trading instruction, or claim of historical validation is authorized by this protocol. Next milestone is a source coverage/PIT feasibility audit, then a *separate* numerical preregistration before backtesting.
