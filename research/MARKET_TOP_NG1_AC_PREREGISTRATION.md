# Market Top Next-Generation A/C — NG1 Preregistration

Status: **PREREGISTERED / NOT VALIDATED / RESEARCH ONLY**

This work does not recover or modify legacy V2.4 Route_A or Route_C.

The legacy formulas remain unresolved.

The purpose of NG1 is to test two new, explicitly named hypotheses using different cross-sectional structure than the rejected A1/A2/C1/C2/C3 replacements.

No threshold, weight, lag, positive window, or negative-control rule may be changed after validation begins.

## Shared canonical components

### Valuation

```
Valuation = expanding_percentile(Shiller CAPE)
```

### SizeWeakness

```
SizeWeakness = expanding_percentile(-CumSMB_6m)
```

### 25-portfolio breadth

Use the Fama-French 25 Size x Book-to-Market value-weighted monthly portfolios.

For each portfolio j:

```
R6_j(t) = compounded six-month return
Market6(t) = compounded six-month Fama-French market return
```

Define:

```
PortfolioExhaustionRaw
  = 1 - count(R6_j > Market6) / 25

PortfolioExhaustionScore
  = expanding_percentile(PortfolioExhaustionRaw)
```

All monthly Fama-French inputs are shifted forward by two calendar months before they may affect a market state.

## Route_C_NG1 — concentration / leadership exhaustion

Three distinct cross-sectional conditions must be elevated.

```
LeaderGapRaw
  = max(R6_j) - median(R6_j)

LeaderGapScore
  = expanding_percentile(LeaderGapRaw)
```

The canonical Big Growth portfolio is the largest-size / lowest-BM cell:

```
BigGrowthGapRaw
  = R6_BIG_LoBM - median(R6_j)

BigGrowthGapScore
  = expanding_percentile(BigGrowthGapRaw)
```

Then:

```
ConcentrationBreadth_NG1
  = cbrt(
      PortfolioExhaustionScore
      * LeaderGapScore
      * BigGrowthGapScore
    )

Route_C_NG1
  = sqrt(
      Valuation
      * ConcentrationBreadth_NG1
    )
```

The geometric aggregation is deliberate: one extreme component cannot compensate for two weak components.

### Route_C_NG1 state gate

NG1 does **not** inherit the legacy Early Breadth direct trigger.

It may only produce an NG research ARMED state when:

```
Route_C_NG1 >= 85
AND price is within 5% of its trailing 24-calendar-month high
AND that high was formed within the preceding 3 calendar months
```

No direct trigger is authorized.

## Route_A_NG1 — credit-market deterioration

The prior A1/A2 candidates failed because accounting / survey credit stress became extreme too late.

NG1 tests whether market-sensitive credit deterioration plus financial-equity weakness can lead the credit cycle.

### Credit spread shock

Use Moody's BAA minus 10Y Treasury spread.

```
SpreadShockRaw
  = max(
      Spread(t) - Spread(t-3m),
      Spread(t) - Spread(t-6m)
    )

SpreadShockScore
  = expanding_percentile(SpreadShockRaw)
```

### Financial equity weakness

Use the Fama-French Finance industry portfolio.

```
FinanceRel6Raw
  = -(Finance6M - Market6M)

FinanceWeaknessScore
  = expanding_percentile(FinanceRel6Raw)
```

Then:

```
CreditMarketStress_NG1
  = sqrt(
      SpreadShockScore
      * FinanceWeaknessScore
    )
```

### Breadth stress

```
BreadthStress_NG1
  = sqrt(
      SizeWeakness
      * PortfolioExhaustionScore
    )
```

Finally:

```
Route_A_NG1
  = sqrt(
      CreditMarketStress_NG1
      * BreadthStress_NG1
    )
```

Route_A_NG1 uses the same 85 threshold and the same 24M top-location gate as Route_C_NG1.

## Point-in-time convention

- monthly Fama-French observations: +2 calendar-month effective lag;
- monthly Shiller CAPE observations: +1 calendar-month effective lag;
- monthly credit-spread observations: +1 calendar-month effective lag;
- percentiles: expanding, current-inclusive;
- SPY top-location gate: trailing 24 calendar months;
- no event-specific lags;
- no interpolation across missing source months.

## Frozen historical screening

The full monthly sample is evaluated from the first date with all required inputs through 2022-12.

### Route_C_NG1 primary positive episodes

The candidate must produce at least one ARMED month in:

```
2000-01 through 2000-04
2021-10 through 2022-01
```

### Route_C_NG1 negative-control windows

It must produce no ARMED month in:

```
1998-06 through 1998-10
2004-01 through 2005-12
2011-03 through 2011-07
2018-08 through 2018-12
2020-01 through 2020-04
```

### Route_A_NG1 primary positive episode

It must produce at least one ARMED month in:

```
2007-05 through 2007-11
```

### Route_A_NG1 negative controls

It must produce no ARMED month in:

```
2000-01 through 2000-04
2011-03 through 2011-07
2018-08 through 2018-12
```

and no more than two additional ARMED episodes outside the 2007 positive window over the complete screening sample.

## Decision policy

Possible decisions:

```
ACCEPT_SCREENING_CANDIDATE
REJECT
```

Acceptance is research-only and does not authorize production use.

If either candidate fails, its threshold, weights, window lengths, portfolio definition, or lags must not be tuned inside NG1.

Any changed formulation must receive a new NG version and a new preregistration before being tested.
