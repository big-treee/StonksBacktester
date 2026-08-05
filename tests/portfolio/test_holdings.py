import datetime
from unittest.mock import MagicMock

import pytest

from core.events import FillEvent
from portfolio.holdings import HoldingsTracker


@pytest.fixture
def mock_data_handler():
    handler = MagicMock()
    handler.get_latest_bar_value.return_value = 150.0
    return handler


@pytest.fixture
def holdings_tracker():
    return HoldingsTracker(["RELIANCE.NS", "TCS.NS"], "2023-01-01", 100000.0)


def test_holdings_init(holdings_tracker):
    assert holdings_tracker.current_holdings["cash"] == 100000.0
    assert holdings_tracker.current_holdings["total"] == 100000.0
    assert holdings_tracker.current_holdings["commission"] == 0.0


def test_holdings_update_from_fill_buy(holdings_tracker):
    fill = FillEvent(
        timeindex=datetime.datetime(2023, 1, 2, tzinfo=datetime.timezone.utc),
        symbol="RELIANCE.NS",
        exchange="NSE",
        quantity=100,
        direction="BUY",
        fill_cost=150.0,
        commission=1.3,
    )
    holdings_tracker.update_from_fill(fill)

    # cost.
    assert holdings_tracker.current_holdings["RELIANCE.NS"] == 15000.0
    assert holdings_tracker.current_holdings["commission"] == 1.3
    assert holdings_tracker.current_holdings["cash"] == 100000.0 - 15000.0 - 1.3
    assert holdings_tracker.current_holdings["total"] == 100000.0 - 1.3


def test_holdings_update_timeindex(holdings_tracker, mock_data_handler):
    dt = datetime.datetime(2023, 1, 2, tzinfo=datetime.timezone.utc)
    positions = {"RELIANCE.NS": 100, "TCS.NS": 0}

    holdings_tracker.update_timeindex(dt, positions, mock_data_handler)

    assert len(holdings_tracker.all_holdings) == 2
    assert holdings_tracker.all_holdings[-1]["datetime"] == dt
    assert holdings_tracker.all_holdings[-1]["RELIANCE.NS"] == 15000.0
    assert holdings_tracker.all_holdings[-1]["total"] == 100000.0 + 15000.0
