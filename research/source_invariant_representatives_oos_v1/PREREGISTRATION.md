# Source-Invariant Representative Factors — Prospective OOS V1

Status: **preregistered / observation-only / no production effect**.

Frozen on 2026-10-05 after the dependence-aware historical screening was rerun with the historical panel frozen through the last completed U.S. session, **2026-10-02**.

Historical screening is explicitly post-discovery and does **not** count as prospective evidence.

## Frozen historical cutoff

- Historical development / screening cutoff: `2026-10-02`.
- Only market dates strictly greater than `2026-10-02` may enter the prospective ledger.
- The incomplete/intraday 2026-10-05 observation was excluded from the historical screening.

## Frozen candidates

Exactly three singleton source-invariant components passed every historical screening gate after the cutoff correction.

### Candidate A — Utilities Volatility

- component key: `fear_volatility::c15`
- member: `sector_utilities_vol`
- expected prospective IC10 sign: **negative**
- frozen historical IC10: `-0.142824`
- frozen 2022+ IC10: `-0.1394`
- frozen BH-FDR q: `0.061938`
- frozen 20-session block-bootstrap 95% CI: `[-0.244367, -0.052791]`
- frozen univariate LOYO MSE improvement: `+0.196%`

### Candidate B — Financials Volatility

- component key: `fear_volatility::c10`
- member: `sector_fin_vol`
- expected prospective IC10 sign: **negative**
- frozen historical IC10: `-0.133312`
- frozen 2022+ IC10: `-0.0899`
- frozen BH-FDR q: `0.077423`
- frozen 20-session block-bootstrap 95% CI: `[-0.239283, -0.033905]`
- frozen univariate LOYO MSE improvement: `+0.167%`

### Candidate C — Geopolitical News Impact

- component key: `sentiment_event::c2`
- member: `geo_news_impact`
- expected prospective IC10 sign: **negative**
- frozen historical IC10: `-0.093116`
- frozen 2022+ IC10: `-0.0714`
- frozen BH-FDR q: `0.030969`
- frozen 20-session block-bootstrap 95% CI: `[-0.162646, -0.024664]`
- frozen univariate LOYO MSE improvement: `+0.148%`

No other historical component is included in V1. Adding another component requires a new preregistered version.

## Source rule

The candidates are evaluated only under the **source-invariant market-price reconstruction** used by `research_factor_map_source_invariant_v1.py` and `research_factor_components_source_invariant_v1.py`.

- official/FRED-dependent indicators are excluded from this evidence stratum;
- no FRED availability change may alter these three candidate formulas;
- each candidate is a singleton component, so no within-component reweighting is allowed;
- the supportive-direction transformation inherited from the frozen component audit is used without change.

## Prospective ledger

For every fully completed U.S. trading session strictly after 2026-10-02:

1. capture each candidate score once;
2. store `first_seen_at` and `first_seen_market_date`;
3. never overwrite the first-seen candidate score;
4. record any later source recomputation disagreement separately as a discrepancy;
5. mature the primary outcome exactly 10 trading sessions later;
6. freeze the first-matured SPY 10D forward return and never rewrite it.

The daily ledger may contain overlapping 10D outcomes. This is intentional; confirmatory inference below is dependence-aware.

## Completed-session rule

A same-day U.S. market bar is not eligible before 17:00 America/New_York. If the newest Yahoo bar is dated today and New York time is earlier than 17:00, that bar must be excluded from the prospective ledger.

## Primary prospective evaluation gate

No confirmatory evaluation before **both** conditions are satisfied:

- at least **252 matured daily observations** per candidate; and
- at least **12 calendar months** elapsed from the first prospective observation.

At the first date both conditions become true, V1 locks the first 252 matured observations as the confirmatory sample. Later observations are monitoring data only and do not rewrite the V1 result.

## Primary statistics

For each of the three candidates on the locked confirmatory sample:

- Spearman correlation between the frozen candidate score and frozen SPY forward-10D return;
- 20-session moving-block bootstrap, 1000 replications;
- circular-shift serial-dependence null, 1000 replications;
- two-sided empirical p-value;
- Benjamini-Hochberg FDR across exactly these three candidate tests.

A candidate passes its V1 prospective test only if:

1. prospective IC10 has the preregistered **negative** sign;
2. the 20-session block-bootstrap 95% CI lies entirely below zero; and
3. BH-FDR q <= 0.10.

No historical magnitude target is required.

## Guardrails

- No automatic promotion to production.
- No production reweighting.
- No threshold tuning.
- No replacing a failed candidate inside V1.
- No adding a fourth candidate to V1.
- No stopping early because a p-value looks good or bad.
- Historical results through 2026-10-02 never count toward the prospective sample.
- A separate review is required after the locked confirmatory sample matures.
