# T_v2.4R Source-Invariance Study

Status: **PASS WITH COVERAGE LIMIT**

The preregistered T_v2.4R formula was not changed.

## 1. Independent snapshot reproduction

Two separately maintained SPY history files were replayed with the identical frozen implementation.

### Snapshot A

`soGeneri/MarketDatasets/SPY_1993-2023_D.csv`

- 7,536 daily rows
- 1993-01-29 through 2022-12-30

### Snapshot B

`Setooooo/etf-insight/data/raw/SPY.csv`

Its source documentation explicitly states:

- Yahoo Finance historical chart API
- SPY daily data
- unadjusted Close retained
- 1993-01-29 through 2026-07-23
- 8,427 trading days

On the 7,536 overlapping dates:

- maximum absolute Close difference: ~4.93e-7 USD
- mean absolute Close difference: ~1.85e-7 USD
- all six event confirmation dates are identical

| Event | Snapshot A | Snapshot B |
|---|---|---|
| 1998 | 1998-08-04 | 1998-08-04 |
| 2000 | 2000-04-14 | 2000-04-14 |
| 2007 | 2007-11-09 | 2007-11-09 |
| 2011 | 2011-06-10 | 2011-06-10 |
| 2018 | 2018-10-11 | 2018-10-11 |
| 2022 | 2022-01-20 | 2022-01-20 |

This is strong **snapshot / serialization invariance**.

It is deliberately not labeled complete provider invariance because one file's upstream provider is not independently established in this study and the other explicitly uses Yahoo.

## 2. SPY vs S&P 500 index cross-check

The same formula was then run on S&P 500 index close series rather than SPY.

### 2011

Legacy SP500 index snapshot:

- SPY confirmation: 2011-06-10
- SP500 confirmation: 2011-06-10
- SP500 DD12: 6.793%
- SP500 T_v2.4R: 77.240

Date result: **MATCH**

The legacy file's upstream provenance is not strong enough to call this a fully verified provider-independent test, so it remains labeled an index-snapshot cross-check.

### 2018

S&P 500 index series:

- SPY confirmation: 2018-10-11
- SP500 confirmation: 2018-10-11
- SP500 DD12: 6.905%
- SP500 T_v2.4R: 83.672

Date result: **MATCH**

### 2022

S&P 500 index series:

- SPY confirmation: 2022-01-20
- SP500 confirmation: 2022-01-20
- SP500 DD12: 6.543%
- SP500 T_v2.4R: 73.904

Date result: **MATCH**

Official FRED SP500 daily closes independently show:

- 2022-01-03 = 4796.56
- 2022-01-18 = 4577.11
- 2022-01-19 = 4532.76
- 2022-01-20 = 4482.73

FRED identifies SP500 as a daily-close S&P 500 index series sourced from S&P Dow Jones Indices LLC.

## 3. What changed across instruments

The **score values** are not identical between SPY and SP500.

Examples:

| Event | SPY T | SP500 T | Confirmation date |
|---|---:|---:|---|
| 2011 | ~72.96 | 77.24 | same |
| 2018 | ~85.62 | 83.67 | same |
| 2022 | ~73.08 | 73.90 | same |

That is the desired behavior for this test:

> numerical level can move modestly, while the state transition date remains stable.

The model is therefore not relying on one exact ETF print to cross the threshold.

## 4. Coverage limit

Current result:

- six-event snapshot invariance: **PASS**
- SPY-vs-index date invariance: **PASS for 2011 / 2018 / 2022**
- official FRED value cross-check: **PASS for 2018 / 2022**
- fully independent non-Yahoo daily-provider validation for 1998 / 2000 / 2007: **OPEN**

This remaining gap must stay visible. It is not a reason to change the formula.

## Decision

```
T_v2.4R source-invariance status:
PASS_WITH_COVERAGE_LIMIT
```

No weights, thresholds, or event dates were tuned after this check.
