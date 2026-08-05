import datetime
import queue
from unittest.mock import MagicMock

import pytest

from core.events import MarketEvent
from strategies.sma import MovingAverageCrossStrategy


@pytest.fixture
def mock_deps():
    data_handler = MagicMock()
    data_handler.symbol_list = ["RELIANCE.NS"]
    events = queue.Queue()
    return data_handler, events


def test_sma_crossover(mock_deps):
    data_handler, events = mock_deps
    strategy = MovingAverageCrossStrategy(data_handler, events, short_window=2, long_window=3)

    dt = datetime.datetime.now()

    # . not enough bars.
    data_handler.get_latest_bars.return_value = [(dt, {"Close": 10.0}), (dt, {"Close": 11.0})]
    strategy.calculate_signals(MarketEvent())
    assert events.empty()

    # . short sma . long sma . . short long buy.
    data_handler.get_latest_bars.return_value = [
        (dt, {"Close": 10.0}),
        (dt, {"Close": 10.0}),
        (dt, {"Close": 12.0}),
    ]
    strategy.calculate_signals(MarketEvent())
    assert not events.empty()
    signal = events.get()
    assert signal.signal_type == "LONG"
    assert strategy.bought["RELIANCE.NS"] == "LONG"

    # . short long exit.
    # short . . long . . short long.
    data_handler.get_latest_bars.return_value = [
        (dt, {"Close": 10.0}),
        (dt, {"Close": 12.0}),
        (dt, {"Close": 7.0}),
    ]
    strategy.calculate_signals(MarketEvent())
    assert not events.empty()
    signal = events.get()
    assert signal.signal_type == "EXIT"
    assert strategy.bought["RELIANCE.NS"] == "OUT"
