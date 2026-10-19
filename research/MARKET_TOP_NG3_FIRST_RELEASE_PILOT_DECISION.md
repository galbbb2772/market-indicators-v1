# Market Top NG3 — 1987 First-Release PPI Pilot Decision

Status:

```
SOURCE_ENGINEERING_PILOT_PASS
FIRST_PUBLICATION_PATH = PROVEN
FIRST_TO_FINAL_REVISION_DELTA = RECOVERED
MODEL_VALIDATION = NOT STARTED
```

## Reproducible boundary

The deterministic workflow protects the historical first-publication contract. The pilot is now extended with a later historical PPI report beyond the four-month revision window.

For May 1987:

```
initial release date = 1987-06-12

Finished Goods
first published = +0.3%
period finalized = -0.1%
delta = -0.4pp

Intermediate Materials
first published = +0.5%
period finalized = +0.5%
delta = 0.0pp at published 0.1pp precision
```

The later values are taken from the March 1988 PPI Detailed Report, not from today's revised BLS history.

This closes the previously open May-1987 period-finalized value and revision-delta tasks.

## Interpretation

The pilot now proves that a historical first-release/finalized split is not merely theoretical. In the finished-goods headline series, the published May monthly signal changes sign between the first report and the period-finalized historical table.

Therefore any future faster NG3 candidate must explicitly choose and preserve its information set:

- FR1 = first publication, usable only after its actual release;
- FINAL = later finalized historical vintage.

These are different research inputs and must never be mixed silently.

## What remains open

January 1987 is still an explicitly documented revision event, but its original first-published numeric values have not yet been frozen.

A complete 1986-1988 panel also does not yet exist.

Therefore:

```
complete vintage panel = NO
faster NG3 preregistration = NO
market-top validation = NO
```

## Next gate

1. recover January 1987 first-published finished/intermediate values;
2. extend the same first-to-final process across additional months;
3. validate multiple month/table mappings;
4. build the bounded 1986-1988 vintage panel;
5. only then preregister a new faster NG3 candidate before outcomes.

NG3-CostPressure V1 remains closed and unchanged.
