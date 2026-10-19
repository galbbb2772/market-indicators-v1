# Market Top Route_C NG3 — Prospective Regime-Normalized Preregistration

Status: **PREREGISTERED / PROSPECTIVE-ONLY / RESEARCH ONLY**

Legacy Route_C remains **UNRESOLVED**.

Route_C NG1 was rejected for excessive false/additional episodes.
Route_C NG2 produced no evaluable pre-1993 holdout events and exposed a cross-era valuation-regime failure.

NG3 is a new hypothesis generated from fully consumed U.S. historical evidence. It therefore **cannot claim another U.S. historical holdout**.

## Why NG3 exists

The NG2 holdout showed that an expanding-all-history CAPE percentile is not era invariant.

Post-1993 target cases such as 2000 and 2021 had:

```
Valuation ~= 98-100
```

while untouched late-1960s / early-1970s concentration states had expanding-CAPE percentiles around:

```
~72-76
```

despite high concentration breadth and low/moderate spread shock.

NG3 therefore changes only the valuation **context definition**. It asks whether CAPE is extreme relative to the recent decade rather than relative to the entire expanding history.

This is hypothesis generation from consumed evidence, not historical validation.

## Frozen concentration block

NG3 retains the NG1 cross-sectional concentration construction unchanged.

For the Fama-French 25 Size x Book-to-Market value-weighted portfolios:

```
PortfolioExhaustionRaw
  = 1 - count(R6_j > Market6) / 25

PortfolioExhaustionScore
  = expanding_percentile(PortfolioExhaustionRaw)

LeaderGapRaw
  = max(R6_j) - median(R6_j)

LeaderGapScore
  = expanding_percentile(LeaderGapRaw)

BigGrowthGapRaw
  = R6_BIG_LoBM - median(R6_j)

BigGrowthGapScore
  = expanding_percentile(BigGrowthGapRaw)

ConcentrationBreadth
  = cbrt(
      PortfolioExhaustionScore
      * LeaderGapScore
      * BigGrowthGapScore
    )
```

No concentration component is reweighted.

## New regime-normalized valuation context

Use the last 120 completed monthly CAPE observations available under the frozen PIT lag.

```
ValuationContext120
  = percentile rank of current CAPE
    within the trailing 120 completed CAPE months,
    current-inclusive
```

The 120-month window is a fixed one-decade context.

It is not an expanding percentile and must not silently fall back to one.

At least 120 usable CAPE months are required.

## NG3 score

```
Route_C_NG3_score
  = sqrt(
      ValuationContext120
      * ConcentrationBreadth
    )
```

Threshold:

```
Route_C_NG3_score >= 85
```

## Phase gates

An NG3 candidate is eligible only when all of the following are true:

```
effective_history_months >= 120

ConcentrationBreadth >= 85

SpreadShockScore <= 50

BigGrowthGapChange3M > 0
```

where:

```
SpreadShockRaw
  = max(
      delta3m(BAA - GS10),
      delta6m(BAA - GS10)
    )

SpreadShockScore
  = expanding_percentile(SpreadShockRaw)

BigGrowthGapChange3M
  = BigGrowthGapRaw(t)
    - BigGrowthGapRaw(t-3m)
```

The credit-spread gate is intended to keep this as a bubble/concentration route rather than a crisis-stress route.

The Big Growth gap-change gate requires the concentration structure to still be intensifying rather than merely remaining high after the phase has already rolled over.

## Price-location gate

ARMED additionally requires:

```
SPY close within 5% of trailing 24-calendar-month close high
AND
that high formed within the preceding 3 calendar months
```

No direct trigger is authorized.

## Point-in-time rules

Frozen:

- Fama-French monthly inputs: +2 calendar months;
- Shiller CAPE monthly input: +1 calendar month;
- BAA / GS10 monthly credit input: +1 calendar month;
- expanding percentiles are current-inclusive;
- the 120-month valuation-context window uses only CAPE observations already effective;
- no interpolation;
- no event-specific lag;
- price gate uses SPY unadjusted Close.

## Prospective boundary

Preregistration date:

```
2026-10-19
```

No effective month earlier than:

```
2026-12
```

may count as prospective NG3 evidence.

First countable source alignment:

```
effective month 2026-12
  -> FF source month 2026-10
  -> CAPE source month 2026-11
  -> credit source month 2026-11
```

Any earlier computation is labeled:

```
RETROSPECTIVE_TRAINING_DIAGNOSTIC
```

and cannot validate NG3.

## Forward source policy

Fama-French:
1. official Kenneth R. French current ZIPs;
2. verified mirror fallback with source label.

Valuation:
1. canonical Robert Shiller / Yale CAPE feed used by the Route_B shadow pipeline;
2. fail closed if the required completed month is unavailable.

Credit:
1. direct FRED BAA and GS10 monthly series;
2. approved static fallback only when source manifest / freshness checks pass.

Price:
- Yahoo Finance SPY unadjusted Close, query1/query2 fallback.

## Prospective episode protocol

A future NG3 episode opens on the first completed effective month with:

```
state = ARMED
```

Consecutive completed ARMED months belong to the same episode.

Anchor:

```
last trading day of the first ARMED effective month
```

Track:

```
63 / 126 / 252 trading sessions
```

Primary 252-session classification:

```
MAJOR_TOP
  if worst_return_from_anchor <= -15%

CLEAR_FALSE
  if worst_return_from_anchor > -7.5%
  AND forward_return_252 > 0%

CORRECTION_OR_AMBIGUOUS
  otherwise
```

## Promotion-review rule

NG3 starts as:

```
PROSPECTIVE_VALIDATION_PENDING
```

No production promotion is authorized.

A formal promotion review is forbidden until at least:

```
4 complete prospective 252-session episodes
```

exist.

The monitor itself never changes production Pressure.

## No-retune rule

From this preregistration forward, do not change inside NG3:

- the 120-month CAPE context window;
- the NG3 score formula;
- route threshold 85;
- ConcentrationBreadth gate 85;
- SpreadShockScore gate 50;
- positive sign requirement for BigGrowthGapChange3M;
- 120-month common-history guard;
- PIT lags;
- top-location gate;
- prospective start month;
- outcome definitions.

Any redesign is Route_C NG4 or later.

Production effect:

```
NONE
```
