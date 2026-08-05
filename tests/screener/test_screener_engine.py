import datetime
from unittest.mock import MagicMock, patch

import pandas as pd

from screener.engine import ScreenerEngine


class MockSignal:
    def __init__(self, symbol, strategy_id, date, direction, strength):
        self.type = "SIGNAL"
        self.symbol = symbol
        self.strategy_id = strategy_id
        self.datetime = date
        self.signal_type = direction
        self.strength = strength


@patch("screener.engine.YahooDataHandler")
@patch("screener.engine.get_strategy")
def test_screener_engine(mock_get_strategy, mock_data_handler):
    # setup mock data handler.
    mock_dh = MagicMock()
    mock_dh.continue_backtest = True

    # we want it to run for exactly loop.
    def update_bars_side_effect():
        mock_dh.continue_backtest = False

    mock_dh.update_bars.side_effect = update_bars_side_effect

    today = datetime.datetime.now()
    mock_dh.get_latest_bar_datetime.return_value = today

    # return mock bars for volatility calculation.
    mock_dh.get_latest_bars.return_value = [
        (today - datetime.timedelta(days=2), pd.Series({"Close": 100})),
        (today - datetime.timedelta(days=1), pd.Series({"Close": 105})),
        (today, pd.Series({"Close": 102})),
    ]

    mock_data_handler.return_value = mock_dh

    # setup mock strategy.
    mock_strat_cls = MagicMock()
    mock_strat_instance = MagicMock()
    mock_strat_instance.strategy_name = "TestStrat"

    # the strategy calculates signals which we will manually put into the queue.
    def calculate_signals_side_effect(event):
        # we need to access the queue which is passed to the data handler or strategy.
        # actually in our test we can just mock the queue or let the engine pick it up.
        pass

    mock_strat_instance.calculate_signals.side_effect = calculate_signals_side_effect
    mock_strat_cls.return_value = mock_strat_instance
    mock_get_strategy.return_value = mock_strat_cls

    engine = ScreenerEngine()

    # we need to manually inject signals into the events queue inside run screen.
    # but queue is local. let s patch queue.queue.

    with patch("screener.engine.queue.Queue") as mock_q:
        q_instance = MagicMock()

        # event queue gets market signal signal empty.
        market_event = MagicMock()
        market_event.type = "MARKET"

        signal1 = MockSignal("RELIANCE.NS", id(mock_strat_instance), today, "LONG", 0.9)
        signal2 = MockSignal(
            "TCS.NS", id(mock_strat_instance), today - datetime.timedelta(days=1), "SHORT", 0.5
        )  # yesterday should be filtered out.

        # we use a stateful side effect for q instance.empty and get.
        # first iteration empty is false gets market.
        # next iterations empty is false gets signal then signal.
        # then empty is true.

        call_count = 0

        def get_side_effect():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return market_event
            elif call_count == 2:
                return signal1
            elif call_count == 3:
                return signal2
            else:
                raise Exception("Queue should be empty")

        def empty_side_effect():
            return call_count >= 3

        q_instance.get.side_effect = get_side_effect
        q_instance.empty.side_effect = empty_side_effect
        mock_q.return_value = q_instance

        # run it.
        results = engine.run_screen(["INDEX:NIFTY_50"], ["TestStrat"])

        assert len(results) == 1
        assert results[0]["symbol"] == "RELIANCE.NS"
        assert results[0]["strategy_name"] == "TestStrat"
        assert results[0]["direction"] == "LONG"
        assert results[0]["confidence_score"] == 90.0
        assert "risk_score" in results[0]
