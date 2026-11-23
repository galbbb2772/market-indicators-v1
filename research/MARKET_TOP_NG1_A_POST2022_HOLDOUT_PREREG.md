# Route_A_NG1 — Post-2022 Temporal Holdout Preregistration

Status: **PREREGISTERED / NOT YET EVALUATED / RESEARCH ONLY**

This holdout is evaluated only after the NG1 formula, threshold, lags, first historical screen, independent 2007 source replay, and 1998/2012 case studies have been frozen.

It is not claimed to be a pure prospective experiment because NG1 was designed in 2026. It is a **retrospective temporal holdout** that was not used in the first 1993-2022 screening.

## Frozen candidate

No NG1 input or threshold changes are allowed.

```
SpreadShockRaw
  = max(delta3m(BAA-GS10), delta6m(BAA-GS10))

SpreadShockScore
  = expanding_percentile(SpreadShockRaw)

FinanceWeaknessScore
  = expanding_percentile(-(Finance6M - Market6M))

CreditMarketStress
  = sqrt(SpreadShockScore * FinanceWeaknessScore)

PortfolioExhaustionScore
  = expanding_percentile(
      1 - count(FF25_portfolio6m > Market6m) / 25
    )

SizeWeakness
  = expanding_percentile(-CumSMB_6m)

BreadthStress
  = sqrt(SizeWeakness * PortfolioExhaustionScore)

Route_A_NG1
  = sqrt(CreditMarketStress * BreadthStress)
```

ARMED:

```
Route_A_NG1 >= 85
AND SPY is within 5% of its trailing 24-calendar-month close high
AND that high was formed within the preceding 3 calendar months
```

PIT lags remain:

```
Fama-French monthly inputs +2 calendar months
BAA/GS10 monthly input +1 calendar month
```

## Holdout window

Start:

```
2023-01
```

End:

> the latest effective month for which all required frozen inputs are present in the selected source set.

The end date must be reported explicitly and may not be filled by interpolation.

## Reporting rules

Every ARMED month and every contiguous ARMED episode must be reported.

No episode may be hidden because its subsequent outcome is inconvenient.

For each episode, anchor on the last trading day of the first ARMED month.

If at least 252 subsequent SPY sessions exist in the price source, report:

- 63-session forward return;
- 63-session worst return from anchor;
- 63-session maximum peak-to-trough drawdown;
- the same three metrics for 126 sessions;
- the same three metrics for 252 sessions.

If fewer than 252 subsequent sessions exist, mark the episode:

```
OPEN_OUTCOME
```

and do not extrapolate.

## Decision policy

The holdout does not have a tuned pass/fail threshold.

Instead it produces one of:

```
NO_ARMED_EPISODES
ARMED_EPISODES_WITH_COMPLETE_OUTCOMES
ARMED_EPISODES_WITH_OPEN_OUTCOMES
MIXED_COMPLETE_AND_OPEN
```

This classification is descriptive.

The holdout may change the research confidence assigned to NG1-A, but it may not change NG1-A parameters.

Any redesign motivated by the holdout must:

1. be named NG2 or later;
2. be preregistered before testing;
3. leave NG1 evidence intact.
