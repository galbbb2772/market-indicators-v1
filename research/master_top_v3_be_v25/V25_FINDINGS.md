# MASTER TOP V3 / Bubble Exhaustion V2.5 — Entry-Price Outcome Audit

**As of 2026-10-19 | RETROSPECTIVE RESEARCH ONLY | no production promotion | no genuine untouched OOS / no vintage-perfect PIT.**

## Primary scientific correction

Previous V2.4 outcome: **future 365-day peak-to-trough SPY close drawdown >=20%**. That can occur even if SPY never trades 20% below the signal-date close.

V2.5 target: **minimum subsequent SPY daily close within 365 calendar days, divided by signal-date SPY close, minus one <= -20%**. This represents post-signal *entry-price-to-future-low* loss. It is not an executable backtest, since the signal is evaluated at closing price and traded after publication; no spreads, dividends, slippage, fills, borrow, hedging or switching assumptions were made.

- All target labels are observed after the initial scoring date. Training rows must satisfy `train_signal_date + 395 days <= forecast_signal_date` (>=12-month outcome maturity + ~30-day safety gap).
- Same four annual-anchor cohorts (Jan/Apr/Jul/Oct), each fitted separately.
- All models re-fit against the **new entry-price label**; no reusing V2.4 probability outputs.
- Predictor inputs: expanding CAPE historical percentile; price distance to 60-month high (TopRatio); leverage-rollover score; leverage-memory percentile.
- Model family and ridge penalty (lambda 2.0) are locked to V2.4, not tuned here.
- Brier and log loss lower is better; AUC higher is better but unreliable for rare events and small year counts.
- Data sourced from V2.2 retrospectively reconstructed FINRA/SHILLER/SPY mirrors under *hypothetical month-end +25 days* margin reporting lag. Not actual publication vintage.

## V2.5 results — 20% entry-price outcome

2019–2025: 27 *annual-anchor observations* but only 7 unique calendar years; 6 positive observations.

| Model | Brier ↓ | AUC ↑ |
|---|---:|---:|
| PRIOR (history-only frequency) | **0.1748** | 0.484 |
| CAPE percentile alone | 0.1751 | 0.484 |
| CAPE + TopRatio | 0.1814 | 0.357 |
| CAPE + TopRatio + Rollover | 0.1855 | **0.556** |
| CAPE + TopRatio + Leverage Memory | 0.2024 | 0.302 |

Adding rollover changes ranking but **worsens squared calibration error** versus CAPE+TopRatio by +0.00414. Compared to the simpler PRIOR baseline, both feature-rich models are worse on Brier.

**Calendar-year cluster bootstrap:** delta Brier (WITH minus WITHOUT rollover) = **+0.00414**, approximate 95% interval **[-0.01302,+0.02824]**, 4000 resamples of the seven years, retaining all annual anchors in each year. Zero is inside interval; no convincing predictive advantage.

2013–2018 has 24 annual anchor observations and **zero** >=20% entry-price-loss events. All-in-one-number metrics from that period cannot demonstrate discrimination; a favorable average Brier there is not proof of crash prediction.

## Predeclared descriptive severity-sensitivity

To test whether a single threshold drives the result, fit separate new-label models at entry-date-to-minimum losses of **10%, 15%, 20%**. This is **research sensitivity**, not threshold optimization or evidence to replace the headline severe threshold after observing performance.

2019–2025 (27 anchor observations, 7 distinct calendar years):

| Entry-date decline | Positive observations | Brier CAPE+Top | Brier +Rollover | Δ Brier | Year-cluster 95% interval |
|---|---:|---:|---:|---:|---|
| >=10% | 12 | .26679 | .25323 | -.01355 | [-.04171,+.01020] |
| >=15% | 8 | .22314 | .23053 | +.00740 | [-.00865,+.02421] |
| >=20% | 6 | .18138 | .18552 | +.00414 | [-.01313,+.02836] |

10% has a suggestive numerical improvement; its uncertainty still includes no change and, because the same data were inspected at three thresholds, it must **not** be promoted as discovered predictive skill.

## Critical limitations

1. All scores and labels come from post-hoc revised sources, with a *hypothetical* FINRA publication delay; true point-in-time availability remains unproven.
2. Architecture and features were historically informed by data through 2025; the 2019–2025 rolling test is chronologically purged but **not independent untouched OOS**.
3. Only seven post-2019 calendar years underpin the 27 correlation-heavy anchor observations. Annual anchor models and labels overlap across anchors.
4. A complete 365-day SPY price window is mandatory, and 2026-10 and unmatched maturities are **right-censored**, not counted as negative.
5. A risk score that predicts a decline doesn't imply profitable trading, especially if the signal triggers after an earlier peak.
6. Rollover's historical ability to identify an *already started* deleveraging phase is different from a tradable, ahead-of-peak warning.
7. No statistical finding here warrants changing MASTER TOP V3 production Dashboard alerts or allocating capital.

## Scientific decision
**Bubble Exhaustion V2.5: NOT VALIDATED / RESEARCH ONLY.**

The next leg should prioritize *real input release timestamps* and **prospective, timestamped frozen signal records** instead of additional threshold fishing. Longer horizons and returns from executable close/open times should be pre-registered before collecting outcomes.

## Versioned research artifacts
- `V25_ENTRY_FORECASTS.csv`: 51 re-fit forecast records with target-specific model outputs.
- `V25_ENTRY_MODEL_SCORECARD.csv`: period × annual anchor model Brier/log loss/AUC.
- `V25_ENTRY_YEAR_CLUSTER_BOOTSTRAP.csv`: paired by-year uncertainty for >=20% entry-price target.
- `V25_SEVERITY_DETAIL.csv`: per-observation forecasts separately fit for 10/15/20% labels.
- `V25_SEVERITY_SENSITIVITY.csv`: 10/15/20% model comparison.
- `V25_SEVERITY_YEAR_BOOTSTRAP.csv`: by-year bootstrap intervals for severity comparisons.
- `reproduce_v25.py`: stdlib source for 20% entry-price target.
