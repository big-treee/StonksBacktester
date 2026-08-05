import datetime
from unittest.mock import MagicMock

from core.events import SignalEvent
from risk.position_sizer import FixedShares
from risk.risk_manager import RiskManager
from risk.validators import MaxPositionSize


def test_risk_manager():
    sizer = FixedShares(shares=500)
    validator = MaxPositionSize(max_shares=1000)

    manager = RiskManager(position_sizer=sizer, validators=[validator])

    mock_portfolio = MagicMock()
    mock_portfolio.positions.current_positions = {"RELIANCE.NS": 600}

    signal = SignalEvent(1, "RELIANCE.NS", datetime.datetime.now(), "LONG", 1.0)

    # sizer generates shares order. .
    # validator rejects because .
    order = manager.size_and_validate(signal, mock_portfolio)
    assert order is None

    # change current pos to . . should pass.
    mock_portfolio.positions.current_positions = {"RELIANCE.NS": 400}
    order2 = manager.size_and_validate(signal, mock_portfolio)
    assert order2 is not None
    assert order2.quantity == 500
