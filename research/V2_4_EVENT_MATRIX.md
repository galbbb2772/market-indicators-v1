# V2.4 Event-Level Shadow Validation Matrix

This matrix separates prior accepted historical outputs from freshly recomputed research results.

## Accepted historical outputs

| Event | Full V2.4 | Accepted path | MDD12 | MDD24 |
|---|---:|---|---:|---:|
| 1998 | NO | — | — | — |
| 2000 | YES | 1999-08 -> 2000-05 Breadth -> Price | -25.9% | -33.1% |
| 2007 | YES | 2007-12 Price | -38.2% | -48.1% |
| 2011 | NO | — | — | — |
| 2018 | NO | — | — | — |
| 2022 | YES | 2021-10 Early Breadth | -25.0% | -25.0% |

These rows are regression fixtures from previously accepted V2.4 research output. They are not presented as newly recomputed daily history.

## Fresh PolicyShock shadow result

For 2022 the branch establishes an independent policy route using a conservative monthly publication lag:

- 2022-01-03 Route_B = **85.3342917570**
- monthly Valuation and SizeWeakness are restricted to 2021-11
- therefore Route_B still independently satisfies Pressure >= 85 in the top zone and can ARM
- 2022-01-18 is the earliest known 4.5% price-drawdown gate crossing for the S&P 500 index
- the separately versioned T_v2.4R confirms the SPY proxy on 2022-01-20

The older ~88.72 value is not treated as the strict-PIT 2022-01-03 golden result.

Interpretation: the patch adds failure-path redundancy to 2022; it does not rewrite the accepted historical event label, which remains the 2021-10 Early Breadth trigger.
