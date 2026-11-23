# Route_A_NG1 — Post-2022 Temporal Holdout

Status:

```
ARMED_EPISODES_WITH_COMPLETE_OUTCOMES
```

Research only. The holdout was preregistered before the 2023+ states were inspected.

No NG1 formula, lag, threshold, or top-location condition was changed.

## Holdout coverage

Effective monthly states:

```
2023-01 through 2026-07
43 months
```

The endpoint is determined by the common availability of the frozen monthly inputs:

- FF25 / FF12 / FF3 source data through 2026-05;
- BAA / GS10 monthly source data through 2026-06;
- +2 month FF lag and +1 month credit lag.

No missing signal month is interpolated.

Two ARMED episodes appear.

## 1. 2025-07

Signal:

```
Route_A_NG1 = 85.4109
threshold = 85
top-location gate = TRUE
```

Frozen component scores:

```
SpreadShock       = 79.56
FinanceWeakness   = 73.27
SizeWeakness      = 96.79
PortfolioExhaust. = 94.33
```

Anchor:

```
2025-07-31
SPY = 632.08
```

Outcome:

| Horizon | Forward return | Worst vs signal | Max peak-to-trough DD |
|---|---:|---:|---:|
| 63 sessions | +8.75% | -1.64% | -2.98% |
| 126 sessions | +9.48% | -1.64% | -5.07% |
| 252 sessions | +19.87% | -1.64% | -9.13% |

Interpretation:

```
CLEAR_TOP_FALSE_POSITIVE
```

The index barely traded below the signal price and finished the 252-session horizon almost 20% higher.

A later correction from a higher local peak does not rescue the original call as a market top.

## 2. 2025-09

Signal:

```
Route_A_NG1 = 85.3933
threshold = 85
top-location gate = TRUE
```

Components:

```
SpreadShock       = 73.93
FinanceWeakness   = 81.84
SizeWeakness      = 89.78
PortfolioExhaust. = 97.89
```

Anchor:

```
2025-09-30
SPY = 666.18
```

Outcome:

| Horizon | Forward return | Worst vs signal | Max peak-to-trough DD |
|---|---:|---:|---:|
| 63 sessions | +3.13% | -2.05% | -5.07% |
| 126 sessions | -1.64% | -5.14% | -9.13% |
| 252 sessions | +14.68% | -5.14% | -9.13% |

Interpretation:

```
CORRECTION_RISK_NOT_MAJOR_TOP
```

The signal preceded a real correction, but not a durable market top. By 252 sessions SPY was roughly 14.7% above the signal close.

## Price-source completion

The original screening price snapshot stopped before either episode had a full 252-session outcome.

The final outcomes were completed with Massive SPY daily aggregates using:

```
adjusted = false
```

The already-observed 63/126-session outcomes match the prior SPY snapshot to normal floating-point precision, and the live source extends both episodes beyond 252 sessions.

## Holdout conclusion

The holdout contains:

```
2 ARMED episodes
0 confirmed major tops
1 clear false top
1 correction-risk / non-major-top
```

Together with the historical cases:

- 1998 = clear false top;
- 2012 = correction-risk, not major top;
- 2007 = genuine major-top hit;

the mechanism is now better described as:

> a credit/breadth stress detector that sometimes coincides with a major top.

It is **not** sufficiently top-specific to be promoted as a Market Top Route_A replacement.

The frozen NG1 evidence remains intact. No post-holdout parameter tuning is allowed.

Any attempt to improve top specificity must be a separately named and preregistered NG2.
