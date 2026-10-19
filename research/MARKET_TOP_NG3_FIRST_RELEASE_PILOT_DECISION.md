# Market Top NG3 — 1987 First-Release PPI Pilot Decision

Status:

```
SOURCE_ENGINEERING_PILOT_PASS
FIRST_PUBLICATION_PATH = PROVEN
FINALIZED_VINTAGE_DELTA = OPEN
MODEL_VALIDATION = NOT STARTED
```

## Reproducible validation

GitHub Actions:

```
workflow: Market Top NG3 First-Release Pilot 1987
run: 39213672805
conclusion: SUCCESS
```

Artifact:

```
market-top-ng3-first-release-pilot-1987
artifact id: 12168871396
sha256: 1d1732af417fb4850c1f543257b432e4c0c1672ee880a256a6add651b11a74e8
```

The workflow is deterministic and does not depend on live FRASER availability.

## Frozen recovered case

For May 1987:

- exact initial PPI release date = 1987-06-12;
- Finished Goods first-published April level = 295.3;
- Finished Goods first-published May level = 296.2;
- reported seasonally adjusted monthly change = +0.3%;
- level-implied monthly change = +0.3048%;
- Intermediate Materials first-published April level = 311.2;
- Intermediate Materials first-published May level = 312.8;
- reported seasonally adjusted monthly change = +0.5%;
- level-implied monthly change = +0.5141%.

These values are treated as historical publication evidence, not reconstructed from today's revised BLS history.

## Revision evidence

The May 1987 historical report explicitly states that January 1987 data had been revised because late reports and respondent corrections became available.

Therefore the repository now has a concrete historical example proving that:

```
FIRST_PUBLISHED_VALUE != necessarily LATER_REVISED_VALUE
```

The January numeric delta is still open because the earlier first-published January artifact has not yet been frozen.

## Decision

The source-engineering pilot passes its narrow gate:

```
Can we recover a dated historical first-published producer-price observation?
YES
```

It does **not** pass the next gate:

```
Can we already construct a complete, numerically revision-aware 1986-1988 panel?
NO
```

and it says nothing about market-top predictive performance.

## Next gate

Before any faster NG3 model is preregistered:

1. recover period-finalized May 1987 Finished Goods and Intermediate Materials values from a later historical PPI report;
2. freeze the first-to-final revision deltas;
3. recover January 1987 first-published numeric values;
4. validate the extraction procedure over multiple months;
5. then construct the bounded 1986-1988 vintage panel.

NG3-CostPressure V1 remains closed. No V1 threshold or lag is changed.
