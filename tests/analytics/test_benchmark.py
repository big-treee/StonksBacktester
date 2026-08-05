from unittest.mock import patch

import pandas as pd
import pytest

from analytics.benchmark import BenchmarkAnalyzer


@pytest.fixture
def dummy_data():
    dates = pd.date_range("2020-01-01", periods=10, freq="D")
    port = pd.Series([0.01, -0.01, 0.02, 0.01, -0.01, 0.01, 0.02, -0.01, 0.01, 0.01], index=dates)
    bench = pd.Series(
        [0.005, -0.005, 0.01, 0.005, -0.005, 0.005, 0.01, -0.005, 0.005, 0.005], index=dates
    )
    return port, bench


@patch("analytics.benchmark.yf.download")
def test_benchmark_analyzer(mock_download, dummy_data):
    port, bench = dummy_data

    # mock yfinance return.
    df = pd.DataFrame({"Close": [100 * (1 + b) for b in bench.cumsum()]}, index=bench.index)
    mock_download.return_value = df

    analyzer = BenchmarkAnalyzer(port, "^NSEI", "2020-01-01", "2020-01-10")
    metrics = analyzer.calculate_all()

    assert "Alpha (Annualized %)" in metrics
    assert "Beta" in metrics
    assert "Tracking Error (%)" in metrics
    assert "Information Ratio" in metrics


@patch("analytics.benchmark.yf.download")
def test_benchmark_empty(mock_download, dummy_data):
    port, _ = dummy_data
    mock_download.return_value = pd.DataFrame()

    analyzer = BenchmarkAnalyzer(port, "INVALID", "2020-01-01", "2020-01-10")
    metrics = analyzer.calculate_all()
    assert metrics == {}


@patch("analytics.benchmark.yf.download")
def test_benchmark_analyzer_handles_duplicate_dates(mock_download):
    dates = pd.to_datetime(
        [
            "2020-01-01",
            "2020-01-02",
            "2020-01-02",
            "2020-01-03",
        ]
    )
    port = pd.Series([0.0, 0.01, 0.02, -0.01], index=dates)
    mock_download.return_value = pd.DataFrame(
        {"Close": [100.0, 101.0, 102.0, 103.0]},
        index=dates,
    )

    analyzer = BenchmarkAnalyzer(port, "^NSEI", "2020-01-01", "2020-01-03")

    assert analyzer.aligned_portfolio.index.is_unique
    assert analyzer.aligned_benchmark.index.is_unique
    assert "Beta" in analyzer.calculate_all()
