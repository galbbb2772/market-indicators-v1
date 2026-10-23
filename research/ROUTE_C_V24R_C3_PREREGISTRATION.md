# Route_C_v2.4R-C3 Preregistration

Status: **PREREGISTERED / NOT YET VALIDATED / RESEARCH ONLY**

This candidate is not presented as a recovery of original V2.4 Route_C.

## Motivation

Two prior replacement candidates failed:

- C1 used absolute-positive 12-industry participation and generated multiple false signals.
- C2 corrected participation to "industry 6M return > market 6M return" but remained too permissive and failed to reproduce the accepted 2021-10 Early Breadth event.

The retained historical clue for the 2000 concentration episode requires two simultaneous properties:

1. very narrow 12-industry participation relative to the market;
2. an extreme leader-versus-median six-month return gap.

An arithmetic mean allows one component to compensate for a weak other component. C3 instead uses a geometric mean so both components must be elevated.

## Frozen candidate formula

For month t:

```
Industry6M_j(t) = compounded 6M return of Fama-French industry j
Market6M(t) = compounded 6M Fama-French market return

RelativeParticipationRaw(t)
    = 1 - count(Industry6M_j(t) > Market6M(t)) / 12

RelativeParticipationScore(t)
    = expanding_percentile(RelativeParticipationRaw(t))

LeaderGapRaw(t)
    = max_j(Industry6M_j(t)) - median_j(Industry6M_j(t))

LeaderGapScore(t)
    = expanding_percentile(LeaderGapRaw(t))

ConcentrationBreadth_C3(t)
    = sqrt(
        RelativeParticipationScore(t)
        * LeaderGapScore(t)
      )

Valuation(t)
    = expanding_percentile(Shiller CAPE_t)

Route_C_C3(t)
    = sqrt(
        Valuation(t)
        * ConcentrationBreadth_C3(t)
      )
```

Breadth used by the existing Early Breadth rule remains:

```
Breadth_R(t)
    = 0.50 * SizeWeakness(t)
    + 0.50 * RelativeParticipationScore(t)
```

with:

```
SizeWeakness = expanding_percentile(-CumSMB_6m)
```

## Point-in-time semantics

For an effective market month M:

- monthly CAPE / SMB / industry observations are shifted forward by **two calendar months**;
- this conservative lag is fixed before validation;
- no event-specific lag is permitted;
- all percentiles are expanding/current-inclusive;
- no weights or thresholds may be changed after seeing C3 results.

## State-machine interaction

Existing V2.4 rules are unchanged.

ARMED via Route_C requires:

```
Route_C_C3 >= 85
AND price within 5% of the 24M high
AND the relevant 24M high formed within the prior 3 months
```

Early Breadth remains the accepted direct-trigger rule:

```
Pressure >= 85
AND Route_C_C3 >= 85
AND delta Breadth_R_3m >= 10
```

No near-high gate is added to Early Breadth.

## Validation decision rule

C3 is considered useful only if it materially improves historical separation without post-hoc tuning.

At minimum:

- 2000 concentration episode should remain detectable;
- accepted 2011 NO and 2018 NO should not become obvious direct-trigger false positives;
- the 2021-10 / 2022 episode timing must be inspected explicitly;
- all unexpected episodes must be reported, not hidden.

Failure does not authorize threshold or weight tuning. A failed C3 remains a rejected research candidate.
