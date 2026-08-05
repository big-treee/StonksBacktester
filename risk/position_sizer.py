import math
from typing import Any

from core.events import OrderEvent, SignalEvent
from risk.base import BasePositionSizer


class FixedShares(BasePositionSizer):
    """buys or sells a fixed number of shares."""

    def __init__(self, shares: int = 100, **kwargs) -> None:
        self.shares = kwargs.get("fixed_quantity", shares)

    def size_order(self, signal: SignalEvent, portfolio: Any) -> OrderEvent | None:
        return self._generate_order(signal, portfolio, self.shares)

    def _generate_order(
        self, signal: SignalEvent, portfolio: Any, quantity: int
    ) -> OrderEvent | None:
        symbol = signal.symbol
        direction = signal.signal_type
        cur_quantity = portfolio.positions.current_positions[symbol]

        if direction == "LONG":
            return OrderEvent(symbol, "MKT", quantity, "BUY")
        elif direction == "SHORT":
            return OrderEvent(symbol, "MKT", quantity, "SELL")
        elif direction == "EXIT" and cur_quantity > 0:
            return OrderEvent(symbol, "MKT", abs(cur_quantity), "SELL")
        elif direction == "EXIT" and cur_quantity < 0:
            return OrderEvent(symbol, "MKT", abs(cur_quantity), "BUY")

        return None


class FixedDollar(BasePositionSizer):
    """buys or sells a fixed dollar amount of the asset."""

    def __init__(self, dollar_amount: float = 10000.0) -> None:
        self.dollar_amount = dollar_amount

    def size_order(self, signal: SignalEvent, portfolio: Any) -> OrderEvent | None:
        price = portfolio.data_handler.get_latest_bar_value(signal.symbol, "Close")
        if price <= 0:
            return None

        quantity = int(math.floor(self.dollar_amount / price))
        if quantity <= 0:
            return None

        fixed_shares = FixedShares(shares=quantity)
        return fixed_shares.size_order(signal, portfolio)


class FixedFractional(BasePositionSizer):
    """risks a fixed fraction of the total portfolio equity per trade."""

    def __init__(self, fraction: float = 0.02) -> None:
        self.fraction = fraction

    def size_order(self, signal: SignalEvent, portfolio: Any) -> OrderEvent | None:
        total_equity = portfolio.holdings.current_holdings["total"]
        target_dollar_amount = total_equity * self.fraction

        fixed_dollar = FixedDollar(dollar_amount=target_dollar_amount)
        return fixed_dollar.size_order(signal, portfolio)


class RiskPercentage(BasePositionSizer):
    """risks a specific percentage of capital based on a predefined stop loss percentage."""

    def __init__(self, risk_pct: float = 0.01, stop_loss_pct: float = 0.05) -> None:
        self.risk_pct = risk_pct
        self.stop_loss_pct = stop_loss_pct

    def size_order(self, signal: SignalEvent, portfolio: Any) -> OrderEvent | None:
        total_equity = portfolio.holdings.current_holdings["total"]
        capital_at_risk = total_equity * self.risk_pct

        price = portfolio.data_handler.get_latest_bar_value(signal.symbol, "Close")
        if price <= 0:
            return None

        risk_per_share = price * self.stop_loss_pct
        quantity = int(math.floor(capital_at_risk / risk_per_share)) if risk_per_share > 0 else 0

        if quantity <= 0:
            return None

        fixed_shares = FixedShares(shares=quantity)
        return fixed_shares.size_order(signal, portfolio)


class ATRPositionSizer(BasePositionSizer):
    """uses average true range to normalize volatility across assets.
    approximation using recent high low close prices."""

    def __init__(
        self, atr_period: int = 14, risk_pct: float = 0.01, atr_multiplier: float = 2.0
    ) -> None:
        self.atr_period = atr_period
        self.risk_pct = risk_pct
        self.atr_multiplier = atr_multiplier

    def size_order(self, signal: SignalEvent, portfolio: Any) -> OrderEvent | None:
        bars = portfolio.data_handler.get_latest_bars(signal.symbol, N=self.atr_period + 1)
        if len(bars) < 2:
            return None

        # very rough atr calculation for demo purposes.
        trs = []
        for i in range(1, len(bars)):
            high = bars[i][1]["High"]
            low = bars[i][1]["Low"]
            prev_close = bars[i - 1][1]["Close"]
            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            trs.append(tr)

        atr = sum(trs) / len(trs) if trs else 0.0

        total_equity = portfolio.holdings.current_holdings["total"]
        capital_at_risk = total_equity * self.risk_pct

        risk_per_share = atr * self.atr_multiplier
        quantity = int(math.floor(capital_at_risk / risk_per_share)) if risk_per_share > 0 else 0

        if quantity <= 0:
            return None

        fixed_shares = FixedShares(shares=quantity)
        return fixed_shares.size_order(signal, portfolio)


class VolatilityPositionSizer(BasePositionSizer):
    """volatility targeting position sizing e.g. target annualized volatility .
    uses standard deviation of recent returns."""

    def __init__(self, lookback: int = 20, target_volatility: float = 0.10) -> None:
        self.lookback = lookback
        self.target_volatility = target_volatility

    def size_order(self, signal: SignalEvent, portfolio: Any) -> OrderEvent | None:
        bars = portfolio.data_handler.get_latest_bars(signal.symbol, N=self.lookback)
        if len(bars) < self.lookback:
            # fallback to simple fractional sizing if history is insufficient.
            return FixedFractional(fraction=0.01).size_order(signal, portfolio)

        import numpy as np

        closes = np.array([b[1]["Close"] for b in bars])
        returns = np.diff(closes) / closes[:-1]

        daily_vol = np.std(returns)
        ann_vol = daily_vol * np.sqrt(252) if daily_vol > 0 else 1.0

        total_equity = portfolio.holdings.current_holdings["total"]
        # target weight target vol forecast vol.
        weight = min(1.0, self.target_volatility / ann_vol)
        target_dollar_amount = total_equity * weight

        return FixedDollar(dollar_amount=target_dollar_amount).size_order(signal, portfolio)


class KellyCriterion(BasePositionSizer):
    """optimal fractional sizing based on estimated win rate and payoff ratio.
    kelly w w r."""

    def __init__(
        self, win_rate: float = 0.55, payoff_ratio: float = 1.5, kelly_fraction: float = 0.5
    ) -> None:
        self.win_rate = win_rate
        self.payoff_ratio = payoff_ratio
        self.kelly_fraction = kelly_fraction  # e.g. half kelly.

    def size_order(self, signal: SignalEvent, portfolio: Any) -> OrderEvent | None:
        if self.payoff_ratio <= 0:
            return None

        kelly_pct = self.win_rate - ((1.0 - self.win_rate) / self.payoff_ratio)
        kelly_pct = max(0.0, kelly_pct) * self.kelly_fraction

        if kelly_pct <= 0:
            return None

        return FixedFractional(fraction=kelly_pct).size_order(signal, portfolio)
