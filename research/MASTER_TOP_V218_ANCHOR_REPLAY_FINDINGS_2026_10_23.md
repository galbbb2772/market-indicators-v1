# MASTER TOP V2.1.8 — independent historical anchor outcomes (2026-10-23)

## Verdict (research-only)

**Real historical price replay was executed successfully**, not merely proposed. GitHub Actions [run 39917289158](https://github.com/galbbb2772/market-indicators-v1/actions/runs/39917289158) completed `SUCCESS`. Its no-secret task fetched **7,246 genuine Yahoo Finance SPY daily price observations spanning 1998-01-02 through 2026-10-22**. The deterministic tests passed **7/7** before real-source replay, and a JSON artifact `master-top-v218-historical-anchor-audit` was uploaded (artifact ID **12484714007**).

This is an **independent forward price-path outcome audit of *previously selected* V2.1.8 score anchors**, **NOT** an all-days historical V2.1.8 signal re-computation. Existing score values remain reported, not recreated. It therefore cannot estimate the full hit rate, false positive rate, crisis recall, or 2026 clean Forward OOS.

## Independent 12-calendar-month SPY close-to-close running-peak MDD

| Archived anchor | Reported V2.1.8 route | Signal? (≥55) | 12M SPY MDD | Market path class | Key timing |
|---|---:|---|---:|---|---|
| 1999-11-29 | 76.90 | YES | **−13.9499%** | Correction | Before 2000-03-24 peak, but **not** proof of full bubble-crash forecasting |
| 2006-06-29 | 44.40 | **NO** | **−5.9504%** | Low drawdown; correctly **no alert** for this selected control | Selected negative control, not an estimate of all 2006 false alarms |
| 2018-10-05 | 66.06 | YES | **−18.5811%** | Severe near miss | **After** the September 2018 peak; confirmation, not early top |
| 2021-12-15 | 69.42 | YES | **−25.3606%** | Major bear | ~19 calendar days before 2022-01-03 top (~12 trading sessions) |
| 2026-09-10 | 60.88 | YES, **pre-freeze seed** | **CENSORED** (to-date interim −2.0331%) | NOT YET EVALUABLE | Signal observed before freeze |
| 2026-10-09 | 99.33 | YES, **same seed episode** | **CENSORED** (to-date interim −1.9677%) | NOT YET EVALUABLE | Same existing episode, not independent new forecast |

The dates have been evaluated using the archived score threshold `55` unchanged. **2006's drawdown bucket must not be called a model false positive**, since the model's archived reported score did not trigger an alert. The 2026 incomplete 12-month windows must not be labeled successful or unsuccessful predictions.

### Independent price-path cross-check of previously claimed 12M drawdown numbers

- 1999: reported −13.43%; independently −13.9499%; difference −0.5199 percentage points.
- 2018: reported −18.52%; independently −18.5811%; difference −0.0611 percentage points.
- 2021: reported −25.43%; independently −25.3606%; difference +0.0694 percentage points.

All three historical **outcome classes** are reproduced with SPY *unadjusted* daily close using a clearly defined 12-calendar-month running-peak MDD. Small discrepancies can result from price source, adjusted/unadjusted treatment, dividend/rounding, or the exact outcome-window convention. They are **not** evidence that the reported *model scores* were independently recalculated or verified.

### Separate 63 / 126 / 252 trading-session outcomes (SPY unadjusted close)

| Anchor | 63-session MDD | 126-session MDD | 252-session MDD |
|---|---:|---:|---:|
| 1999-11-29 | −9.3006% | −11.4367% | −13.9499% |
| 2006-06-29 (untriggered control) | −3.4898% | −3.4898% | −5.9504% |
| 2018-10-05 | −18.5811% | −18.5811% | −18.5811% |
| 2021-12-15 | −12.8655% | −23.2484% | −25.3606% |

These horizons are **not interchangeable** with 12-month MDD or with the frozen 126-session signal *episode lock*.

## Fatal evidence gap discovered in original Stage-0 CSV

The private `market-top-research` archive's Stage-0 `master_top_v3_stage0_scores_through_2026-10-09.csv` has **1,784 dated rows** from 2019-09-05 to 2026-10-09, but only **28 actual PB score rows**, all in September–October 2026. The other **1,756 PB score cells are blank**, not numeric zero. It also has **zero** complete daily CB/BE/SLF composite outputs. Therefore that CSV cannot be reported as a 1,784-day backtest.

A separate archive completeness finding is saved in `galbbb2772/market-top-research/00_Master_Index/PB_V218_COVERAGE_AUDIT_2026_10_23.md`.

## What is proven and what is not

**Proven:** real historical SPY price outcomes for a handful of previously selected V2.1.8 dates; historical negative control's realized low drawdown; classifications match the archived outcome categories; exact source range and replay code are available.

**Not proven:** that V2.1.8 generated these historical score values with complete independent point-in-time 252-session all-US highs/lows data, and certainly not its false positive rate across all days, missing 2007/2020/other bear markets, or true future signal-generation efficacy. Archived anchors suffer selection bias. For 2018, post-peak confirmation cannot be counted as early peak prediction.

## Next critical research step

Collect a complete *dated historical* all-US stock universe and 2Y Treasury yield from independent dated sources, reconstruct daily 252-prior-session highs/lows and 20-session persistence with the frozen V2.1.8 formula, align ^GSPC prices and source vintages, then generate **all-day score history** and independent 126-session episodes. Once complete, calculate **all historical warnings, missed bear markets, false alerts and lead times**, with no frozen threshold changes and no promotion based on selected anchor examples.

Keep PR research-only until those requirements are met.
