# MASTER TOP V3 — Bubble Exhaustion V2.4 Conditional Incremental Value

Date: 2026-10-19  
Status: RETROSPECTIVE WALK-FORWARD DIAGNOSTIC ONLY. NOT untouched OOS, NOT publication-vintage PIT. Never market as calibrated crash probabilities.

## Research question
Does leverage rollover add forecasting value **conditional on CAPE and the already-realized market position/drawdown**, beyond a simpler valuation/price-location baseline?

## Tested models
All forecasts are regularized logistic probabilities generated using ONLY training rows whose future 365-calendar-day outcome windows had already matured by the forecast date (training eligibility: training_signal_date + 395 calendar days <= current_signal_date). Train in four parallel annual anchors: Jan / Apr / Jul / Oct; don't treat these four correlated anchors as independent market regimes.
- PRIOR: Laplace-smoothed training-set frequency.
- CAPE: CAPE historical percentile.
- CAPE_TOP: CAPE + distance from trailing 60-month closing high.
- CAPE_TOP_ROLL: CAPE_TOP + leverage rollover score (12-month prior peak less current leverage heat).
- CAPE_TOP_MEMORY: CAPE_TOP + 12-month leverage memory.

Transformations: (CAPEpct−75)/25, (1−TopRatio)/0.1, Rollover/25, (Memory−50)/25. Logistic ridge penalizes slopes at λ=2, not intercept. Slopes, features and λ are not hyperparameter-selected within these rolling folds. Training has at least 11 rows and both outcome classes. This remains exploratory because feature set and thresholds were informed by prior research.

### Main result: calendar 2019–2025, 27 annual-anchor forecasts (7 actual years)

| Model | Brier score ↓ | Log loss ↓ | AUC ↑ |
|---|---:|---:|---:|
| PRIOR frequency | 0.1995 | 0.5911 | 0.332 |
| CAPE only | 0.2012 | 0.5950 | 0.293 |
| CAPE + price location | 0.2088 | 0.6155 | 0.293 |
| CAPE + price location + rollover | 0.2097 | 0.6132 | 0.464 |
| CAPE + price location + leverage memory | 0.2246 | 0.7175 | 0.364 |

There is **no demonstrated incremental practical forecasting value** from adding rollover. Compared to CAPE_TOP, Brier is slightly worse (+0.00087) and log loss marginally better (−0.00225); ranking AUC improves but remains below 0.5 and is unstable by annual anchor. All multi-model forecasts have worse Brier than simple PRIOR-only baseline in this period. These results are strongly limited by only seven distinct years; AUC is fragile and should not be viewed as deployment-level evidence.

### Paired year-cluster resampling
Resample the seven calendar years, including all available anchors within each selected year, 4,000 times. Each replicate computes mean *loss difference* (WITH rollover − WITHOUT rollover). Resampling by year avoids naively assuming each monthly/quarterly anchor is independent; it still does not yield perfectly valid independent uncertainty due to market-regime dependence.

| Period | Years | Anchor forecasts | Mean Δ Brier | Approximate 95% year-cluster interval |
|---|---:|---:|---:|---:|
| 2013–2018 | 6 | 24 | -0.01013 | [-0.04073, +0.02169] |
| 2019–2025 | 7 | 27 | +0.00087 | [-0.01824, +0.02412] |
| Combined | 13 | 51 | -0.00431 | [-0.02305, +0.01488] |

All intervals cross zero. No robust improvement can be concluded.

## Design limitations
1. Existing V2.2 scores were derived from retrospective FINRA/CAPE and SPY mirrors and a hypothetical lag of month-end +25 calendar days. Exact historical release-vintage inputs are not available, and this is not true PIT.
2. Training outcomes are matured before prediction, but model architecture was shaped after seeing 2021, 2025, and earlier historical episodes. Thus neither 2019+ nor this rolling run is untouched external OOS.
3. Annual anchors are highly correlated across calendar years; 27 anchor observations = only seven distinct years.
4. Target means 20% peak-to-trough **inside the following** 365-day price window, which may occur even when price never drops 20% from signal price. This is a weakness of the target definition; a separate entry-price-to-minimum target must be checked before production.
5. **2018 Q4 and the 2020 pandemic crash are missed by the bubble route**. This indicator should not be mistaken for an all-crash predictor.
6. Extreme 2000/2008 crises influence model parameters. All four annual anchors are potentially affected by overlapping economic regimes. Small-sample AUC and Brier estimates have large uncertainty.
7. No leverage-specific uplift can be assumed on the basis of historical coincidence alone.

## Decision
- Bubble Exhaustion remains **RESEARCH_CANDIDATE_ONLY**. Do NOT freeze, promote to Dashboard production, or claim credible crash probabilities.
- Retain CAPE_TOP_ROLL only as an experimental incremental comparison, not as an approved forecast model.
- Next validate source publication dates and snapshot vintages, perform a rolling analysis on **entry-price losses** as well as window drawdowns, audit missingness and ensure rigorous pre-declared prospective logging from the next fully available month.
- Keep separate credit/policy/breadth/shock routes in the broader MASTER TOP V3 project.

## Artifacts
- V24_ROLLING_FORECASTS.csv: individual predictions and matured date training folds.
- V24_YEAR_BLOCK_BOOTSTRAP.csv: paired mean loss difference and year-cluster resampling uncertainty.
- V24_PER_YEAR_LOSS_DIFFERENCE.csv: annual loss differences; year is the non-duplicated statistical unit.
- V24_REPRODUCIBILITY_LOCK.json: pinned inherited sources/metrics and no-OOS declaration.

**Do not interpret these as independent forward-test skill or as trading recommendations.**
