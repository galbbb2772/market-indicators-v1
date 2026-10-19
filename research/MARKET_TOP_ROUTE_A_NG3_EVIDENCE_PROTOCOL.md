# Market Top Route_A NG3 — Prospective Evidence Protocol

Status: **FROZEN BEFORE PROSPECTIVE START**

This protocol defines how future NG3 evidence is recorded. It does not change the NG3 score or state gate.

Prospective evidence begins only at:

```
effective month >= 2026-12
```

## Episode definition

A prospective episode starts on the first completed effective month with:

```
NG3 state = ARMED
```

Consecutive completed ARMED effective months belong to the same episode.

The first completed effective month with:

```
state = IDLE
```

after an ARMED run closes that signal episode.

A later ARMED month after at least one completed IDLE month opens a new episode.

Episode ID:

```
NG3-<first armed effective month>
```

Anchor:

```
last trading day of the first ARMED effective month
```

No episode may be created from 2026-11 or earlier output.

## Outcome tracking

Price:

```
SPY unadjusted Close
```

Track from the first trading session after the anchor at:

```
63 sessions
126 sessions
252 sessions
```

At each horizon record:

- forward return from anchor;
- worst return below/above the original anchor;
- maximum peak-to-trough drawdown along the observed path.

Overlapping outcome windows are retained rather than deleted. The ledger is evidence storage, not a trade-count estimator.

## Frozen 252-session classification

```
MAJOR_TOP
  if worst_return_from_anchor <= -15%

CLEAR_FALSE
  if worst_return_from_anchor > -7.5%
  AND forward_return_252 > 0%

CORRECTION_OR_AMBIGUOUS
  otherwise
```

Classification is emitted only after all 252 sessions are observed.

### Completed-horizon immutability

Once any 63 / 126 / 252-session horizon reaches:

```
complete = true
```

its stored metrics become immutable.

Later scheduled runs must not recompute that completed horizon from a rolling price-download window. Only incomplete horizons may accumulate new sessions.

This makes the evidence ledger append-only in substance: a completed prospective outcome cannot drift years later because an upstream price API changes its lookback window.

## Promotion-review rule

NG3 is not automatically promoted.

Only after:

```
>= 4 complete prospective 252-session episodes
```

may the ledger set:

```
review_eligible = true
```

A separate research decision record is still required. The monitor itself never creates a production or action signal.

## Governance

This evidence protocol is frozen before the first prospective source months exist.

Changing episode grouping, horizon definitions, classification, or promotion-review count requires a new protocol version.

The model itself remains frozen under the NG3 preregistration; model changes require NG4 or later.


## Source-vintage fingerprints

Every prospective NG3 snapshot must preserve the identity of the actual bytes used for the signal.

Required provenance:

- SHA-256 of each current Fama-French ZIP used by FF25 / FF12 / FF3;
- SHA-256 of direct FRED BAA / GS10 payloads, or the fallback manifest + extension/base payload hashes;
- SHA-256 of the Yahoo SPY payload used for the completed-month price gate.

When an episode opens, the full snapshot source provenance is copied into:

```
source_provenance_at_start
```

and remains attached to that episode.

This is required because the upstream datasets can be revised. A later dataset revision must not change which vintage generated a prospective signal.
