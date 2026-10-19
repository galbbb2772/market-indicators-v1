# Market Top NG2-A — Financial-Lead Credit Route Preregistration

Status:

```
PREREGISTERED / NOT VALIDATED / RESEARCH ONLY
```

This is a newly named next-generation hypothesis. It does **not** recover, replace, or reinterpret the unresolved legacy V2.4 Route_A.

NG1 is closed and will not be retuned.

## Why NG2 exists

The frozen NG1-A case diagnostic showed that the absolute stress components cannot be made top-specific by simple positive reweighting.

In particular, the 1998 false positive had component stress at least as extreme as 2007.

The only structural distinction retained for a new hypothesis is lead-lag:

```
FinancialLeadGap
  = FinanceWeaknessScore - SpreadShockScore
```

The economic hypothesis is:

> A major credit-cycle top may be more specific when financial equities have already deteriorated sharply while broad credit spreads have not yet reached the same percentile extremity.

The cases used to generate that hypothesis — 1998, 2007, 2012, 2025-07 and 2025-09 — are training / hypothesis-generation evidence and are not allowed to validate NG2.

## Frozen source components

Reuse the NG1 source definitions without modification.

### SpreadShockScore

Monthly BAA minus 10Y Treasury spread:

```
SpreadShockRaw
  = max(
      Spread(t) - Spread(t-3m),
      Spread(t) - Spread(t-6m)
    )

SpreadShockScore
  = expanding_percentile(SpreadShockRaw)
```

### FinanceWeaknessScore

Fama-French Finance industry portfolio:

```
FinanceRel6Raw
  = -(Finance6M - Market6M)

FinanceWeaknessScore
  = expanding_percentile(FinanceRel6Raw)
```

### Breadth components

```
SizeWeakness
  = expanding_percentile(-CumSMB_6m)

PortfolioExhaustionScore
  = expanding_percentile(
      1 - count(R6_j > Market6) / 25
    )
```

using the Fama-French 25 Size x Book-to-Market value-weighted portfolios.

## New NG2 lead-lag component

At each effective month:

```
FinancialLeadGapRaw
  = FinanceWeaknessScore - SpreadShockScore

FinancialLeadScore
  = expanding_percentile(FinancialLeadGapRaw)
```

This uses the already-normalized stress scores so that the gap is dimensionless.

No fixed lead-gap cutoff is added.

## Frozen NG2 formula

```
CreditLeadStress_NG2
  = cbrt(
      SpreadShockScore
      * FinanceWeaknessScore
      * FinancialLeadScore
    )

BreadthStress_NG2
  = sqrt(
      SizeWeakness
      * PortfolioExhaustionScore
    )

Route_A_NG2
  = sqrt(
      CreditLeadStress_NG2
      * BreadthStress_NG2
    )
```

The route threshold remains:

```
Route_A_NG2 >= 85
```

No NG2-specific threshold is introduced.

## Top-location gate

An NG2 research ARMED month additionally requires:

```
price within 5% of trailing 24-calendar-month high
AND
that high formed within the preceding 3 calendar months
```

No direct trigger is authorized.

NG2 is only a candidate pressure route.

## Point-in-time convention

Frozen conventions:

- Fama-French monthly inputs: +2 calendar-month effective lag;
- monthly credit-spread inputs: +1 calendar-month effective lag;
- percentiles: expanding, current-inclusive;
- no event-specific lags;
- no interpolation across missing source months;
- no use of future revisions to set thresholds or weights.

For the lead-gap calculation at effective month t:

- FinanceWeaknessScore is the score available from the t-2 Fama-French source month;
- SpreadShockScore is the score available from the t-1 credit source month;
- FinancialLeadScore is computed only from lead-gap observations available through t.

## Untouched validation set

The first NG2 validation is the pre-1993 temporal holdout.

Evaluation period:

```
1963-01 through 1992-12
```

or the first later month with all frozen inputs available.

Why 1963:

- all required source histories are allowed to begin earlier;
- the first 120 months of common source history are treated as percentile warm-up;
- no ARMED outcome before the evaluation start is scored.

The post-1993 cases used to generate the hypothesis are excluded from this first validation.

## Pre-SPY price bridge

Because SPY does not cover the full holdout, the price gate and outcome path use the S&P 500 price index (`^GSPC`) unadjusted close for the pre-1993 validation.

Before interpreting holdout results, the implementation must document an overlap sanity check showing that the index proxy does not materially change the frozen top-location rule during the available SPY overlap.

The proxy bridge may not change the threshold, 24-month window, 5% distance, or 3-month high-age rule.

## Episode construction

Compute every monthly NG2 ARMED state in the holdout.

Consecutive ARMED months are one episode.

Episode anchor:

```
first ARMED month
-> last trading-day close of that month
```

No episode may be removed because its later outcome is inconvenient.

## Outcome classification

For each episode, inspect the next 252 trading sessions from the anchor close.

Define:

```
WorstVsSignal
  = min(future_close / signal_close - 1)
```

Classification:

```
MAJOR_TOP_HIT
  if WorstVsSignal <= -20%

CORRECTION_RISK_NOT_MAJOR_TOP
  if -20% < WorstVsSignal <= -10%

CLEAR_TOP_FALSE_POSITIVE
  if WorstVsSignal > -10%
```

Forward return and maximum peak-to-trough drawdown are reported as diagnostics, but they do not override the classification above.

## Frozen first-gate decision rule

The pre-1993 holdout result is:

```
ACCEPT_HOLDOUT_CANDIDATE
```

only if all are true:

1. at least 2 independent ARMED episodes occur;
2. at least 1 episode is a MAJOR_TOP_HIT;
3. there are 0 CLEAR_TOP_FALSE_POSITIVE episodes;
4. MAJOR_TOP_HIT episodes are at least 50% of all evaluated episodes.

Otherwise:

```
REJECT
```

If fewer than 2 complete episodes exist, the result is:

```
INSUFFICIENT_HOLDOUT_EVENTS
```

not a pass.

## Governance

After the first holdout is run:

- do not retune NG2;
- do not change the 85 threshold;
- do not add a hand-picked lead-gap cutoff;
- do not change lags;
- do not delete failed episodes;
- do not reinterpret correction-risk episodes as major-top hits;
- do not relabel NG2 as legacy Route_A.

If NG2 fails, any structural change must be named NG3 or later and preregistered before testing.

If NG2 passes, it remains research-only. A separate post-preregistration prospective / untouched validation gate is still required before any promotion review.

## Production boundary

Until a later promotion decision explicitly says otherwise:

```
legacy Route_A = UNRESOLVED
Route_A_NG2 = RESEARCH_ONLY
Pressure must not include Route_A_NG2
production scoring effect = NONE
```
