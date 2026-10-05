# Sector Rotation Robustness V1

Status: **research-only / diagnostic-only / post-discovery follow-up**.

This study follows the frozen `Sector Rotation Stage-2 V1` result and does not change production behavior.

Historical cutoff remains **2026-10-02**.

## Questions

1. Is the weak negative cross-sectional relationship driven by 20D or 60D relative momentum, or does it require their equal-weight combination?
2. Does the result survive removing each sector one at a time?
3. Is the sign stable by calendar year and in non-overlapping 10D phases?
4. Which sectors contribute most when they are in the Top-2 versus Bottom-2 momentum groups?
5. Does a fixed contrarian portfolio (Bottom-2 minus Top-2) have a positive historical excess return without threshold optimization?

## Frozen variants

No new lookbacks are searched. Exactly three momentum definitions are compared:

- `rel20_only`: cross-sectional percentile of sector 20D return minus SPY 20D return;
- `rel60_only`: cross-sectional percentile of sector 60D return minus SPY 60D return;
- `combo_20_60`: the already frozen equal-weight combination from Stage-2 V1.

Primary horizon: **10 trading days**. Secondary horizons: 5D and 20D only for the fixed combo.

## Leave-one-sector-out

For the primary 10D combo IC, recompute the daily cross-sectional Spearman after excluding exactly one sector ETF at a time. No sector is deleted based on this result.

## Fixed contrarian portfolio diagnostic

At each eligible date:

- long the two lowest Momentum Score sectors, equal weight;
- short the two highest Momentum Score sectors, equal weight;
- outcome = Bottom-2 mean future sector excess return minus Top-2 mean future sector excess return.

This is a research diagnostic only. It ignores execution, turnover, financing, borrow, tax and costs.

## Sector contribution table

For each ETF, report:

- count and average 10D excess return when ranked Top-2;
- count and average 10D excess return when ranked Bottom-2;
- Bottom-2 minus Top-2 difference where both samples exist.

## Guardrails

- No lookback optimization.
- No choosing sectors after seeing results.
- No production rule.
- No historical result counts as Forward-OOS evidence.
