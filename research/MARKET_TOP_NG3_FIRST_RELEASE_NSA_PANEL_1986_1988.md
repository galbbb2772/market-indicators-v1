# Market Top NG3 — 1986–1988 First-Release NSA PPI Panel

Status:

```
ARCHIVE_COVERAGE = PASS
RELEASE_DATE_PANEL = PASS
FIRST_RELEASE_NSA_PANEL = PASS
AMBIGUOUS_ROWS = 0
FASTER_NG3_FORMULA = NOT PREREGISTERED
MARKET_OUTCOME_TEST = NOT AUTHORIZED
PRODUCTION_EFFECT = NONE
```

Research only. NG3-CostPressure V1 remains closed and unchanged.

## Reproducible checkpoint

```
workflow = Market Top NG3 First-Release NSA Panel 1986-1988
run = 39238392645
conclusion = SUCCESS
head = 3e1851bbe07d84d59b4bc9af26bb36e6efc61e7d
artifact = market-top-ng3-first-release-nsa-panel-1986-1988
artifact id = 12180486118
artifact sha256 = 3a9f8e4cbe9e78cf1f757eb28bb29c4bccf3591d123c694b536caf586d34e53d
```

Coverage:

```
months = 36
source reports recovered = 36
Table 1 pages found = 36
release dates recovered = 36
complete first-release NSA rows = 36
ambiguous rows = 0
```

## Source definition

The panel uses the contemporaneous PPI Detailed Report aggregate **Table 1 — Producer price indexes and percent changes by stage of processing**.

For each observation month it retains:

- documented initial release date;
- Finished Goods current-month NSA level;
- Finished Goods NSA year-over-year change;
- Intermediate Materials, Supplies and Components current-month NSA level;
- Intermediate Materials NSA year-over-year change;
- source PDF and printed-table provenance.

The values are taken from the information set published at the time. They are not reconstructed from today's revised BLS history.

## Why NSA is the frozen research path

NG3-CostPressure V1 was defined from not-seasonally-adjusted BLS indexes and 12-month changes.

BLS distinguishes ordinary PPI respondent/late-report revisions from annual seasonal-factor revisions. Therefore historical seasonally-adjusted month-over-month tables are retained only as source/parser diagnostics. A faster V1-aligned branch must use first-published NSA levels / NSA YoY.

## Parser integrity

Historical PDFs are not layout-stable. The source pipeline therefore uses PDF text coordinates rather than flattening the table to whitespace-separated text.

Guardrails include:

- ignore small-font superscript footnotes;
- map printed columns by x-coordinate;
- fail closed on duplicate/ambiguous numeric cells;
- support PDFs that emit several printed cells in one text object;
- use structural Table 1 fingerprints when its title is lost in text extraction;
- recover an OCR-corrupted aggregate label only from the printed 100.000 relative-importance stage rows and fixed Table 1 stage order;
- keep anchor checks independent of market outcomes.

The last unresolved source row was May 1988 Finished Goods. Its printed numeric row survived intact but the aggregate text label was OCR-corrupted. The fallback recovers the top 100.000 stage row as Finished Goods. The reconstructed row is:

```
1988-05
release = 1988-06-10
Finished Goods NSA level = 107.5
Finished Goods NSA YoY = 2.0%
Intermediate NSA level = 106.2
Intermediate NSA YoY = 5.3%
```

## Anchor checks

All frozen anchor checks passed, including:

```
1986-02
Finished Goods NSA level = 292.3
Finished Goods NSA YoY = -0.1%

1987-05
release = 1987-06-12
Finished Goods NSA level = 296.3
Finished Goods NSA YoY = 2.6%
Intermediate NSA level = 312.7
Intermediate NSA YoY = 2.0%

1988-03
Intermediate NSA level = 104.6
Intermediate NSA YoY = 5.0%
```

The panel also captures the 1988 reference-base transition directly from contemporaneous publications; no rebasing is required for the same-publication YoY percentages.

## What this closes

For the bounded 1986–1988 source-engineering pilot, we now have a complete point-in-time producer-price panel with exact release dates and V1-aligned NSA/YoY information.

This closes the **first-release PPI source availability gate** for the pilot period.

It does not yet validate a top model.

## Next gate

Before any faster NG3 outcome test:

1. document the historical stage-of-processing concept bridge to the modern BLS series used by V1;
2. align CPI publication timing with the PPI publication date so every monthly state uses only information actually available at the first usable equity close;
3. freeze the new first-release formula, percentile history, warm-up, threshold, market-location rule and evaluation windows in a separately named preregistration;
4. only after that commit may market outcomes be generated.

Still prohibited:

```
use current revised BLS history as first-release PIT = NO
use SA MoM panel as V1 substitute = NO
tune threshold after viewing outcomes = NO
reuse 1987 as validation = NO
production inclusion = NO
```
