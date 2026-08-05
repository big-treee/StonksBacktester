import datetime
import logging
import queue
from unittest.mock import MagicMock

import pytest

from core.events import FillEvent, SignalEvent
from portfolio.portfolio import Portfolio


@pytest.fixture
def mock_data_handler():
    handler = MagicMock()
    handler.symbol_list = ["RELIANCE.NS", "TCS.NS"]
    handler.get_latest_bar_value.return_value = 150.0
    handler.get_latest_bar_datetime.return_value = datetime.datetime(
        2023, 1, 1, tzinfo=datetime.timezone.utc
    )
    return handler


@pytest.fixture
def portfolio(mock_data_handler):
    events = queue.Queue()
    logger = logging.getLogger("TestLogger")
    port = Portfolio(
        data_handler=mock_data_handler,
        events=events,
        start_date="2023-01-01",
        initial_capital=100000.0,
        logger=logger,
    )
    return port, events, mock_data_handler


def test_portfolio_update_fill(portfolio):
    port, events, dh = portfolio

    fill = FillEvent(
        timeindex=datetime.datetime(2023, 1, 2, tzinfo=datetime.timezone.utc),
        symbol="RELIANCE.NS",
        exchange="NSE",
        quantity=100,
        direction="BUY",
        fill_cost=150.0,
        commission=1.3,
    )
    port.update_fill(fill)

    assert port.positions.current_positions["RELIANCE.NS"] == 100
    assert port.holdings.current_holdings["RELIANCE.NS"] == 15000.0


def test_portfolio_update_signal(portfolio):
    port, events, dh = portfolio

    signal = SignalEvent(1, "RELIANCE.NS", datetime.datetime.now(), "LONG", 1.0)
    port.update_signal(signal)

    assert not events.empty()
    order = events.get()
    assert order.type == "ORDER"
    assert order.symbol == "RELIANCE.NS"
    assert order.direction == "BUY"
    assert order.quantity == 100
