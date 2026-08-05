import pandas as pd
import pytest

from data.yahoo import YahooDataHandler


def test_prepare_symbol_frame_flattens_multiindex_and_deduplicates_dates():
    handler = YahooDataHandler.__new__(YahooDataHandler)
    dates = pd.to_datetime(["2020-01-01", "2020-01-01", "2020-01-02"])
    columns = pd.MultiIndex.from_tuples(
        [
            ("Close", "RELIANCE.NS"),
            ("Open", "RELIANCE.NS"),
        ]
    )
    raw = pd.DataFrame(
        [
            [100.0, 99.0],
            [101.0, 100.0],
            [102.0, 101.0],
        ],
        index=dates,
        columns=columns,
    )

    prepared = handler._prepare_symbol_frame(raw, "RELIANCE.NS")

    assert list(prepared.columns) == ["Close", "Open"]
    assert prepared.index.is_unique
    assert prepared.loc[pd.Timestamp("2020-01-01"), "Close"] == 101.0


def test_prepare_symbol_frame_rejects_empty_data():
    handler = YahooDataHandler.__new__(YahooDataHandler)

    with pytest.raises(ValueError, match="No usable historical data"):
        handler._prepare_symbol_frame(pd.DataFrame(), "RELIANCE.NS")
