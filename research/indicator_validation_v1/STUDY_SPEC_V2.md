# Indicator Validation V1 — Stage-2 Study Spec

Status: research-only / diagnostic-only. No production weighting, threshold, or Forward-OOS rule may change from this study.

## Purpose
Audit every bottom-level indicator for which `ablation_runner.run_update_and_capture()` exposes a sufficiently long historical `series_store` score history. The study asks whether each indicator contains stable forward information, how quickly that information decays, where it works by regime, and which indicators are redundant.

## Frozen universe
- Source: runtime-captured `series_store` from the current `market-indicators-v1` build.
- Market target: SPY adjusted close from the same captured build.
- Minimum usable overlapping observations per indicator: 252 trading days.
- Horizons: 1D, 5D, 10D, 20D.
- No indicator may be excluded because its historical result is weak.

## Direction convention
Use each indicator's configured `impact_polarity`.
- `polarity = +1`: higher score is interpreted as more supportive.
- `polarity = -1`: higher score is interpreted as more adverse.
- `polarity = 0`: report raw IC but exclude from directional-support ranking.
Directional score = `polarity * (score - 50)`.

## Tests
For each eligible indicator:
1. Full-history Spearman IC between directional score and SPY forward returns at 1/5/10/20D.
2. Calendar-year IC table where a year has at least 60 usable observations.
3. Stability summary: positive-year share, median yearly IC, minimum yearly IC, maximum yearly IC.
4. Regime IC at 10D under four frozen regimes built only from SPY history:
   - above MA200
   - below MA200
   - high-volatility (`RV20` expanding percentile >=70)
   - low/normal volatility (`RV20` expanding percentile <70)
5. Decay profile across 1/5/10/20D, including the horizon with largest absolute IC. This is descriptive; the best horizon may not be promoted as a new rule.
6. 2022-present chronological holdout IC at each horizon.
7. Redundancy map using pairwise Spearman correlation of 5D score changes; report pairs with `|rho| >= 0.80` and cluster connected components.

## Family / model metadata
Attach each indicator's current Model V2 role and bucket when available (active/context/archive) but do not use role to filter the study.

## Multiple-testing guardrail
This study is a discovery/diagnostic map, not a promotion test. Raw IC magnitudes and rankings are descriptive only. No indicator can be promoted, reweighted, or removed solely because of this output. Any candidate generated here requires separate preregistration and Forward-OOS validation.

## Data caveats
- Historical series are reconstructed from current available Yahoo/FRED/official data and are not fully point-in-time.
- Some macro inputs may use observation dates rather than exact historical publication timestamps.
- Current-history macro data may contain revisions.

## Outputs
- `docs/data/indicator_validation_v1.json`: full diagnostics.
- `docs/data/indicator_validation_v1_summary.json`: compact ranking / family summary.
