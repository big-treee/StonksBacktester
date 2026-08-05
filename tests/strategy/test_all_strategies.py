import datetime
import queue
from unittest.mock import MagicMock

import pytest

from core.events import MarketEvent
from strategies.bollinger import BollingerBandsStrategy
from strategies.donchian import DonchianChannelStrategy
from strategies.ema import EMACrossStrategy
from strategies.macd import MACDStrategy
from strategies.mean_reversion import MeanReversionStrategy
from strategies.momentum import MomentumStrategy
from strategies.rsi import RSIStrategy


@pytest.fixture
def mock_deps():
    data_handler = MagicMock()
    data_handler.symbol_list = ["RELIANCE.NS"]
    events = queue.Queue()
    return data_handler, events


def make_bars(closes):
    dt = datetime.datetime.now()
    return [(dt, {"Close": c, "High": c + 1, "Low": c - 1}) for c in closes]


def test_ema(mock_deps):
    dh, ev = mock_deps
    strat = EMACrossStrategy(dh, ev, short_window=2, long_window=3)
    # give enough data to buy.
    dh.get_latest_bars.return_value = make_bars([10, 10, 10, 15, 20])
    strat.calculate_signals(MarketEvent())
    assert strat.bought["RELIANCE.NS"] == "LONG"
    # exit.
    dh.get_latest_bars.return_value = make_bars([20, 20, 10, 5, 2])
    strat.calculate_signals(MarketEvent())
    assert strat.bought["RELIANCE.NS"] == "OUT"


def test_rsi(mock_deps):
    dh, ev = mock_deps
    strat = RSIStrategy(dh, ev, period=2, overbought=70, oversold=30)
    dh.get_latest_bars.return_value = make_bars([10, 5, 1])  # drops oversold.
    strat.calculate_signals(MarketEvent())
    assert strat.bought["RELIANCE.NS"] == "LONG"

    dh.get_latest_bars.return_value = make_bars([1, 10, 20])  # rises overbought.
    strat.calculate_signals(MarketEvent())
    assert strat.bought["RELIANCE.NS"] == "OUT"


def test_macd(mock_deps):
    dh, ev = mock_deps
    strat = MACDStrategy(dh, ev, fast=2, slow=4, signal=2)
    dh.get_latest_bars.return_value = make_bars([10, 11, 12, 13, 14, 15])  # rising macd.
    strat.calculate_signals(MarketEvent())
    assert strat.bought["RELIANCE.NS"] == "LONG"

    dh.get_latest_bars.return_value = make_bars([15, 14, 10, 8, 5, 2])  # falling macd.
    strat.calculate_signals(MarketEvent())
    assert strat.bought["RELIANCE.NS"] == "OUT"


def test_bollinger(mock_deps):
    dh, ev = mock_deps
    strat = BollingerBandsStrategy(dh, ev, window=3, num_std=1.0)
    # buy when below lower band.
    dh.get_latest_bars.return_value = make_bars([10, 10, 5])  # mean . std . . lower . . .
    strat.calculate_signals(MarketEvent())
    assert strat.bought["RELIANCE.NS"] == "LONG"

    # exit when above sma.
    dh.get_latest_bars.return_value = make_bars([5, 5, 10])  # mean . . .
    strat.calculate_signals(MarketEvent())
    assert strat.bought["RELIANCE.NS"] == "OUT"


def test_donchian(mock_deps):
    dh, ev = mock_deps
    strat = DonchianChannelStrategy(dh, ev, window=3)
    # current close max past highs.
    # bars b b b current.
    dh.get_latest_bars.return_value = make_bars([10, 11, 12, 15])
    # max high of past bars is since high close .
    # current close long.
    strat.calculate_signals(MarketEvent())
    assert strat.bought["RELIANCE.NS"] == "LONG"

    # current close min past lows.
    dh.get_latest_bars.return_value = make_bars([15, 14, 13, 8])
    # min low of past is . current exit.
    strat.calculate_signals(MarketEvent())
    assert strat.bought["RELIANCE.NS"] == "OUT"


def test_momentum(mock_deps):
    dh, ev = mock_deps
    strat = MomentumStrategy(dh, ev, window=2, threshold=0.1)
    dh.get_latest_bars.return_value = make_bars([10, 11, 15])  # . .
    strat.calculate_signals(MarketEvent())
    assert strat.bought["RELIANCE.NS"] == "LONG"

    dh.get_latest_bars.return_value = make_bars([15, 14, 10])  # . .
    strat.calculate_signals(MarketEvent())
    assert strat.bought["RELIANCE.NS"] == "OUT"


def test_edge_cases(mock_deps):
    dh, ev = mock_deps
    strat = EMACrossStrategy(dh, ev, short_window=2, long_window=3)

    # . non market event.
    strat.calculate_signals(
        MarketEvent()
    )  # marketevent has type market by default wait i need to check how it s defined.

    # actually signalevent has type signal . let s pass a dummy event.
    class DummyEvent:
        type = "DUMMY"

    strat.calculate_signals(DummyEvent())
    assert ev.empty()

    # . not enough bars.
    dh.get_latest_bars.return_value = make_bars([10])
    strat.calculate_signals(MarketEvent())
    assert ev.empty()

    # . none returned.
    dh.get_latest_bars.return_value = None
    strat.calculate_signals(MarketEvent())
    assert ev.empty()

    # also test on market event and reset for base coverage.
    strat.on_market_event(MarketEvent())
    strat.reset()
    assert strat.bought["RELIANCE.NS"] == "OUT"


def test_mean_reversion(mock_deps):
    dh, ev = mock_deps
    strat = MeanReversionStrategy(dh, ev, window=3, entry_z=1.0, exit_z=0.0)
    dh.get_latest_bars.return_value = make_bars([10, 10, 5])
    # mean . std . . z . . . .
    strat.calculate_signals(MarketEvent())
    assert strat.bought["RELIANCE.NS"] == "LONG"

    dh.get_latest_bars.return_value = make_bars([5, 5, 10])
    # mean . std . . z . . . .
    strat.calculate_signals(MarketEvent())
    assert strat.bought["RELIANCE.NS"] == "OUT"
