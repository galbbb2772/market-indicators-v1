# Market Top Route_A NG2 — Pre-1993 Holdout

Status:

```
REJECT_NG2_TOP_ROUTE
```

NG2 was preregistered before the pre-1993 outcome set was inspected.

No formula, threshold, lag, top-location rule, outcome classification, or acceptance threshold was changed after the holdout was opened.

## Frozen hypothesis

```
FinancialLeadGapRaw
  = FinanceWeaknessScore - SpreadShockScore

FinancialLeadGapScore
  = expanding_percentile(FinancialLeadGapRaw)

Route_A_NG2
  = sqrt(
      Route_A_NG1
      * FinancialLeadGapScore
    )
```

Threshold:

```
85
```

with the unchanged 24-calendar-month top-location gate.

## Untouched validation sample

```
first effective month = 1953-11
last effective month  = 1992-12
monthly states        = 470
```

Data path:

- official Kenneth R. French FF25 / FF12 / FF3 histories;
- pinned immutable independent BAA / GS10 snapshots;
- Yahoo Finance `^GSPC` unadjusted daily close for the price gate and outcomes.

No 1993+ state was allowed into the first validation set.

## Preregistered decision rule

A research screening pass required all of:

```
complete evaluable episodes >= 2
major-top share >= 50%
clear-false share <= 25%
```

## Result

The frozen model produced:

```
NG2 ARMED episodes = 0
complete evaluable episodes = 0
```

Therefore it fails the first preregistered requirement immediately.

Decision:

```
REJECT_NG2_TOP_ROUTE
```

This is a model rejection, not a workflow failure. The GitHub Actions job passed because it successfully reproduced the frozen calculation and the preregistered reject decision.

## Governance

NG2 must not be rescued by:

- lowering 85;
- changing the geometric aggregation;
- adding an event-specific gate;
- changing the lead-gap percentile;
- changing point-in-time lags;
- reclassifying the holdout.

The pre-1993 holdout is now consumed evidence and may be used only for hypothesis generation.

Any redesigned route must be:

```
NG3 or later
```

with a new preregistration before a new validation set is inspected.
