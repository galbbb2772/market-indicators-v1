# MASTER TOP V2.1.8 — Massive Data Provider Gate (2026-10-23)

**Classification: RESEARCH ONLY / SOURCE AUDIT.** Not a scored model variant, not a replacement for the archived V2.1.8 frozen scorer, and not an authorized production feed change.

## Why this separate route was necessary

The MarketParquet default-branch live scorer requires a repository secret and its latest committed `2026-10-09` value 99.33 is a historical **seed**. The separate operational fix in PR #18 guards missing keys, stale score dates, S&P 500 price dates and DGS2 dates. It does not, by itself, provide a new authenticated source.

We examined Massive's official grouped daily endpoint and its dated reference tickers endpoint. An authenticated connected-data inspection of:

- **2026-10-22** `/v2/aggs/grouped/locale/us/market/stocks/{date}` with `adjusted=true, include_otc=false` yielded **12,618 grouped ticker bars, 12,618 unique symbols, and 0 null/nonpositive closes**.
- **2026-10-16** yielded **12,630 grouped ticker bars**.
- The grouped rows include **ETFs** (e.g., SPY, FNDA, QQQ), so a direct raw grouped-data substitute would change the stock breadth denominator and invalidate comparability.
- Date-specific Massive ticker reference listings permit `type=CS` and `type=ADRC` with `active=true`; ETFs belong to a different type and must be excluded from stock-only breadth. A sample dated CS page and ETF page each returned 1,000 records and continuation cursors.

These observations establish that data are reachable through the connected Massive research service, **NOT** that a GitHub Actions repository secret is installed or that every historical calendar date/symbol-class page can be fetched within the account's rate limits.

## What the new code does

`research/provider_audit_massive_v218.py` takes a date, downloads adjusted non-OTC grouped OHLC, validates one ticker and sane OHLC/date per bar, paginates **date-specific** CS and ADRC reference metadata, and explicitly excludes all other security types from the qualified-ticker count.

The output `research/out/master_top_massive_source_audit.json` is a small audit **receipt only**. It records total bars, count qualified by class, excluded/unclassified count, reference page counts and deterministic fingerprints. No complete data are written to the GitHub repository. The API key is never printed.

The file hard-codes both `production_eligible=false` and `frozen_score_comparable=false`. It does not calculate an H/L score, does not update the V2.1.8 history or seed, and does not manufacture a market-top alert.

The separate `.github/workflows/master_top_massive_provider_audit.yml` runs no-secret offline tests on a PR/push and supports optional credentialed **manual** source audits; only the manual job reads `MASSIVE_API_KEY` and saves a 30-day artifact.

## Promotion / go-no-go requirements

1. Confirm that **this repository** (not only `box-strategy-lab`) has a usable `MASSIVE_API_KEY` secret, and run the manual provider audit with the exact observation date; no private key values in logs.
2. Validate source universe against original MarketParquet `stock_daily` definition: common shares and ADR inclusion/exclusion, ETFs, SPACs, delistings, ticker reuse, exchanges, and price adjustment. Different source universes constitute a distinct source epoch and must not be grafted into the frozen historical run.
3. Acquire at least **252 prior sessions plus 20 persistence sessions** with sufficient per-ticker date coverage. A couple of grouped EOD days do **not** support a 52-week high/low computation.
4. Assess daily-call rate limits, data rights, and completeness; the 252-session historical backfill may require hundreds of group calls and date-specific classification pages. Do not assume a 20-minute workflow is enough.
5. After coverage and source invariance pass, design a **new, separately versioned** scored research pipeline with immutable receipts and strictly post-freeze forward evaluation. No silently changed threshold or unverified "live" label.

## Current decision

**MASSIVE_FEED_REACHABLE; MASSIVE_V218_SCORE_NOT_VALIDATED.**

Keep PR #18 operational fix and this provider audit separate. Keep original MarketParquet production score frozen. No new trading recommendation or production Market Top signal is inferred.
