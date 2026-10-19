# Market Top Route_C NG1 — Failure Diagnostic

Status:

```
HYPOTHESIS_GENERATION_ONLY
```

The frozen NG1 decision remains:

```
Route_C_NG1 = REJECT
legacy Route_C = UNRESOLVED
```

No NG1 formula, threshold, lag, or top-location rule was changed.

## Reproduction

The reconstruction reproduces the original important states closely:

```
1998-06 reconstructed Route_C = 93.10
original screen                 = 93.05

2000-03 reconstructed Route_C = 92.33
original screen                = 92.36

2021-10 reconstructed Route_C = 95.60
original screen                = 95.59
```

The intended Big Growth portfolio is confirmed as:

```
BIG LoBM
```

## What distinguishes the target cases

### 2000-03

```
Route_C = 92.33
Valuation = 99.6
ConcentrationBreadth = 85.6
SpreadShock = 6.5
BigGrowthGap 3m change = +5.69
BigGrowth leader share, prior 6m = 0.00
252-session worst vs signal = -26.10%
252-session return = -24.06%
```

### 2021-10

```
Route_C = 95.60
Valuation = 98.5
ConcentrationBreadth = 92.8
SpreadShock = 32.7
BigGrowthGap 3m change = +33.17
BigGrowth leader share, prior 6m = 0.00
252-session worst vs signal = -22.36%
252-session return = -15.90%
```

Both are high-valuation / high-concentration states while credit-spread shock is not the dominant extreme, and both have a positive three-month change in the Big Growth gap.

## Why NG1 generated false/additional episodes

The false/additional episodes are not one homogeneous mechanism.

### Crisis-stress contamination

Examples:

```
1995-07 SpreadShock = 85.0
1998-11 SpreadShock = 96.9
2020-08 SpreadShock = 92.6
```

These concentration readings occur while broad credit stress is already extreme. That is not the intended pure bubble-exhaustion mechanism.

### High valuation without sufficiently extreme concentration

Examples:

```
1997-04 Valuation = 99.6, ConcentrationBreadth = 76.9
2017-07 Valuation = 96.4, ConcentrationBreadth = 77.9
2019-10 Valuation = 94.9, ConcentrationBreadth = 80.1
```

NG1's geometric score lets one very high component compensate for a weaker one.

### Decaying leadership-gap episodes

Examples:

```
1999-04 BigGrowthGap 3m change = -7.17
1999-06 BigGrowthGap 3m change = -17.12
2020-11 BigGrowthGap 3m change = -14.02
```

Those states are high-level concentration readings, but the specific Big Growth gap is already contracting rather than re-accelerating.

## Important negative result

Absolute Big Growth leadership is **not** required by the true target cases.

At the effective target months:

```
2000-03 Big Growth rank = 9; leader share over prior 6m = 0.00
2021-10 Big Growth rank = 3; leader share over prior 6m = 0.00
```

Therefore a rule such as "Big Growth must be the current #1 portfolio" would contradict the target mechanism and is rejected at the hypothesis-generation stage.

## NG2 hypothesis boundary

The diagnostic supports testing a newly named NG2 as a **phase-gated NG1 score**, rather than retuning NG1 weights.

Candidate gates generated from the consumed 1993–2022 cases:

- very high valuation;
- very high concentration breadth;
- credit-spread shock not already extreme;
- Big Growth gap still increasing over three months;
- existing top-location gate.

Because these gates are derived from observed post-1993 cases, those cases cannot validate NG2.

The first NG2 test must therefore be preregistered on an untouched **pre-1993** holdout before any pre-1993 Route_C_NG2 output is inspected.

Diagnostic provenance:

```
workflow = 39204999131
artifact = 12165401107
artifact sha256 = 8f8862fe76f70a61bdecaff8c4a4bcf791d5aa70af8fd8298df2ee5f8062a4d9
```
