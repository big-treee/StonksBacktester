from unittest.mock import MagicMock, patch

from factors.analytics import FactorAnalytics
from factors.engine import FactorEngine


@patch("factors.engine.UniverseEngine.expand_symbol_list")
def test_factor_size_mocked(mock_expand):
    mock_expand.return_value = ["A.NS", "B.NS", "C.NS", "D.NS", "E.NS"]

    with patch("factors.engine.UniverseEngine.get_all_stocks") as mock_get_stocks:
        mock_stock_A = MagicMock(symbol="A.NS", market_cap_category="LARGECAP")
        mock_stock_B = MagicMock(symbol="B.NS", market_cap_category="MIDCAP")
        mock_stock_C = MagicMock(symbol="C.NS", market_cap_category="SMALLCAP")
        mock_stock_D = MagicMock(symbol="D.NS", market_cap_category="LARGECAP")
        mock_stock_E = MagicMock(symbol="E.NS", market_cap_category="MIDCAP")

        mock_get_stocks.return_value = [
            mock_stock_A,
            mock_stock_B,
            mock_stock_C,
            mock_stock_D,
            mock_stock_E,
        ]

        engine = FactorEngine()
        ranked = engine.rank_universe(["DUMMY"], "SIZE")

        assert len(ranked) == 5
        # c should have the highest raw score . for small cap.
        assert ranked[0]["symbol"] == "C.NS"
        assert ranked[0]["raw_value"] == 3.0
        assert ranked[0]["z_score"] > 0


def test_quantile_generation():
    ranked_universe = [
        {"symbol": "A", "z_score": 1.5},
        {"symbol": "B", "z_score": 1.0},
        {"symbol": "C", "z_score": 0.5},
        {"symbol": "D", "z_score": 0.0},
        {"symbol": "E", "z_score": -0.5},
        {"symbol": "F", "z_score": -1.0},
    ]

    quintiles = FactorAnalytics.generate_quantile_portfolios(ranked_universe, quantiles=3)

    # items quantiles items per quantile.
    assert len(quintiles) == 3
    assert quintiles[1] == ["A", "B"]
    assert quintiles[2] == ["C", "D"]
    assert quintiles[3] == ["E", "F"]
