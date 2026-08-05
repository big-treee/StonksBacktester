import pandas as pd

from core.events import MarketEvent, SignalEvent
from strategy.base import BaseStrategy
from strategy.registry import register_strategy


@register_strategy("ema")
class EMACrossStrategy(BaseStrategy):
    description = "Exponential Moving Average Crossover Strategy"
    required_parameters = {"short_window": int, "long_window": int}

    def initialize(self) -> None:
        self.short_window = getattr(self, "short_window", 50)
        self.long_window = getattr(self, "long_window", 200)
        self.symbol_list = self.data_handler.symbol_list
        self.bought = {symbol: "OUT" for symbol in self.symbol_list}

    def on_market_event(self, event: MarketEvent) -> None:
        pass

    def generate_signals(self, event: MarketEvent) -> None:
        if event.type != "MARKET":
            return

        for symbol in self.symbol_list:
            bars = self.data_handler.get_latest_bars(symbol, N=self.long_window)
            if bars is None or len(bars) < self.long_window:
                if bars is not None and len(bars) > 0:
                    self.log_decision(
                        bars[-1][0],
                        symbol,
                        bars[-1][1]["Close"],
                        f"Bars: {len(bars)}/{self.long_window}",
                        self.bought[symbol],
                        "IGNORE",
                        "Not enough history",
                    )
                continue

            closes = pd.Series([b[1]["Close"] for b in bars])
            short_ema = closes.ewm(span=self.short_window, adjust=False).mean().iloc[-1]
            long_ema = closes.ewm(span=self.long_window, adjust=False).mean().iloc[-1]

            bar_date = bars[-1][0]
            close_price = closes.iloc[-1]
            state_str = (
                f"EMA({self.short_window})={short_ema:.2f}, EMA({self.long_window})={long_ema:.2f}"
            )

            if short_ema > long_ema and self.bought[symbol] == "OUT":
                self.events.put(SignalEvent(1, symbol, bar_date, "LONG", 1.0))
                self.bought[symbol] = "LONG"
                self.log_decision(
                    bar_date,
                    symbol,
                    close_price,
                    state_str,
                    "OUT",
                    "BUY",
                    "Short EMA crossed above Long EMA",
                )

            elif short_ema < long_ema and self.bought[symbol] == "LONG":
                self.events.put(SignalEvent(1, symbol, bar_date, "EXIT", 1.0))
                self.bought[symbol] = "OUT"
                self.log_decision(
                    bar_date,
                    symbol,
                    close_price,
                    state_str,
                    "LONG",
                    "EXIT",
                    "Short EMA crossed below Long EMA",
                )

            else:
                self.log_decision(
                    bar_date,
                    symbol,
                    close_price,
                    state_str,
                    self.bought[symbol],
                    "HOLD" if self.bought[symbol] == "LONG" else "IGNORE",
                    "No crossover",
                )

    def reset(self) -> None:
        self.bought = {symbol: "OUT" for symbol in self.symbol_list}
