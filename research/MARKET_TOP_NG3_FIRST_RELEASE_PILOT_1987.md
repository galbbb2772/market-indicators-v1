# Market Top NG3 — 1987 First-Release PPI Source Pilot

Status:

```
PASS
FIRST_PUBLICATION_VALUE_RECOVERED
EXACT_RELEASE_DATE_RECOVERED
FIRST_TO_FINAL_REVISION_DELTA_RECOVERED
MODEL_VALIDATION_NOT_STARTED
```

Research only. This is a source-engineering pilot, not a market-top test.

## Why this pilot exists

The closed NG3-CostPressure V1 used a conservative +6-calendar-month finalized-data lag and produced too few eligible top episodes. That does **not** authorize a shorter lag on today's revised PPI history.

A faster future version must first prove that historical first-published producer-price information and the later period-finalized vintage can actually be reconstructed.

Calendar year 1987 remains a hypothesis-generation period and cannot validate a future top model.

## May 1987 first publication

The May 1987 release calendar gives:

```
Producer Price Index
period covered: May
release date: 1987-06-12
```

The contemporaneous PPI Detailed Report reports, seasonally adjusted:

```
Finished Goods: +0.3%
Intermediate Materials, Supplies, and Components: +0.5%
```

Its stage-of-processing table on the 1967=100 base gives:

```
Finished Goods
April 1987 = 295.3
May   1987 = 296.2
implied change = +0.3048%

Intermediate Materials
April 1987 = 311.2
May   1987 = 312.8
implied change = +0.5141%
```

The level-implied changes are consistent with the published rounded +0.3% and +0.5%.

## May 1987 period-finalized vintage

The March 1988 PPI Detailed Report is well beyond the documented four-month revision window for a May 1987 observation.

Its historical tables report the seasonally adjusted May 1987 monthly changes as:

```
Finished Goods = -0.1%
Intermediate Goods Total = +0.5%
```

The finished-goods number comes from Table B, whose column is explicitly Finished Goods.

The intermediate-goods number comes from Table A's Intermediate goods — Total series.

Therefore the first-published versus period-finalized comparison is:

```
Finished Goods
first published = +0.3%
period finalized = -0.1%
revision delta = -0.4 percentage points

Intermediate Materials
first published = +0.5%
period finalized = +0.5%
revision delta = 0.0 percentage points
at the publication's 0.1pp reporting precision
```

This is a material result for the data architecture: at least one headline stage-of-processing PPI signal in the pilot changes sign between first publication and the later finalized historical table.

## Why percent changes are used for the revision delta

The PPI underwent reference-base changes around this period. Raw index levels from reports using different bases should not be compared mechanically.

The pilot therefore freezes the first-to-final diagnostic using the published seasonally adjusted month-over-month percentage changes, which are scale-free.

The final values are labeled:

```
RECOVERED_AT_PUBLISHED_0_1PP_PRECISION
```

No extra precision is invented.

## January 1987 documented revision case

The May 1987 report explicitly states that January 1987 data had been revised to reflect late reports and respondent corrections.

January remains:

```
REVISION_EVENT_CONFIRMED_NUMERIC_DELTA_PENDING
```

because the earlier first-published January numbers have not yet been frozen from the initial report.

## Availability semantics

For May 1987, the initial release date is 1987-06-12.

A future genuine first-release market state may use the observation only after the actual release. If exact intraday release time is not established, the fail-closed rule remains:

```
first usable equity state
= next U.S. trading-day close after publication date
```

No generic +1-month or +2-month lag replaces an actual dated release.

## What is now proved

- a historical first-published PPI observation can be recovered;
- the exact May 1987 initial release date can be recovered;
- first-published finished/intermediate changes can be reconstructed;
- a later report beyond the revision window can recover period-finalized May values;
- a first-to-final numerical revision delta can be measured without using today's revised BLS history;
- Finished Goods changed from +0.3% to -0.1% in this pilot;
- Intermediate Materials remained +0.5% at published 0.1pp precision.

Still not proved:

- January 1987 first-to-final numeric delta;
- a complete 1986-1988 vintage panel;
- stable automated extraction across many issues;
- any market-top predictive value.

## Next gate

1. recover the January 1987 initial publication values;
2. repeat first-to-final extraction for additional 1986-1988 months;
3. build a bounded machine-readable vintage panel;
4. validate the panel against manually checked publication tables;
5. only then preregister any faster NG3 model before looking at outcomes.

NG3-CostPressure V1 remains closed. No V1 threshold or lag is changed.
