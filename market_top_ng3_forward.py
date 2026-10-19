from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import requests

from audit_market_top_ng1_a_independent import (
    FF25_URL,
    FF12_URL,
    FF3_URL,
    parse_portfolio_block,
    parse_ff3,
    compounded,
    expanding_pct,
)

THRESHOLD = 85.0
LEAD_GAP_MIN = 10.0
WARMUP_MONTHS = 120
FIRST_PROSPECTIVE_EFFECTIVE_MONTH = "202612"

PINNED_COMMIT = "71af02cba3493ffa15ac47f512dc346598f2e23f"
PINNED_BASE = (
    "https://raw.githubusercontent.com/Snow-Ouyang/"
    "Market-Regime-Clustering/"
    + PINNED_COMMIT
    + "/"
)
PINNED_BAA = PINNED_BASE + "data_raw/macro/Credit/BAA.csv"
PINNED_GS10 = PINNED_BASE + "data_raw/macro/rate/GS10.csv"

MACRO_BASE = (
    "https://raw.githubusercontent.com/dlockar1mtg/"
    "MacroIntelligencePlatform/main/data/snapshot/"
)
MACRO_BAA = MACRO_BASE + "BAA.csv"
MACRO_GS10 = MACRO_BASE + "GS10.csv"
MACRO_MANIFEST = MACRO_BASE + "MANIFEST.json"

FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv"
YAHOO_SPY = (
    "https://query1.finance.yahoo.com/v8/finance/chart/SPY"
    "?range=5y&interval=1d&events=history&includeAdjustedClose=false"
)

OUT_CURRENT = Path("docs/data/market_top_ng3_current.json")
OUT_HISTORY = Path("docs/data/market_top_ng3_history.json")
OUT_EPISODES = Path("docs/data/market_top_ng3_episodes.json")
OUT_MONTHLY = Path("docs/data/market_top_ng3_monthly_snapshots.json")

HTTP = requests.Session()
HTTP.headers.update({"User-Agent": "market-top-ng3-forward/1.0"})


def get(url: str, timeout: int = 30, **kwargs) -> requests.Response:
    last = None
    for candidate in (
        url,
        url.replace("query1.finance.yahoo.com", "query2.finance.yahoo.com"),
    ):
        try:
            r = HTTP.get(candidate, timeout=timeout, **kwargs)
            r.raise_for_status()
            return r
        except Exception as exc:
            last = exc
        if "query1.finance.yahoo.com" not in candidate:
            break
    raise RuntimeError(f"request failed: {url}: {last!r}")


def add_months(ym: str, n: int) -> str:
    y = int(ym[:4])
    m = int(ym[4:6]) - 1 + n
    y += m // 12
    m %= 12
    return f"{y:04d}{m+1:02d}"


def completed_month_ym(now: datetime) -> str:
    ts = pd.Timestamp(now.astimezone(timezone.utc))
    first = pd.Timestamp(year=ts.year, month=ts.month, day=1)
    prev = first - pd.offsets.MonthBegin(1)
    return prev.strftime("%Y%m")


def parse_monthly_csv(text: str, value_col: str) -> pd.Series:
    df = pd.read_csv(io.StringIO(text), dtype=str)
    if df.empty:
        raise ValueError("empty monthly CSV")
    dcol = next((x for x in df.columns if "date" in x.lower()), df.columns[0])
    if value_col not in df.columns:
        raise ValueError(f"{value_col} missing: {list(df.columns)}")
    idx = pd.to_datetime(df[dcol], errors="coerce")
    vals = pd.to_numeric(df[value_col], errors="coerce")
    s = pd.Series(vals.to_numpy(), index=idx, name=value_col).dropna().sort_index()
    s = s[~s.index.duplicated(keep="last")]
    if len(s) < 500:
        raise ValueError(f"{value_col} history too short: {len(s)}")
    return s


def fetch_fred_monthly(series_id: str) -> pd.Series:
    r = HTTP.get(
        FRED_CSV,
        params={"id": series_id},
        timeout=12,
    )
    r.raise_for_status()
    s = parse_monthly_csv(r.text, series_id)
    s.attrs["source"] = f"FRED {series_id} direct CSV"
    s.attrs["payload_sha256"] = hashlib.sha256(r.content).hexdigest()
    return s


def month_lag(latest_ym: str, now: datetime) -> int:
    y, m = int(latest_ym[:4]), int(latest_ym[4:6])
    return (now.year - y) * 12 + (now.month - m)


