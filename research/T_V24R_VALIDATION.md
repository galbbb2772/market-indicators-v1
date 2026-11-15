# T_v2.4R Validation Report

Status: **research-only / formula unchanged after preregistration**

## Data

Validation uses the public `soGeneri/MarketDatasets` daily SPY file `SPY_1993-2023_D.csv`, using the unadjusted Close column.

Usable score range after lookback warm-up:

- 1993-11-01 through 2022-12-30
- 7,345 daily observations

This is a SPY proxy validation, not a claim that ETF close is numerically identical to the S&P 500 index close.

## Frozen preregistered formula

```
DDScore = 100 * clip((DD12_pct - 1) / 6, 0, 1)
MAScore = 100 * clip(MAGap_pct / 4, 0, 1)
T_v2.4R = 0.80 * DDScore + 0.20 * MAScore

Price Breakdown =
    existing ARMED
    AND DD12_pct >= 4.5
    AND T_v2.4R >= 70
```

No threshold or weight was changed after observing the validation output.

## Known-event first confirmations

| Event top | First T_v2.4R price confirmation |
|---|---|
| 1998-07-17 | 1998-08-04 |
| 2000-03-24 | 2000-04-14 |
| 2007-10-09 | 2007-11-09 |
| 2011-04-29 | 2011-06-10 |
| 2018-09-20 | 2018-10-11 |
| 2022-01-03 | 2022-01-20 |

These dates are **unconditional price-confirmation dates** after the listed event tops. They do not imply a full Market Top Trigger unless an ARMED state already exists.

## 2022 path

SPY proxy:

| Date | DD12 | 10M MA | T_v2.4R | Price confirmation |
|---|---:|---:|---:|---|
| 2022-01-03 | 0.00% | 437.071 | 0.00 | NO |
| 2022-01-18 | 4.442% | 437.071 | 45.894 | NO |
| 2022-01-19 | 5.434% | 437.071 | 59.123 | NO |
| 2022-01-20 | 6.481% | 437.071 | 73.079 | YES |

Combined with the conservatively publication-lagged PolicyShock route:

```
2022-01-03:
Route_B = 85.3342917569589
=> ARMED

2022-01-20:
T_v2.4R = 73.079
DD12 = 6.481%
=> PRICE_BREAKDOWN_v2.4R
```

So the newly versioned research path is:

```
2022-01-03 ARMED
    -> 17 calendar days
2022-01-20 PRICE_BREAKDOWN_v2.4R
```

This is separate from the accepted historical V2.4 Early Breadth trigger in 2021-10.

## Unconditional frequency

The price-confirmation state is true on 2,218 of 7,345 usable days, or about **30.2%**.

That is intentionally too frequent to be a standalone market-top predictor. During prolonged bear markets it remains high for long periods.

The state machine is therefore essential:

```
Price confirmation alone != top signal
ARMED + price confirmation = breakdown confirmation
```

This result supports keeping T_v2.4R in the narrow role for which it was preregistered.

## Comparison with the missing original T

T_v2.4R does **not** attempt to reproduce the archived original T values.

The original formula remains unresolved and its historical fingerprints stay preserved separately.

The correct labels are:

- `T`: unresolved original V2.4 score;
- `T_v2.4R`: new transparent replacement candidate.

They must never be silently interchanged.
