from core.events import MarketEvent, SignalEvent
from strategy.base import BaseStrategy
from strategy.registry import register_strategy


@register_strategy("momentum")
class MomentumStrategy(BaseStrategy):
    description = "Simple Rate of Change Momentum Strategy"
    required_parameters = {"window": int, "threshold": float}

    def initialize(self) -> None:
        self.window = getattr(self, "window", 10)
        self.threshold = getattr(self, "threshold", 0.05)
        self.symbol_list = self.data_handler.symbol_list
        self.bought = {symbol: "OUT" for symbol in self.symbol_list}

    def on_market_event(self, event: MarketEvent) -> None:
        pass

    def generate_signals(self, event: MarketEvent) -> None:
        if event.type != "MARKET":
            return

        for symbol in self.symbol_list:
            bars = self.data_handler.get_latest_bars(symbol, N=self.window + 1)
            if bars is None or len(bars) < self.window + 1:
                if len(bars) > 0:
                    self.log_decision(
                        bars[-1][0],
                        symbol,
                        bars[-1][1]["Close"],
                        f"Bars: {len(bars)}/{self.window + 1}",
                        self.bought[symbol],
                        "IGNORE",
                        "Not enough history",
                    )
                continue

            past_close = bars[0][1]["Close"]
            current_close = bars[-1][1]["Close"]

            roc = (current_close - past_close) / past_close
            bar_date = bars[-1][0]
            state_str = f"ROC={roc:.4f}, Threshold={self.threshold:.4f}"

            if roc > self.threshold and self.bought[symbol] == "OUT":
                self.events.put(SignalEvent(1, symbol, bar_date, "LONG", 1.0))
                self.bought[symbol] = "LONG"
                self.log_decision(
                    bar_date,
                    symbol,
                    current_close,
                    state_str,
                    "OUT",
                    "BUY",
                    "Momentum ROC above threshold",
                )

            elif roc < -self.threshold and self.bought[symbol] == "LONG":
                self.events.put(SignalEvent(1, symbol, bar_date, "EXIT", 1.0))
                self.bought[symbol] = "OUT"
                self.log_decision(
                    bar_date,
                    symbol,
                    current_close,
                    state_str,
                    "LONG",
                    "EXIT",
                    "Momentum ROC below threshold",
                )

            else:
                self.log_decision(
                    bar_date,
                    symbol,
                    current_close,
                    state_str,
                    self.bought[symbol],
                    "HOLD" if self.bought[symbol] == "LONG" else "IGNORE",
                    "ROC within bounds",
                )

    def reset(self) -> None:
        self.bought = {symbol: "OUT" for symbol in self.symbol_list}
