# Market Top NG3 — 1986–1988 First-Release PPI Panel: Source-Engineering Checkpoint

Status:

```
ARCHIVE_COVERAGE = PASS
RELEASE_DATE_PANEL = PASS
FIRST_VALUE_EXTRACTION = PARTIAL
FINALIZED_VALUE_PANEL = NOT BUILT
MODEL_OUTCOME_TEST = NOT AUTHORIZED
```

Research only. NG3-CostPressure V1 remains closed and is not retuned.

## Reproducible checkpoint

GitHub Actions run:

```
39229612648
workflow = Market Top NG3 First-Release Panel 1986-1988
conclusion = SUCCESS
artifact = market-top-ng3-first-release-panel-1986-1988
artifact id = 12175408387
artifact sha256 = c4e21ae984b3fcab1b95af7dd48ef9b1ec9794288e3ac8932f562658a38d722a
```

The workflow retrieved every monthly PPI Detailed Report PDF for 1986-01 through 1988-12 from the FRASER archive.

```
months requested = 36
source PDFs recovered = 36
source PDFs unavailable = 0
```

It also reconstructs exact scheduled initial release dates by reading the release-calendar tables printed in the historical reports. All 36 observation months received a dated release.

Examples:

```
1986-01 -> 1986-02-14
1987-01 -> 1987-02-13
1987-05 -> 1987-06-12
1987-10 -> 1987-11-13
1988-12 -> 1989-01-13
```

The dated-release layer therefore closes the previous guessed-lag problem for this bounded pilot period.

## First-publication value extraction

The first parser pass recovered both seasonally adjusted headline stage-of-processing changes for 18 of 36 months and marked the other 18 AMBIGUOUS rather than guessing.

The parser is fail-closed:

```
ambiguous historical text != zero
ambiguous historical text != inferred value
```

The previously frozen manual cases are reproduced exactly:

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

Those two cases are the independent anchor checks. Other automatically parsed values remain provisional until a second extraction path or manual table cross-check agrees.

## Parser limitation found

Historical PDF/OCR layout changes materially across the 36 issues.

In particular:

- the lead paragraph sometimes uses `Intermediate Goods` rather than the full `Intermediate Materials, Supplies, and Components` title;
- some reports insert `domestic producers` into the sentence;
- line-wrap hyphenation can split words such as `per-cent`;
- an overly broad match can accidentally capture a 12-month change rather than the current-month change.

This is a source-engineering issue, not a model signal.

The parser has therefore been revised to prefer the earliest current-report intermediate-goods statement rather than a later detailed-section match. No market outcome has been consulted in making this change.

## What this checkpoint proves

The 1986–1988 historical first-release source path is not merely theoretical anymore:

- all 36 source issues are machine retrievable;
- all 36 initial release dates can be reconstructed from contemporaneous schedules;
- known first-release values can be reproduced;
- parser ambiguity can be surfaced explicitly instead of silently filled.

## What it does not prove

This checkpoint does **not** establish:

- a complete validated 36-month first-value panel;
- a complete finalized/revision panel;
- a faster NG3 score;
- a shorter lag;
- a threshold;
- market-top predictive value.

No price outcomes are read by this workflow.

## Next gate

1. resolve the remaining first-value ambiguities using the current-report lead paragraph and Table A as independent extraction paths;
2. require agreement between the two paths or label the month AMBIGUOUS;
3. recover each month's value after the historical four-month revision window;
4. freeze first-to-final revision deltas for the complete 1986–1988 panel;
5. only then preregister a separately named first-release NG3 candidate.

Until those steps pass:

```
FASTER_NG3_PREREGISTRATION = NO
HISTORICAL_OUTCOME_SCREEN = NO
PRODUCTION_EFFECT = NONE
```
