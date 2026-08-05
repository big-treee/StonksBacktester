import pandas as pd

from core.events import MarketEvent, SignalEvent
from strategy.base import BaseStrategy
from strategy.registry import register_strategy


@register_strategy("mean_reversion")
class MeanReversionStrategy(BaseStrategy):
    description = "Z-Score Mean Reversion Strategy"
    required_parameters = {"window": int, "entry_z": float, "exit_z": float}

    def initialize(self) -> None:
        self.window = getattr(self, "window", 20)
        self.entry_z = getattr(self, "entry_z", 2.0)
        self.exit_z = getattr(self, "exit_z", 0.0)
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

            if std == 0:
                self.log_decision(
                    bars[-1][0],
                    symbol,
                    closes.iloc[-1],
                    f"SMA={sma:.2f}, Std=0",
                    self.bought[symbol],
                    "IGNORE",
                    "Zero volatility",
                )
                continue

            current_close = closes.iloc[-1]
            z_score = (current_close - sma) / std

            bar_date = bars[-1][0]
            state_str = (
                f"Z-Score={z_score:.2f}, EntryZ={-self.entry_z:.2f}, ExitZ={self.exit_z:.2f}"
            )

            # buy when z score is very low oversold.
            if z_score < -self.entry_z and self.bought[symbol] == "OUT":
                self.events.put(SignalEvent(1, symbol, bar_date, "LONG", 1.0))
                self.bought[symbol] = "LONG"
                self.log_decision(
                    bar_date,
                    symbol,
                    current_close,
                    state_str,
                    "OUT",
                    "BUY",
                    "Z-Score oversold threshold reached",
                )

            # exit when z score reverts past exit z usually.
            elif z_score > self.exit_z and self.bought[symbol] == "LONG":
                self.events.put(SignalEvent(1, symbol, bar_date, "EXIT", 1.0))
                self.bought[symbol] = "OUT"
                self.log_decision(
                    bar_date,
                    symbol,
                    current_close,
                    state_str,
                    "LONG",
                    "EXIT",
                    "Z-Score mean reversion threshold reached",
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
