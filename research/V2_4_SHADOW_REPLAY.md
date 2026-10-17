# V2.4 Shadow Replay Contract

This shadow harness integrates PolicyShock V2.1.1 without changing production scoring.

Frozen behavior represented here:

- Pressure = max(Route_A, Route_B, Route_C)
- ARMED requires Pressure >= 85, price within 5% of the 24-month high, and the relevant high formed within the prior 3 months.
- ARMED retention: maximum 6 calendar months.
- Price Breakdown requires an existing ARMED state plus T >= 70 and drawdown from the 12-month high >= 4.5%.
- Accepted Early Breadth behavior is a direct trigger: Pressure >= 85, Route_C >= 85, and delta Breadth_3m >= 10.

## Important limitation

The exact historical daily formula for V2.4 T was not preserved in the prior research record. The shadow replay therefore accepts t_score as an upstream PIT-safe input and does not invent a replacement formula.

This harness can validate PolicyShock -> Route_B -> ARMED wiring, state ordering, six-month retention, Early Breadth behavior, and Price Breakdown thresholds once a frozen T score is supplied.

## 2022 shadow path

- 2022-01-03 strict-PIT Route_B = 88.7229415743, so the policy route can independently ARM the system in the top zone.
- 2022-01-03 S&P 500 close = 4796.56; the 4.5% line is 4580.71.
- 2022-01-18 close = 4577.11, so this is the earliest possible price-breakdown date from the drawdown condition alone.
- The exact formal Price Trigger date remains conditional on upstream frozen T >= 70.