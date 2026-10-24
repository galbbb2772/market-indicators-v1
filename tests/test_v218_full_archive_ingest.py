"""Audit downloader must never turn missing provider entitlement into fake history."""
from __future__ import annotations
import os
import pandas as pd
import pytest
from research.v218_full_archive_ingest import (
    safe_filename,authorize_manifest,read_verify_stock_parquet,run
)

class Resp:
    def __init__(self,data,status=200):
        self.data=data;self.status_code=status
    def json(self):return self.data
    def raise_for_status(self):
        if self.status_code>=400:raise RuntimeError("test HTTP fail")

class Fake:
    def __init__(self,answer):self.answer=answer
    def get(self,*a,**kw):return self.answer


def test_manifest_blocks_without_existing_legal_access():
    with pytest.raises(RuntimeError,match="BLOCKED_NO_AUTHORIZED"):
        authorize_manifest(Fake(None),"2000-01-01","2026-10-22","")


def test_manifest_rejects_duplicate_and_forged_external_domain():
    item={"date":"2021-12-15","download_url":"https://marketparquet.com/api/data/download/stock_daily/2021-12-15.parquet"}
    ok=authorize_manifest(Fake(Resp({"files":[item]})),"2000-01-01","2026-10-22","DUMMY_TEST_KEY")
    assert len(ok)==1 and ok[0]["filename"]=="stock_daily_2021-12-15.parquet"
    with pytest.raises(ValueError,match="duplicate"):
        authorize_manifest(Fake(Resp({"files":[item,item]})),"2000-01-01","2026-10-22","DUMMY_TEST_KEY")
    forged=dict(item,download_url="https://attacker.invalid/fake.parquet")
    with pytest.raises(ValueError,match="unapproved"):
        authorize_manifest(Fake(Resp({"files":[forged]})),"2000-01-01","2026-10-22","DUMMY_TEST_KEY")


def test_runnable_archive_no_key_produces_nothing_in_market_history(tmp_path,monkeypatch):
    monkeypatch.delenv("MARKETPARQUET_API_KEY",raising=False)
    with pytest.raises(RuntimeError,match="BLOCKED_NO_AUTHORIZED"):
        run("2000-01-01","2026-10-22",tmp_path)
    assert not list(tmp_path.glob("**/*.parquet"))


def test_stock_partition_validation_no_hypothetical_cs_certification(monkeypatch):
    frame=pd.DataFrame({"date":["2021-12-15"]*1001,
                       "symbol":[f"STK{i}" for i in range(1001)],
                       "close":[12.0]*1001,
                       "asset_type":["Stock"]*1001})
    monkeypatch.setattr(pd,"read_parquet",lambda *a,**k:frame)
    r=read_verify_stock_parquet(b"PAR1"+b"data"+b"PAR1","2021-12-15")
    assert r["rows"]==1001
    bad=frame.copy();bad.loc[5,"asset_type"]="ETF"
    monkeypatch.setattr(pd,"read_parquet",lambda *a,**k:bad)
    with pytest.raises(ValueError,match="ETF"):
        read_verify_stock_parquet(b"PAR1"+b"data"+b"PAR1","2021-12-15")


def test_bad_date_and_filename_fail_closed():
    with pytest.raises(ValueError):safe_filename("2026-99-99")
