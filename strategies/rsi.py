import pandas as pd

from core.events import MarketEvent, SignalEvent
from strategy.base import BaseStrategy
from strategy.registry import register_strategy


@register_strategy("rsi")
class RSIStrategy(BaseStrategy):
    description = "Relative Strength Index Strategy"
    required_parameters = {
        "period": int,
        "overbought": float,  # allow float or int.
        "oversold": float,
    }

    def initialize(self) -> None:
        self.period = getattr(self, "period", 14)
        self.overbought = getattr(self, "overbought", 70)
        self.oversold = getattr(self, "oversold", 30)
        self.symbol_list = self.data_handler.symbol_list
        self.bought = {symbol: "OUT" for symbol in self.symbol_list}

    def on_market_event(self, event: MarketEvent) -> None:
        pass

    def generate_signals(self, event: MarketEvent) -> None:
        if event.type != "MARKET":
            return

        for symbol in self.symbol_list:
            bars = self.data_handler.get_latest_bars(symbol, N=self.period + 1)
            if bars is None or len(bars) < self.period + 1:
                if len(bars) > 0:
                    self.log_decision(
                        bars[-1][0],
                        symbol,
                        bars[-1][1]["Close"],
                        f"Bars: {len(bars)}/{self.period + 1}",
                        self.bought[symbol],
                        "IGNORE",
                        "Not enough history",
                    )
                continue

            closes = pd.Series([b[1]["Close"] for b in bars])
            delta = closes.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=self.period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=self.period).mean()

            rs = gain / loss
            rsi = 100 - (100 / (1 + rs)).iloc[-1]

            bar_date = bars[-1][0]
            close_price = closes.iloc[-1]
            state_str = f"RSI({self.period})={rsi:.2f}"

            if rsi < self.oversold and self.bought[symbol] == "OUT":
                self.events.put(SignalEvent(1, symbol, bar_date, "LONG", 1.0))
                self.bought[symbol] = "LONG"
                self.log_decision(
                    bar_date, symbol, close_price, state_str, "OUT", "BUY", "RSI is oversold"
                )

            elif rsi > self.overbought and self.bought[symbol] == "LONG":
                self.events.put(SignalEvent(1, symbol, bar_date, "EXIT", 1.0))
                self.bought[symbol] = "OUT"
                self.log_decision(
                    bar_date, symbol, close_price, state_str, "LONG", "EXIT", "RSI is overbought"
                )

            else:
                self.log_decision(
                    bar_date,
                    symbol,
                    close_price,
                    state_str,
                    self.bought[symbol],
                    "HOLD" if self.bought[symbol] == "LONG" else "IGNORE",
                    "RSI not at thresholds",
                )

    def reset(self) -> None:
        self.bought = {symbol: "OUT" for symbol in self.symbol_list}
