# Market Top Route_A NG2 — Lead/Lag Preregistration

Status: **PREREGISTERED / NOT YET VALIDATED / RESEARCH ONLY**

NG1 is closed and will not be retuned.

NG2 tests one new structural hypothesis generated from the frozen NG1-A component diagnostic:

> a top-specific credit regime may occur when financial equities have already deteriorated more severely than broad credit-spread shock, i.e. financial weakness leads credit-spread extremity.

The five cases used to generate this hypothesis (1998, 2007, 2012, 2025-07, 2025-09) are **training / hypothesis-generation evidence only**. They cannot validate NG2.

## Frozen NG1 inputs

NG2 inherits the NG1 component definitions without modification:

```
SpreadShockScore
  = expanding_pct(
      max(delta3m(BAA-GS10), delta6m(BAA-GS10))
    )

FinanceWeaknessScore
  = expanding_pct(-(Finance6M - Market6M))

SizeWeakness
  = expanding_pct(-CumSMB_6m)

PortfolioExhaustionScore
  = expanding_pct(
      1 - count(FF25 portfolio6m > Market6M) / 25
    )
```

NG1 route:

```
Route_A_NG1
  = fourth_root(
      SpreadShockScore
      * FinanceWeaknessScore
      * SizeWeakness
      * PortfolioExhaustionScore
    )
```

## New NG2 component

No hand-selected lead-gap cutoff is introduced.

```
FinancialLeadGapRaw
  = FinanceWeaknessScore - SpreadShockScore

FinancialLeadGapScore
  = expanding_pct(FinancialLeadGapRaw)
```

NG2 route:

```
Route_A_NG2
  = sqrt(
      Route_A_NG1
      * FinancialLeadGapScore
    )
```

This geometric aggregation requires both:

- broad NG1 credit/breadth stress;
- unusually strong financial-equity weakness relative to spread-shock extremity.

## Frozen state gate

Threshold remains unchanged:

```
Route_A_NG2 >= 85
```

and the top-location gate remains unchanged:

```
price within 5% of trailing 24-calendar-month close high
AND that high formed within prior 3 calendar months
```

No direct trigger is authorized.

## Point-in-time rules

Unchanged from NG1:

- Fama-French monthly inputs: +2 calendar months;
- credit-spread monthly inputs: +1 calendar month;
- expanding percentiles: current-inclusive;
- no interpolation;
- no event-specific lags.

## First validation set

The first validation set is the **pre-1993 temporal holdout**.

Reason:

- it was not used in generating the lead-gap hypothesis;
- credit BAA/GS10 common history begins in the 1950s;
- Fama-French factor/portfolio history extends earlier;
- S&P 500 daily history can provide the unchanged 24M top-location gate and forward outcomes.

The holdout ends at:

```
1992-12
```

No 1993+ observation may affect the NG2 percentile or outcome evaluation for this first validation.

## Outcome protocol

For every NG2 ARMED episode:

```
anchor = last trading day of first ARMED month
horizon = next 252 trading sessions
price = S&P 500 daily close
```

Metrics:

- 252-session forward return;
- worst return from anchor inside 252 sessions;
- max peak-to-trough drawdown.

Frozen classification:

```
MAJOR_TOP
  if worst_return_from_anchor_252 <= -15%

CLEAR_FALSE
  if worst_return_from_anchor_252 > -7.5%
  AND forward_return_252 > 0%

CORRECTION_OR_AMBIGUOUS
  otherwise
```

A later drawdown from a much higher price does not rescue a signal whose price never fell materially below the original anchor.

## Decision rule

NG2 becomes only a **research screening candidate** if all conditions pass:

```
complete_evaluable_episodes >= 2

major_top_share >= 50%

clear_false_share <= 25%
```

Otherwise:

```
REJECT_NG2_TOP_ROUTE
```

Even a pass does not authorize production use or replacement of legacy Route_A.

## No-retune rule

After the pre-1993 holdout is inspected, none of the following may be changed inside NG2:

- formula;
- threshold 85;
- lead-gap construction;
- percentile mapping;
- lags;
- top-location gate;
- outcome classifications;
- acceptance thresholds.

Any redesign must be NG3 or later.
