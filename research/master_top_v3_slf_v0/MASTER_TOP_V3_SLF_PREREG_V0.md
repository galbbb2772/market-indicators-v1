# MASTER TOP V3 — SLF V0 Pre-Registration
## Systemic Liquidity / Fragility（系统性流动性与金融脆弱性路线）预注册

Date: 2026-10-19
Status: **DESIGN PRE-REGISTERED / NOT SCORED / NOT PRODUCTION**

Data contract:
MASTER_TOP_V3_SLF_DATA_CONTRACT_V0.md

### 1. Hypothesis
A market top caused or amplified by systemic liquidity stress should show:

1. rising funding stress;
2. either market-plumbing / settlement stress OR a strong flight into safe assets;
3. optionally, the broad equity market is still close enough to a long-term high for the signal to be relevant to a top rather than only to a post-crash panic.

This route is deliberately distinct from:
- PB = policy + breadth deterioration
- CB = credit deterioration
- BE = valuation / speculation / leverage exhaustion

### 2. Causal transforms
All percentile transforms are expanding and use only values available by effective_session.

Strict empirical percentile:

Pct(x_t) = 100 * count(history_available < x_t) / count(history_available)

Minimum warmup = 252 eligible daily observations.

#### 2.1 Funding stress
Let OFR_Funding_t be the OFR FSI Funding category contribution available at t.

FundingPositive_t = max(OFR_Funding_t, 0)

FundingPct_t = Pct(FundingPositive_t)

Interpretation:
0 = no positive funding stress.
Higher percentile = unusually severe funding stress relative to available history.

#### 2.2 Settlement / market-plumbing stress
Let:

FailsTotal_w = FailsToDeliver_w + FailsToReceive_w

Use weekly released data only after its Thursday 4:15 p.m. publication.

To reduce nominal market-size drift:

FailsRel_w = log(1 + FailsTotal_w) - median_52w(log(1 + FailsTotal))

SettlementRaw_w = max(FailsRel_w, 0)

SettlementPct_w = Pct(SettlementRaw_w)

The latest released weekly SettlementPct is held constant until the next scheduled weekly release, subject to the missing-data rules in the data contract.

#### 2.3 Safe-asset migration
Let OFR_Safe_t be the OFR FSI Safe Assets category contribution available at t.

SafePositive_t = max(OFR_Safe_t, 0)

SafePct_t = Pct(SafePositive_t)

#### 2.4 Confirmation leg
ConfirmationPct_t = max(SettlementPct_t, SafePct_t)

Rationale:
A funding squeeze may be confirmed either by malfunction in settlement/liquidity plumbing or by a broad migration into safe assets.
No fitted weights are introduced.

### 3. Primary raw score
SLF_RAW_t = sqrt(FundingPct_t * ConfirmationPct_t)

Range: 0..100.

Important:
- no threshold is frozen at V0 preregistration
- SLF_RAW is a research score, not a crash probability

### 4. Market-top contextualized variants
Both variants are pre-declared and must always be reported together.

Let:
TopRatio_t = Price_t / HH_60M_t

#### Variant A — SLF90
TopProx90_t = clip((TopRatio_t - 0.90) / 0.10, 0, 1)

SLF90_t = SLF_RAW_t * sqrt(TopProx90_t)

#### Variant B — SLF95
TopProx95_t = clip((TopRatio_t - 0.95) / 0.05, 0, 1)

SLF95_t = SLF_RAW_t * sqrt(TopProx95_t)

Neither variant may be selected as “the winner” merely because it fits famous historical tops better.
Robustness should be judged across both.

### 5. Pre-declared diagnostic threshold grid
For legacy diagnostics only, report all of:

- 70
- 80
- 90

for:
- SLF_RAW
- SLF90
- SLF95

No threshold becomes frozen from the retrospective scan alone.

### 6. Episode rule
Use the existing V3 common episode lock:

126 observed sessions.

Within a route/threshold pair:
- first threshold crossing opens an episode
- additional crossings inside the next 126 observed sessions belong to the same episode
- no counting multiple daily hits as separate successes

### 7. Legacy evaluation set
Primary historical episodes to inspect after the formula is frozen:

Risk/top episodes:
- 2007
- 2011
- 2015-16
- 2018 Q4
- 2020
- 2022

Negative/control periods:
- 2003-04
- 2005-06
- 2013-14
- 2017
- 2019 excluding the repo-stress event window

2000 is WARMUP-limited because the OFR FSI begins in January 2000 and the transform requires 252 observations.

2025-2026:
- censored/current-era observations
- may be displayed only after the full formula is frozen
- must not be used to choose formula, threshold, top gate, or lookback

### 8. Metrics to report
For every pre-declared variant/threshold:

- episode count
- false-positive count
- time from first crossing to subsequent equity peak
- 63-session forward drawdown
- 126-session forward drawdown
- 252-session forward drawdown
- whether signal began before or after the local market peak
- overlap / incremental information vs PB, CB, BE

Do not collapse different horizons into one “hit rate.”

### 9. Robustness controls
After the primary legacy scan, and without changing V0:

- compare against STLFSI4 as an external broad-stress control
- compare against NFCI only as a revised-history sensitivity
- run a modern-only 2019+ check using OFR repo-market data

These controls may diagnose V0 but may not silently replace a V0 input.

### 10. Promotion rule
SLF V0 may be considered for FROZEN_V3 only if:

1. data availability implementation passes no-lookahead audit;
2. primary results are not dependent on one crisis only;
3. both top-location variants tell broadly consistent stories;
4. false positives are disclosed;
5. no post-result parameter rescue is performed;
6. a prospective immutable ledger is started after the research lock.

Until then:
SLF status = DESIGN_PRE_REGISTERED / RESEARCH ONLY.
