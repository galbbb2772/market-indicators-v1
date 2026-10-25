# Market Top Route_A NG2 — Failure Diagnostic

Status: **HYPOTHESIS GENERATION ONLY**

NG2 remains:

```
REJECT_NG2_TOP_ROUTE
```

No result in this diagnostic can reopen NG2.

## Why NG2 produced zero ARMED episodes

Pre-1993:

```
monthly states                     = 470
Route_A_NG2 >= 85, ignoring price  = 1
top-location gate pass months      = 191
NG2 ARMED months                   = 0
NG1 ARMED months, same price gate  = 2
```

The two conditions simply never overlap.

The maximum NG2 value while the top-location gate passes is:

```
1964-03
Route_A_NG2 = 80.4535
```

well below 85.

## Early-sample percentile artifact

The only month where NG2 exceeds 85 without the price gate is:

```
1953-11
Route_A_NG2 = 91.2505
FinancialLeadGapRaw = -33.8509
FinancialLeadGapScore = 100
```

The paradox is mechanical: this is the first effective observation of the derived expanding percentile, so the first value receives percentile 100 even though the raw gap is negative.

This is not valid top evidence.

Any future derived-percentile route needs an explicit preregistered warmup rule.

## What NG2 did to the two pre-1993 NG1 signals

### 1955-11

```
Route_A_NG1 = 88.93
LeadGapScore = 44.00
Route_A_NG2 = 62.55
```

252-session outcome:

- forward return: -2.48%
- worst below anchor: -5.27%
- max peak-to-trough DD: -10.60%

Classification:

```
CORRECTION_OR_AMBIGUOUS
```

### 1991-02

```
Route_A_NG1 = 92.47
LeadGapScore = 47.10
Route_A_NG2 = 65.99
```

252-session outcome:

- forward return: +12.75%
- worst below anchor: -0.13%
- max peak-to-trough DD: -5.60%

Classification:

```
CLEAR_FALSE
```

So the lead-lag idea did suppress two non-major-top NG1 signals. That part is useful.

## But multiplication destroys the desired 2007 signal

Using the same NG2 mapping on already-consumed hypothesis-generation cases:

| Episode | Outcome | NG1 | LeadGapRaw | LeadGapScore | NG2 |
|---|---|---:|---:|---:|---:|
| 1998-11 | clear false | 96.30 | -5.21 | 48.80 | 68.55 |
| 2007-11 | major top | 86.79 | +16.77 | **65.64** | **75.48** |
| 2012-02 | correction | 86.30 | +4.20 | 54.29 | 68.44 |
| 2025-07 | clear false | 85.45 | -6.29 | 43.79 | 61.17 |
| 2025-09 | correction | 85.40 | +8.00 | 58.52 | 70.69 |

The lead-gap variable contains useful ordering information: 2007 is the strongest of these mature-sample cases.

But:

```
sqrt(Route_A_NG1 * LeadGapScore)
```

is the wrong use of that information. It turns a phase distinction into a severity penalty and pushes even 2007 far below 85.

## Research conclusion

Supported hypothesis for a future version:

> financial-equity lead relative to spread stress may be useful as an eligibility / phase condition.

Unsupported conclusion:

> NG2 should be retuned until 2007 passes.

NG2 stays rejected.

All U.S. historical periods in this line, 1953-2026, have now been consumed by screening, holdout, or hypothesis generation. Therefore any NG3 designed from this evidence cannot claim a new untouched historical validation.

If NG3 is built, its top-specificity evidence must be **prospective after preregistration**.
