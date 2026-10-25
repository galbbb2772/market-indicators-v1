# Market Top Route_A NG3 — Prospective Evidence Protocol v2

Status: **FROZEN BEFORE PROSPECTIVE START / SUPERSEDES PROTOCOL v1**

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


## Monthly signal immutability

Beginning with the first countable effective month, each monthly signal is captured only once.

Rule:

```
effective_month >= 2026-12
```

The **first successful run after that effective month is complete** becomes the canonical frozen snapshot for that month.

If the required source data are unavailable or stale, the run fails closed and freezes nothing. A later scheduled run may try again.

Once the monthly snapshot is frozen, later upstream revisions must not alter its:

- NG3 score;
- component scores;
- phase gate;
- top-location gate;
- ARMED / IDLE state;
- source months;
- source SHA-256 fingerprints.

Later runs may continue updating only the forward outcome path of already-opened prospective episodes.

This prevents a revised Fama-French or credit history from rewriting what the model actually knew when the prospective month was first scored.


## Protocol v2 — evidence-gap episode continuity

Protocol v1 defined episode continuity only for observed consecutive monthly states.
Before the first prospective effective month, a review found a conservative-evidence bug:

```
ARMED -> missing month -> ARMED
```

could be split into two episodes even though the missing month did not prove that
the first episode ended. That could inflate the number of prospective episodes
and make the four-episode promotion-review threshold reachable too early.

Protocol v2 changes **only evidence bookkeeping**. It does not change:

- NG3 score;
- Route >= 85 threshold;
- FinancialLeadGapRaw >= 10 phase gate;
- 120-month warmup;
- PIT lags;
- top-location gate;
- prospective start month;
- 63 / 126 / 252-session outcome definitions.

Frozen v2 rule:

```
observed ARMED
-> one or more missing effective months
-> observed ARMED

= one episode
  + continuity_evidence_gap = true
  + missing_effective_months = [...]
```

This deliberately undercounts rather than overcounts episodes when continuity
cannot be proven.

If an episode has:

```
continuity_evidence_gap = true
```

its completed 252-session outcome remains stored, but it does **not** count
toward the minimum four clean episodes required for:

```
review_eligible = true
```

The ledger reports both:

```
complete_252_session_episodes
complete_252_session_episodes_without_continuity_gaps
episodes_with_continuity_gaps
```

and only the second quantity drives promotion-review eligibility.

This protocol hardening was made on 2026-10-19, before the first countable
prospective effective month (2026-12), so it does not relabel or discard any
prospective evidence.


## Monotonic episode-ledger time

Protocol v2 also fails closed on time reversal.

For the prospective ledger as a whole:

```
incoming effective_month
< latest month already represented by any episode
=> ERROR
```

This applies regardless of whether the stale incoming state is `ARMED` or
`IDLE`, and regardless of whether the latest existing episode is open or
already closed.

An older manual rerun, stale workflow checkout, or out-of-order job may not move
the evidence ledger backward, reopen an older month after a later close, or
rewrite episode continuity.

This is an implementation hardening of the already-frozen
`out_of_order_episode_updates_forbidden` rule, made before the first
prospective effective month. It does not change any model or evidence-count
criterion.

This is bookkeeping protection only; it does not change any NG3 model rule.


## Incomplete-outcome path coverage

An incomplete 63 / 126 / 252-session horizon may continue accumulating only
when the current price payload still covers the beginning of the post-anchor
path.

Fail-closed rule:

```
first available price observation after anchor
> anchor + 10 calendar days
=> ERROR
```

This guard prevents a rolling provider window from dropping the early part of
an unfinished episode and then incorrectly treating much later observations as
sessions 1..N after the signal.

Completed horizons remain immutable as before. This hardening applies only to
still-incomplete outcomes and changes no model, classification, or promotion
criterion.
