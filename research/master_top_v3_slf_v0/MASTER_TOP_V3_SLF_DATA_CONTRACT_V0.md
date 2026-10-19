# MASTER TOP V3 — SLF V0 Data Contract
## Systemic Liquidity / Fragility（系统性流动性与金融脆弱性路线）数据契约

Date: 2026-10-19
Status: **DATA CONTRACT FROZEN FOR V0 DESIGN / NO BACKTEST YET**

### 1. 这条路线做什么
SLF = Systemic Liquidity / Fragility（系统性流动性与金融脆弱性）。

它不是：
- PB（Policy–Breadth，政策冲击—市场宽度）
- CB（Credit Break，信用破裂）
- BE（Bubble Exhaustion，泡沫耗竭）

SLF 专门回答一个问题：

> 当市场仍接近高位时，金融系统的短期融资、结算与安全资产迁移是否已经出现系统性压力？

大类：MASTER TOP → V3 → 第四核心主路线。

### 2. V0 主数据源

#### A. OFR Financial Stress Index — Funding contribution
中文：OFR 金融压力指数中的“融资压力”分项。

用途：衡量金融机构获得短期资金是否变得困难。

官方说明：
- OFR FSI 是每日市场化金融压力指标。
- Funding 类别专门衡量金融机构融资活动的难易程度。
- 当前网页说明最新数据通常滞后两个工作日。

Source:
https://www.financialresearch.gov/financial-stress-index/

Retrospective retrieval fallback frozen before any successful score run:
- Preferred bytes: official OFR downloadable Financial Stress Index file.
- The official static CSV returns HTTP 403 to the GitHub CI runner. Before any successful SLF score run, the fallback is therefore frozen as the Economic Risk Clock retained OFR history API for the two published OFR category contributions used by V0: Funding and Safe Assets.
- The mirror exposes the full OFR-derived history, source-period values, retained source-file hashes, and explicitly labels it as original published OFR index/contribution data; however, its reconstructed history is **not historical point-in-time evidence**.
- V0 retrieves this fallback in calendar-year chunks and SHA256-pins the exact JSON bytes for reproducibility.
- This fallback is **retrospective research only**. Prospective evidence must capture official OFR publication bytes/observations; the mirror cannot establish the original historical publication timestamp.
- The earlier Diawonds HTML fallback was attempted but did not expose a machine-readable table to CI and is not used.
- These changes are data-access substitutions made before any legacy SLF score was produced; no formula, threshold, top gate, or outcome rule changed.

Availability rule for historical causal scan:
- observation date = t
- assume publication availability no earlier than t + 2 U.S. business days
- signal may become actionable only on the next U.S. trading session after publication
- therefore conservative historical effective date = t + 3 U.S. business days when exact intraday timestamp is unavailable

Vintage rule:
- retrospective history is marked LATEST_VINTAGE_ONLY
- prospective runs must save the exact downloaded source file / payload and SHA256 before scoring
- later revisions are stored as RESTATED values and may not overwrite the original AS_PUBLISHED score

#### B. OFR Financial Stress Index — Safe Assets contribution
中文：OFR 金融压力指数中的“安全资产迁移”分项。

用途：识别市场参与者是否正在从风险资产向安全资产集中迁移。

Same availability/vintage rules as Funding.

Important boundary:
- Do NOT use OFR Credit or Equity Valuation categories in the core SLF formula.
- Credit belongs to CB; valuation belongs to BE.
- Volatility may be reported as a robustness control but is excluded from SLF V0 primary score.

#### C. New York Fed Primary Dealer Aggregate Fails
中文：纽约联储一级交易商“未能交割 / 未能收货”数据。

Primary series:
- Aggregate Fails to Deliver
- Aggregate Fails to Receive
- Prefer Treasury-specific fails when a consistent long-history field is available; otherwise use aggregate total in V0 and disclose the choice.

用途：
- 高 fails 往往意味着证券市场底层流动性/结算链条出现问题。
- 这是 market plumbing（市场基础设施/结算管道）压力，而不是估值或信用周期本身。

Official release timing:
- New York Fed updates Primary Dealer Statistics on Thursdays at approximately 4:15 p.m.
- release contains the previous week's statistics
- actionable availability = next U.S. trading session after the Thursday release

Source:
https://www.newyorkfed.org/markets/counterparties/primary-dealers-statistics

OFR mirror/API may be used for reproducible retrieval:
https://www.financialresearch.gov/short-term-funding-monitor/datasets/nypd/

Prospective rule:
- save release date, observation week, source URL/API request, captured_at, raw payload SHA256
- do not replace an original captured release with a later revised value

### 3. Price context
SLF itself measures systemic liquidity stress. To test whether it is useful as a *market-top* route, two top-location contextualized variants will be reported side-by-side.

Historical research price source for V0:
- Yahoo Finance chart history for SPY adjusted close is frozen before the first successful SLF legacy score run as the research-only broad-U.S.-equity top-location proxy.
- The earlier Stooq ^SPX endpoint was attempted first but returned a JavaScript verification page to GitHub CI; no SLF score was produced from it.
- SPY is already the canonical broad-market ETF used elsewhere in this repository, and it has history spanning the full SLF common research era.
- close at session t is usable only after that close
- earliest executable interpretation is session t+1
- exact downloaded JSON bytes are SHA256-pinned per run
- a later production implementation must either preserve this source or prove date-by-date parity with the canonical MASTER TOP market-price feed before substitution

No alternative price source may be selected after seeing SLF historical performance merely to improve results.

### 4. Alignment schema
Every observation used by SLF must have:

- source_date
- published_at
- available_at
- captured_at
- effective_session
- source_version / vintage label
- raw_sha256
- transformed_value
- score_version

No join may use source_date as if it were availability date.

### 5. Missing/revision semantics
- Missing input = NA, never zero.
- OFR daily category values may not be forward-filled more than 3 U.S. business days.
- NY Fed weekly fails may be carried until the next scheduled release; if no new release is available for more than 10 calendar days, SLF becomes NA.
- Later historical corrections do not rewrite the original prospective decision record.
- A retrospective latest-vintage scan is research evidence only, not genuine PIT proof.

### 6. Historical coverage
- OFR FSI inception: 2000-01-03.
- New York Fed Primary Dealer published statistics accessible from 1998 onward in the current data tool.
- SLF V0 therefore uses 2000 onward as the common research era.
- Expanding percentile transforms require at least 252 eligible daily observations; earlier dates are WARMUP / NOT SCORED.

### 7. Explicit exclusions from V0 primary formula
Excluded to avoid overlap or short-history bias:
- OFR Credit category — belongs conceptually to CB
- OFR Equity Valuation category — overlaps BE
- NFCI / ANFCI — may revise historically; robustness only
- STLFSI4 — broad composite; robustness only
- modern OFR repo transaction series — useful from 2019 onward but too short for the primary legacy route
- ad-hoc emergency-facility usage — event/context only, not a core feature

### 8. Data-contract acceptance
The V0 formula may be frozen only if all three primary data families can be retrieved reproducibly and the availability mapping above is implemented.

After formula freeze:
data load -> legacy scan -> negative controls -> sensitivity -> forward holdout.

No formula or threshold may be changed after viewing the legacy results without incrementing the route version.
