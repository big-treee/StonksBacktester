import datetime
from unittest.mock import MagicMock

import pytest

from core.events import SignalEvent
from risk.position_sizer import (
    ATRPositionSizer,
    FixedDollar,
    FixedFractional,
    FixedShares,
    KellyCriterion,
    RiskPercentage,
    VolatilityPositionSizer,
)


@pytest.fixture
def mock_portfolio():
    portfolio = MagicMock()
    # mock positions.
    portfolio.positions.current_positions = {"RELIANCE.NS": 0, "TCS.NS": 100}

    # mock holdings.
    portfolio.holdings.current_holdings = {
        "RELIANCE.NS": 0.0,
        "TCS.NS": 15000.0,
        "cash": 85000.0,
        "commission": 0.0,
        "total": 100000.0,
    }

    # mock data handler.
    portfolio.data_handler.get_latest_bar_value.return_value = 150.0

    # mock for atr and volatility.
    mock_bars = []
    # days of mock prices.
    for i in range(20):
        bar = (None, {"Open": 150.0 + i, "High": 155.0 + i, "Low": 145.0 + i, "Close": 152.0 + i})
        mock_bars.append(bar)
    portfolio.data_handler.get_latest_bars.return_value = mock_bars

    return portfolio


def test_fixed_shares_sizer(mock_portfolio):
    sizer = FixedShares(shares=200)
    signal = SignalEvent(1, "RELIANCE.NS", datetime.datetime.now(), "LONG", 1.0)
    order = sizer.size_order(signal, mock_portfolio)
    assert order is not None
    assert order.quantity == 200


def test_fixed_dollar_sizer(mock_portfolio):
    sizer = FixedDollar(dollar_amount=15000.0)
    signal = SignalEvent(1, "RELIANCE.NS", datetime.datetime.now(), "LONG", 1.0)
    order = sizer.size_order(signal, mock_portfolio)
    assert order is not None
    assert order.quantity == 100


def test_fixed_fractional_sizer(mock_portfolio):
    sizer = FixedFractional(fraction=0.1)
    signal = SignalEvent(1, "RELIANCE.NS", datetime.datetime.now(), "LONG", 1.0)
    order = sizer.size_order(signal, mock_portfolio)
    assert order is not None
    assert order.quantity == 66


def test_risk_percentage_sizer(mock_portfolio):
    sizer = RiskPercentage(risk_pct=0.01, stop_loss_pct=0.05)
    signal = SignalEvent(1, "RELIANCE.NS", datetime.datetime.now(), "LONG", 1.0)
    order = sizer.size_order(signal, mock_portfolio)
    assert order is not None
    assert order.quantity == 133


def test_kelly_criterion_sizer(mock_portfolio):
    sizer = KellyCriterion(win_rate=0.55, payoff_ratio=1.5, kelly_fraction=0.5)
    signal = SignalEvent(1, "RELIANCE.NS", datetime.datetime.now(), "LONG", 1.0)
    order = sizer.size_order(signal, mock_portfolio)
    assert order is not None
    assert order.quantity == 83


def test_atr_sizer(mock_portfolio):
    sizer = ATRPositionSizer(atr_period=14, risk_pct=0.01, atr_multiplier=2.0)
    signal = SignalEvent(1, "RELIANCE.NS", datetime.datetime.now(), "LONG", 1.0)
    order = sizer.size_order(signal, mock_portfolio)
    assert order is not None
    # risk . tr is consistently . atr . risk per share . .
    assert order.quantity == 50


def test_volatility_sizer(mock_portfolio):
    sizer = VolatilityPositionSizer(lookback=10, target_volatility=0.10)
    signal = SignalEvent(1, "RELIANCE.NS", datetime.datetime.now(), "LONG", 1.0)
    order = sizer.size_order(signal, mock_portfolio)
    assert order is not None
    assert order.quantity > 0
