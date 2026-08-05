import pandas as pd

from core.events import MarketEvent, SignalEvent
from strategy.base import BaseStrategy
from strategy.registry import register_strategy


@register_strategy("bollinger")
class BollingerBandsStrategy(BaseStrategy):
    description = "Bollinger Bands Mean Reversion Strategy"
    required_parameters = {"window": int, "num_std": float}

    def initialize(self) -> None:
        self.window = getattr(self, "window", 20)
        self.num_std = getattr(self, "num_std", 2.0)
        self.symbol_list = self.data_handler.symbol_list
        self.bought = {symbol: "OUT" for symbol in self.symbol_list}

    def on_market_event(self, event: MarketEvent) -> None:
        pass

    def generate_signals(self, event: MarketEvent) -> None:
        if event.type != "MARKET":
            return

        for symbol in self.symbol_list:
            bars = self.data_handler.get_latest_bars(symbol, N=self.window)
            if bars is None or len(bars) < self.window:
                if len(bars) > 0:
                    self.log_decision(
                        bars[-1][0],
                        symbol,
                        bars[-1][1]["Close"],
                        f"Bars: {len(bars)}/{self.window}",
                        self.bought[symbol],
                        "IGNORE",
                        "Not enough history",
                    )
                continue

            closes = pd.Series([b[1]["Close"] for b in bars])
            sma = closes.mean()
            std = closes.std()

            upper_band = sma + (self.num_std * std)
            lower_band = sma - (self.num_std * std)
            current_close = closes.iloc[-1]

            bar_date = bars[-1][0]
            state_str = f"SMA={sma:.2f}, Lower={lower_band:.2f}, Upper={upper_band:.2f}"

            # mean reversion buy when price drops below lower band exit when it reverts to sma.
            if current_close < lower_band and self.bought[symbol] == "OUT":
                self.events.put(SignalEvent(1, symbol, bar_date, "LONG", 1.0))
                self.bought[symbol] = "LONG"
                self.log_decision(
                    bar_date,
                    symbol,
                    current_close,
                    state_str,
                    "OUT",
                    "BUY",
                    "Price crossed below lower band",
                )

            elif current_close > sma and self.bought[symbol] == "LONG":
                self.events.put(SignalEvent(1, symbol, bar_date, "EXIT", 1.0))
                self.bought[symbol] = "OUT"
                self.log_decision(
                    bar_date,
                    symbol,
                    current_close,
                    state_str,
                    "LONG",
                    "EXIT",
                    "Price crossed above SMA",
                )

            else:
                self.log_decision(
                    bar_date,
                    symbol,
                    current_close,
                    state_str,
                    self.bought[symbol],
                    "HOLD" if self.bought[symbol] == "LONG" else "IGNORE",
                    "No signal generated",
                )

    def reset(self) -> None:
        self.bought = {symbol: "OUT" for symbol in self.symbol_list}
