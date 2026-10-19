# Market Top NG3-CostPressure — First Historical Screen Decision

Status: NG3_COSTPRESSURE_V1_CLOSED_INSUFFICIENT_SCREEN_EVENTS.

The preregistered screen ran successfully without changing the frozen formula, threshold, lag, location gate, windows or outcome rules.

## Reproducible run

GitHub Actions run: 39212213028.

Workflow conclusion: SUCCESS.

Artifact: market-top-ng3-costpressure-screen.

Artifact id: 12168052479.

Artifact SHA-256: a0b4d70fed744f8c41e71d2f95c873508d01848ef1129ac965c94bab7bdc3f0b.

Coverage:

- 708 valid transformed source rows;
- 487 screened effective-month states;
- first screened state: 1958-06;
- last screened state: 2006-12.

The first state is later than the nominal 1957 window start because the frozen 120-valid-month warm-up and +6-month effective lag are enforced.

## Frozen candidate result

NG3-CostPressure produced only one complete ARMED episode:

- start/end: 2006-03;
- CostPressure_NG3 at start: 85.831479;
- classification: CLEAR_TOP_FALSE_POSITIVE;
- worst return from the signal over 252 sessions: -5.497081%.

Candidate summary:

- complete episodes: 1;
- major-top hits: 0;
- correction-risk episodes: 0;
- clear false-top episodes: 1;
- major fraction: 0.00;
- false fraction: 1.00.

Under the preregistered rule, fewer than three complete candidate episodes means:

INSUFFICIENT_SCREEN_EVENTS.

The result is not converted to a pass or a different failure class after seeing the data.

## Baselines

Inflation-only:

- complete episodes: 4;
- major-top hits: 0;
- correction-risk: 1;
- clear false positives: 3;
- major fraction: 0.00;
- false fraction: 0.75.

Producer-gap:

- complete episodes: 6;
- major-top hits: 0;
- correction-risk: 0;
- clear false positives: 6;
- major fraction: 0.00;
- false fraction: 1.00.

Top-location only:

- complete episodes: 39;
- major-top hits: 3;
- correction-risk: 6;
- clear false positives: 30;
- major fraction: 0.076923;
- false fraction: 0.769231.

The NG3 candidate therefore also fails the frozen incremental-value gate against the two score baselines.

## Post-result mechanism diagnostic

This diagnostic does not change the decision or parameters.

The largest CostPressure scores in the screened sample occur immediately after the excluded 1968-1974 hypothesis-generation regime, once the market is already far from its recent high:

- 1975-01: 100.000, TopLocationGate false;
- 1975-04: 100.000, TopLocationGate false;
- 1975-05: 100.000, TopLocationGate false;
- 1975-06: 99.381, TopLocationGate false;
- 1975-03: 98.738, TopLocationGate false;
- 1975-02: 98.417, TopLocationGate false.

This is important because the frozen finalized-data convention delays a source month by six calendar months.

The evidence is consistent with a structural timing problem: the cost-pressure information can become extreme only after the market has already moved far enough from the top that the independently frozen location gate rejects it.

This is a diagnostic statement, not permission to shorten the lag.

Among screened months where TopLocationGate is true, the highest candidate scores include:

- 2006-03: 85.8315, the sole ARMED false positive;
- 2006-04: 84.7252;
- 2006-07: 83.0849;
- 2006-12: 81.0441;
- 1979-09: 77.8791;
- 1980-08: 76.5767.

## Decision

NG3-CostPressure V1 is not promoted.

Do not:

- lower 85;
- shorten the +6-month finalized-data lag inside V1;
- remove TopLocationGate;
- change the geometric formula;
- add MarginConfirm to rescue the result;
- count 1968-1974 or 1987 as validation observations.

Production scoring remains unchanged.

## Next scientifically valid branch

The result identifies a legitimate next research question, but it requires a new data contract rather than a parameter tweak.

A faster candidate may only be studied as a separately named first-release version after historical PPI publication vintages are reconstructed.

That future branch must distinguish:

- first-published PPI observations;
- subsequent revisions;
- exact release dates / first usable equity close;
- current revised BLS history.

It may not simply take today's revised PPI history, reduce +6 to +1 or +2 months, and call that point-in-time.

Until a first-release PPI vintage pipeline is demonstrated, NG3-CostPressure V1 remains closed with no promotion.
