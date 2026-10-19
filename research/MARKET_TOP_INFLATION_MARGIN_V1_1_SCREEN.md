# Market Top Inflation–Margin Route V1.1 — Screening Result

Status:

```
REJECT
```

Research only. Production effect: **none**.

## Execution provenance

The first V1 run failed before any model output because the FRED graph endpoint timed out. That attempt is recorded separately as a provider failure.

V1.1 hardened transport before the first successful model calculation:

- CPIAUCSL: pinned public historical snapshot;
- PRS85006111: BLS public API;
- PRS88003191: BLS public API;
- ^GSPC: Yahoo Finance unadjusted close.

Successful workflow:

```
run = 39204352570
job = 117903827966
conclusion = success
artifact = 12164882009
artifact sha256 = f38b27115fd80a95dea5875409dcce3242aeca3ce23cb9936ce63df5ce786125
```

The workflow success means the frozen calculation executed correctly. It does **not** mean the model passed.

## Frozen result

Sample after warm-up:

```
1958-05 through 2018-03
719 monthly states
```

Decision:

```
REJECT
```

Preregistered positive-window gate:

```
1968-08 .. 1969-02 -> no ARMED month
1980-08 .. 1981-02 -> no ARMED month
positive_windows_all_hit = false
```

Preregistered negative controls were clean:

```
1987-06 .. 1987-10 -> no ARMED month
1998-06 .. 1998-10 -> no ARMED month
2000-01 .. 2000-04 -> no ARMED month
2007-06 .. 2007-10 -> no ARMED month
2018-08 .. 2018-12 -> no ARMED month
negative_windows_all_clean = true
```

No ARMED episodes were produced anywhere in the evaluated sample, so there are no non-training episode outcomes to score.

## What the route actually did

The macro-cost/profit score itself became extremely high, but mostly **after** the market had already moved away from its recent high.

Highest frozen route values include:

```
1970-06  96.8009   top-location = false
1970-07  96.6812   top-location = false
1970-08  96.0316   top-location = false
1970-03  95.3840   top-location = false

1974-06  92.2328   top-location = false
1974-07  92.2328   top-location = false
1974-08  92.2328   top-location = false
```

The underlying economic stress is real:

```
1970-06:
InflationScore = 90.7063
ULCScore = 100.0000
MarginCompressionScore = 100.0000
```

but the signal is too late to satisfy the frozen top-location condition.

## Interpretation

V1.1 successfully identifies **inflation / labor-cost / profit-compression stress**, but the conjunction of all three extreme components is a late-cycle / post-top state rather than a robust pre-top state.

The supported statement is:

> Inflation–Margin V1.1 is a macro stress diagnostic.

The unsupported statement is:

> Inflation–Margin V1.1 is a validated market-top route.

## Governance

No rescue is permitted by:

- lowering 85;
- removing the top-location gate;
- shortening the publication lag after seeing the result;
- changing the geometric aggregation;
- deleting the failed positive windows.

V1.1 is closed as a top-route candidate.

Any new leading version must use a newly preregistered mechanism and version number before testing.
