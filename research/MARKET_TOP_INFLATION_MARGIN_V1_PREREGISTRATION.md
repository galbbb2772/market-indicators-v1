# Market Top Inflation–Margin Route V1 — Preregistration

Status:

```
PREREGISTERED / NOT VALIDATED / RESEARCH ONLY
```

This is a separate supplemental route. It does **not** modify PolicyShock V2.1.1, Route_B, legacy Route_A/Route_C, MASTER TOP V2.1.8, or production Pressure.

## Hypothesis

Some historical U.S. equity tops occurred in an inflation/cost regime that the modern credit/liquidity routes do not describe well.

The frozen mechanism is:

1. consumer-price inflation is historically elevated;
2. unit labor-cost growth is historically elevated;
3. nonfinancial corporate unit profits are compressing;
4. the equity index is still near a recent high.

This route is deliberately macro-cost/profit based. No QE/taper variable is used.

## Official source series

FRED identifiers:

- `CPIAUCSL` — CPI for All Urban Consumers, monthly;
- `PRS85006111` — Nonfarm Business Unit Labor Costs, percent change from year ago, quarterly;
- `A466RD3Q052SBEA` — nonfinancial corporate after-tax unit profits, quarterly.

Price gate and forward outcomes:

- S&P 500 index `^GSPC`, unadjusted close.

## Frozen component definitions

### Inflation

```
CPIYoY(t) = 100 * (CPI(t) / CPI(t-12) - 1)

InflationScore(t)
  = expanding_percentile(CPIYoY)
```

### Unit labor-cost pressure

```
ULCScore(q)
  = expanding_percentile(ULC_YoY)
```

### Margin compression

```
UnitProfitYoY(q)
  = 100 * (UnitProfit(q) / UnitProfit(q-4) - 1)

MarginCompressionRaw(q)
  = -UnitProfitYoY(q)

MarginCompressionScore(q)
  = expanding_percentile(MarginCompressionRaw)
```

### Route

```
Route_IM_V1
  = cbrt(
      InflationScore
      * ULCScore
      * MarginCompressionScore
    )
```

Threshold:

```
Route_IM_V1 >= 85
```

No weight or component threshold is added.

## Point-in-time convention

This first historical screen uses current official histories and conservative publication lags.

- CPI monthly source observation: effective one calendar month later.
- Quarterly ULC and unit-profit observation: effective five calendar months after the quarter-start label.
  - Q1 label Jan -> effective Jun
  - Q2 label Apr -> effective Sep
  - Q3 label Jul -> effective Dec
  - Q4 label Oct -> effective Mar of the next year
- expanding percentiles are current-inclusive using only source observations effective by that month;
- no interpolation;
- no event-specific lags;
- first 10 years of component history are warm-up only.

This is **not** an exact historical-vintage replay. If the route survives screening, source-vintage robustness is a separate gate.

## Top-location gate

An ARMED month additionally requires:

```
index close within 5% of trailing 24-calendar-month close high
AND
that high formed within the prior 3 calendar months
```

No direct price-breakdown trigger is authorized in V1.

## Hypothesis-generation windows

These motivated the route and are not counted as independent validation evidence:

```
1965-12 through 1966-06
1972-10 through 1973-03
```

## Frozen validation expectations

Positive mechanism windows:

```
1968-08 through 1969-02
1980-08 through 1981-02
```

Each must contain at least one ARMED month.

Negative-control windows:

```
1987-06 through 1987-10
1998-06 through 1998-10
2000-01 through 2000-04
2007-06 through 2007-10
2018-08 through 2018-12
```

None may contain an ARMED month.

## Episode outcome protocol

For every ARMED episode outside the two hypothesis-generation windows:

- consecutive ARMED months are one episode;
- anchor = last trading day of the first ARMED month;
- horizon = next 252 trading sessions.

Frozen classification:

```
MAJOR_TOP
  if worst return from anchor <= -15%

CLEAR_FALSE
  if worst return from anchor > -7.5%
  AND 252-session forward return > 0%

CORRECTION_OR_AMBIGUOUS
  otherwise
```

## Decision rule

```
ACCEPT_SCREENING_CANDIDATE
```

only if all are true:

1. both positive mechanism windows contain an ARMED month;
2. all five negative-control windows are clean;
3. at least 2 complete non-training ARMED episodes exist;
4. MAJOR_TOP share among complete non-training episodes >= 50%;
5. CLEAR_FALSE share <= 25%.

Otherwise:

```
REJECT
```

A pass remains research-only.

## Governance

After screening begins:

- do not change the 85 threshold;
- do not change component weights;
- do not change lags;
- do not remove the top-location gate;
- do not redefine the positive/negative windows;
- do not suppress failed episodes.

Any structural redesign must be a new version.

Production effect remains:

```
NONE
```
