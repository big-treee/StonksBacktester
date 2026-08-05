import datetime
from unittest.mock import MagicMock

import pytest

from core.events import OrderEvent
from risk.validators import (
    DailyLossLimit,
    MaxDrawdownStop,
    MaxOpenPositions,
    MaxPortfolioExposure,
    MaxPositionSize,
    SectorExposureLimit,
)


@pytest.fixture
def mock_portfolio():
    portfolio = MagicMock()
    portfolio.positions.current_positions = {"RELIANCE.NS": 500, "TCS.NS": 100}
    portfolio.holdings.current_holdings = {
        "RELIANCE.NS": 75000.0,
        "TCS.NS": 15000.0,
        "cash": 10000.0,
        "commission": 0.0,
        "total": 100000.0,
    }
    portfolio.data_handler.get_latest_bar_value.return_value = 150.0

    dt = datetime.datetime.now()
    portfolio.holdings.all_holdings = [{"datetime": dt, "total": 105000.0}]

    return portfolio


def test_max_position_size(mock_portfolio):
    validator = MaxPositionSize(max_shares=1000)
    order1 = OrderEvent("RELIANCE.NS", "MKT", 400, "BUY")
    assert validator.validate_order(order1, mock_portfolio) is True
    order2 = OrderEvent("RELIANCE.NS", "MKT", 600, "BUY")
    assert validator.validate_order(order2, mock_portfolio) is False


def test_max_portfolio_exposure(mock_portfolio):
    validator = MaxPortfolioExposure(max_exposure_pct=1.2)
    order1 = OrderEvent("INFY.NS", "MKT", 100, "BUY")
    assert validator.validate_order(order1, mock_portfolio) is True
    order2 = OrderEvent("INFY.NS", "MKT", 500, "BUY")
    assert validator.validate_order(order2, mock_portfolio) is False


def test_daily_loss_limit(mock_portfolio):
    validator_fail = DailyLossLimit(max_daily_loss=4000.0)
    validator_fail.current_date = datetime.datetime.now().date()
    validator_fail.start_of_day_equity = 105000.0

    order = OrderEvent("RELIANCE.NS", "MKT", 100, "BUY")
    assert validator_fail.validate_order(order, mock_portfolio) is False

    validator_pass = DailyLossLimit(max_daily_loss=6000.0)
    validator_pass.current_date = datetime.datetime.now().date()
    validator_pass.start_of_day_equity = 105000.0
    assert validator_pass.validate_order(order, mock_portfolio) is True


def test_max_drawdown_stop(mock_portfolio):
    validator = MaxDrawdownStop(max_dd=0.10)
    order = OrderEvent("RELIANCE.NS", "MKT", 100, "BUY")
    assert validator.validate_order(order, mock_portfolio) is True
    mock_portfolio.holdings.current_holdings["total"] = 85000.0
    assert validator.validate_order(order, mock_portfolio) is False


def test_max_open_positions(mock_portfolio):
    validator = MaxOpenPositions(max_positions=2)
    order1 = OrderEvent("RELIANCE.NS", "MKT", 100, "BUY")
    assert validator.validate_order(order1, mock_portfolio) is True
    order2 = OrderEvent("INFY.NS", "MKT", 100, "BUY")
    assert validator.validate_order(order2, mock_portfolio) is False


def test_sector_exposure_limit(mock_portfolio):
    symbol_to_sector = {"RELIANCE.NS": "Tech", "TCS.NS": "Tech", "ONGC.NS": "Energy"}
    validator = SectorExposureLimit("Tech", 1.0, symbol_to_sector)

    # current tech exposure k k k. total k. max is . k .
    # buying reliance.ns k. projected k. k k . . . fails.
    order1 = OrderEvent("RELIANCE.NS", "MKT", 100, "BUY")
    assert validator.validate_order(order1, mock_portfolio) is False

    # buying ongc.ns k. projected tech exposure k. k k . . . passes.
    order2 = OrderEvent("ONGC.NS", "MKT", 100, "BUY")
    assert validator.validate_order(order2, mock_portfolio) is True
