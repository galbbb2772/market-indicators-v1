# Route_C NG1 — Component Failure Diagnostic

Status: **HYPOTHESIS GENERATION ONLY**

This diagnostic explains why the rejected Route_C_NG1 produced false positives. It does not reopen NG1 and does not validate a new route.

## Frozen NG1 context

Route_C_NG1 used:

```
ConcentrationBreadth_NG1 =
  cbrt(
    PortfolioExhaustionScore
    * LeaderGapScore
    * BigGrowthGapScore
  )

Route_C_NG1 =
  sqrt(Valuation * ConcentrationBreadth_NG1)
```

NG1 is already rejected. No NG1 parameter is changed here.

## Case decomposition

| Effective month | Classification | Route_C_NG1 | Leader 6M | BIG LoBM 6M | LeadershipHandoffShare |
|---|---|---:|---:|---:|---:|
| 1998-06 | false positive | 93.05 | 31.10% | 25.92% | 31.73% |
| 2000-03 | target top | 92.36 | 58.95% | 11.78% | 82.82% |
| 2017-07 | false positive | 86.34 | 16.63% | 16.63% | 0.00% |
| 2020-08 | false positive | 94.11 | 12.70% | 11.28% | 4.85% |
| 2021-10 | target top | 95.59 | 29.90% | 20.07% | 45.17% |

Derived diagnostic:

```
LeadershipHandoffShare =
  clip(
    (LeaderGapRaw - BigGrowthGapRaw)
    / max(LeaderGapRaw, eps),
    0,
    1
  )
```

Interpretation:

- 0 means BIG LoBM itself is the cross-sectional leader;
- a high value means another portfolio has taken a material part of the leadership premium while the market remains concentrated.

## What the consumed history suggests

The false-positive cases studied here are dominated by BIG LoBM itself or keep it very close to the leader.

The two target episodes have a larger leadership handoff:

- 2000-03: 82.82%
- 2021-10: 45.17%

That is economically different from merely raising concentration severity again.

## Evidence restriction

These cases were already consumed by NG1 development and failure analysis.

Therefore this diagnostic may generate a next hypothesis, but it may **not** be used as validation evidence for that hypothesis.

Any Route_C_NG2 built from this finding must be prospective-only. No historical hit rate, precision or false-positive rate may be claimed for NG2 from these cases.
