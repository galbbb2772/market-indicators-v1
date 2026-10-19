# Market Top NG3 — Architecture Decision After Source Audit

Status:

```
ARCHITECTURE_FROZEN
NUMERICAL_FORMULA_NOT_FROZEN
HISTORICAL_BACKTEST_NOT_STARTED
```

## Decision

NG3 will not force one accounting series to cover every historical inflation regime.

The research branch is split into two logically separate blocks.

### Block 1 — NG3-CostPressure

Purpose:

Detect a persistent inflation / producer-cost configuration using source families whose historical coverage and definitions are sufficiently stable for long-history research.

Eligible source families:

```
CPI-U all items NSA        CUUR0000SA0
Finished-goods PPI NSA     WPUFD49207
Processed intermediate PPI WPUID61
```

This block is the only NG3 component currently eligible for a 1960s/1970s long-history test.

No exact score, window, weight or threshold is frozen by this architecture record.

### Block 2 — NG3-MarginConfirm

Purpose:

Measure whether corporate unit-profit conditions confirm cost pressure.

Preferred economic source:

```
BEA/SCB nonfinancial corporate cost-and-profit-per-unit tables
```

The historical publication concept changes across the 1970s.

Therefore MarginConfirm:

- may not silently backfill today's revised A463RD into older dates;
- may not be a mandatory gate for an era where the contemporaneous concept is not comparable;
- may only enter a historical state after its vintage, publication lag and concept are documented.

## Why the split is frozen now

This decision is based on **source compatibility**, before any NG3 historical score or hit rate has been calculated.

It is not legal later to claim that MarginConfirm was made optional because a particular historical top was missed.

The reason is already fixed:

```
historical accounting concept continuity is not yet established
```

## Missing-value semantics

A missing or non-comparable MarginConfirm value means:

```
MARGIN_NOT_COMPARABLE
```

It does not mean:

```
margin stress = 0
```

and it does not mean:

```
margin confirmation = pass
```

The model must preserve that distinction in all future datasets and dashboards.

## Future state-machine boundary

Before a numerical preregistration, NG3 may eventually define separate research states such as:

```
COST_PRESSURE_ONLY
COST_PRESSURE_WITH_MARGIN_CONFIRMATION
```

but neither state name is yet authorized as a market-top trigger.

A future preregistration must specify:

- transformations;
- windows;
- percentiles or normalization;
- release lags;
- thresholds;
- top-location rule;
- episode construction;
- development and untouched validation windows;
- how MARGIN_NOT_COMPARABLE is handled.

Those choices must be committed before any outcome screen.

## Baseline requirement

Any later NG3 validation must compare the candidate against at least:

1. inflation-only baseline;
2. producer-consumer cost-gap baseline;
3. top-location gate alone.

A more complex NG3 formula is not considered useful merely because it produces historical hits; it must improve specificity, timing or false-alarm control relative to these frozen baseline families.

## Promotion boundary

At this stage:

```
NG3 production inclusion = NOT AUTHORIZED
NG3 Pressure inclusion = NOT AUTHORIZED
NG3 historical validation claim = NOT AUTHORIZED
```

The next gate remains numerical source reconstruction and then a separate preregistration.
