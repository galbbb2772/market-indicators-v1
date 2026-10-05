# Sector Rotation State V1

Status: **research-only / diagnostic-only / post-discovery**.

This study follows `sector_rotation_stage2_v1` and `sector_rotation_robustness_v1`. It does not alter production signals, weights, thresholds, or portfolio rules.

## Frozen universe and horizon
- Benchmark: SPY.
- Sectors: XLB, XLC, XLE, XLF, XLI, XLK, XLP, XLRE, XLU, XLV, XLY.
- Historical cutoff: 2026-10-02.
- Primary outcome: sector forward 10-trading-day return minus SPY forward 10-trading-day return.

## Frozen predictors
1. `momentum_rank`: equal-weight cross-sectional percentile ranks of sector-minus-SPY 20D and 60D returns.
2. `contrarian_rank = 1 - momentum_rank`.
3. `activity_rank`: equal-weight cross-sectional percentile ranks of absolute 1D sector-minus-SPY move and volume / trailing 20D average volume.
4. `activity_weighted_contrarian = contrarian_rank * activity_rank`.
5. `dispersion`: cross-sectional standard deviation of `0.5*rel20 + 0.5*rel60` raw percentage-point excess returns. High/low dispersion is defined against the trailing 252-session median using only past/current data, minimum 126 observations.
6. `leader_persistence_5d`: overlap fraction between today's Top3 momentum sectors and the Top3 from 5 trading sessions earlier. High persistence is >= 2/3; low persistence is <= 1/3.

## Tests
- Plain contrarian cross-sectional IC versus activity-weighted contrarian IC.
- Bottom2-minus-Top2 10D excess-return spread conditional on high/low dispersion.
- The same spread conditional on high/low leader persistence.
- Crossed date states: high-dispersion + low-persistence, high-dispersion + high-persistence, low-dispersion + low-persistence, low-dispersion + high-persistence.
- Non-overlapping 10D phase robustness for the fixed state subsets.
- Year-by-year sign stability for the fixed state subsets.

## Guardrails
- No threshold search or lookback optimization.
- No sector deletion after seeing results.
- No production effect.
- Historical results do not count as Forward-OOS evidence.
