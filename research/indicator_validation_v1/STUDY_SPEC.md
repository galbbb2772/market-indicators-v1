# Full Indicator History Validation V1

Status: research-only / diagnostic-only. No production effect.

## Purpose
Validate the full historical score series that already exist in `update_data.py`'s in-memory `series_store`. The existing dashboard only exposes a short tail per indicator, while `ablation_runner.py` can capture the complete reconstructed histories.

This study asks four questions for every calculable indicator with enough history:
1. Does the score level contain forward-return information, and at what horizon?
2. Is the relationship stable across eras and market regimes?
3. Does the apparent IC survive an overlapping-return check?
4. Which indicators are historically redundant with one another?

## Frozen universe rule
Use every indicator present in the captured `series_store` that has:
- at least 252 aligned SPY trading-day observations;
- at least 10 distinct score values;
- a valid `indicator_config.json` definition.

Do not drop an indicator because its result is weak or inconvenient.

## Forward horizons
Fixed before results: 1D, 5D, 10D, 20D, 60D SPY close-to-close forward return.

## Score views
For each indicator report:
- raw score IC: Spearman(score, forward return);
- polarity-aligned supportive score IC where `impact_polarity` is +/-1, using `50 + polarity * (score - 50)`;
- raw-score quintile forward returns and Q5-Q1 spread.

A negative supportive-state IC is not automatically bad: for a mean-reversion system it may indicate contrarian behavior. Direction is interpreted descriptively rather than optimized.

## Overlap robustness
For each horizon H, split observations into H deterministic phase samples by trading-session index modulo H. Report the median/min/max phase Spearman IC and the percentage of valid phases with the same sign as the full-sample IC. This is the primary overlapping-return robustness check; no phase is selected.

## Era splits
Fixed eras:
- 2017-2019
- 2020-2021
- 2022-present

## Regime splits
Fixed market regimes from SPY only:
- above vs below SPY 200D moving average;
- realized-volatility regime: annualized 20D RV >=20% vs <20%.

## Rolling IC
Report 252-trading-day rolling Spearman IC sampled every 21 trading sessions for 10D and 20D horizons. Report median, p10, p90, min, max and positive-share; do not select windows.

## Redundancy
Use 5-trading-day score changes, pairwise aligned. For pairs with >=120 common observations report Spearman correlation. Store each indicator's maximum absolute peer correlation and all pairs with |rho| >= 0.85.

## Guardrails
- Reconstructed history is not fully point-in-time; macro observation dates may differ from public release dates.
- No indicator weight, threshold, active/context/archive status, or production rule changes in this study.
- No historical best-indicator selection may be promoted directly.
- No p-hacking via horizon, era, phase, or regime selection.
- Results are descriptive evidence for later preregistered Forward-OOS candidates only.