def merge_pinned_with_extension(
    base: pd.Series,
    extension: pd.Series,
    *,
    overlap_months_required: int = 2,
) -> pd.Series:
    overlap = sorted(set(base.index) & set(extension.index))
    if len(overlap) < overlap_months_required:
        raise ValueError("not enough overlap between pinned history and extension")
    for d in overlap[-overlap_months_required:]:
        if not math.isclose(
            float(base.loc[d]), float(extension.loc[d]), abs_tol=1e-12
        ):
            raise ValueError(
                f"credit extension parity failed at {d.date()}: "
                f"{base.loc[d]} != {extension.loc[d]}"
            )
    new = extension.loc[extension.index > base.index[-1]]
    out = pd.concat([base, new]).sort_index()
    out = out[~out.index.duplicated(keep="last")]
    return out


def fetch_credit_fallback(now: datetime) -> tuple[pd.Series, pd.Series, dict[str, Any]]:
    manifest_r = get(MACRO_MANIFEST, timeout=20)
    baa_ext_r = get(MACRO_BAA, timeout=20)
    gs_ext_r = get(MACRO_GS10, timeout=20)
    baa_base_r = get(PINNED_BAA, timeout=20)
    gs_base_r = get(PINNED_GS10, timeout=20)

    manifest = manifest_r.json()
    baa_ext = parse_monthly_csv(baa_ext_r.text, "BAA")
    gs_ext = parse_monthly_csv(gs_ext_r.text, "GS10")

    baa_base = parse_monthly_csv(baa_base_r.text, "BAA")
    gs_base = parse_monthly_csv(gs_base_r.text, "GS10")

    baa = merge_pinned_with_extension(baa_base, baa_ext)
    gs10 = merge_pinned_with_extension(gs_base, gs_ext)

    latest_baa = baa.index[-1].strftime("%Y%m")
    latest_gs10 = gs10.index[-1].strftime("%Y%m")
    if latest_baa != latest_gs10:
        raise ValueError(
            f"credit fallback latest-month mismatch: {latest_baa} vs {latest_gs10}"
        )
    if month_lag(latest_baa, now) > 2:
        raise ValueError(f"credit fallback stale: latest {latest_baa}")

    ms = manifest.get("series") or {}
    for sid, latest in (("BAA", latest_baa), ("GS10", latest_gs10)):
        entry = ms.get(sid) or {}
        manifest_latest = str(entry.get("last") or "")[:7].replace("-", "")
        if manifest_latest != latest:
            raise ValueError(
                f"manifest/data latest mismatch for {sid}: "
                f"{manifest_latest} != {latest}"
            )
        if "fred.stlouisfed.org" not in str(entry.get("source") or ""):
            raise ValueError(f"{sid} fallback manifest does not identify FRED")

    meta = {
        "source": (
            "Pinned 1953+ credit history extended with "
            "MacroIntelligencePlatform FRED snapshot"
        ),
        "pinned_commit": PINNED_COMMIT,
        "extension_manifest_taken_at_utc": manifest.get("taken_at_utc"),
        "latest_month": latest_baa,
        "manifest_sha256": hashlib.sha256(manifest_r.content).hexdigest(),
        "baa_extension_sha256": hashlib.sha256(baa_ext_r.content).hexdigest(),
        "gs10_extension_sha256": hashlib.sha256(gs_ext_r.content).hexdigest(),
        "baa_pinned_base_sha256": hashlib.sha256(baa_base_r.content).hexdigest(),
        "gs10_pinned_base_sha256": hashlib.sha256(gs_base_r.content).hexdigest(),
    }
    baa.attrs.update(meta)
    gs10.attrs.update(meta)
    return baa, gs10, meta


def fetch_credit(now: datetime) -> tuple[pd.Series, pd.Series, dict[str, Any]]:
    errors = []
    try:
        baa = fetch_fred_monthly("BAA")
        gs10 = fetch_fred_monthly("GS10")
        latest_baa = baa.index[-1].strftime("%Y%m")
        latest_gs = gs10.index[-1].strftime("%Y%m")
        if latest_baa != latest_gs:
            raise ValueError(
                f"FRED latest-month mismatch {latest_baa} vs {latest_gs}"
            )
        if month_lag(latest_baa, now) > 2:
            raise ValueError(f"FRED monthly credit stale: {latest_baa}")
        return baa, gs10, {
            "source": "FRED direct monthly CSV",
            "latest_month": latest_baa,
            "baa_payload_sha256": baa.attrs.get("payload_sha256"),
            "gs10_payload_sha256": gs10.attrs.get("payload_sha256"),
        }
    except Exception as exc:
        errors.append(f"fred={exc!r}")

    try:
        return fetch_credit_fallback(now)
    except Exception as exc:
        errors.append(f"fallback={exc!r}")

    raise RuntimeError("all credit sources failed: " + "; ".join(errors))


