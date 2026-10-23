"""Offline contract tests for Massive source readiness; do not require a key."""
from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from research import provider_audit_massive_v218 as m

DAY = "2026-10-22"
MILLIS = int(datetime(2026, 10, 22, 20, 0, tzinfo=timezone.utc).timestamp() * 1000)


def bar(ticker, close=10.0, stamp=MILLIS):
    return {"T": ticker, "c": close, "h": 10.5, "l": 9.5, "t": stamp}


def grouped(*bars, adjusted=True):
    return {"status": "OK", "adjusted": adjusted, "results": list(bars)}


def test_grouped_shape_rejects_etf_inclusion_as_universe_proof(monkeypatch):
    monkeypatch.setattr(m, "MIN_GROUPED_ROWS", 2)
    info, tickers = m.audit_grouped(grouped(bar("AAPL"), bar("SPY")), DAY)
    assert info["grouped_rows"] == 2
    assert info["includes_non_common_securities"] is True
    assert tickers == {"AAPL", "SPY"}


def test_grouped_requires_adjusted_and_unique(monkeypatch):
    monkeypatch.setattr(m, "MIN_GROUPED_ROWS", 2)
    with pytest.raises(RuntimeError, match="not explicitly adjusted"):
        m.audit_grouped(grouped(bar("AAPL"), bar("SPY"), adjusted=False), DAY)
    with pytest.raises(RuntimeError, match="duplicated"):
        m.audit_grouped(grouped(bar("AAPL"), bar("AAPL")), DAY)


def test_grouped_rejects_wrong_market_date_and_bad_ohlc(monkeypatch):
    monkeypatch.setattr(m, "MIN_GROUPED_ROWS", 2)
    prior = MILLIS - 86_400_000
    with pytest.raises(RuntimeError, match="mismatch"):
        m.audit_grouped(grouped(bar("AAPL", stamp=prior), bar("SPY")), DAY)
    with pytest.raises(RuntimeError, match="price range"):
        m.audit_grouped(grouped(bar("AAPL", close=11.0), bar("SPY")), DAY)


def test_reference_eligible_security_types_are_only_common_and_common_adr():
    assert m.ELIGIBLE_TYPES == ("CS", "ADRC")
    assert "ETF" not in m.ELIGIBLE_TYPES


def test_reference_pagination_and_type_guard(monkeypatch):
    data = [
        {"status": "OK", "results": [{"ticker": "A", "type": "CS", "market": "stocks",
                                    "active": True, "primary_exchange": "XNYS"}],
         "next_url": "https://api.massive.com/v3/reference/tickers?cursor=two"},
        {"status": "OK", "results": [{"ticker": "B", "type": "CS", "market": "stocks",
                                    "active": True, "primary_exchange": "XNAS"}]},
    ]
    calls = []
    def fake_request(session, url, key, params=None):
        calls.append((url, params))
        return data[len(calls) - 1]
    monkeypatch.setattr(m, "request_json", fake_request)
    symbols, metas, pages = m.reference_universe(None, "dummy", DAY, "CS")
    assert symbols == {"A", "B"} and pages == 2
    assert {x["exchange"] for x in metas} == {"XNYS", "XNAS"}
    assert calls[1][1] is None


def test_reference_rejects_bad_ticker_type(monkeypatch):
    def fake_request(*args, **kwargs):
        return {"status": "OK", "results": [
            {"ticker": "SPY", "type": "ETF", "market": "stocks", "active": True}
        ]}
    monkeypatch.setattr(m, "request_json", fake_request)
    with pytest.raises(RuntimeError, match="contract violation"):
        m.reference_universe(None, "dummy", DAY, "CS")


def test_reference_full_page_without_cursor_is_not_certified(monkeypatch):
    def fake_request(*args, **kwargs):
        return {"status": "OK", "results": [
            {"ticker": f"C{i:04d}", "type": "CS", "market": "stocks",
             "active": True, "primary_exchange": "XNYS"}
            for i in range(1000)
        ]}
    monkeypatch.setattr(m, "request_json", fake_request)
    with pytest.raises(RuntimeError, match="possibly truncated"):
        m.reference_universe(None, "dummy", DAY, "CS")


def test_request_json_never_exposes_key_in_http_error():
    class FakeResponse:
        status_code = 403
    class FakeSession:
        def get(self, *args, **kwargs):
            return FakeResponse()
    with pytest.raises(RuntimeError, match="HTTP 403") as e:
        m.request_json(FakeSession(), m.BASE + "/v3/reference/tickers", "TOP_SECRET_VALUE")
    assert "TOP_SECRET_VALUE" not in str(e.value)


def test_full_audit_does_not_promote_frozen_score(monkeypatch):
    tickers = [f"C{i:04d}" for i in range(1001)]
    rows = [bar(ticker) for ticker in tickers] + [bar("SPY")]
    def fake_request(session, url, key, params=None):
        if "/v2/aggs/grouped/" in url:
            return grouped(*rows)
        if params and params.get("type") == "CS":
            return {"status": "OK", "results": [
                {"ticker": t, "type": "CS", "market": "stocks", "active": True, "primary_exchange": "XNYS"}
                for t in tickers
            ]}
        return {"status": "OK", "results": []}
    monkeypatch.setattr(m, "request_json", fake_request)
    result = m.run_audit(None, "dummy", DAY)
    assert result["classification"]["qualified_bars"] == 1001
    assert result["classification"]["excluded_or_unclassified_bars"] == 1
    assert result["production_eligible"] is False
    assert result["frozen_score_comparable"] is False
    assert result["status"] == "PROVIDER_SOURCE_AUDIT_ONLY"
