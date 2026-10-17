# Market Top Cross-Model Prospective Monitor

Status: **RESEARCH ONLY / NO ENSEMBLE**

This monitor observes two independent frozen research routes:

1. Market Top V2.4R Route_B Shadow
2. MASTER TOP V2.1.8

It does **not** combine them into one score.

## Comparability gate

A comparison is allowed only when:

- Route_B Shadow is a resolved live snapshot;
- MASTER TOP V2.1.8 is not a seed/proxy snapshot;
- both snapshots have the exact same `asof` date.

Otherwise:

```
status = NOT_COMPARABLE
```

with explicit reasons such as:

- `MASTER_TOP_SEED_ONLY`
- `MASTER_TOP_MISSING_LIVE_FIELDS`
- `ROUTE_B_NOT_RESOLVED`
- `ASOF_MISMATCH`

## Same-day labels

Only after the gate passes:

```
Route_B high = Route_B >= 85
MASTER TOP high = supplemental_route >= 55
```

The monitor may label:

- `BOTH_HIGH`
- `BOTH_LOW`
- `MASTER_TOP_ONLY`
- `ROUTE_B_ONLY`

These labels are diagnostic only.

The monitor always keeps:

```
ensemble_score = null
action_signal = null
```

No averaging, maximum, voting, or trading action is authorized.

## Why this matters

The two models encode different mechanisms.

Route_B Shadow requires:

- expensive valuation;
- 2Y repricing plus genuine QE/taper-flow reversal;
- small-cap weakness;
- later price confirmation through T_v2.4R.

MASTER TOP V2.1.8 requires:

- short- and medium-horizon 2Y repricing;
- persistent New High/New Low breadth deterioration;
- proximity to a 60-month high.

Therefore disagreement is useful information about *which mechanism is active*.

It should not be erased by an ensemble before prospective evidence exists.

## Current repository state

At the time this monitor was introduced:

- Route_B Shadow has a live-validated 2026-10-16 snapshot;
- MASTER TOP V2.1.8 repository payload is explicitly a 2026-10-09 seed snapshot.

Therefore the correct current monitor state is:

```
NOT_COMPARABLE
```

not `MASTER_TOP_ONLY`.

A real cross-model label will begin only after MASTER TOP V2.1.8 produces a non-seed snapshot on the same market date.
