# Market Top NG3 — Source Coverage / PIT Feasibility Audit

Status:

```
BLS_COVERAGE_PASS
BEA_CURRENT_COVERAGE_PASS
BEA_EXACT_VINTAGE_AUTOMATION_NOT_YET_PROVEN
FORMULA_NOT_FROZEN
```

Research only. No production effect.

## Executed coverage audit

GitHub Actions run:

```
39209452843
conclusion = SUCCESS
```

The BLS Public Data API was queried over the full 1947-01 through 1992-12 research window.

| Role | BLS series | First | Last | Missing months |
|---|---|---:|---:|---:|
| CPI-U all items, NSA | CUUR0000SA0 | 1947-01 | 1992-12 | 0 |
| Finished goods PPI, NSA | WPUFD49207 | 1947-01 | 1992-12 | 0 |
| Processed goods for intermediate demand, NSA | WPUID61 | 1947-01 | 1992-12 | 0 |

This closes the basic frequency/coverage question for the price side of NG3.

## Why WPUID61 is used

The historical SOP series:

```
WPUSOP2000
Intermediate materials, supplies and components
```

is discontinued.

BLS's official SOP -> FD-ID concordance maps:

```
SOP2000 -> ID61
```

which gives the current unadjusted identifier:

```
WPUID61
Processed goods for intermediate demand
```

BLS also states that goods indexes corresponding to old SOP series retain long historical coverage.

The first audit attempted the discontinued public-API identifier directly and received no pre-1993 observations. The audit was therefore corrected to use the official current concordant series instead of silently sourcing a third-party reconstruction.

## CPI revision boundary

The candidate CPI input is deliberately:

```
CUUR0000SA0
CPI-U, U.S. city average, all items, not seasonally adjusted
```

BLS states that CPI-U and CPI-W are final when issued, except rare corrections.

Therefore CPI-U NSA is structurally suitable for point-in-time work without the five-year seasonal-factor revision problem attached to seasonally adjusted CPI.

A historical implementation still needs a release-date gate; observation month alone is not enough.

## PPI revision boundary

BLS states that PPI indexes may be revised for up to four months after first publication.

Therefore current-history PPI values cannot automatically be described as exact first-release point-in-time values.

Two acceptable future implementations are:

1. reconstruct first-published/interim vintage observations from BLS historical release material; or
2. use a preregistered conservative availability rule that waits until the index is final, approximately four months after initial publication.

The second choice sacrifices lead time but is much easier to make genuinely non-lookahead.

No decision between these is made in this audit.

## BEA margin source

The preferred corporate-margin block is now BEA NIPA Table 1.15:

```
Price, Costs, and Profit Per Unit of Real Gross Value Added
of Nonfinancial Domestic Corporate Business
```

The useful lines include:

```
line 1: price per unit of real gross value added
line 2: unit labor cost
line 3: unit nonlabor cost
line 7: corporate profits with IVA and CCAdj
        (unit profits from current production)
line 9: profits after tax with IVA and CCAdj
```

Quarterly Table 1.15 coverage extends back to 1947 Q1, so it covers the intended 1968-74 and 1987 research episodes.

This is superior to inventing a custom profit/GVA ratio when BEA already publishes unit-profit and unit-cost measures.

## BEA revision / vintage boundary

Current BEA NIPA history is revised history.

BEA explicitly publishes previously published estimates and historical Survey of Current Business tables, which proves that vintage-aware reconstruction is possible in principle.

However, automated exact-vintage reconstruction of Table 1.15 for the complete 1947-1992 sample has not yet been demonstrated in this repository.

The table numbering also changed historically: older Survey of Current Business material used Table 7.15 for the analogous price/cost/profit-per-unit table.

Therefore:

```
current BEA Table 1.15 coverage = PASS
exact historical PIT vintage pipeline = OPEN
```

No model is allowed to use today's revised 1947-1992 BEA unit-profit values while labeling them as genuine contemporaneous observations.

## Source decision

Price-side feasibility:

```
PASS
```

Margin-side coverage:

```
PASS
```

Margin-side exact-vintage automation:

```
NOT YET PROVEN
```

Overall:

```
NG3_SOURCE_FEASIBILITY = PARTIAL_PASS
```

## Next gate

Do not freeze an NG3 score formula yet.

The next research task is a targeted BEA vintage audit:

- demonstrate that historical Table 7.15 / 1.15 snapshots can be recovered at dated publication points;
- test at least one 1970s vintage and one 1980s vintage;
- compare those published values with today's revised history;
- quantify revision magnitude;
- decide whether NG3 should use genuine vintage BEA data or a deliberately delayed/finalized margin input.

Only after that decision is frozen should the numerical NG3 formula, thresholds and validation windows be preregistered.
