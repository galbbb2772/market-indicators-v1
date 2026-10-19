# Market Top Route_C NG3 — Seed Snapshot 2026-09

Status:

```
RETROSPECTIVE_TRAINING_DIAGNOSTIC
NOT PROSPECTIVE VALIDATION EVIDENCE
```

The prospective NG3 contract was frozen before this pipeline run.

Workflow:

```
run = 39205851962
conclusion = success
```

The successful run verifies that the preregistered source alignment and formula execute end-to-end.

## Effective state

```
effective month = 2026-09
FF source month = 2026-07
CAPE source month = 2026-08
credit source month = 2026-08
```

Because the first countable month is 2026-12:

```
counts_toward_prospective_validation = false
```

## Frozen seed values

```
CAPE = 40.98739355
ValuationContext120 = 100.0000

PortfolioExhaustionScore = 27.3411
LeaderGapScore = 96.1538
BigGrowthGapScore = 10.6187

ConcentrationBreadth = 30.3356
BigGrowthGapChange3M = +5.2491

SpreadShockRaw = +0.0200
SpreadShockScore = 47.3143

Route_C_NG3_score = 55.0777
```

Gates:

```
Route >= 85                  = false
history >= 120               = true
ConcentrationBreadth >= 85   = false
SpreadShockScore <= 50       = true
BigGrowthGapChange3M > 0     = true
phase gate                   = false
top-location gate            = true
```

Therefore:

```
state = IDLE
```

## Interpretation boundary

The current market is extremely high in trailing-decade CAPE context, but the frozen cross-sectional concentration block is weak because:

- portfolio exhaustion is low;
- Big Growth gap percentile is low;
- only the generic leader-gap percentile is extreme.

That combination is not sufficient for NG3.

This seed is **not** evidence that NG3 works or fails. It is only a pre-start execution / training diagnostic.

## Source fingerprints

Fama-French:

```
FF25 ZIP SHA-256
e02edcd282d8993cf3133e71181665f888ecb57c202a99a9cbd6cdf7fc6b8429

FF3 ZIP SHA-256
593f4fbef03181bc0b22ff6292f217689dd1fb79355049ca905d95b262040a66
```

Shiller payload:

```
41fcfb636f28b0090e11a498f93d9741ec107e5c2d57921b00eaa0b649eedada
```

Credit fallback manifest:

```
5e91e7461ff2ee9d80b8c74f8b78cff5b8a627442b347da0355422cb517361a0
```

SPY payload:

```
16ea3f622ae4c4ab028f167795d00dea7eaef5a8aadab89f90290bf650f7704e
```

No model parameter was changed after seeing this snapshot.
