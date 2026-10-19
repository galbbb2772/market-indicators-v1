# Market Top Inflation–Margin V1 — Provider Failure Record

Status:

```
NO_MODEL_RESULT / PROVIDER_FAILURE
```

The first historical-screen workflow attempt did **not** produce any model output.

Workflow:

```
run = 39203646674
job = 117901695607
```

Frozen preregistration tests passed before the data step.

The screen then failed on its first macro download:

```
https://fred.stlouisfed.org/graph/fredgraph.csv?id=CPIAUCSL
ReadTimeout
```

No CPI series was loaded, no component percentile was computed, no Route_IM_V1 score was computed, and no validation window or episode result was observed.

Therefore this failure is classified as:

```
DATA_PROVIDER_FAILURE
NOT_MODEL_EVIDENCE
```

## Provider hardening boundary

Before the first successful model calculation, the source transport is hardened without changing:

- the economic mechanism;
- the three component meanings;
- the geometric formula;
- threshold 85;
- point-in-time lags;
- top-location gate;
- training windows;
- validation windows;
- negative controls;
- outcome classifications;
- acceptance rule.

The hardened source chain is versioned as **V1.1**.

CPI remains the CPIAUCSL history, but the screen reads a pinned public snapshot instead of depending on the timing-sensitive FRED graph endpoint.

The labor-cost and unit-profit components use the corresponding BLS Major Sector Productivity series directly:

```
PRS85006111
= Nonfarm Business unit labor costs
= % change same quarter one year ago

PRS88003191
= Nonfinancial Corporate unit profits
= % change same quarter one year ago
```

The second series is the direct BLS unit-profit growth concept underlying the margin-compression hypothesis, so V1.1 uses:

```
MarginCompressionRaw = -PRS88003191
```

No model result from V1 existed before this source hardening.
