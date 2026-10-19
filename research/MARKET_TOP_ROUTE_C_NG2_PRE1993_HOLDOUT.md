# Market Top Route_C NG2 — Pre-1993 Holdout Result

Status:

```
INSUFFICIENT_HOLDOUT_EVENTS
```

Research only. Legacy Route_C remains **UNRESOLVED** and production scoring is unchanged.

## Frozen execution

The NG2 phase gates and decision rule were committed before the pre-1993 holdout was run.

Workflow:

```
run = 39205354725
job = 117906877168
conclusion = success
```

Artifact:

```
market-top-route-c-ng2-pre1993
artifact id = 12165188838
sha256 = c6d6b4eeb8640a911124672a9fbeaf3d11eb5e9380b7d89281bbf44af74ed5ee
```

The workflow completed successfully. The model decision did **not** pass.

## Proxy bridge

The preregistered pre-SPY price bridge passes:

```
overlap = 1995-02 .. 1999-12
months = 59
gate agreements = 58
agreement rate = 98.3051%
required = 95%
```

Only 1999-05 differed:

```
S&P 500 gate = true
SPY gate = false
```

Therefore the holdout failure is not explained by a broken price proxy.

## Holdout result

Preregistered positive mechanism windows:

```
1968-09 .. 1969-01 -> no ARMED month
1972-11 .. 1973-02 -> no ARMED month
```

Full holdout:

```
ARMED episodes = 0
complete episodes = 0
major-top episodes = 0
clear-false episodes = 0
```

Under the frozen decision rule:

```
decision = INSUFFICIENT_HOLDOUT_EVENTS
```

This is not converted into a pass merely because no false positives were produced.

## Why NG2 did not generalize

The dominant failure is **valuation-regime dependence**.

NG2 inherited an absolute phase gate derived from the consumed post-1993 cases:

```
Valuation >= 98
```

But the pre-1993 concentration episodes do not occupy the same expanding-CAPE-percentile regime.

Representative untouched states:

```
1969-10
Route_C_NG1 = 82.3994
Valuation = 75.5869
ConcentrationBreadth = 89.8261
SpreadShock = 3.1250
BigGrowthGapChange3M = +15.6296
```

```
1969-11
Route_C_NG1 = 82.3236
Valuation = 75.9850
ConcentrationBreadth = 89.1911
SpreadShock = 43.5233
BigGrowthGapChange3M = +3.5977
```

```
1972-09
Route_C_NG1 = 79.6253
Valuation = 72.5455
ConcentrationBreadth = 87.3960
SpreadShock = 15.8590
BigGrowthGapChange3M = +15.1909
Top-location = true
```

```
1972-12
Route_C_NG1 = 81.9165
Valuation = 75.9746
ConcentrationBreadth = 88.3231
SpreadShock = 4.7826
BigGrowthGapChange3M = -2.9485
Top-location = true
```

The concentration and credit-phase structure can resemble the intended mechanism while absolute expanding-percentile CAPE does not.

A second regime pattern is visible in the 1964–65 states:

```
Valuation ~= 98
ConcentrationBreadth ~= 18–43
Route_C ~= 42–65
```

So high valuation by itself also does not solve the problem.

## Scientific conclusion

The supported conclusion is:

> The post-1993 Route_C NG2 phase definition is not invariant across U.S. market eras.

The unsupported conclusion is:

> Lower the valuation gate from 98 to ~75 and rerun until 1969/1973 pass.

That would be direct post-hoc fitting to the untouched holdout.

## Evidence boundary

The pre-1993 U.S. sample has now been inspected and is no longer untouched for any successor derived from this result.

Therefore any successor that changes the valuation treatment must be newly versioned and cannot claim historical U.S. validation from the same pre-1993 sample.

A successor may use the full U.S. history for **hypothesis generation**, but validation must come from:

- prospective observations after preregistration; or
- a genuinely independent market/data domain with separately justified semantics.

## Governance

Frozen from this result:

- Route_C NG2 is not promoted;
- legacy Route_C remains UNRESOLVED;
- production Pressure remains partial coverage;
- no NG2 threshold/gate retuning is allowed;
- the pre-1993 U.S. sample is consumed;
- any structural change must be Route_C NG3 or later.

Production effect:

```
NONE
```
