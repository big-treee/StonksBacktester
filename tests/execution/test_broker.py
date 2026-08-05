import queue
from unittest.mock import MagicMock

from core.events import OrderEvent
from execution.simulated_broker import SimulatedBroker


def test_simulated_broker_execute_order():
    events = queue.Queue()
    mock_data_handler = MagicMock()
    mock_data_handler.get_latest_bar_value.return_value = 150.0

    broker = SimulatedBroker(events, mock_data_handler)
    order = OrderEvent("RELIANCE.NS", "MKT", 100, "BUY")

    broker.execute_order(order)

    assert not events.empty()
    fill = events.get()
    assert fill.type == "FILL"
    assert fill.symbol == "RELIANCE.NS"
    assert fill.quantity == 100
    assert fill.direction == "BUY"
    assert fill.fill_cost == 150.0
