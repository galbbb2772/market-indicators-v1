# Market Top Route_A NG3 — Source-Temporality Addendum

Status: **EVIDENCE-QUALITY CLARIFICATION / NO MODEL CHANGE**

This addendum does not change any NG3 formula, threshold, state rule, PIT lag, outcome definition, promotion-review rule, or the preregistered first countable effective month.

The frozen NG3 preregistration remains:

```
first countable effective month = 2026-12
```

## Clarification discovered before prospective evidence begins

NG3 was preregistered on:

```
2026-10-19
```

The first countable effective month uses:

```
effective 2026-12
  -> Fama-French source month 2026-10
  -> credit source month 2026-11
```

The October Fama-French monthly observation was not complete or published at preregistration time, so the December effective signal was still unknown when the model was frozen.

However, the underlying source month **straddles the preregistration date**:

```
2026-10-01 ... 2026-10-18 = already occurred
2026-10-19                 = preregistration
2026-10-20 ... 2026-10-31 = post-preregistration
```

Therefore it is inaccurate to describe the December 2026 signal as being built from source months that are wholly post-preregistration.

## Evidence-quality tiers

The forward monitor now records, without changing model eligibility:

```
SOURCE_MONTH_STRADDLES_PREREGISTRATION
FULL_SOURCE_MONTHS_POST_PREREGISTRATION
SOURCE_MONTHS_INCLUDE_PRE_PREREGISTRATION
```

For the frozen NG3 schedule:

```
effective 2026-12
  FF 2026-10
  Credit 2026-11
  => SOURCE_MONTH_STRADDLES_PREREGISTRATION

effective 2027-01
  FF 2026-11
  Credit 2026-12
  => FULL_SOURCE_MONTHS_POST_PREREGISTRATION
```

So:

- December 2026 remains countable under the original preregistration;
- December 2026 must be visibly tagged as a straddling-source-month episode if it opens an episode;
- January 2027 and later are the first months whose required monthly source periods are wholly after the preregistration date.

This is an evidence-quality annotation only. It does not retroactively retune NG3.

## Monthly evidence-gap rule

Every countable prospective effective month should be frozen exactly once after the month closes.

If an entire month is missed because all eligible scheduled runs fail, that missing month cannot later be recreated with the original first-available source vintage.

Therefore the monthly snapshot book now records:

```
missing_effective_months
evidence_gaps_present
```

A later month may still be frozen, but the missing month remains permanently visible as an evidence gap.

Do not silently backfill a missed month from later revised upstream data and present it as first-successful prospective evidence.

## Episode provenance

When an episode opens, the ledger stores:

```
source_temporality_at_start
source_provenance_at_start
```

so later promotion review can distinguish:

- straddling-source-month episodes;
- fully post-preregistration-source episodes.

The original promotion-review threshold remains unchanged:

```
>= 4 complete 252-session prospective episodes
```

A future decision record must inspect the evidence-quality mix rather than pretending all prospective episodes have identical temporal purity.

## Governance

This addendum is intentionally stricter in disclosure but does not alter model behavior.

Changing the actual first countable effective month would violate the original NG3 no-retune rule and would require a new model/protocol version rather than silently editing NG3.
