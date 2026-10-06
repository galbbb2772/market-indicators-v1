# Indicator Pruning V1

Frozen evidence through **2026-10-02**. Research-only; no production membership/weight change.

Current active directional set: **19**.
Proposed KEEP_ACTIVE: **11**; Context: **7**; Archive duplicate: **1**.

## KEEP_ACTIVE

| indicator | full IC10 | 2022+ IC10 | phase sign % | component partial IC | component LOYO % | reason |
|---|---:|---:|---:|---:|---:|---|
| breadth_concentration | 0.082 | -0.0136 | 100.0 | 0.0287 | 0.299 | source-invariant component retains incremental evidence |
| global_cb_rhythm | -0.077 | -0.101 | 100.0 | None | None | strong, same-sign, phase-stable historical signal |
| market_fear | -0.1493 | -0.0883 | 100.0 | None | None | strong, same-sign, phase-stable historical signal |
| market_liquidity | -0.1394 | -0.0704 | 100.0 | None | None | strong, same-sign, phase-stable historical signal |
| market_support | -0.0819 | -0.0785 | 80.0 | -0.0471 | -0.184 | source-invariant component retains incremental evidence |
| options_anomaly | -0.1029 | -0.0604 | 100.0 | -0.0147 | -0.282 | strong, same-sign, phase-stable historical signal |
| retail_participation | -0.0625 | -0.0812 | 100.0 | 0.0294 | 0.148 | incremental component/LOYO evidence plus stable recent direction |
| tech100_volatility | -0.0559 | 0.0363 | 90.0 | 0.0485 | -0.594 | source-invariant component retains incremental evidence |
| treasury_rate_regime | 0.1127 | 0.0517 | 100.0 | None | None | strong, same-sign, phase-stable historical signal |
| us_loans_speed | -0.1396 | -0.2146 | 100.0 | None | None | strong, same-sign, phase-stable historical signal |
| valuation_percentile | 0.119 | 0.0931 | 100.0 | 0.0095 | -1.344 | strong, same-sign, phase-stable historical signal |

## CONTEXT

| indicator | proposed action | representative | full IC10 | 2022+ IC10 | reason |
|---|---|---|---:|---:|---|
| business_cycle | CONTEXT_WEAK |  | 0.0209 | 0.0109 | weak full/recent IC with limited phase stability |
| employment | CONTEXT_WEAK |  | -0.0235 | -0.0242 | weak full/recent IC with limited phase stability |
| geopolitical_risk | CONTEXT_UNSTABLE |  | -0.0884 | 0.0198 | 2022+ direction conflicts with full-sample direction |
| market_overextension | CONTEXT_LOW_INCREMENTAL |  | -0.0307 | -0.0923 | historically informative but insufficient incremental/stability evidence for active scoring |
| money_making_effect | CONTEXT_LOW_INCREMENTAL |  | -0.0582 | -0.0235 | historically informative but insufficient incremental/stability evidence for active scoring |
| sme_survival_growth | CONTEXT_LOW_INCREMENTAL |  | -0.0081 | -0.0703 | historically informative but insufficient incremental/stability evidence for active scoring |
| yield_curve | CONTEXT_LOW_INCREMENTAL |  | 0.043 | 0.1076 | historically informative but insufficient incremental/stability evidence for active scoring |

## ARCHIVE duplicates

| indicator | representative | reason |
|---|---|---|
| high_yield | market_liquidity | near-identical active signal to market_liquidity (|rho|=1.000) |

## Interpretation

Pruning here means **stop giving redundant/weak indicators an independent vote**. Context indicators remain visible for explanation/regime inspection. Archive indicators retain raw history, but should not independently enter the aggregate score.

A separate score-preservation A/B should be run before changing live role labels: current Active set vs proposed pruned Active set, using the same frozen historical dates and Forward-OOS guardrails.
