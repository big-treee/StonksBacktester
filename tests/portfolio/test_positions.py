import datetime

import pytest

from core.events import FillEvent
from portfolio.positions import PositionTracker


@pytest.fixture
def position_tracker():
    return PositionTracker(["RELIANCE.NS", "TCS.NS"], "2023-01-01")


def test_position_tracker_init(position_tracker):
    assert position_tracker.symbol_list == ["RELIANCE.NS", "TCS.NS"]
    assert position_tracker.current_positions["RELIANCE.NS"] == 0
    assert len(position_tracker.all_positions) == 1
    assert position_tracker.all_positions[0]["datetime"] == "2023-01-01"


def test_position_update_from_fill(position_tracker):
    fill = FillEvent(
        timeindex=datetime.datetime(2023, 1, 2, tzinfo=datetime.timezone.utc),
        symbol="RELIANCE.NS",
        exchange="NSE",
        quantity=100,
        direction="BUY",
        fill_cost=150.0,
    )
    position_tracker.update_from_fill(fill)
    assert position_tracker.current_positions["RELIANCE.NS"] == 100


def test_position_update_timeindex(position_tracker):
    position_tracker.current_positions["RELIANCE.NS"] = 50
    dt = datetime.datetime(2023, 1, 2, tzinfo=datetime.timezone.utc)
    position_tracker.update_timeindex(dt)

    assert len(position_tracker.all_positions) == 2
    assert position_tracker.all_positions[-1]["RELIANCE.NS"] == 50
    assert position_tracker.all_positions[-1]["datetime"] == dt
