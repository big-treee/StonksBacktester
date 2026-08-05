from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd

from portfolio.construction import PortfolioConstructor


@patch("portfolio.construction.YahooDataHandler")
@patch("portfolio.construction.UniverseEngine")
def test_portfolio_construction_methods(mock_universe, mock_data_handler):
    mock_universe.get_all_stocks.return_value = []

    # mock price data.
    mock_dh = MagicMock()
    mock_dh.continue_backtest = False

    dates = pd.date_range(start="2022-01-01", periods=100)
    # generate some random walks.
    np.random.seed(42)
    p1 = np.cumprod(1 + np.random.normal(0.001, 0.02, 100)) * 100
    p2 = np.cumprod(1 + np.random.normal(0.0005, 0.015, 100)) * 100
    p_bench = np.cumprod(1 + np.random.normal(0.001, 0.01, 100)) * 100

    def get_latest_bars_side_effect(symbol, N):
        if symbol == "A.NS":
            return [(d, {"Close": p}) for d, p in zip(dates, p1)]
        elif symbol == "B.NS":
            return [(d, {"Close": p}) for d, p in zip(dates, p2)]
        elif symbol == "^NSEI":
            return [(d, {"Close": p}) for d, p in zip(dates, p_bench)]
        return []

    mock_dh.get_latest_bars.side_effect = get_latest_bars_side_effect
    mock_data_handler.return_value = mock_dh

    constructor = PortfolioConstructor()

    # test equal weight.
    res_equal = constructor.construct(["A.NS", "B.NS"], "EQUAL_WEIGHT")
    assert res_equal["weights"]["A.NS"] == 0.5
    assert res_equal["weights"]["B.NS"] == 0.5

    # test inverse volatility.
    res_vol = constructor.construct(["A.NS", "B.NS"], "VOLATILITY_WEIGHT")
    w_a = res_vol["weights"]["A.NS"]
    w_b = res_vol["weights"]["B.NS"]
    # a has higher vol so it should have lower weight.
    assert w_a < w_b
    assert round(w_a + w_b, 4) == 1.0

    # test risk parity.
    res_rp = constructor.construct(["A.NS", "B.NS"], "RISK_PARITY")
    assert "statistics" in res_rp
    assert "beta" in res_rp["statistics"]
    assert "expected_return" in res_rp["statistics"]
