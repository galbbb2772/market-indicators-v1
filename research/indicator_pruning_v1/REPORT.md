# Indicator Pruning V1 — Final Research Readout

**Evidence window:** historical validation frozen through 2026-10-02; score-preservation A/B reconstructed through 2026-10-05.  
**Status:** research-only. No raw indicator history is deleted and production membership is not changed by this report.

## What happened

The first statistical screen suggested compressing the 19 directional Active indicators to 11. That aggressive 19→11 version was **rejected** by score-preservation A/B:

- score-series correlation vs current model: **0.769**
- mean absolute score difference: **5.15 points**
- OOS objective delta: **-15.43**
- OOS risk-separation delta: **-2.47 pp**

Therefore the project does **not** adopt the 11-indicator version.

We then switched to conservative pruning: test individual removals and accept cumulative removals only while preserving the current score structure and 2022+ risk behavior.

## Conservative result

Accepted cumulative removals:

1. **high_yield** → Archive / no independent vote
2. **employment** → Context
3. **geopolitical_risk** → Context

Rejected cumulative removals — keep Active for now:

- business_cycle
- market_overextension
- money_making_effect
- sme_survival_growth
- yield_curve

Also, **volume_speed** has zero directional polarity and should be treated as Context rather than an independent directional vote.

### Final candidate directional Active set

The conservative pass keeps **16 directional Active indicators**:

- market_support
- money_making_effect
- market_overextension
- breadth_concentration
- options_anomaly
- tech100_volatility
- market_fear
- retail_participation
- valuation_percentile
- business_cycle
- sme_survival_growth
- yield_curve
- market_liquidity
- treasury_rate_regime
- global_cb_rhythm
- us_loans_speed

## Preservation test for the 16-indicator candidate

Compared with the current 19-directional-indicator score:

- observations: **2,453**
- score correlation: **0.991472**
- mean absolute score difference: **1.0721 points**
- 95th-percentile absolute score difference: **2.5408 points**
- full-history objective delta: **-0.6607**
- 2022+ objective delta: **-0.1783**
- full-history risk-separation delta: **-0.1386 pp**
- 2022+ risk-separation delta: **+0.1193 pp**
- full-history forward-10d IC delta: **-0.0102**
- 2022+ forward-10d IC delta: **-0.0274**

The conservative preservation gate **passes**.

## Why high_yield is the clearest deletion

Within the current Active set, **high_yield** and **market_liquidity** have an absolute 5-day-change Spearman correlation of **1.000** over about 2,450 aligned observations. They are effectively supplying the same historical vote in opposite score orientation after polarity handling. Retaining both gives the same underlying state more influence than intended.

## Interpretation

The main lesson is not “fewer is always better.” The data show that several individually weak-looking indicators still matter jointly because the current bucketed score uses them as state anchors. Removing many at once materially changes the model.

So the proper pruning rule is:

> Remove only indicators whose information is redundant **and** whose deletion preserves the aggregate score and OOS risk structure.

Under that rule, the defensible first reduction is **19 directional Active → 16**, not 19→11.

## Guardrail

This report does not delete source histories. Context indicators remain visible for explanation and regime inspection. Archive means “no independent vote,” not “erase the data.”
