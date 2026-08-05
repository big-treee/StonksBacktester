import pytest

from markets.india.brokers import get_broker_charges


def test_zerodha_cnc_buy():
    broker = get_broker_charges("zerodha")
    # buy shares at rs rs.
    charges = broker.calculate_charges(product="cnc", price=1000.0, qty=100, direction="BUY")

    assert charges["brokerage"] == 0.0
    assert charges["stt"] == 100.0  # . of k.
    assert charges["exchange_txn"] == pytest.approx(3.45)  # .
    assert charges["stamp_duty"] == pytest.approx(15.0)  # .
    assert charges["sebi"] == pytest.approx(0.1)  # cr . of trade value.
    assert charges["gst"] == pytest.approx(0.18 * (0 + 3.45 + 0.1))


def test_zerodha_cnc_sell():
    broker = get_broker_charges("zerodha")
    # sell shares at rs.
    charges = broker.calculate_charges(product="cnc", price=1000.0, qty=100, direction="SELL")

    assert charges["brokerage"] == 0.0
    assert charges["stt"] == 100.0
    assert charges["stamp_duty"] == 0.0  # no stamp duty on sell.


def test_zerodha_mis_buy():
    broker = get_broker_charges("zerodha")
    charges = broker.calculate_charges(product="mis", price=1000.0, qty=100, direction="BUY")

    # brokerage is . or rs whichever is lower.
    # . of rs capped at rs.
    assert charges["brokerage"] == 20.0
    assert charges["stt"] == 0.0  # no stt on mis buy.
    assert charges["stamp_duty"] == pytest.approx(3.0)  # .


def test_upstox_cnc():
    broker = get_broker_charges("upstox")
    charges = broker.calculate_charges(product="cnc", price=1000.0, qty=100, direction="BUY")

    # upstox cnc brokerage is . or rs max.
    # . of capped at.
    assert charges["brokerage"] == 20.0
