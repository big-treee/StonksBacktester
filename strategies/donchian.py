from core.events import MarketEvent, SignalEvent
from strategy.base import BaseStrategy
from strategy.registry import register_strategy


@register_strategy("donchian")
class DonchianChannelStrategy(BaseStrategy):
    description = "Donchian Channel Breakout Strategy"
    required_parameters = {"window": int}

    def initialize(self) -> None:
        self.window = getattr(self, "window", 20)
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

            # previous n bars for channel calculation.
            past_highs = [b[1]["High"] for b in bars[:-1]]
            past_lows = [b[1]["Low"] for b in bars[:-1]]

            channel_high = max(past_highs)
            channel_low = min(past_lows)

            current_close = bars[-1][1]["Close"]
            bar_date = bars[-1][0]
            state_str = f"High={channel_high:.2f}, Low={channel_low:.2f}"

            if current_close > channel_high and self.bought[symbol] == "OUT":
                self.events.put(SignalEvent(1, symbol, bar_date, "LONG", 1.0))
                self.bought[symbol] = "LONG"
                self.log_decision(
                    bar_date,
                    symbol,
                    current_close,
                    state_str,
                    "OUT",
                    "BUY",
                    "Close broke above Donchian channel",
                )

            elif current_close < channel_low and self.bought[symbol] == "LONG":
                self.events.put(SignalEvent(1, symbol, bar_date, "EXIT", 1.0))
                self.bought[symbol] = "OUT"
                self.log_decision(
                    bar_date,
                    symbol,
                    current_close,
                    state_str,
                    "LONG",
                    "EXIT",
                    "Close broke below Donchian channel",
                )

            else:
                self.log_decision(
                    bar_date,
                    symbol,
                    current_close,
                    state_str,
                    self.bought[symbol],
                    "HOLD" if self.bought[symbol] == "LONG" else "IGNORE",
                    "Inside channel",
                )

    def reset(self) -> None:
        self.bought = {symbol: "OUT" for symbol in self.symbol_list}
