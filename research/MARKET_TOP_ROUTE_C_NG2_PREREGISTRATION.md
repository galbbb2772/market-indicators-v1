# Market Top Route_C NG2 — Prospective Preregistration

Status: **PREREGISTERED / PROSPECTIVE ONLY / RESEARCH ONLY**

Route_C_NG2 is not legacy Route_C and does not reopen rejected Route_C_NG1.

## Hypothesis

NG1 showed that static concentration can remain extreme during non-top regimes.

NG2 tests a phase hypothesis:

> A concentration regime may become more top-relevant when leadership starts handing off away from the canonical BIG LoBM portfolio while concentration severity is still extreme.

The hypothesis was generated from already consumed history. Therefore NG2 receives **no historical validation credit**.

## Frozen score

NG2 does not retune the NG1 concentration score:

```
Route_C_NG2_score = Route_C_NG1
```

NG1 definitions remain unchanged:

```
PortfolioExhaustionRaw =
  1 - count(Portfolio6M > Market6M) / 25

LeaderGapRaw =
  max(Portfolio6M) - median(Portfolio6M)

BigGrowthGapRaw =
  BIG_LoBM_6M - median(Portfolio6M)

ConcentrationBreadth_NG1 =
  cbrt(
    PortfolioExhaustionScore
    * LeaderGapScore
    * BigGrowthGapScore
  )

Route_C_NG1 =
  sqrt(Valuation * ConcentrationBreadth_NG1)
```

## New phase gate

```
LeadershipHandoffShare =
  clip(
    (LeaderGapRaw - BigGrowthGapRaw)
    / max(LeaderGapRaw, eps),
    0,
    1
  )
```

Frozen threshold:

```
LeadershipHandoffShare >= 0.40
```

This is an eligibility gate, not another severity multiplier.

## NG2 ARMED rule

```
Route_C_NG1 >= 85
AND LeadershipHandoffShare >= 0.40
AND effective_history_months >= 120
AND price within 5% of trailing 24M high
AND that high formed within the prior 3 calendar months
```

No direct Early-Breadth trigger is authorized.

## PIT rules

Frozen:

```
Fama-French monthly inputs = +2 calendar-month effective lag
Shiller CAPE              = +1 calendar-month effective lag
percentiles               = expanding/current-inclusive
missing months            = no interpolation
```

## Prospective boundary

Preregistration date:

```
2026-10-19
```

To avoid the source-month straddle ambiguity entirely, NG2 does **not** count effective 2026-12.

First countable effective month:

```
2027-01
```

which requires:

```
Fama-French source month >= 2026-11
Shiller CAPE source month >= 2026-12
```

Both source periods are wholly post-preregistration.

Anything before 2027-01 is:

```
RETROSPECTIVE_HYPOTHESIS_DIAGNOSTIC
```

and cannot validate NG2.

## Governance

No post-preregistration change to:

- the 40% handoff gate;
- Route_C_NG1 score formula;
- threshold 85;
- 120-month warmup;
- PIT lags;
- top-location gate;
- episode/outcome protocol;

is allowed inside NG2.

Any change requires Route_C_NG3 or later.

Production review is prohibited until at least four clean prospective episodes have complete 252-session outcomes with no continuity evidence gaps.
