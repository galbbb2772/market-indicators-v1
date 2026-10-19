# Market Top Route_C NG3 — Prospective Evidence Protocol

Status: **FROZEN BEFORE PROSPECTIVE START**

This protocol governs prospective evidence storage for Route_C NG3. It does not change the preregistered model.

Prospective evidence begins only at:

```
effective month >= 2026-12
```

## Monthly snapshot immutability

For each completed effective month at or after 2026-12, the first successful run with all required source months available becomes the canonical frozen monthly snapshot.

If required inputs are missing or stale, the run fails closed and freezes nothing.

Once frozen, later upstream revisions must not alter:

- Route_C_NG3_score;
- ValuationContext120;
- ConcentrationBreadth;
- SpreadShockScore;
- BigGrowthGapChange3M;
- phase-gate results;
- top-location result;
- ARMED / IDLE state;
- source months;
- source fingerprints.

## Episode definition

An episode starts on the first completed prospective month with:

```
state = ARMED
```

Consecutive ARMED months are one episode.

The first completed IDLE month after an ARMED run closes that episode.

A later ARMED month after at least one completed IDLE month opens a new episode.

Episode ID:

```
CNG3-<first armed effective month>
```

Anchor:

```
last trading day of the first ARMED effective month
```

No pre-2026-12 state may create a prospective episode.

## Outcome tracking

Price:

```
SPY unadjusted Close
```

Track:

- 63 sessions;
- 126 sessions;
- 252 sessions.

At each horizon record:

- forward return from anchor;
- worst return from the original anchor;
- maximum peak-to-trough drawdown.

Completed horizon metrics are immutable.

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

Classification is emitted only after 252 sessions are complete.

## Source-vintage fingerprints

Every canonical monthly snapshot must preserve the identity of the actual bytes used.

Required fingerprints:

- FF25 ZIP SHA-256;
- FF3 ZIP SHA-256;
- Shiller payload SHA-256 or equivalent immutable payload fingerprint;
- BAA / GS10 payload SHA-256 or approved fallback manifest fingerprint;
- SPY payload SHA-256 used for the completed-month price gate.

When an episode opens, copy the monthly snapshot provenance into:

```
source_provenance_at_start
```

and never rewrite it.

## Review eligibility

Only after:

```
>= 4 complete prospective 252-session episodes
```

may the evidence ledger set:

```
review_eligible = true
```

A separate research decision record is still required.

No automatic production promotion is permitted.

## Governance

Changing episode grouping, horizon definitions, source-vintage rules, classification, or review count requires a new evidence-protocol version.

Changing any model formula or gate requires Route_C NG4 or later.
