import numpy as np

from core.events import MarketEvent, SignalEvent
from strategy.base import BaseStrategy
from strategy.registry import register_strategy


@register_strategy("sma")
class MovingAverageCrossStrategy(BaseStrategy):
    """moving average cross strategy.
    generates a long signal when the short term sma crosses above the long term sma.
    and an exit signal when it crosses below.
    supports multiple assets."""

    description = "Moving Average Crossover Strategy"
    required_parameters = {"short_window": int, "long_window": int}

    def initialize(self) -> None:
        self.short_window = int(getattr(self, "short_window", 50))
        self.long_window = int(getattr(self, "long_window", 200))
        self.symbol_list = self.data_handler.symbol_list

        # state tracking per symbol.
        self.bought = {symbol: "OUT" for symbol in self.symbol_list}

    def on_market_event(self, event: MarketEvent) -> None:
        # state is automatically managed by data handler so we don t necessarily.
        # need to do heavy processing here as we fetch the latest bars in generate signals.
        pass

    def generate_signals(self, event: MarketEvent) -> None:
        if event.type != "MARKET":
            return

        for symbol in self.symbol_list:
            bars = self.data_handler.get_latest_bars(symbol, N=self.long_window)
            if bars is None or len(bars) < self.long_window:
                if len(bars) > 0:
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

            # extract closing prices.
            closes = np.array([b[1]["Close"] for b in bars], dtype=float)

            short_sma = np.mean(closes[-self.short_window :])
            long_sma = np.mean(closes[-self.long_window :])

            bar_date = bars[-1][0]
            close_price = closes[-1]
            state_str = (
                f"SMA{self.short_window}: {short_sma:.2f} | SMA{self.long_window}: {long_sma:.2f}"
            )
            diff_pct = ((short_sma - long_sma) / long_sma) * 100

            if short_sma > long_sma and self.bought[symbol] == "OUT":
                signal = SignalEvent(1, symbol, bar_date, "LONG", 1.0)
                self.events.put(signal)
                self.bought[symbol] = "LONG"
                reason = (
                    f"{self.short_window} SMA crossed above {self.long_window} SMA. "
                    f"SMA{self.short_window}: {short_sma:.2f} SMA{self.long_window}: {long_sma:.2f} Diff: +{diff_pct:.2f}%"
                )
                self.log_decision(
                    bar_date,
                    symbol,
                    close_price,
                    state_str,
                    "OUT",
                    "BUY",
                    reason,
                    signal_strength=abs(diff_pct),
                )

            elif short_sma < long_sma and self.bought[symbol] == "LONG":
                signal = SignalEvent(1, symbol, bar_date, "EXIT", 1.0)
                self.events.put(signal)
                self.bought[symbol] = "OUT"
                reason = (
                    f"{self.short_window} SMA crossed below {self.long_window} SMA. "
                    f"Bearish crossover detected. Diff: {diff_pct:.2f}%"
                )
                self.log_decision(
                    bar_date,
                    symbol,
                    close_price,
                    state_str,
                    "LONG",
                    "EXIT",
                    reason,
                    signal_strength=abs(diff_pct),
                )

            else:
                if self.bought[symbol] == "LONG":
                    reason = "Holding position. Bullish trend. No crossover."
                    self.log_decision(
                        bar_date,
                        symbol,
                        close_price,
                        state_str,
                        self.bought[symbol],
                        "HOLD",
                        reason,
                        signal_strength=abs(diff_pct),
                    )
                else:
                    reason = f"No position. Short SMA below Long SMA. Diff: {diff_pct:.2f}%"
                    self.log_decision(
                        bar_date,
                        symbol,
                        close_price,
                        state_str,
                        self.bought[symbol],
                        "IGNORE",
                        reason,
                        signal_strength=abs(diff_pct),
                    )

    def reset(self) -> None:
        self.bought = {symbol: "OUT" for symbol in self.symbol_list}
