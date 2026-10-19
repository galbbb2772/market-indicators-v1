# Market Top NG3 — BEA/SCB Historical Vintage Concept Audit

Status:

```
ARCHIVED_PUBLICATION_PATH = FOUND
1974_TO_LATER_CONCEPT_IDENTITY = NOT ASSUMED
FORMULA = NOT FROZEN
```

Research only. No production effect.

## Question

Can the modern BEA NIPA Table 1.15 unit-profit series be projected backward into the 1960s/1970s and treated as if the same accounting concept had been available to an investor at the time?

Decision:

```
NO
```

The historical Survey of Current Business publications show a visible concept-label transition.

## August 1974 publication

Archived source:

```
Survey of Current Business — August 1974 Part I
FRASER / Federal Reserve Bank of St. Louis
```

In the historical nonfinancial-corporate cost-per-unit table, the profit row is labeled:

```
Corporate profits and inventory valuation adjustment
```

The same table reports current-dollar cost per unit of real nonfinancial-corporate product and its cost/profit components.

This historical row is **not labeled with the later explicit capital-consumption-adjustment concept**.

Therefore the current revised modern line-7 concept must not be silently substituted for the 1974 published concept and called genuine point-in-time evidence.

## April 1976 publication

Archived source:

```
Survey of Current Business — April 1976
FRASER / Federal Reserve Bank of St. Louis
```

The archived publication explicitly reports:

```
Corporate profits with inventory valuation and capital consumption adjustments
```

This is materially closer in accounting definition to the modern BEA unit-profit concept.

The audit therefore establishes a **concept transition by the mid-1970s**. It does not establish that every modern revised historical value equals the number originally published in 1976.

## March 1988 publication

Archived source:

```
Survey of Current Business — March 1988
FRASER / Federal Reserve Bank of St. Louis
```

The archived publication again explicitly reports:

```
Corporate profits with inventory valuation and capital consumption adjustments
```

Thus the late-1980s vintage is conceptually much closer to the modern Table 1.15 unit-profit block than the August-1974 publication.

## What the automated audit proves

The repository audit retrieves the three archived FRASER full-text publications and checks the required historical concept labels.

It is deliberately narrow.

It proves:

- the archived publication path is operational;
- the 1974 unit-table uses the IVA wording;
- 1976 and 1988 explicitly use IVA + capital-consumption-adjustment wording.

It does **not** prove:

- exact quarter-to-column mapping from OCR text;
- exact historical numerical vintage for every quarter;
- equality between a historical publication and today's revised BEA history;
- that a raw level difference is purely a statistical revision.

## Why raw level comparisons are unsafe

Even where profit concepts align, historical national-account tables can differ in benchmark revisions, price bases, deflators, classifications and later comprehensive revisions.

Therefore:

```
historical published raw unit-profit level
vs
today's revised raw unit-profit level
```

is not automatically a clean "revision error" statistic.

A safer comparison, where numerator and denominator concepts are internally consistent in the same vintage, is a scale-free within-vintage ratio such as:

```
PublishedProfitShare
  = published unit profit
    / published total current-dollar cost-and-profit per unit
```

However, the 1974 numerator concept itself differs from the later explicit IVA+CCAdj concept. A ratio does not erase that accounting-definition break.

## Frozen scientific boundary

For NG3, the following shortcut is prohibited:

```
take modern revised A463RD history
-> shift it backward with a guessed lag
-> call 1968-1974 genuine PIT margin data
```

That would introduce both revision hindsight and concept hindsight.

## Architecture consequence

NG3 will now be separated into two research blocks before any numerical formula is frozen:

### NG3-CostPressure

Long-history price/cost pressure block using source families with consistent documented historical coverage:

- CPI-U NSA;
- PPI finished goods;
- PPI processed intermediate demand;
- later, any rate control only if its own PIT contract passes.

This block may cover the older inflation regimes.

### NG3-MarginConfirm

Corporate-margin confirmation block using historical BEA/SCB vintages only where the accounting concept and publication timing are documented.

This block is **not allowed to be mandatory for an early-era state** until a defensible pre-transition bridge exists.

The split is a source-integrity decision made before model results are inspected; it is not a post-hoc performance adjustment.

## Next gate

Before numerical preregistration:

1. recover one dated 1976 publication table with unambiguous column mapping;
2. recover one dated 1987/1988 table with unambiguous column mapping;
3. calculate within-vintage profit shares from the same table;
4. compare them with corresponding modern revised ratios as a **revision diagnostic**, not as a scoring feature;
5. determine the earliest date from which the margin-confirmation concept is sufficiently stable for a frozen historical test.

Until then:

```
NG3 numerical formula = NOT FROZEN
NG3 historical performance = NOT TESTED
production effect = NONE
```
