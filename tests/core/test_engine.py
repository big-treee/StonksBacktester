import logging
import queue
from unittest.mock import MagicMock

import pytest

from core.engine import Engine
from core.events import FillEvent, MarketEvent, OrderEvent, SignalEvent


@pytest.fixture
def mock_components():
    events_queue = queue.Queue()
    data_handler = MagicMock()
    strategy = MagicMock()
    portfolio = MagicMock()
    execution_handler = MagicMock()
    logger = logging.getLogger("TestLogger")

    return events_queue, data_handler, strategy, portfolio, execution_handler, logger


def test_engine_initialization(mock_components):
    events_queue, data_handler, strategy, portfolio, execution_handler, logger = mock_components

    engine = Engine(events_queue, data_handler, strategy, portfolio, execution_handler, logger)

    assert engine.events_queue == events_queue
    assert engine.data_handler == data_handler
    assert engine.strategy == strategy
    assert engine.portfolio == portfolio
    assert engine.execution_handler == execution_handler
    assert engine.logger == logger


def test_engine_run_backtest_loop_break(mock_components):
    events_queue, data_handler, strategy, portfolio, execution_handler, logger = mock_components

    engine = Engine(events_queue, data_handler, strategy, portfolio, execution_handler, logger)

    # engine should break out of the while true loop on the first iteration.
    # if data handler.continue backtest is false.
    data_handler.continue_backtest = False

    engine.run_backtest()

    # verify that portfolio wrap up methods were called.
    portfolio.create_equity_curve_dataframe.assert_called_once()
    portfolio.output_summary_stats.assert_called_once()


def test_engine_event_dispatch_market(mock_components):
    events_queue, data_handler, strategy, portfolio, execution_handler, logger = mock_components
    engine = Engine(events_queue, data_handler, strategy, portfolio, execution_handler, logger)

    event = MarketEvent()
    engine.dispatch_event(event)

    strategy.calculate_signals.assert_called_once_with(event)
    portfolio.update_timeindex.assert_called_once_with(event)


def test_engine_event_dispatch_signal(mock_components):
    events_queue, data_handler, strategy, portfolio, execution_handler, logger = mock_components
    engine = Engine(events_queue, data_handler, strategy, portfolio, execution_handler, logger)

    event = SignalEvent(1, "RELIANCE.NS", None, "LONG", 1.0)
    engine.dispatch_event(event)

    portfolio.update_signal.assert_called_once_with(event)


def test_engine_event_dispatch_order(mock_components):
    events_queue, data_handler, strategy, portfolio, execution_handler, logger = mock_components
    engine = Engine(events_queue, data_handler, strategy, portfolio, execution_handler, logger)

    event = OrderEvent("RELIANCE.NS", "MKT", 100, "BUY")
    engine.dispatch_event(event)

    execution_handler.execute_order.assert_called_once_with(event)


def test_engine_event_dispatch_fill(mock_components):
    events_queue, data_handler, strategy, portfolio, execution_handler, logger = mock_components
    engine = Engine(events_queue, data_handler, strategy, portfolio, execution_handler, logger)

    event = FillEvent(None, "AAPL", "NASDAQ", 100, "BUY", 150.0)
    engine.dispatch_event(event)

    portfolio.update_fill.assert_called_once_with(event)
