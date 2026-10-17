# Market Top Forward Shadow

Status: **RESEARCH ONLY / ROUTE_B PATH ONLY**

This forward process operationalizes only the parts of the Market Top research model that are currently reproducible:

```
DGS2 + WALCL
    -> PolicyShock V2.1.1

Shiller CAPE
    -> canonical Valuation

Fama-French SMB
    -> canonical SizeWeakness

Valuation + PolicyShock + SizeWeakness
    -> Route_B

SPY close
    -> T_v2.4R / DD12 / top-location gates
```

Original Route_A and Route_C remain unresolved and are never synthesized by the forward updater.

## Output files

When run in write mode:

- `docs/data/market_top_shadow_current.json`
- `docs/data/market_top_shadow_history.json`

The history is keyed by market as-of date so a rerun replaces that date rather than duplicating it.

## Data-source policy

### 2Y Treasury

Primary source:

- U.S. Treasury Daily Treasury Par Yield Curve Rates CSV;
- the `2 Yr` column is used directly.

Fallback:

- FRED DGS2 if the Treasury endpoint is unavailable.

For the live calculation:

- use the latest observation on or before the latest SPY close;
- the six-month anchor is the last observation on or before the calendar six-month anchor date.

The actual source used on each run is written into the snapshot.

### WALCL / Federal Reserve total assets

Primary operational source:

- `market-weather-map` static GitHub mirror of FRED WALCL;
- the mirror records its own generation timestamp and FRED source URL.

Fallback:

- direct FRED WALCL CSV.

The mirror was introduced because the direct FRED CSV endpoint timed out from GitHub Actions during live dry-run, while the mirror was current through 2026-10-14 and reproduced the already verified WALCL values exactly.

For the signal:

- use the latest observation at least one calendar day older than the market as-of date;
- this conservatively respects the normal Wednesday-observation / Thursday-release pattern;
- 13-week and 26-week anchors are selected on-or-before their calendar-week targets.

### Shiller CAPE

The forward job consumes the public `shiller-data` JSON feed.

That feed states that it resolves the current `ie_data.xls` link from `shillerdata.com`, maps columns by header text, performs freshness/sanity validation, and refuses stale/regressed output.

For the Market Top signal:

- the current unfinished calendar month is never used;
- the last completed month is the newest eligible CAPE observation.

### Fama-French SMB

The updater first attempts the Ken French Data Library ZIP directly.

If the direct source is unavailable, it falls back to a GitHub mirror of the same Fama-French factor file and records that fallback in the output.

Only factor months actually present in the downloaded published dataset are consumed.

### SPY

Yahoo Finance chart history is used for **unadjusted Close**, matching the T_v2.4R validation convention.

The query1 endpoint falls back to query2.

## Price semantics

`T_v2.4R` retains its preregistered definitions:

- 252-session high for DD12;
- prior 10 completed calendar month-end closes for the 10M MA;
- 70 T threshold;
- 4.5% DD12 guard.

The Route_B ARMED location gate uses:

- trailing **24 calendar months**;
- price within 5% of that high;
- high date within the prior 3 calendar months.

## Route_B-only state machine

The forward path maintains an independent policy-route state:

```
IDLE -> ARMED -> TRIGGERED
```

An arm starts only when:

```
Route_B >= 85
AND top-location gate passes
```

The original arm date is retained; repeated ARMED observations do **not** renew the six-month clock.

Within six calendar months:

```
T_v2.4R >= 70
AND DD12 >= 4.5%
```

moves the Route_B-only shadow path to terminal `TRIGGERED`, matching the frozen replay semantics.

## Critical scope boundary

The forward JSON must always keep:

```
full_legacy_model.pressure_authoritative = false
Route_A = UNRESOLVED
Route_C = UNRESOLVED
```

Therefore:

- `policy_path.state` is an authoritative state for the reconstructed **Route_B-only shadow path**;
- it is not the full legacy V2.4 state;
- `Pressure=max(A,B,C)` remains unavailable until authentic A/C definitions are recovered or a separately versioned next-generation model is accepted.

## Workflow

`.github/workflows/market_top_shadow_forward.yml`

On pull requests it:

1. compiles the updater;
2. runs deterministic unit contracts;
3. performs a live network dry-run without writing data.

If the workflow is later merged to the default branch, the scheduled path is prepared to run after U.S. market closes and commit only the two research shadow JSON outputs.

No production Market Model V2 score is modified.


## Live source validation

GitHub Actions live dry-run on 2026-10-17 passed end-to-end with:

- 2Y source: U.S. Treasury Daily Treasury Par Yield Curve Rates;
- WALCL source: FRED WALCL via the static GitHub mirror;
- Shiller source: Robert Shiller / Yale feed;
- Fama-French source: Ken French Data Library;
- SPY source: Yahoo Finance unadjusted Close.

The live 2026-10-16 snapshot produced:

```
DGS2 = 4.74%
6M anchor = 3.78%
RateShock = 100.00

TaperShock = 6.8606
PolicyShock = 62.7442

Valuation = 98.9137
SizeWeakness = 45.4470
Route_B = 65.5810

top-location gate = TRUE
Route_B pressure gate = FALSE
Route_B-only state = IDLE

T_v2.4R = 13.7753
DD12 = 2.0331%
Price Breakdown = FALSE
```

This live run validates both the calculation path and the current provider failover design.
