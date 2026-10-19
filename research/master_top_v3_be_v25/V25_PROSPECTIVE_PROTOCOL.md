# V2.5 — Prospective signal lock protocol (not yet active)

**2026-10-19. Research-only. Do not call this an active real-time signal or an independently validated OOS forecast.**

## Why this exists
Bubble Exhaustion V2.1–V2.5 was shaped by known historical outcomes, and its historical series were assembled from later-revised public mirrors. Calendar train/test ordering alone does NOT remove hindsight contamination. Future evidence requires an append-only time-stamped signal ledger.

## Exact required process
1. Wait for the **entire signal month to close**. October 2026 has not yet completed on 2026-10-19; a provisional October research score is not a prospective October signal.
2. Verify margin, CAPE and SPY input observations, separately recording `reference_month`, `published_at` (source first known to be public, with documented evidence), `captured_at` (UTC), `source_url`, `release_evidence_url`, `snapshot_path` and SHA-256 over unmodified raw source bytes.
3. Assert margin and CAPE observation months are no later than the month *preceding* the signal month; SPY source month must equal the signal month; never assume month-end data was available immediately.
4. Freeze model code hash, score date, source hashes and complete candidate. The `prospective_lock.py` ledger validator rejects incomplete months, future-dated publication/capture, missing release documentation, mismatched hashes and duplicate month records.
5. Because the signal can only be known once all sources are captured and the month has finished, **the earliest hypothetical execution is after signal locking**. A month-end closing price used as model input is not an attainable same-close entry.
6. Store one immutable record for each signal month. Never overwrite a historical signal after observing returns. Any correction becomes a new version with an audit trail and cites the original record.
7. Do NOT tag the candidate `is_true_oos_validated=true` in a signal record. Only independent later review of matured 6-, 12- and 18-month outcomes can establish prospective performance.
8. The release-documentation guard checks the declared release evidence **exists as a URL**, not that its contents genuinely prove a particular release timestamp. That evidentiary judgment must be checked manually by the researcher; the validator does not independently browse evidence or certify vintage PIT.

### Candidate schema (illustrative only; not a live signal)
```json
{
  "schema_version": "BE_V25_PROSPECTIVE_1",
  "signal_month": "2026-10",
  "data_status": "COMPLETE_MONTH",
  "locked_at": "2026-11-01T03:00:00Z",
  "code_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "is_true_oos_validated": false,
  "sources": {
    "margin": {
      "reference_month": "2026-09",
      "published_at": "2026-10-20T12:00:00Z",
      "captured_at": "2026-11-01T02:00:00Z",
      "source_url": "https://example.org/margin",
      "release_evidence_url": "https://example.org/margin-release-notice",
      "snapshot_path": "snapshots/margin_raw.csv",
      "sha256": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
    },
    "cape": {
      "reference_month": "2026-09",
      "published_at": "2026-10-20T12:00:00Z",
      "captured_at": "2026-11-01T02:00:00Z",
      "source_url": "https://example.org/cape",
      "release_evidence_url": "https://example.org/cape-release",
      "snapshot_path": "snapshots/cape_raw.csv",
      "sha256": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"
    },
    "spy": {
      "reference_month": "2026-10",
      "published_at": "2026-10-31T00:00:00Z",
      "captured_at": "2026-11-01T02:00:00Z",
      "source_url": "https://example.org/spy",
      "release_evidence_url": "https://example.org/spy-release",
      "snapshot_path": "snapshots/spy_raw.csv",
      "sha256": "dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd"
    }
  }
}
```

All example URLs, dates and hashes above are **placeholders and not historical facts or verified FINRA release evidence**. Never lock this illustrative JSON.

**Scope:** The ledger is not a full forecasting engine: it controls availability/provenance and append-only recording. The corresponding model calculations still require the separately frozen signal-engine code and external review.
