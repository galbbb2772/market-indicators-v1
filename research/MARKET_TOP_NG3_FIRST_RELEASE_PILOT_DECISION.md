# Market Top NG3 — 1987 First-Release PPI Pilot Decision

Status:

```
SOURCE_ENGINEERING_PILOT_PASS
TWO_MONTH_REVISION_CASES = RECOVERED
MODEL_VALIDATION = NOT STARTED
```

## January 1987

Official release date:

```
1987-02-13
```

The February report carries January's pre-revision values:

```
Finished Goods = +0.6%
Intermediate Materials = +0.9%
```

A later May-data report explicitly says January 1987 was revised for late reports and respondent corrections and gives:

```
Finished Goods = +0.4%
Intermediate Materials = +0.9%
```

Frozen revision diagnostic:

```
Finished Goods delta = -0.2pp
Intermediate Materials delta = 0.0pp
```

The pre-revision values are labeled PRE_REVISION_CARRY_FORWARD because the evidence comes from the next monthly report before the documented revision, rather than a directly parsed January issue table.

## May 1987

Initial release date:

```
1987-06-12
```

Direct first publication:

```
Finished Goods = +0.3%
Intermediate Materials = +0.5%
```

Period-finalized values from the March 1988 historical tables:

```
Finished Goods = -0.1%
Intermediate Materials = +0.5%
```

Frozen revision diagnostic:

```
Finished Goods delta = -0.4pp
Intermediate Materials delta = 0.0pp
```

The finished-goods May signal changes sign.

## Decision

The source-engineering pilot now has two numerically recovered 1987 revision cases.

This is enough to demonstrate that:

```
first-release information
and
period-finalized information
```

are distinct datasets and must have separate versioned pipelines.

It is not enough to validate a faster top model.

## What remains open

- broader 1986-1988 month coverage;
- direct initial-issue recovery for cases currently supported by pre-revision carry-forward;
- automated parser validation over changing historical table layouts;
- any market-top outcome test.

Therefore:

```
complete 1986-1988 vintage panel = NO
faster NG3 preregistration = NO
market-top validation = NO
```

## Next gate

Build the bounded 1986-1988 source panel with explicit per-month provenance, publication date, first/pre-revision value, later finalized value, and revision delta.

Only after that panel passes source-integrity tests may a new faster NG3 formula be preregistered.

NG3-CostPressure V1 remains closed and unchanged.


## Reproducible validation

Latest deterministic contract run:

```
workflow = Market Top NG3 First-Release Pilot 1987
run = 39214748917
conclusion = SUCCESS
artifact = market-top-ng3-first-release-pilot-1987
artifact id = 12168599810
sha256 = 8e299b613023d1fdc574fd97a47cabed69ea1f56095ecd177e2cf71403fa443f
```

This run validates both frozen January and May revision cases while preserving the research-only boundary.
