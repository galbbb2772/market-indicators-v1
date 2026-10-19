# Inflation–Margin V1.1 — Failure Diagnostic

Status:

```
HYPOTHESIS_GENERATION_ONLY
```

The frozen V1.1 decision remains:

```
REJECT
```

No formula, threshold, lag, gate, or validation rule was changed.

## Core diagnostic

Across the evaluated sample:

```
Route >= 85 months               = 24
Top-location pass months         = 324
Route >= 85 AND top-location     = 0
```

The strongest route reading while the market was still in the frozen top-location zone was only:

```
1991-02
Route = 71.0788
```

So the V1.1 failure is not a narrow 85-vs-84 threshold accident.

## Timing pattern

### 1966 training window

The route was roughly 63–67.

Margin compression was already elevated near the 85th percentile, but ULC pressure remained only around the 45th percentile.

### 1968–69 validation window

The market was mostly still at the top-location gate, while:

```
InflationScore ~ 89–90
ULCScore       ~ 45–67
MarginScore    ~ 38–51
Route          ~ 54–65
```

The actual three-way stress extreme arrived later:

```
1970-06
Route = 96.8009
InflationScore = 90.7063
ULCScore = 100
MarginCompressionScore = 100
CPI YoY = 6.04%
ULC YoY = 8.3%
Unit-profit YoY = -23.9%
```

By then the top-location gate was false.

### 1972–73 training window

The route was only about 38–44.

Most importantly, the cost-profit gap was negative:

```
1972-12 / 1973-01:
ULC YoY - Unit-profit YoY ~= -7.2 pp
```

So nonfinancial unit-profit growth was still stronger than labor-cost growth around that top under the frozen PIT alignment.

This rejects the idea that already-visible profit compression was the pre-top mechanism for the 1973 episode.

### 1980–81 validation window

The route stayed near 55 despite:

```
InflationScore ~ 95–98
ULCScore       ~ 82.5
```

because:

```
MarginCompressionScore ~ 21.2
cost-profit gap ~ -6.9 pp
```

Again, actual profit compression was not yet the extreme pre-top leg.

## Research conclusion

The common failure mechanism is now clear:

> observed margin compression is predominantly a late / post-top confirmation variable, not a robust pre-top pressure variable.

A simple cost-profit gap does not rescue the route either; it is negative in important pre-top windows such as 1972–73 and 1980–81.

Therefore the next route should **not** be a retuned Inflation–Margin formula.

A cleaner next hypothesis is a separate long-history **Monetary Restriction** route based on information that can genuinely be extreme before the top, such as yield-curve inversion / rate restriction, while leaving Route_B unchanged.

Artifact provenance:

```
diagnostic workflow = 39204551814
artifact = 12164614953
artifact sha256 = 2ed7c30a4bed19d6bb5f5b26f12d4d40ecba3b623462499fbc8554ecacf84b7b
```
