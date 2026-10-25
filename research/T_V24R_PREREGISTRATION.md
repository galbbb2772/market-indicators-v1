# T_v2.4R Preregistration

Status: **PREREGISTERED / NOT PRODUCTION**

This is a new price-confirmation model. It is **not** a recovery of the missing original V2.4 T.

The formula below is frozen before full-history validation.

## Data contract

Instrument: S&P 500 price proxy / index close series.

Evaluation frequency: daily EOD.

Point-in-time rules:

1. `Close_t` is the completed trading-day close.
2. `High12M_t` is the highest **daily close** in the trailing 252 trading sessions including t.
3. The 10-month moving average uses only the **last 10 completed calendar month-end closes** strictly before the current calendar month.
4. No current-month month-end value may leak into an earlier day.
5. A signal computed from Close_t is actionable no earlier than the next trading session.

## Components

### 12M drawdown

```
DD12_pct = 100 * (High12M - Close) / High12M
```

```
DDScore = 100 * clip((DD12_pct - 1.0) / 6.0, 0, 1)
```

Interpretation:

- <=1% drawdown -> 0
- 4% drawdown -> 50
- >=7% drawdown -> 100

### 10M trend loss

Let `MA10M_prev` be the mean of the last 10 completed calendar month-end closes.

```
MAGap_pct = 100 * max(0, (MA10M_prev - Close) / MA10M_prev)
```

```
MAScore = 100 * clip(MAGap_pct / 4.0, 0, 1)
```

Interpretation:

- price at/above the frozen 10M MA -> 0
- 2% below -> 50
- >=4% below -> 100

## New score

```
T_v2.4R = 0.80 * DDScore + 0.20 * MAScore
```

Weights are frozen before validation.

## Trigger interaction

The surrounding state machine remains unchanged:

```
PRICE_BREAKDOWN_v2.4R =
    existing ARMED
    AND DD12_pct >= 4.5
    AND T_v2.4R >= 70
```

The separate 4.5% drawdown guard remains intentionally redundant. It prevents a moving-average break by itself from confirming a top.

## Structural properties fixed before validation

- If price remains at/above the 10M MA, T_v2.4R cannot reach 70 until DD12 is about 6.25%.
- A shallow 4.5% drawdown cannot trigger merely because the score exists.
- A combined drawdown plus MA break can confirm earlier than a severe drawdown alone.
- The model has only two monotonic inputs and no event-specific dates or parameters.

## Validation plan

No parameter changes are allowed after seeing results in this study.

Report:

1. full SPY daily history available from 1993 onward;
2. number and duration of unconditional T_v2.4R>=70 episodes;
3. first crossing around 1998, 2000, 2007, 2011, 2018, 2022;
4. 2022 date relative to the known 4.5% drawdown gate;
5. sensitivity only as a separate diagnostic -- not parameter selection;
6. explicit separation between unconditional price-confirmation episodes and actual top triggers, which still require ARMED.

Any parameter change requires a new version, e.g. T_v2.4R2.
