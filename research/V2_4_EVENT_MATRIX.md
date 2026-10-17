# V2.4 Event-Level Shadow Validation Matrix

This matrix deliberately separates prior accepted historical outputs from results freshly recomputed in the PolicyShock V2.1.1 work.

## Accepted historical outputs

| Event | Full V2.4 | Accepted path | MDD12 | MDD24 |
|---|---:|---|---:|---:|
| 1998 | NO | — | — | — |
| 2000 | YES | 1999-08 -> 2000-05 Breadth -> Price | -25.9% | -33.1% |
| 2007 | YES | 2007-12 Price | -38.2% | -48.1% |
| 2011 | NO | — | — | — |
| 2018 | NO | — | — | — |
| 2022 | YES | 2021-10 Early Breadth | -25.0% | -25.0% |

These rows are regression fixtures from the previously accepted V2.4 research output. They are not presented as newly recomputed daily history.

## Fresh PolicyShock shadow result

For 2022 only, this branch freshly establishes the independent policy route:

- 2022-01-03 strict-PIT Route_B = 88.7229415743
- therefore Route_B independently satisfies Pressure >= 85 in the top zone and can ARM
- 2022-01-18 is the earliest possible price-breakdown date from the 4.5% drawdown condition
- the exact formal Price Trigger date remains unresolved until the original frozen daily T score is supplied

Interpretation: the patch adds failure-path redundancy to 2022; it does not rewrite the accepted historical event label, which remains the 2021-10 Early Breadth trigger.