def unzip_current_ff(url: str) -> tuple[str, dict[str, str]]:
    raw = get(url, timeout=45).content
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        names = [n for n in z.namelist() if n.lower().endswith(".csv")]
        if not names:
            raise ValueError(f"no CSV in {url}")
        member = names[0]
        text = z.read(member).decode("utf-8", "replace")
    return text, {
        "url": url,
        "zip_member": member,
        "zip_sha256": hashlib.sha256(raw).hexdigest(),
    }


def build_ff_scores() -> tuple[dict[str, dict], dict[str, str]]:
    ff25_text, ff25_prov = unzip_current_ff(FF25_URL)
    ff12_text, ff12_prov = unzip_current_ff(FF12_URL)
    ff3_text, ff3_prov = unzip_current_ff(FF3_URL)

    _, r25 = parse_portfolio_block(
        ff25_text, "Average Value Weighted Returns -- Monthly", 25
    )
    h12, r12 = parse_portfolio_block(
        ff12_text, "Average Value Weighted Returns -- Monthly", 12
    )
    ff3 = parse_ff3(ff3_text)

    money_i = h12.index("Money")
    ff3_map = {ym: (i, mkt, smb) for i, (ym, mkt, smb) in enumerate(ff3)}
    r12_map = {ym: (i, vals) for i, (ym, vals) in enumerate(r12)}

    rows = []
    for i in range(5, len(r25)):
        ym, _ = r25[i]
        if ym not in ff3_map or ym not in r12_map:
            continue
        fi, _, _ = ff3_map[ym]
        qi, _ = r12_map[ym]
        if fi < 5 or qi < 5:
            continue
        p6 = [
            compounded([r25[k][1][j] for k in range(i - 5, i + 1)])
            for j in range(25)
        ]
        mkt6 = compounded([ff3[k][1] for k in range(fi - 5, fi + 1)])
        money6 = compounded(
            [r12[k][1][money_i] for k in range(qi - 5, qi + 1)]
        )
        rows.append(
            {
                "ym": ym,
                "portfolio_exhaustion_raw": (
                    1.0 - sum(x > mkt6 for x in p6) / 25.0
                ),
                "size_weakness_raw": -compounded(
                    [ff3[k][2] for k in range(fi - 5, fi + 1)]
                ),
                "finance_weakness_raw": -(money6 - mkt6),
            }
        )

    for raw_name, score_name in (
        ("portfolio_exhaustion_raw", "portfolio_exhaustion_score"),
        ("size_weakness_raw", "size_weakness_score"),
        ("finance_weakness_raw", "finance_weakness_score"),
    ):
        vals = [x[raw_name] for x in rows]
        for i, row in enumerate(rows):
            row[score_name] = expanding_pct(vals, i)

    meta = {
        "ff25_last_month": r25[-1][0],
        "ff12_last_month": r12[-1][0],
        "ff3_last_month": ff3[-1][0],
        "source": "Kenneth R. French official current ZIPs",
        "ff25_provenance": ff25_prov,
        "ff12_provenance": ff12_prov,
        "ff3_provenance": ff3_prov,
    }
    return {x["ym"]: x for x in rows}, meta


def build_credit_scores(
    baa: pd.Series, gs10: pd.Series
) -> dict[str, dict]:
    common = sorted(set(baa.index) & set(gs10.index))
    levels = [
        (d.strftime("%Y%m"), float(baa.loc[d] - gs10.loc[d]))
        for d in common
    ]
    rows = []
    for i in range(6, len(levels)):
        raw = max(
            levels[i][1] - levels[i - 3][1],
            levels[i][1] - levels[i - 6][1],
        )
        rows.append({"ym": levels[i][0], "spread_shock_raw": raw})
    vals = [x["spread_shock_raw"] for x in rows]
    for i, row in enumerate(rows):
        row["spread_shock_score"] = expanding_pct(vals, i)
    return {x["ym"]: x for x in rows}


