import pandas as pd
import pytest

from analytics.plots import PlotGenerator


@pytest.fixture
def dummy_data():
    dates = pd.date_range("2020-01-01", periods=10, freq="D")
    equity = pd.DataFrame(
        {
            "total": [100, 101, 102, 101, 105, 104, 106, 108, 107, 110],
            "returns": [0.0, 0.01, 0.01, -0.01, 0.04, -0.01, 0.02, 0.02, -0.01, 0.03],
        },
        index=dates,
    )

    trades = [{"pnl": 500, "holding_period": 2}, {"pnl": -200, "holding_period": 1}]
    return equity, trades


def test_plot_generator(dummy_data):
    equity, trades = dummy_data
    plotter = PlotGenerator(equity, trades)

    assert plotter.plot_equity_curve().startswith("iVBOR")
    assert plotter.plot_drawdowns().startswith("iVBOR")
    assert plotter.plot_monthly_heatmap().startswith("iVBOR")
    assert plotter.plot_trade_distribution().startswith("iVBOR")
    assert plotter.plot_rolling_sharpe(window=2).startswith("iVBOR")
