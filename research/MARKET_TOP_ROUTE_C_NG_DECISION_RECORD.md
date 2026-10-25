# Market Top Route_C — Next-Generation Decision Record

Status: **LEGACY UNRESOLVED / NG1 REJECTED / NG2 PROSPECTIVE VALIDATION PENDING**

## Legacy Route_C

```
status = UNRESOLVED
```

The exact final legacy ConcentrationBreadth formula was never recovered.

Rejected reconstruction candidates:

- C1 absolute-positive sector participation;
- C2 market-relative participation with arithmetic aggregation;
- C3 market-relative participation with geometric aggregation.

None is legacy Route_C.

## Route_C NG1

NG1 was a newly versioned FF25 concentration model:

```
ConcentrationBreadth_NG1 =
  cbrt(
    PortfolioExhaustionScore
    * LeaderGapScore
    * BigGrowthGapScore
  )

Route_C_NG1 =
  sqrt(
    Valuation
    * ConcentrationBreadth_NG1
  )
```

It detected the intended 2000 and 2021-2022 concentration regimes, but it failed the preregistered 1998 negative control and produced many additional ARMED episodes.

Decision:

```
Route_C_NG1 = REJECT
```

No NG1 retuning is allowed.

## NG1 failure diagnostic

Consumed-history decomposition showed that static concentration severity is not top-specific.

A useful phase clue emerged:

```
LeadershipHandoffShare =
  clip(
    (LeaderGapRaw - BigGrowthGapRaw)
    / max(LeaderGapRaw, eps),
    0,
    1
  )
```

Selected hypothesis-generation cases:

| Effective month | Case | Handoff share |
|---|---|---:|
| 1998-06 | false positive | 31.73% |
| 2000-03 | target top | 82.82% |
| 2017-07 | false positive | 0.00% |
| 2020-08 | false positive | 4.85% |
| 2021-10 | target top | 45.17% |

These observations are **not validation evidence**. They were already consumed by model development.

## Route_C NG2

NG2 is preregistered prospective-only.

It preserves the NG1 score:

```
Route_C_NG2_score = Route_C_NG1
```

and adds only an eligibility gate:

```
LeadershipHandoffShare >= 0.40
```

ARMED requires:

```
Route_C_NG1 >= 85
AND LeadershipHandoffShare >= 0.40
AND effective_history_months >= 120
AND unchanged 24M top-location gate
```

No direct Early-Breadth trigger is authorized.

## Prospective boundary

Preregistration date:

```
2026-10-19
```

First countable effective month:

```
2027-01
```

This intentionally skips effective 2026-12 so the required FF and Shiller monthly source periods are wholly post-preregistration.

Anything earlier is:

```
RETROSPECTIVE_HYPOTHESIS_DIAGNOSTIC
```

and cannot validate NG2.

## Current live monitor diagnostic

GitHub Actions live dry-run on 2026-10-19 produced:

```
effective month = 2026-09
FF source       = 2026-07
Shiller source  = 2026-08

PortfolioExhaustionScore = 27.3411
LeaderGapScore           = 96.1538
BigGrowthGapScore        = 10.6187
ConcentrationBreadth     = 30.3356

LeadershipHandoffShare   = 1.0000
Valuation                 = 98.9703

Route_C_NG2 = 54.7934
threshold   = 85

top-location = TRUE
state        = IDLE
```

The 100% handoff share does not matter because concentration severity is far below the frozen 85 route threshold.

This result does not count toward prospective validation.

## Governance

Current canonical Route_C research state:

```
legacy Route_C = UNRESOLVED
C1/C2/C3       = REJECTED
Route_C NG1    = REJECTED
Route_C NG2    = PROSPECTIVE VALIDATION PENDING
```

No version is production-authorized.

NG2 cannot be tuned after preregistration. Any formula/gate/lag/threshold change requires NG3 or later.

No production review is allowed before at least four clean prospective episodes have complete 252-session outcomes with no continuity evidence gaps.