def build_effective_states(
    ff: dict[str, dict], credit: dict[str, dict]
) -> list[dict]:
    effective = sorted(
        set(add_months(x, 2) for x in ff)
        & set(add_months(x, 1) for x in credit)
    )
    rows = []
    for eff in effective:
        fy = add_months(eff, -2)
        cy = add_months(eff, -1)
        f, c = ff.get(fy), credit.get(cy)
        if not f or not c:
            continue
        parts = {
            "spread_shock_score": float(c["spread_shock_score"]),
            "finance_weakness_score": float(f["finance_weakness_score"]),
            "size_weakness_score": float(f["size_weakness_score"]),
            "portfolio_exhaustion_score": float(
                f["portfolio_exhaustion_score"]
            ),
        }
        route = math.prod(parts.values()) ** 0.25
        lead = parts["finance_weakness_score"] - parts["spread_shock_score"]
        rows.append(
            {
                "effective_month": eff,
                "ff_source_month": fy,
                "credit_source_month": cy,
                "effective_history_months": len(rows) + 1,
                **parts,
                "route_a_ng1": route,
                "financial_lead_gap_raw": lead,
            }
        )
    return rows


def fetch_spy() -> pd.Series:
    response = get(YAHOO_SPY, timeout=20)
    obj = response.json()
    x = obj["chart"]["result"][0]
    ts = x["timestamp"]
    close = x["indicators"]["quote"][0]["close"]
    idx = (
        pd.to_datetime(ts, unit="s", utc=True)
        .tz_convert(None)
        .normalize()
    )
    s = pd.Series(pd.to_numeric(close, errors="coerce"), index=idx).dropna()
    s = s[~s.index.duplicated(keep="last")].sort_index()
    if len(s) < 600:
        raise ValueError("SPY history too short")
    s.attrs["source"] = "Yahoo Finance SPY unadjusted Close"
    s.attrs["payload_sha256"] = hashlib.sha256(response.content).hexdigest()
    s.attrs["latest_date"] = pd.Timestamp(s.index[-1]).date().isoformat()
    return s


def top_gate(price: pd.Series, ym: str) -> dict[str, Any]:
    y, m = int(ym[:4]), int(ym[4:6])
    start = pd.Timestamp(year=y, month=m, day=1)
    end = start + pd.offsets.MonthEnd(1)
    month = price.loc[(price.index >= start) & (price.index <= end)]
    if month.empty:
        raise ValueError(f"no SPY data for completed month {ym}")
    asof = pd.Timestamp(month.index[-1])
    close = float(month.iloc[-1])
    win = price.loc[
        (price.index >= asof - pd.DateOffset(months=24))
        & (price.index <= asof)
    ]
    high = float(win.max())
    high_date = pd.Timestamp(win.idxmax())
    within = close >= 0.95 * high
    recent = high_date >= asof - pd.DateOffset(months=3)
    return {
        "asof": asof.date().isoformat(),
        "close": close,
        "high24": high,
        "high24_date": high_date.date().isoformat(),
        "within_5pct": bool(within),
        "high_within_3m": bool(recent),
        "passes": bool(within and recent),
    }


def select_completed_state(
    states: list[dict[str, Any]],
    completed_month: str,
) -> dict[str, Any]:
    eligible = [x for x in states if x["effective_month"] <= completed_month]
    if not eligible:
        raise ValueError("no completed effective NG3 state")
    x = eligible[-1]
    if x["effective_month"] != completed_month:
        raise ValueError(
            "NG3 monthly inputs are stale: "
            f"latest effective {x['effective_month']} != completed {completed_month}"
        )
    return x


