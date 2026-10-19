# Market Top NG3 — First-Release PPI Source Feasibility

Status: SOURCE_PATH_FOUND / FULL_VINTAGE_PANEL_NOT_YET BUILT / RESEARCH ONLY.

This work follows the closed NG3-CostPressure V1 screen. V1 is not retuned. The purpose here is to determine whether a separately named future first-release candidate can be built from data that actually existed at the time.

## Why this is a new data problem

NG3-CostPressure V1 used a conservative finalized-data convention: source month + 6 calendar months.

The screen showed that the largest cost-pressure scores often appeared only after the independent top-location gate had already failed.

A scientifically valid faster version therefore requires historical first-published producer-price vintages. It is not valid to take today's revised BLS history and simply shorten the lag.

## Archive coverage map

### Modern BLS Detailed Report archive

BLS's current PPI Detailed Report archive explicitly describes historical records from 2005 to current.

It also states that PPI indexes are subject to monthly revisions for up to four months after originally scheduled publication.

Therefore current BLS web archives are directly useful for post-2005 first-release reconstruction, but they do not by themselves solve the pre-2005 history.

Source:
https://www.bls.gov/ppi/detailed-report/

### FRASER PPI Detailed Report

FRASER preserves the PPI Detailed Report series from 1978 onward.

Its title history documents the publication-name sequence:

- Producer Prices and Price Indexes, March 1978 through December 1984;
- Producer Price Indexes, January 1985 onward.

The archive contains monthly 1987 issues and earlier issues beginning in March 1978.

Examples:
https://fraser.stlouisfed.org/title/ppi-detailed-report-63?browse=1980s
https://fraser.stlouisfed.org/title/ppi-detailed-report-63/may-1987-21618/fulltext

The May 1987 report explicitly says January 1987 data had been revised because of late reports and respondent corrections. This proves that extracting the current-month observation from the contemporaneous report and separately tracking later revisions is the correct vintage-aware approach.

### Pre-1978 wholesale-price archive

Before the PPI renaming, the relevant stage-of-processing concepts existed under the Wholesale Price Index.

FRASER preserves the Federal Reserve G.8 "Index Numbers of Wholesale Prices" monthly release from 1955 through June 1978.

Publication-history evidence states:

- G.8 was monthly;
- it ended in June 1978;
- most G.8 data were provided by the Bureau of Labor Statistics.

Specific dated 1974 issues are preserved, including:

- January 25, 1974;
- May 29, 1974;
- July 18, 1974.

Sources:
https://fraser.stlouisfed.org/title/g8-index-numbers-wholesale-prices-3936
https://fraser.stlouisfed.org/title/g8-index-numbers-wholesale-prices-3936/january-25-1974-484344
https://fraser.stlouisfed.org/title/g8-index-numbers-wholesale-prices-3936/may-29-1974-484347
https://fraser.stlouisfed.org/title/g8-index-numbers-wholesale-prices-3936/july-18-1974-484348

A contemporaneous federal publication on statistical-release schedules describes G.8 as approximately a 20th-of-month release referring to the previous month. Actual issue dates must still be used when available rather than replacing them with the approximation.

### Stage-of-processing continuity

Contemporaneous 1970s publications explicitly report:

- Intermediate materials;
- Producer finished goods.

The September 1975 CPI Detailed Report, for example, contains Wholesale Price Index stage-of-processing rows for intermediate materials and producer finished goods.

The January 1974 Economic Indicators issue likewise reports intermediate materials and producer finished goods.

These are the historical concepts needed for a future first-release cost-pressure panel.

They must not be assumed numerically identical to today's FD-ID series without a documented bridge.

### ALFRED limitation

ALFRED is useful for real-time vintages but describes itself as economic-data time travel since 2006.

Therefore ALFRED cannot by itself recover genuine 1960s-1980s first-release PPI/WPI vintages.

It remains useful as an independent post-2006 cross-check.

## Concept bridge required

A future first-release model must use native historical stage-of-processing concepts rather than silently substituting modern series identifiers.

Provisional eras:

1. 1955 through February 1978:
   - wholesale-price publication regime;
   - use contemporaneously published intermediate materials and producer finished goods.

2. March 1978 onward:
   - PPI publication regime;
   - use contemporaneous stage-of-processing finished/intermediate goods from monthly PPI reports.

3. modern FD-ID era:
   - retain an explicit mapping layer to current finished-goods and processed-intermediate-demand concepts.

The mapping layer is a research artifact, not a performance parameter.

## Release-time semantics

A future first-release observation may affect the equity state only on or after the first U.S. equity close following the documented publication date/time.

Where only a publication date is available and intraday time is not documented, the fail-closed convention is:

first usable state = next U.S. trading-day close after publication date.

No observation-month-based guessed +1/+2 lag is authorized when an actual dated publication exists.

## Revision semantics

For each source observation, a future vintage panel should retain at least:

- observation month;
- publication date;
- value as first published;
- value in each identifiable revision during the four-month revision window;
- final/four-month-later value when recoverable;
- source publication and page/table provenance;
- historical concept label.

This enables two separate studies:

- FR1: first-published information;
- FINAL: finalized information.

The closed V1 +6-month result remains the finalized-data reference and is not overwritten.

## Feasibility decision

The archive path is sufficient to justify building a first-release vintage panel:

FIRST_RELEASE_SOURCE_FEASIBILITY = PASS_IN_PRINCIPLE.

But:

FULL_FIRST_RELEASE_PANEL = NOT YET BUILT.

No faster NG3 score, lag or threshold is preregistered yet.

## Next implementation gate

Before any first-release outcome test:

1. build a machine-readable vintage panel for a bounded pilot period;
2. start with 1986-1988 because monthly PPI Detailed Reports are well preserved and the known 1987 episode is hypothesis-generation only;
3. extract first-published finished-goods and intermediate-goods observations plus publication dates;
4. compare with later revised values from subsequent reports;
5. validate the parser on manually checked months;
6. only then extend backward into the G.8 wholesale-price era.

The pilot is a source-engineering test only. It must not be used to claim market-top validation.
