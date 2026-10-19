# Market Top NG3 — 1987 First-Release PPI Source Pilot

Status:

```
PASS
TWO_MONTH_REVISION_CASES_RECOVERED
MAY_DIRECT_FIRST_PUBLICATION_RECOVERED
JANUARY_PRE_REVISION_CARRY_FORWARD_RECOVERED
MODEL_VALIDATION_NOT_STARTED
```

Research only. This is a source-engineering pilot, not a market-top test.

## Why this pilot exists

NG3-CostPressure V1 used a conservative +6-calendar-month finalized-data lag and produced too few eligible top episodes. That result does not authorize shortening the lag on today's revised PPI history.

A faster future version must preserve the information set that actually existed at the time.

Calendar year 1987 remains hypothesis-generation evidence and cannot validate a future top model.

## January 1987 — pre-revision and four-month revision values

The official 1987 BLS schedule gives:

```
Producer Price Index
January observation
initial release date = 1987-02-13
```

The February 1987 PPI report states that January had:

```
Finished Goods = +0.6%
Intermediate Materials = +0.9%
```

This February report is important for provenance: its revision footnote refers to October 1986, not January 1987.

The later May-data report explicitly states that **January 1987 data were revised** because of late reports and respondent corrections. In that revised table:

```
Finished Goods January = +0.4%
Intermediate Materials January = +0.9%
```

Therefore, at the published 0.1 percentage-point precision:

```
Finished Goods
pre-revision = +0.6%
four-month revision = +0.4%
delta = -0.2pp

Intermediate Materials
pre-revision = +0.9%
four-month revision = +0.9%
delta = 0.0pp
```

### January provenance boundary

The January pre-revision numbers are recovered from the next monthly report before the later documented January revision. They are not claimed to have been parsed directly from the January issue table.

The frozen label is therefore:

```
PRE_REVISION_CARRY_FORWARD
```

rather than an unsupported claim of exact first-issue byte recovery.

## May 1987 — direct first publication

The May 1987 release date is:

```
1987-06-12
```

The contemporaneous May report gives, seasonally adjusted:

```
Finished Goods = +0.3%
Intermediate Materials = +0.5%
```

Its 1967=100 table gives:

```
Finished Goods
April = 295.3
May   = 296.2
level-implied change = +0.3048%

Intermediate Materials
April = 311.2
May   = 312.8
level-implied change = +0.5141%
```

which agrees with the rounded published changes.

## May 1987 — period-finalized vintage

The March 1988 PPI report is well beyond the four-month revision window for May 1987.

Its historical tables give:

```
Finished Goods May 1987 = -0.1%
Intermediate Goods Total May 1987 = +0.5%
```

Therefore:

```
Finished Goods
first published = +0.3%
period finalized = -0.1%
delta = -0.4pp

Intermediate Materials
first published = +0.5%
period finalized = +0.5%
delta = 0.0pp
```

The finished-goods signal changes sign. This is direct evidence that first-release and finalized PPI information cannot be mixed silently.

## Why published percent changes are the revision diagnostic

Reference bases changed around this era. Comparing raw index levels across differently based historical tables can create false revision estimates.

The pilot therefore compares the published seasonally adjusted month-over-month percentage changes and preserves their 0.1pp publication precision.

No extra precision is invented.

## Availability semantics

A genuine first-release market state may use an observation only after its actual release date.

Where exact intraday release time is unavailable, the fail-closed rule remains:

```
first usable equity state
= next U.S. trading-day close after publication date
```

## What is now proved

- January 1987 exact release date is recovered;
- January pre-revision Finished/Intermediate values are recovered from a pre-revision report;
- January's later revision event and numeric deltas are recovered;
- May direct first-publication values and exact release date are recovered;
- May period-finalized historical values are recovered;
- the first-to-final delta can be material enough to reverse the sign of a headline monthly PPI move;
- all evidence remains source engineering only.

Still not proved:

- a complete 1986-1988 vintage panel;
- a robust automated parser across many historical layouts;
- any market-top predictive value.

## Next gate

1. extend the same evidence structure to additional 1986-1988 months;
2. prefer direct initial-issue tables when recoverable;
3. validate several manual month mappings against the structured panel;
4. build the bounded 1986-1988 first-release/finalized panel;
5. only then preregister a faster NG3 candidate before outcome testing.

NG3-CostPressure V1 remains closed and unchanged.