def build_snapshot(
    now: datetime | None = None,
    price: pd.Series | None = None,
) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    completed = completed_month_ym(now)

    ff, ff_meta = build_ff_scores()
    baa, gs10, credit_meta = fetch_credit(now)
    credit = build_credit_scores(baa, gs10)
    states = build_effective_states(ff, credit)
    x = select_completed_state(states, completed)

    phase_gate = (
        x["effective_history_months"] >= WARMUP_MONTHS
        and x["financial_lead_gap_raw"] >= LEAD_GAP_MIN
    )
    route_gate = x["route_a_ng1"] >= THRESHOLD
    price = price if price is not None else fetch_spy()
    gate = top_gate(price, x["effective_month"])
    armed = bool(phase_gate and route_gate and gate["passes"])

    prospective = x["effective_month"] >= FIRST_PROSPECTIVE_EFFECTIVE_MONTH
    evidence_phase = (
        "PROSPECTIVE"
        if prospective
        else "RETROSPECTIVE_TRAINING_DIAGNOSTIC"
    )

    return {
        "schema_version": "market-top-route-a-ng3-forward-1",
        "generated_at": now.astimezone(timezone.utc).isoformat(),
        "research_only": True,
        "production_effect": "none",
        "validation_status": "PROSPECTIVE_VALIDATION_PENDING",
        "effective_month": x["effective_month"],
        "evidence_phase": evidence_phase,
        "counts_toward_prospective_validation": bool(prospective),
        "prospective_start_effective_month": (
            FIRST_PROSPECTIVE_EFFECTIVE_MONTH
        ),
        "source_months": {
            "fama_french": x["ff_source_month"],
            "credit": x["credit_source_month"],
        },
        "components": {
            "spread_shock_score": x["spread_shock_score"],
            "finance_weakness_score": x["finance_weakness_score"],
            "size_weakness_score": x["size_weakness_score"],
            "portfolio_exhaustion_score": (
                x["portfolio_exhaustion_score"]
            ),
            "financial_lead_gap_raw": x["financial_lead_gap_raw"],
            "effective_history_months": x["effective_history_months"],
        },
        "route_a_ng1_score": x["route_a_ng1"],
        "route_a_ng3_score": x["route_a_ng1"],
        "gates": {
            "route_ge_85": bool(route_gate),
            "lead_gap_ge_10": bool(
                x["financial_lead_gap_raw"] >= LEAD_GAP_MIN
            ),
            "warmup_ge_120": bool(
                x["effective_history_months"] >= WARMUP_MONTHS
            ),
            "phase_gate": bool(phase_gate),
            "top_location": gate,
        },
        "state": "ARMED" if armed else "IDLE",
        "sources": {
            "fama_french": ff_meta,
            "credit": credit_meta,
            "price": {
                "source": price.attrs.get(
                    "source",
                    "Yahoo Finance SPY unadjusted Close",
                ),
                "payload_sha256": price.attrs.get("payload_sha256"),
                "latest_date": price.attrs.get("latest_date"),
            },
        },
        "governance": {
            "historical_validation_authorized": False,
            "production_promotion_authorized": False,
            "post_preregistration_tuning_allowed": False,
        },
    }


def load_history() -> list[dict[str, Any]]:
    if not OUT_HISTORY.exists():
        return []
    obj = json.loads(OUT_HISTORY.read_text(encoding="utf-8"))
    return list(obj.get("history") or [])


def load_monthly_snapshot_book() -> dict[str, Any]:
    if not OUT_MONTHLY.exists():
        return {
            "schema_version": "market-top-route-a-ng3-monthly-snapshots-1",
            "research_only": True,
            "production_effect": "none",
            "prospective_start_effective_month": (
                FIRST_PROSPECTIVE_EFFECTIVE_MONTH
            ),
            "snapshots": [],
        }
    return json.loads(OUT_MONTHLY.read_text(encoding="utf-8"))


def freeze_monthly_signal_snapshot(
    snapshot: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], bool]:
    book = load_monthly_snapshot_book()
    if not snapshot["counts_toward_prospective_validation"]:
        return snapshot, book, False

    month = str(snapshot["effective_month"])
    existing = next(
        (
            x
            for x in book.get("snapshots") or []
            if str(x.get("effective_month")) == month
        ),
        None,
    )
    if existing is not None:
        return existing, book, False

    frozen = json.loads(json.dumps(snapshot))
    frozen["evidence_lock"] = {
        "mode": "FIRST_SUCCESSFUL_POST_MONTH_CLOSE_SNAPSHOT",
        "frozen_at": snapshot["generated_at"],
        "effective_month": month,
        "immutable_signal_fields": True,
    }

    snapshots = list(book.get("snapshots") or [])
    snapshots.append(frozen)
    snapshots = sorted(
        snapshots,
        key=lambda x: str(x.get("effective_month") or ""),
    )
    book = {
        "schema_version": "market-top-route-a-ng3-monthly-snapshots-1",
        "research_only": True,
        "production_effect": "none",
        "prospective_start_effective_month": (
            FIRST_PROSPECTIVE_EFFECTIVE_MONTH
        ),
        "snapshots": snapshots,
        "summary": {
            "frozen_prospective_months": len(snapshots),
            "first_frozen_effective_month": (
                snapshots[0]["effective_month"] if snapshots else None
            ),
            "latest_frozen_effective_month": (
                snapshots[-1]["effective_month"] if snapshots else None
            ),
        },
    }
    return frozen, book, True


