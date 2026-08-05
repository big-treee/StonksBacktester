import pandas as pd

from core.events import MarketEvent, SignalEvent
from strategy.base import BaseStrategy
from strategy.registry import register_strategy


@register_strategy("macd")
class MACDStrategy(BaseStrategy):
    description = "Moving Average Convergence Divergence Strategy"
    required_parameters = {"fast": int, "slow": int, "signal": int}

    def initialize(self) -> None:
        self.fast = getattr(self, "fast", 12)
        self.slow = getattr(self, "slow", 26)
        self.signal_period = getattr(self, "signal", 9)
        self.symbol_list = self.data_handler.symbol_list
        self.bought = {symbol: "OUT" for symbol in self.symbol_list}

    def on_market_event(self, event: MarketEvent) -> None:
        pass

    def generate_signals(self, event: MarketEvent) -> None:
        if event.type != "MARKET":
            return

        for symbol in self.symbol_list:
            required_bars = self.slow + self.signal_period
            bars = self.data_handler.get_latest_bars(symbol, N=required_bars)
            if bars is None or len(bars) < required_bars:
                if len(bars) > 0:
                    self.log_decision(
                        bars[-1][0],
                        symbol,
                        bars[-1][1]["Close"],
                        f"Bars: {len(bars)}/{required_bars}",
                        self.bought[symbol],
                        "IGNORE",
                        "Not enough history",
                    )
                continue

            closes = pd.Series([b[1]["Close"] for b in bars])
            fast_ema = closes.ewm(span=self.fast, adjust=False).mean()
            slow_ema = closes.ewm(span=self.slow, adjust=False).mean()
            macd_line = fast_ema - slow_ema
            signal_line = macd_line.ewm(span=self.signal_period, adjust=False).mean()

            macd_current = macd_line.iloc[-1]
            signal_current = signal_line.iloc[-1]

            bar_date = bars[-1][0]
            close_price = closes.iloc[-1]
            state_str = f"MACD={macd_current:.2f}, Signal={signal_current:.2f}"

            if macd_current > signal_current and self.bought[symbol] == "OUT":
                self.events.put(SignalEvent(1, symbol, bar_date, "LONG", 1.0))
                self.bought[symbol] = "LONG"
                self.log_decision(
                    bar_date,
                    symbol,
                    close_price,
                    state_str,
                    "OUT",
                    "BUY",
                    "MACD crossed above Signal",
                )

            elif macd_current < signal_current and self.bought[symbol] == "LONG":
                self.events.put(SignalEvent(1, symbol, bar_date, "EXIT", 1.0))
                self.bought[symbol] = "OUT"
                self.log_decision(
                    bar_date,
                    symbol,
                    close_price,
                    state_str,
                    "LONG",
                    "EXIT",
                    "MACD crossed below Signal",
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
