# V2.4 T Recovery Study

Status: **original formula not recovered**

## What is known

The retained research record defines T as a **price/trend confirmation score**, separate from Pressure.

Known inputs:

- S&P 500 price versus the 10-month moving average;
- distance / drawdown from the 12-month high.

Frozen trigger interaction:

```
Price Trigger =
    existing ARMED
    AND T >= 70
    AND drawdown_from_12m_high >= 4.5%
```

ARMED retention remains six calendar months.

## Historical fingerprints recovered from the prior research record

| Event | Top-month T | First T>=70 delay |
|---|---:|---:|
| 1998 | 73.8 | 0 months |
| 2000 | 47.5 | +2 months |
| 2007 | 48.0 | +1 month |
| 2011 | 38.3 | +3 months |
| 2018 | 39.7 | +1 month |
| 2022 | 83.8 | 0 months |

These are now treated as **recovery fingerprints**, not as a definition of T.

## Price-data cross-check

Public historical S&P 500 monthly data were used only to test whether a very simple two-feature reconstruction could plausibly be the missing original mapping.

Using month-end close, trailing 10-month close average, and the highest monthly high in the relevant 12-month window, the recovered top-month feature fingerprints are approximately:

| Event | Price below 10M MA (%) | Drawdown from 12M high (%) | Archived T |
|---|---:|---:|---:|
| 1998 | -7.46 | 5.87 | 73.8 |
| 2000 | -8.71 | 3.50 | 47.5 |
| 2007 | -4.78 | 1.69 | 48.0 |
| 2011 | -11.62 | 0.07 | 38.3 |
| 2018 | -5.75 | 0.92 | 39.7 |
| 2022 | -1.79 | 6.29 | 83.8 |

Negative "below MA" means price was still above the trailing 10-month average.

Sources used for this diagnostic:
- StatMuse monthly S&P 500 OHLC history for the corresponding event years.
- Multpl/Shiller monthly S&P 500 history as an independent monthly-price cross-check.

## Rejected simple surrogate

A least-squares diagnostic of the form:

```
T_hat = a + b * Drawdown12M_pct + c * Below10MMA_pct
```

produced an in-sample fit around:

```
a ~= 41.89
b ~= 6.32
c ~= 0.90
```

with in-sample RMSE around **4.8 score points**.

That is not sufficient evidence. More importantly, leave-one-event-out reconstruction deteriorated to roughly **10.1 score points RMSE**, with large errors on 2000, 2011 and 2022.

Therefore this simple linear mapping is **REJECTED** as a recovery of the original T.

It must not be wired into V2.4 and must not be called T.

## Recovery rule

A formula may use the original label only if it simultaneously:

1. is supported by an actual recovered formula/code artifact, **or**
2. reproduces all six archived top-month T scores within ±0.25;
3. reproduces every archived first-T>=70 delay exactly;
4. uses point-in-time-safe inputs;
5. does not alter the frozen Price Trigger or ARMED rules.

If a new price-confirmation model is designed instead, it must receive a new explicit version name such as **T_v2.4R** and be validated as a new model rather than presented as recovered history.

## Current consequence

The PolicyShock V2.1.1 shadow integration remains valid through:

```
PolicyShock -> Route_B -> Pressure -> ARMED
```

For 2022:

```
2022-01-03 strict-PIT Route_B = 88.7229415743 -> ARMED
```

The 4.5% drawdown gate is first known to be crossed on 2022-01-18.

The exact formal Price Trigger date remains intentionally unresolved until the original T formula is genuinely recovered or a new T_v2.4R is preregistered and validated.
