# Market Top Cross-Model Boundary

Status: **FROZEN MODEL-IDENTITY CONTRACT**

There are now two distinct top-risk research lines in this repository. They must not be silently merged.

## 1. Market Top V2.4R Route_B Shadow

Current validated live snapshot:

```
as of 2026-10-16
Route_B = 65.5810
threshold = 85
top-location gate = TRUE
Policy path = IDLE

T_v2.4R = 13.7753
DD12 = 2.0331%
Price Breakdown = FALSE
```

Mechanism:

```
Shiller CAPE
  -> Valuation

2Y 6M repricing + WALCL taper
  -> PolicyShock V2.1.1

Fama-French SMB
  -> SizeWeakness

Route_B = cbrt(Valuation * PolicyShock * SizeWeakness)
```

This is the independent 2022 policy-route repair.

It is **not** the complete legacy V2.4 model because Route_A and Route_C remain unresolved.

## 2. MASTER TOP V2.1.8

Frozen on 2026-10-17.

Mechanism:

```
2Y 6M repricing
2Y 1M repricing
    -> Policy = sqrt(R6 * R1)

52-week New High/New Low balance
20-session persistence
    -> HL

60M top proximity
    -> TopProx

Supplemental Route
    = Policy * sqrt(HL/100) * sqrt(TopProx)
```

Threshold:

```
Route >= 55
```

This is a breadth + short-rate momentum supplemental route.

It is not Route_B, Route_C, or T_v2.4R.

## Current 2026 values are not directly comparable yet

The repository payload for MASTER TOP V2.1.8 currently says:

```
as of 2026-10-09
Route = 99.33
Triggered = TRUE
research_status = seed snapshot only
```

That value came from the pre-freeze seed/audit path.

The workflow is designed to replace it with:

- MarketParquet `stock_daily`;
- FRED DGS2;
- Yahoo `^GSPC`;

when `MARKETPARQUET_API_KEY` is available.

At this audit point, the repository contains no later `data: refresh MASTER TOP V2.1.8` bot commit.

Therefore it is not valid to state:

> On the same live date V2.1.8 says 99.33 while Route_B says 65.58.

The valid statement is:

> The V2.1.8 2026-10-09 seed/audit snapshot is triggered, while the independently live-validated Route_B Shadow is not armed on 2026-10-16.

## Historical mechanism comparison

### 2000

MASTER TOP V2.1.8:

- 1999-11-29 route ≈ 76.90;
- subsequent 12M MDD ≈ -13.43%;
- classified as Correction;
- its own spec says the 2000 bubble remains primarily an old-engine event.

Route_B Shadow:

- pure rate repricing alone cannot cross the 85 Route_B threshold by construction;
- legacy V2.4 concentration/breadth path is still unresolved.

### 2018

MASTER TOP V2.1.8:

- 2018-10-05 ≈ 66.06;
- post-top severe-near-miss confirmation.

Route_B Shadow:

- 2018 rate shock without genuine taper/QE-flow reversal is insufficient to arm Route_B.

### 2022

MASTER TOP V2.1.8:

- 2021-12-15 ≈ 69.42;
- roughly 12 trading sessions before the 2022-01-03 top.

Route_B Shadow:

- 2022-01-03 Route_B = 85.3343 -> ARMED;
- 2022-01-20 T_v2.4R + DD12 -> PRICE_BREAKDOWN_v2.4R.

The two routes therefore capture different stages of the same episode.

## Frozen non-equivalence rules

Do **not**:

- average the two model scores;
- take `max(Route_B Shadow, MASTER TOP V2.1.8)` unless a future explicitly preregistered ensemble says so;
- rename one route as the other;
- treat a seed snapshot as a same-day live score;
- use V2.1.8 as a substitute for the missing legacy V2.4 Route_C formula.

Agreement between the routes is corroborating evidence.

Disagreement is **diagnostic information** because the mechanisms are intentionally different.