def load_episode_ledger() -> dict[str, Any]:
    if not OUT_EPISODES.exists():
        return {
            "schema_version": "market-top-route-a-ng3-episodes-1",
            "research_only": True,
            "production_effect": "none",
            "protocol": "market-top-route-a-ng3-evidence-protocol-1",
            "episodes": [],
            "summary": {
                "complete_252_session_episodes": 0,
                "minimum_for_promotion_review": 4,
                "review_eligible": False,
                "automatic_promotion": False,
                "action_signal": None,
            },
        }
    return json.loads(OUT_EPISODES.read_text(encoding="utf-8"))


def classify_252(metrics: dict[str, Any]) -> str | None:
    if not metrics.get("complete"):
        return None
    worst = float(metrics["worst_return_from_anchor_pct"])
    forward = float(metrics["forward_return_pct"])
    if worst <= -15.0:
        return "MAJOR_TOP"
    if worst > -7.5 and forward > 0.0:
        return "CLEAR_FALSE"
    return "CORRECTION_OR_AMBIGUOUS"


def evaluate_horizon(
    price: pd.Series,
    *,
    anchor_date: str,
    anchor_close: float,
    sessions: int,
) -> dict[str, Any]:
    anchor = pd.Timestamp(anchor_date)
    after = price.loc[price.index > anchor]
    observed = min(len(after), sessions)
    if observed == 0:
        return {
            "sessions_required": sessions,
            "sessions_observed": 0,
            "complete": False,
            "asof": None,
            "forward_return_pct": None,
            "worst_return_from_anchor_pct": None,
            "max_peak_to_trough_dd_pct": None,
        }

    path = after.iloc[:sessions]
    forward = (float(path.iloc[-1]) / float(anchor_close) - 1.0) * 100.0
    worst = (float(path.min()) / float(anchor_close) - 1.0) * 100.0

    full = pd.concat(
        [
            pd.Series(
                [float(anchor_close)],
                index=pd.DatetimeIndex([anchor]),
                dtype=float,
            ),
            path.astype(float),
        ]
    )
    dd = (full / full.cummax() - 1.0) * 100.0

    return {
        "sessions_required": sessions,
        "sessions_observed": observed,
        "complete": bool(len(after) >= sessions),
        "asof": pd.Timestamp(path.index[-1]).date().isoformat(),
        "forward_return_pct": float(forward),
        "worst_return_from_anchor_pct": float(worst),
        "max_peak_to_trough_dd_pct": float(dd.min()),
    }


