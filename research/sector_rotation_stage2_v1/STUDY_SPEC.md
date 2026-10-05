# Sector Rotation Stage-2 V1

Status: **research-only / diagnostic-only / no production effect**.

## Frozen universe

SPY benchmark plus the 11 U.S. Select Sector SPDR ETFs already present in the repository's Yahoo source:

`XLB, XLC, XLE, XLF, XLI, XLK, XLP, XLRE, XLU, XLV, XLY`.

Historical panel is frozen through **2026-10-02** so the incomplete 2026-10-05 U.S. session cannot enter the V1 historical evidence set.

## Frozen features

All rankings are cross-sectional percentiles among the available sector ETFs on the same date.

### Relative Momentum Score

- `rel20`: sector 20D total-price return minus SPY 20D return;
- `rel60`: sector 60D total-price return minus SPY 60D return;
- `momentum_score = 0.5 * rank_pct(rel20) + 0.5 * rank_pct(rel60)`.

No weight optimization is allowed in V1.

### Activity / Attention Score

- `abs_excess_1d`: absolute value of sector 1D return minus SPY 1D return;
- `volume_ratio20`: current sector volume divided by its trailing 20D average volume;
- `activity_score = 0.5 * rank_pct(abs_excess_1d) + 0.5 * rank_pct(volume_ratio20)`.

Activity is evaluated primarily against the **magnitude** of future sector excess returns, not direction.

## Frozen outcomes

For every sector/date:

- 5D, 10D and 20D forward sector excess return versus SPY;
- absolute 5D and 10D forward sector excess return.

## Primary Stage-2 diagnostics

1. Daily cross-sectional Spearman IC of Momentum Score vs future sector excess return for 5D/10D/20D.
2. Top-2 minus Bottom-2 future excess-return spread.
3. Year-by-year mean daily IC.
4. SPY regime splits: above/below MA200 and RV20 >=20 / <20.
5. Non-overlap phase robustness for each horizon.
6. Leader persistence: fraction of today's Top-3 Momentum sectors still Top-3 after 5/10/20 sessions.
7. Activity Score vs future absolute sector excess-return magnitude at 5D/10D.
8. Random-label placebo: within each date, future sector outcomes are permuted across sector labels; 1000 deterministic replications, seed `20261005`.

## Interpretation

- Positive Momentum IC / Top-Bottom spread = relative-strength continuation.
- Negative Momentum IC / spread = cross-sector mean reversion.
- Positive Activity-to-magnitude relation = activity is an attention/volatility state signal even if it does not predict direction.

## Guardrails

- No sector-selection production rule is created by this study.
- No threshold optimization.
- No changing the ETF universe after seeing results.
- No changing 20D/60D or equal weights after seeing results.
- No historical finding counts as Forward-OOS evidence.
