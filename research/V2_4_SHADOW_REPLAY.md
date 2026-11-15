# V2.4 Shadow Replay Contract

This shadow harness integrates PolicyShock V2.1.1 without changing production scoring.

Frozen behavior represented here:

- Pressure = max(Route_A, Route_B, Route_C)
- ARMED requires Pressure >= 85, price within 5% of the 24-month high, and the relevant high formed within the prior 3 months.
- ARMED retention: maximum 6 calendar months.
- Price Breakdown requires an existing ARMED state plus T >= 70 and drawdown from the 12-month high >= 4.5%.
- Accepted Early Breadth behavior is a direct trigger: Pressure >= 85, Route_C >= 85, and delta Breadth_3m >= 10.

## Original T limitation

The exact historical daily formula for original V2.4 T was not preserved. It is not re-invented here. A separately versioned T_v2.4R has been preregistered and validated as a new research confirmation model.

## 2022 shadow path

Conservative publication-lag policy route:

- 2022-01-03 Route_B = **85.3342917570**
- monthly Valuation and SizeWeakness inputs are restricted to 2021-11
- Policy Route independently ARMS the system in the top zone

Price path:

- 2022-01-03 S&P 500 close = 4796.56
- 4.5% line = 4580.71
- 2022-01-18 close = 4577.11, the earliest known drawdown-gate crossing
- T_v2.4R on the SPY proxy first confirms on 2022-01-20

The earlier ~88.72 Route_B value used later monthly SizeWeakness information and is no longer labeled strict PIT.