def update_episode_ledger(
    snapshot: dict[str, Any],
    price: pd.Series,
    *,
    observed_at: str | None = None,
) -> dict[str, Any]:
    ledger = load_episode_ledger()
    episodes = list(ledger.get("episodes") or [])

    current_month = str(snapshot["effective_month"])
    is_prospective = bool(snapshot["counts_toward_prospective_validation"])
    state = str(snapshot["state"])

    open_episode = next(
        (x for x in reversed(episodes) if x.get("signal_status") == "OPEN"),
        None,
    )

    if is_prospective:
        if state == "ARMED":
            needs_new = open_episode is None
            if open_episode is not None:
                last = str(open_episode["last_armed_effective_month"])
                if current_month == last:
                    needs_new = False
                elif current_month == add_months(last, 1):
                    open_episode["last_armed_effective_month"] = current_month
                    needs_new = False
                else:
                    open_episode["signal_status"] = "CLOSED"
                    open_episode["closed_reason"] = "NONCONTIGUOUS_EFFECTIVE_MONTH"
                    open_episode["closed_before_effective_month"] = current_month
                    open_episode = None
                    needs_new = True

            if needs_new:
                gate = snapshot["gates"]["top_location"]
                open_episode = {
                    "episode_id": f"NG3-{current_month}",
                    "signal_status": "OPEN",
                    "start_effective_month": current_month,
                    "last_armed_effective_month": current_month,
                    "closed_effective_month": None,
                    "closed_reason": None,
                    "anchor_date": gate["asof"],
                    "anchor_close": float(gate["close"]),
                    "source_months_at_start": dict(snapshot["source_months"]),
                    "source_provenance_at_start": dict(
                        snapshot.get("sources") or {}
                    ),
                    "start_score": float(snapshot["route_a_ng3_score"]),
                    "start_financial_lead_gap_raw": float(
                        snapshot["components"]["financial_lead_gap_raw"]
                    ),
                    "outcomes": {},
                    "classification_252": None,
                }
                episodes.append(open_episode)
        elif state == "IDLE" and open_episode is not None:
            last = str(open_episode["last_armed_effective_month"])
            if current_month > last:
                open_episode["signal_status"] = "CLOSED"
                open_episode["closed_effective_month"] = current_month
                open_episode["closed_reason"] = "FIRST_COMPLETED_IDLE_MONTH"

    for ep in episodes:
        previous = dict(ep.get("outcomes") or {})
        outcomes = {}
        for horizon in (63, 126, 252):
            key = str(horizon)
            prior = previous.get(key) or {}
            if prior.get("complete") is True:
                outcomes[key] = prior
            else:
                outcomes[key] = evaluate_horizon(
                    price,
                    anchor_date=str(ep["anchor_date"]),
                    anchor_close=float(ep["anchor_close"]),
                    sessions=horizon,
                )
        ep["outcomes"] = outcomes
        ep["classification_252"] = classify_252(outcomes["252"])

    complete_252 = sum(
        1
        for ep in episodes
        if (ep.get("outcomes") or {}).get("252", {}).get("complete")
    )
    ledger = {
        "schema_version": "market-top-route-a-ng3-episodes-1",
        "generated_at": observed_at or snapshot["generated_at"],
        "research_only": True,
        "production_effect": "none",
        "protocol": "market-top-route-a-ng3-evidence-protocol-1",
        "prospective_start_effective_month": FIRST_PROSPECTIVE_EFFECTIVE_MONTH,
        "episodes": episodes,
        "summary": {
            "prospective_episode_count": len(episodes),
            "complete_252_session_episodes": complete_252,
            "minimum_for_promotion_review": 4,
            "review_eligible": bool(complete_252 >= 4),
            "automatic_promotion": False,
            "action_signal": None,
        },
    }
    return ledger


def write_outputs(snapshot: dict[str, Any], price: pd.Series) -> None:
    OUT_CURRENT.parent.mkdir(parents=True, exist_ok=True)

    canonical, monthly_book, _ = freeze_monthly_signal_snapshot(snapshot)
    OUT_MONTHLY.write_text(
        json.dumps(monthly_book, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    current_view = json.loads(json.dumps(canonical))
    current_view["monitor_checked_at"] = snapshot["generated_at"]
    current_view["signal_snapshot_frozen"] = bool(
        canonical.get("evidence_lock")
    )
    OUT_CURRENT.write_text(
        json.dumps(current_view, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    hist = load_history()
    row = {
        "effective_month": canonical["effective_month"],
        "generated_at": canonical["generated_at"],
        "evidence_phase": canonical["evidence_phase"],
        "counts_toward_prospective_validation": (
            canonical["counts_toward_prospective_validation"]
        ),
        "route_a_ng3_score": canonical["route_a_ng3_score"],
        "financial_lead_gap_raw": (
            canonical["components"]["financial_lead_gap_raw"]
        ),
        "phase_gate": canonical["gates"]["phase_gate"],
        "top_location_pass": canonical["gates"]["top_location"]["passes"],
        "state": canonical["state"],
    }
    by_month = {x["effective_month"]: x for x in hist}
    by_month[row["effective_month"]] = row
    rows = [by_month[k] for k in sorted(by_month)]
    OUT_HISTORY.write_text(
        json.dumps(
            {
                "schema_version": "market-top-route-a-ng3-history-1",
                "research_only": True,
                "history": rows[-240:],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


    ledger = update_episode_ledger(
        canonical,
        price,
        observed_at=snapshot["generated_at"],
    )
    OUT_EPISODES.write_text(
        json.dumps(ledger, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    price = fetch_spy()
    x = build_snapshot(price=price)
    print(json.dumps(x, ensure_ascii=False, indent=2))
    if not args.dry_run:
        write_outputs(x, price)


if __name__ == "__main__":
    main()
