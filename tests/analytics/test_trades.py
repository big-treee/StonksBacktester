import datetime

from analytics.trades import TradeTracker
from core.events import FillEvent


def test_trade_tracker_basic():
    tracker = TradeTracker()

    t1 = datetime.datetime(2020, 1, 1, tzinfo=datetime.timezone.utc)
    t2 = datetime.datetime(2020, 1, 5, tzinfo=datetime.timezone.utc)

    # buy reliance.ns.
    f1 = FillEvent(t1, "RELIANCE.NS", "NSE", 100, "BUY", 150.0, 1.3)
    tracker.process_fill(f1)

    assert len(tracker.open_positions["RELIANCE.NS"]) == 1
    assert len(tracker.closed_trades) == 0

    # sell reliance.ns.
    f2 = FillEvent(t2, "RELIANCE.NS", "NSE", 100, "SELL", 160.0, 1.3)
    tracker.process_fill(f2)

    assert len(tracker.open_positions["RELIANCE.NS"]) == 0
    assert len(tracker.closed_trades) == 1

    trade = tracker.closed_trades[0]
    assert trade["symbol"] == "RELIANCE.NS"
    assert trade["direction"] == "LONG"
    assert trade["entry_price"] == 150.0
    assert trade["exit_price"] == 160.0
    assert trade["quantity"] == 100
    assert trade["pnl"] == (160 - 150) * 100 - 2.6
    assert trade["holding_period"] == 2


def test_trade_tracker_scaling():
    tracker = TradeTracker()

    t1 = datetime.datetime(2020, 1, 1, tzinfo=datetime.timezone.utc)
    t2 = datetime.datetime(2020, 1, 2, tzinfo=datetime.timezone.utc)

    # buy.
    tracker.process_fill(FillEvent(t1, "RELIANCE.NS", "NSE", 50, "BUY", 100.0, 1.0))
    # sell closes long opens short.
    tracker.process_fill(FillEvent(t2, "RELIANCE.NS", "NSE", 100, "SELL", 110.0, 2.0))

    assert len(tracker.closed_trades) == 1
    assert tracker.closed_trades[0]["pnl"] == (110 - 100) * 50 - 2.0  # . from entry . from exit.
    assert tracker.closed_trades[0]["direction"] == "LONG"

    assert len(tracker.open_positions["RELIANCE.NS"]) == 1
    assert tracker.open_positions["RELIANCE.NS"][0]["direction"] == -1
    assert tracker.open_positions["RELIANCE.NS"][0]["quantity"] == 50
