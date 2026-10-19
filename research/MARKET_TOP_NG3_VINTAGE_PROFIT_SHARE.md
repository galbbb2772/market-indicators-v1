# Market Top NG3 — Historical Vintage Profit-Share Diagnostic

Status:

```
VINTAGE_RATIO_DIAGNOSTIC_PASS
MARGIN_REVISION_SENSITIVITY_CONFIRMED
SCORING_EFFECT = NONE
```

Research only.

## Purpose

The BEA/SCB concept audit showed that historical accounting definitions cannot be treated as automatically identical across all eras.

This follow-up asks a narrower quantitative question:

> When the historical publication has an internally consistent price-per-unit and unit-profit column, how different is the profit share published at the time from the same quarter in today's revised BEA history?

The diagnostic uses a scale-free ratio:

```
PublishedProfitShare
  = published unit profit
    / published current-dollar cost-and-profit per unit
```

This reduces pure base-year scale effects, but it does not erase changes in accounting concepts, classifications, benchmark revisions or methodology.

## 1976 Q1 — April 1976 SCB vintage

Historical publication:

```
Survey of Current Business — April 1976
Table 28
Current Dollar Cost and Profit Per Unit of Constant Dollar
Gross Domestic Product of Nonfinancial Corporate Business
```

Column mapping:

```
1974 annual
1975 annual
1975 Q1
1975 Q2
1975 Q3
1975 Q4
1976 Q1
```

For 1976 Q1 the published table gives:

```
current-dollar cost and profit per unit = 1.296
corporate unit profit with IVA + capital-consumption adjustment = 0.131
```

Therefore:

```
historical profit share
= 0.131 / 1.296
= 10.1080%
```

Frozen current revised BEA/FRED history observed on 2026-10-19 gives:

```
price per unit = 0.376
unit profit    = 0.052

current revised profit share
= 13.8298%
```

Diagnostic gap:

```
+3.7218 percentage points
+36.8199% relative to the historical published ratio
```

This is a large enough difference that the modern revised 1976 ratio cannot be treated as a harmless substitute for the contemporaneous publication.

## 1987 Q4 — March 1988 SCB vintage

Historical publication:

```
Survey of Current Business — March 1988
Table 7.18
Current-Dollar Cost and Profit Per Unit of Constant-Dollar
Gross Domestic Product of Nonfinancial Corporate Business
```

Column mapping:

```
1986 annual
1987 revised annual
1986 Q3
1986 Q4
1987 Q1
1987 Q2
1987 Q3
1987 Q4
```

For 1987 Q4 the table gives:

```
current-dollar cost and profit per unit = 1.123
corporate unit profit with IVA + CCAdj = 0.108
```

Therefore:

```
historical profit share
= 0.108 / 1.123
= 9.6171%
```

Frozen current revised BEA/FRED history observed on 2026-10-19 gives:

```
price per unit = 0.621
unit profit    = 0.062

current revised profit share
= 9.9839%
```

Diagnostic gap:

```
+0.3668 percentage points
+3.8140% relative
```

The 1987 Q4 difference is much smaller than the 1976 Q1 example, but it is not zero.

Two observations are not enough to infer a monotonic decline in revision size through time.

## Automated reproduction

GitHub Actions workflow:

```
Market Top NG3 Vintage Profit Share Diagnostic
run 39211709080
conclusion = SUCCESS
```

Frozen contract tests protect the two historical publication ratios.

Workflow artifact:

```
market-top-ng3-vintage-profit-share
artifact id = 12168056556
sha256 = 16f1ed2c20378082e9355eef6308f31c0458d437187fdfd90794092645b35000
```

The live FRED check is intentionally optional. Provider availability must not control the deterministic historical evidence contract.

## Decision

The margin-side research boundary is now stronger:

```
pre-1976 MarginConfirm = NOT COMPARABLE by default
1976+ MarginConfirm = conceptually eligible only with documented vintage data
modern revised historical margin != genuine historical PIT margin
```

The 1976 date is an eligibility boundary, not a claim that all post-1976 observations are already vintage-clean.

## Consequence for NG3

The long-history NG3 route will be built first from BLS CostPressure inputs under conservative PIT lags.

MarginConfirm may later add a separately versioned confirmation state where genuine historical-vintage evidence is available.

No margin value from today's revised history may be used to manufacture a pre-1976 top signal.

## Next gate

With source coverage, concept transition and two quantitative vintage checks documented, the next step is a numerical preregistration for **NG3-CostPressure** before any historical outcome screen is run.
