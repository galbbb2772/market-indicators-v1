# Market Top NG3 — Margin Revision Diagnostic

Status:

```
PIT_NEED_CONFIRMED
EARLY_MARGIN_START_POLICY_FROZEN
NUMERICAL_NG3_FORMULA_NOT_FROZEN
HISTORICAL_TOP_HIT_RATE_NOT_TESTED
```

Research only. No production effect.

## What changed

The historical margin block now has two dated publication snapshots that can be compared with the present revised BEA/FRED series using the scale-free ratio:

```
profit_share = unit_profit / total_cost_and_profit_per_unit
```

The ratio is used only as a **revision / comparability diagnostic**. It is not an NG3 score.

## 1976 publication snapshot covering 1974–1975

The April 1976 *Economic Indicators* table, sourced to BEA, explicitly reports:

- total current-dollar cost and profit per unit of output;
- corporate profits with inventory valuation and capital consumption adjustments;
- quarterly rows for 1974 Q1–Q4 and 1975 Q1–Q4.

Frozen historical profit shares:

| Quarter | 1976-vintage share | Current revised share | Vintage - current |
|---|---:|---:|---:|
| 1974 Q1 | 8.664% | 11.285% | -2.621 pp |
| 1974 Q2 | 8.494% | 11.009% | -2.515 pp |
| 1974 Q3 | 7.483% | 10.355% | -2.872 pp |
| 1974 Q4 | 6.683% | 9.742% | -3.059 pp |
| 1975 Q1 | 6.795% | 9.777% | -2.982 pp |
| 1975 Q2 | 8.919% | 11.050% | -2.131 pp |
| 1975 Q3 | 10.485% | 12.737% | -2.252 pp |
| 1975 Q4 | 10.062% | 12.834% | -2.772 pp |

Mean absolute diagnostic gap:

```
2.651 percentage points
```

Maximum:

```
3.059 percentage points
```

This is too large to treat present revised history as a harmless stand-in for the publication-era margin series.

## June 1988 publication snapshot

The June 1988 *Survey of Current Business* Table 7.18 gives a contemporaneous unit-cost/profit table. The issue states that it went to the printer on July 11, 1988, so this research uses **1988-07-11 as a conservative no-earlier-than availability boundary** for the snapshot.

Frozen diagnostic:

| Quarter | 1988-vintage share | Current revised share | Vintage - current |
|---|---:|---:|---:|
| 1986 Q4 | 9.332% | 8.896% | +0.436 pp |
| 1987 Q1 | 9.610% | 9.150% | +0.460 pp |
| 1987 Q2 | 9.541% | 9.772% | -0.231 pp |
| 1987 Q3 | 10.197% | 10.373% | -0.176 pp |
| 1987 Q4 | 9.795% | 9.984% | -0.189 pp |
| 1988 Q1 | 9.973% | 10.256% | -0.283 pp |

Mean absolute diagnostic gap:

```
0.296 percentage points
```

Maximum:

```
0.460 percentage points
```

The later-era vintage is materially closer to today's revised series, but it is still not identical.

## Historical concept timing

The August 1974 SCB unit-profit table used an IVA-only profit label. By the 1975 *Business Statistics* supplement and the January 1976 SCB, BEA publications explicitly showed corporate profits with inventory valuation **and capital consumption adjustments**.

Because the exact first public release day of the comparable unit-margin construction has not yet been recovered, NG3 freezes a conservative policy:

```
MarginConfirm before 1976-01-31 = MARGIN_NOT_COMPARABLE
MarginConfirm from 1976-01-31 onward = eligible only when a dated vintage is actually available
```

This does **not** mean January 31, 1976 was the historical first release date. It is a conservative research boundary.

## Scientific consequence

The source audit has now answered an important design question:

```
Can current revised BEA unit-profit history be used as a point-in-time substitute?
NO
```

Especially around the 1974–75 inflation regime, the difference is large enough to change thresholds or rankings in a model.

Therefore future NG3 work must retain:

- `NG3-CostPressure` for long-history inflation/cost detection;
- `NG3-MarginConfirm` only from a documented comparable vintage;
- `MARGIN_NOT_COMPARABLE` before the frozen early-era boundary;
- current revised BEA/FRED data as diagnostic/reference only.

## Next gate

The next step is **numerical preregistration of CostPressure**, not historical score tuning.

Before viewing top outcomes, freeze:

1. CPI/PPI transformations;
2. lookback windows;
3. normalization;
4. cost-pressure threshold;
5. top-location gate;
6. release lags;
7. episode construction;
8. development / validation / untouched holdout windows.

MarginConfirm may be added only as a separately preregistered confirmation layer.

No historical top hit-rate has been tested in this memo.
