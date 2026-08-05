import datetime
import logging
import queue
from typing import Any, Dict, List, Optional

import numpy as np

from data.yahoo import YahooDataHandler
from markets.india.universe import UniverseEngine
from strategy.registry import get_strategy, load_strategies


class ScreenerEngine:
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger("ScreenerEngine")

    def run_screen(
        self, symbol_list: List[str], strategy_names: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """runs specified strategies over symbol list for the last year to find opportunities."""
        load_strategies()

        # expand universe magic keywords.
        symbols = UniverseEngine.expand_symbol_list(symbol_list)

        if not strategy_names:
            # if not provided we should probably run a predefined set or query registry.
            # for this engine we ll run sma cross and bollingerbands if nothing provided.
            strategy_names = ["SMA_Cross", "BollingerBands"]

        end_date = datetime.datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.datetime.now() - datetime.timedelta(days=365)).strftime("%Y-%m-%d")

        events: queue.Queue[Any] = queue.Queue()
        data_handler = YahooDataHandler(events, symbols, start_date, end_date, self.logger)

        # initialize strategies.
        strategies = []
        for s_name in strategy_names:
            try:
                s_cls = get_strategy(s_name)
                # use default parameters for the screener.
                s_instance = s_cls(data_handler, events)
                strategies.append(s_instance)
            except Exception as e:
                self.logger.error(f"Failed to load strategy {s_name}: {str(e)}")

        if not strategies:
            self.logger.error("No valid strategies loaded for screening.")
            return []

        signals = []
        last_market_date = None

        # process the data.
        while True:
            if data_handler.continue_backtest:
                data_handler.update_bars()
            else:
                break

            while not events.empty():
                event = events.get()
                if event.type == "MARKET":
                    last_market_date = (
                        data_handler.get_latest_bar_datetime(symbols[0]) if symbols else None
                    )
                    for strategy in strategies:
                        strategy.calculate_signals(event)
                elif event.type == "SIGNAL":
                    signals.append(event)

        # filter signals to only those generated on the very last available market date.
        if not last_market_date:
            return []

        # last market date is datetime we want the date part to compare.
        last_date = last_market_date.date()

        current_signals = [sig for sig in signals if sig.datetime.date() == last_date]

        opportunities = []
        for sig in current_signals:
            # resolve strategy name from class or instance attribute.
            strat_name = "Unknown"
            for s in strategies:
                if id(s) == sig.strategy_id:
                    strat_name = getattr(s, "strategy_name", s.__class__.__name__)
                    break

            # simple confidence and risk logic for demonstration.
            # in a real engine confidence could be based on distance from moving averages rsi etc.
            # risk could be recent volatility.
            # we ll calculate a basic volatility based risk score here.
            try:
                bars = data_handler.get_latest_bars(sig.symbol, N=20)
                closes = [b[1]["Close"] for b in bars]
                returns = np.diff(closes) / closes[:-1]
                vol = np.std(returns) * np.sqrt(252) * 100  # annualized volatility.
                risk_score = round(min(vol, 100), 2)  # to.

                # confidence score could just be sig.strength.
                confidence_score = min(abs(sig.strength * 100), 100.0)
            except Exception:
                risk_score = 50.0
                confidence_score = 50.0

            opportunities.append(
                {
                    "symbol": sig.symbol,
                    "strategy_name": strat_name,
                    "direction": sig.signal_type,  # long or short.
                    "confidence_score": round(confidence_score, 1),
                    "risk_score": risk_score,
                    "date": sig.datetime.strftime("%Y-%m-%d"),
                }
            )

        # rank sort by confidence score descending.
        opportunities.sort(key=lambda x: x["confidence_score"], reverse=True)
        return opportunities
