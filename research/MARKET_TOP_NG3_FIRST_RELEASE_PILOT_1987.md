# Market Top NG3 — 1987 First-Release PPI Source Pilot

Status:

```
PARTIAL_PASS
FIRST_PUBLICATION_VALUE_RECOVERED
EXACT_RELEASE_DATE_RECOVERED
FINALIZED_VALUE_RECOVERY_PENDING
```

Research only. This is a source-engineering pilot, not a market-top test.

## Why this pilot exists

The closed NG3-CostPressure V1 used a conservative +6-calendar-month finalized-data lag and produced too few eligible top episodes. That does **not** authorize a shorter lag on today's revised PPI history.

A faster future version must first prove that historical first-published producer-price information can actually be reconstructed.

The bounded pilot period is 1987 because the monthly PPI reports are well preserved. Calendar year 1987 remains a hypothesis-generation period and cannot validate a future top model.

## May 1987 first publication

The May 1987 Monthly Labor Review release calendar gives:

```
Producer Price Index
period covered: May
release date: June 12, 1987
```

Therefore the exact initial release date for the May PPI observation is recovered.

The PPI Detailed Report for data through May 1987 reports, seasonally adjusted:

```
Finished Goods:
April -> May = +0.3%

Intermediate Materials, Supplies, and Components:
April -> May = +0.5%
```

Its stage-of-processing table, on the 1967=100 base, gives:

```
Finished Goods:
April 1987 = 295.3
May   1987 = 296.2

Intermediate Materials:
April 1987 = 311.2
May   1987 = 312.8
```

The level-implied changes are approximately:

```
Finished Goods = +0.3048%
Intermediate   = +0.5141%
```

which are consistent with the report's rounded +0.3% and +0.5% statements.

This case is frozen as:

```
FIRST_PUBLICATION_VALUE_RECOVERED
```

## Revision contract

The same historical report states that PPI data are subject to revision four months after original publication.

Therefore the pilot stores first-published information separately from a later finalized vintage.

At this stage:

```
May 1987 first publication = RECOVERED
May 1987 finalized period vintage = RECOVERY_PENDING
numeric first-to-final revision delta = PENDING
```

Today's revised BLS history may not be substituted for the missing period-finalized vintage.

## January 1987 documented revision case

The May 1987 report explicitly states that January 1987 data had been revised to reflect late reports and respondent corrections and that some figures therefore differ from those previously reported.

This is important because it independently demonstrates that the first-published / revised distinction is economically real, not merely a theoretical concern.

However, the exact January first-published numeric values have not yet been recovered from an earlier source artifact.

Therefore January 1987 is frozen as:

```
REVISION_EVENT_CONFIRMED_NUMERIC_DELTA_PENDING
```

It cannot be used to estimate revision magnitude yet.

## Availability semantics

For May 1987, the release date is June 12, 1987.

A future genuine first-release market state may use the observation only after the actual release.

If exact intraday release time is not established, the fail-closed rule remains:

```
first usable equity state
= next U.S. trading-day close after publication date
```

No generic +1-month or +2-month lag replaces the actual dated release.

## What is and is not proved

Proved in this pilot:

- a historical first-published PPI observation can be recovered;
- the exact May 1987 initial release date can be recovered;
- finished-goods and intermediate-goods first-published changes can be reconstructed from the contemporaneous report;
- the historical four-month revision rule is documented;
- a January 1987 revision event is explicitly documented.

Not yet proved:

- a complete first-release panel;
- exact finalized May 1987 period-vintage values;
- January 1987 first-to-revised numeric deltas;
- stable automated extraction over many issues;
- any market-top predictive value.

## Next gate

The next source-engineering step is deliberately narrow:

1. recover a post-September-1987 PPI report in which May is beyond the four-month revision window;
2. unambiguously map the finished-goods and intermediate-materials May rows;
3. freeze the finalized May values;
4. calculate first-published versus finalized revision deltas;
5. recover the earlier January report needed for the explicit January revision case.

Only after those checks can the 1986-1988 pilot become a machine-readable vintage panel.

No faster NG3 formula is preregistered by this document.
