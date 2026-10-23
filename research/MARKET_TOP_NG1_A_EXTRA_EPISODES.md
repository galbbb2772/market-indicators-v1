# Route_A_NG1 — Additional Episode Case Studies

Status:

```
SOURCE_VALIDATED_SCREENING_CANDIDATE_WITH_KNOWN_FALSE_POSITIVE
```

No NG1 parameter is changed by this analysis.

## Diagnostic protocol

Before calculating the outcomes, the case-study protocol was fixed as:

- anchor = last trading day of the first ARMED month;
- horizons = 63 / 126 / 252 trading sessions;
- SPY unadjusted Close;
- forward return;
- worst return from the signal close;
- maximum peak-to-trough drawdown inside the horizon.

Two independent SPY snapshots give the same results:

- `soGeneri/MarketDatasets`;
- `Setooooo/etf-insight`.

## 1998-11 through 1999-03

First ARMED anchor:

```
1998-11-30
SPY = 116.125
```

Outcomes:

| Horizon | Forward return | Worst vs signal | Max peak-to-trough DD |
|---|---:|---:|---:|
| 63 sessions | +6.32% | -2.05% | -5.11% |
| 126 sessions | +11.84% | -2.05% | -6.39% |
| 252 sessions | +19.94% | -2.05% | -11.94% |

Interpretation:

```
CLEAR_TOP_FALSE_POSITIVE
```

SPY never traded more than roughly 2.05% below the initial signal close during the next 252 sessions and ended almost 20% higher.

A later drawdown from a higher local peak does not make the original signal a valid market-top call.

This episode must remain visible in all NG1 reporting.

## 2012-02

Anchor:

```
2012-02-29
SPY = 137.020004
```

Outcomes:

| Horizon | Forward return | Worst vs signal | Max peak-to-trough DD |
|---|---:|---:|---:|
| 63 sessions | -3.84% | -5.31% | -8.53% |
| 126 sessions | +3.20% | -6.51% | -9.69% |
| 252 sessions | +11.60% | -6.51% | -9.69% |

Interpretation:

```
CORRECTION_RISK_NOT_MAJOR_TOP
```

NG1-A did identify a period of real stress: a roughly 9.7% correction followed.

But it did not identify a durable major top. The market recovered and was materially higher one year later.

## What this changes

The 2007 result still survives:

- preregistered first screen;
- clean preregistered 2000 / 2011 / 2018 negative windows;
- independent source replay;
- top-location gate.

But the extra episodes show that NG1-A is not a pure top detector.

A more precise description is:

> NG1-A detects a credit-market/breadth stress configuration that was present at the 2007 top but can also occur before ordinary corrections or during continuing bull markets.

Therefore it remains a research screening candidate, not a production route.

## Next gate

Do not tune NG1 using 1998 or 2012.

Instead, freeze NG1 unchanged and inspect an untouched post-2022 holdout.

Any structural redesign after that must be named NG2 and preregistered before testing.
