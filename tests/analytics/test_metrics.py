import pandas as pd
import pytest

from analytics.metrics import MetricsEngine


@pytest.fixture
def dummy_data():
    dates = pd.date_range("2020-01-01", periods=5, freq="D")
    equity = pd.DataFrame(
        {
            "total": [100000, 101000, 100500, 102000, 105000],
            "returns": [0.0, 0.01, -0.00495, 0.0149, 0.0294],
        },
        index=dates,
    )

    trades = [
        {"pnl": 500, "holding_period": 2},
        {"pnl": -200, "holding_period": 1},
        {"pnl": 1000, "holding_period": 3},
    ]
    return equity, trades


def test_metrics_engine(dummy_data):
    equity, trades = dummy_data
    engine = MetricsEngine(equity, trades)

    metrics = engine.calculate_all()

    assert metrics["Total Trades"] == 3
    assert metrics["Win Rate (%)"] == (2 / 3) * 100
    assert metrics["Largest Win (INR)"] == 1000
    assert metrics["Largest Loss (INR)"] == -200
    assert "CAGR (%)" in metrics
    assert "Sharpe Ratio" in metrics
    assert "Max Drawdown (%)" in metrics


def test_metrics_engine_empty():
    engine = MetricsEngine(pd.DataFrame({"total": [], "returns": []}), [])
    metrics = engine.calculate_all()
    assert metrics["Total Trades"] == 0
    assert metrics["Sharpe Ratio"] == 0.0
