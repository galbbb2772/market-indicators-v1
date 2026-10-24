"""Public discontinued WIKI archive probe must be source-scoped and fail closed."""
from pathlib import Path
import pandas as pd
import pytest
from research.v218_wiki_free_2000_2018_schema_probe import inspect,HANDLE,RESULT


def test_public_wiki_is_separate_from_original_2019_source():
    assert HANDLE=="marketneutral/quandl-wiki-prices-us-equites"
    assert "WIKI" in RESULT


def test_valid_csv_can_be_detected_without_scanning_historical_paid_prices(tmp_path):
    df=pd.DataFrame({"ticker":["AAPL","YHOO"],"date":["2000-01-03","2000-01-03"],
                     "adj_close":[1.0,2.0]})
    df.to_csv(tmp_path/"prices.csv",index=False)
    report=inspect(tmp_path)
    assert report["status"]==RESULT
    assert report["prices"][0]["status"]=="SCHEMA_RELEVANT"
    assert not report["real_prices_actually_scored"]
    assert not report["full_all_US_delisted_stock_universe_PIT_proven"]
    assert not report["data_ingested_into_approved_2019_2026_history"]


def test_empty_dataset_fails(tmp_path):
    with pytest.raises(ValueError,match="no usable files"):
        inspect(tmp_path)


def test_unrelated_dataset_fails(tmp_path):
    pd.DataFrame({"text":["not the expected prices"]}).to_csv(tmp_path/"bad.csv",index=False)
    with pytest.raises(ValueError,match="no Kaggle historical price file"):
        inspect(tmp_path)
