import datetime

from core.events import FillEvent, MarketEvent, OrderEvent, SignalEvent


def test_market_event():
    event = MarketEvent()
    assert event.type == "MARKET"


def test_signal_event():
    event = SignalEvent(1, "RELIANCE.NS", datetime.datetime.now(), "LONG", 1.0)
    assert event.type == "SIGNAL"
    assert event.symbol == "RELIANCE.NS"


def test_order_event():
    event = OrderEvent("RELIANCE.NS", "MKT", 100, "BUY")
    assert event.type == "ORDER"
    assert event.quantity == 100


def test_fill_event_commission_calculation():
    event = FillEvent(
        timeindex=datetime.datetime.now(),
        symbol="RELIANCE.NS",
        exchange="NSE",
        quantity=100,
        direction="BUY",
        fill_cost=150.0,
    )
    assert event.type == "FILL"
    assert event.commission == max(1.3, 0.013 * 100)
