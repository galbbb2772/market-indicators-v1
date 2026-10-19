# Market Top NG3 — 1986–1988 First-Release PPI Panel

Status:

```
ARCHIVE_COVERAGE = PASS
RELEASE_DATE_PANEL = PASS
FIRST_VALUE_PANEL = COMPLETE_SOURCE_PANEL
FINALIZED_VALUE_PANEL = IN PROGRESS
MODEL_OUTCOME_TEST = NOT AUTHORIZED
```

Research only. NG3-CostPressure V1 remains closed and is not retuned.

## Reproducible first-release checkpoint

A fully reproducible source-panel run completed successfully:

```
workflow = Market Top NG3 First-Release Panel 1986-1988
run = 39234720575
conclusion = SUCCESS
artifact = market-top-ng3-first-release-panel-1986-1988
artifact id = 12178279558
artifact sha256 = 6096416c985ce943fcac2779bca62fa40dcadd50d6be6814935dee658e09a859
```

Coverage:

```
months = 36
source PDFs recovered = 36
initial release dates recovered = 36
first values resolved = 36
ambiguous first-value rows = 0
```

Examples of recovered release dates:

```
1986-01 -> 1986-02-14
1987-01 -> 1987-02-13
1987-05 -> 1987-06-12
1987-10 -> 1987-11-13
1988-12 -> 1989-01-13
```

## Numeric source hierarchy

The printed seasonally adjusted **Table A current-month row** is now the primary numeric authority whenever all expected columns are recovered.

The headline narrative is a separate cross-check.

Resolution rule:

```
complete Table A + matching narrative
    -> VERIFIED_DUAL_PATH

complete Table A + conflicting narrative
    -> TABLE_A_PRIMARY_NARRATIVE_CONFLICT

complete Table A + incomplete narrative
    -> TABLE_A_ONLY_PROVISIONAL

incomplete Table A + complete narrative
    -> NARRATIVE_RECOVERED

neither complete
    -> AMBIGUOUS
```

This ordering was frozen before any faster-NG3 market outcome test. It prevents a prose parser error from overriding a complete printed table row.

Current source-path counts:

```
VERIFIED_DUAL_PATH = 10
TABLE_A_PRIMARY_NARRATIVE_CONFLICT = 7
TABLE_A_ONLY_PROVISIONAL = 7
NARRATIVE_RECOVERED = 12
AMBIGUOUS = 0
```

The seven cross-path conflicts are retained as diagnostics; they are not averaged. Table A wins when the complete row is available.

## Anchor checks

Previously hand-verified cases still reproduce:

```
1987-01
Finished Goods = +0.6%
Intermediate Goods = +0.9%
release = 1987-02-13

1987-05
Finished Goods = +0.3%
Intermediate Goods = +0.5%
release = 1987-06-12
```

The September 1988 regression case also explicitly prevents a 12-month Intermediate Goods change from being accepted as the current-month change.

## What is now closed

For the bounded 1986–1988 pilot, the source-engineering layer now has:

- every monthly source issue;
- every initial release date;
- one resolved first-publication Finished Goods value per month;
- one resolved first-publication Intermediate Goods value per month;
- explicit provenance/status for every row;
- regression tests for known narrative/OCR failure modes.

This is a **complete source panel**, not a predictive-model validation.

## Remaining source gate

The next task is period-finalized reconstruction.

A single later PDF parse is not trusted because isolated OCR errors can turn values such as `-.7` into `-7.0`.

The finalized-panel pipeline therefore uses repeated later historical Table A snapshots and requires at least two snapshots to agree at the published 0.1 percentage-point precision.

Only after the finalized panel passes can first-to-final revision deltas be frozen.

## Research boundary

Still prohibited:

```
FASTER_NG3_PREREGISTRATION = NO
MARKET_TOP_OUTCOME_SCREEN = NO
POST_RESULT_THRESHOLD_TUNING = NO
PRODUCTION_EFFECT = NONE
```

The next valid gate is:

```
complete finalized 1986–1988 panel
-> freeze revision distribution
-> decide whether first-release source quality is sufficient
-> preregister a separately named faster NG3 candidate
-> only then run outcomes
```
