# Market Top NG1-A Component Diagnostic

Status: **HYPOTHESIS GENERATION ONLY / NOT NG2 VALIDATION**

NG1-A is closed as a top route. This diagnostic asks one narrow question:

> Why did the same frozen credit/breadth stress construct fire at 2007, but also at 1998, 2012 and 2025?

No NG1 formula is changed.

## Frozen component comparison

| Episode | Outcome | SpreadShock | FinanceWeakness | SizeWeakness | PortfolioExhaustion | Finance − Spread |
|---|---|---:|---:|---:|---:|---:|
| 1998-11 | clear false top | 96.86 | 91.65 | 98.38 | 98.49 | **-5.21** |
| 2007-11 | major top | 75.81 | 92.58 | 87.63 | 92.27 | **+16.77** |
| 2012-02 | correction, not major top | 85.71 | 89.91 | 82.27 | 87.46 | **+4.20** |
| 2025-07 | clear false top | 79.56 | 73.27 | 96.79 | 94.33 | **-6.29** |
| 2025-09 | correction, not major top | 73.93 | 81.84 | 89.78 | 97.89 | **+7.91** |

## Important negative result: no monotonic reweighting

1998 is the decisive case.

Its four NG1 component scores are all extremely high and, component by component, are at least as dangerous-looking as 2007.

Therefore a new formula of the form:

```
positive_weight_1 * SpreadShock
+ positive_weight_2 * FinanceWeakness
+ positive_weight_3 * SizeWeakness
+ positive_weight_4 * PortfolioExhaustion
```

or another monotonic positive geometric aggregation cannot solve the top-specificity problem in a principled way.

It would continue to prefer the 1998 false positive.

So:

```
NG2 != tuned NG1 weights
```

## Rejected diagnostic: current spread widening

A first mechanistic idea was that a true top might require credit spreads to still be actively worsening.

The raw credit path rejects that idea.

Credit source months:

```
1998-10: 1m spread change ~= +0.37, 3m ~= +0.96
2007-10: 1m spread change ~= -0.12, 3m ~= +0.30
2012-01: 1m spread change ~= -0.01, 3m ~= +0.04
2025-06: 1m spread change ~= -0.10, 3m ~= +0.12
2025-08: 1m spread change ~= +0.03, 3m ~= -0.13
```

1998 was actually worsening much more strongly than 2007.

So a simple "spread still widening" gate would make the false positive worse.

## New mechanism worth testing

The one visible structural distinction is **lead-lag**, not absolute stress:

```
FinancialLeadGap
  = FinanceWeaknessScore
  - SpreadShockScore
```

Known hypothesis-generation cases:

```
1998-11  -5.21
2007-11 +16.77
2012-02  +4.20
2025-07  -6.29
2025-09  +7.91
```

Economic interpretation:

> A pre-top credit regime may be more specific when financial equities are already deteriorating severely while broad credit spreads have not yet reached the same percentile extremity.

This is different from a crisis/recovery state in which credit spreads themselves are already the dominant extreme.

## Critical evidence rule

These five cases were inspected to generate the hypothesis.

Therefore they are **training / hypothesis-generation evidence** and cannot validate NG2.

Any NG2 formulation derived from this pattern must be written down before another outcome set is inspected.

The first proposed temporal holdout is the pre-1993 period, which was not used to derive this lead-gap hypothesis.
