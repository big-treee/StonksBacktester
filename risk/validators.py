import datetime
from typing import Any

from core.events import OrderEvent
from risk.base import BaseRiskValidator


class MaxPositionSize(BaseRiskValidator):
    """rejects order if the resulting position size exceeds a maximum threshold."""

    def __init__(self, max_shares: int = 1000) -> None:
        self.max_shares = max_shares

    def validate_order(self, order: OrderEvent, portfolio: Any) -> bool:
        current_pos = portfolio.positions.current_positions.get(order.symbol, 0)
        qty = order.quantity if order.direction == "BUY" else -order.quantity

        projected_pos = current_pos + qty
        return abs(projected_pos) <= self.max_shares


class MaxPortfolioExposure(BaseRiskValidator):
    """rejects order if it would push the portfolio s gross exposure beyond the limit.
    exposure sum of absolute value of all active positions total equity."""

    def __init__(self, max_exposure_pct: float = 1.0) -> None:
        self.max_exposure_pct = max_exposure_pct

    def validate_order(self, order: OrderEvent, portfolio: Any) -> bool:
        # calculate current gross exposure.
        holdings = portfolio.holdings.current_holdings
        gross_exposure = sum(
            abs(v) for k, v in holdings.items() if k not in ["cash", "commission", "total"]
        )

        price = portfolio.data_handler.get_latest_bar_value(order.symbol, "Close")
        trade_value = order.quantity * price

        # if it s a closing trade it generally reduces exposure so we pass.
        current_pos = portfolio.positions.current_positions.get(order.symbol, 0)
        is_closing = (current_pos > 0 and order.direction == "SELL") or (
            current_pos < 0 and order.direction == "BUY"
        )

        if is_closing:
            return True

        projected_exposure = gross_exposure + trade_value
        total_equity = holdings["total"]

        return (projected_exposure / total_equity) <= self.max_exposure_pct


class SufficientCashValidator(BaseRiskValidator):
    """rejects buy orders if available cash is insufficient to cover purchase cost."""

    def validate_order(self, order: OrderEvent, portfolio: Any) -> bool:
        if order.direction != "BUY":
            return True
        price = portfolio.data_handler.get_latest_bar_value(order.symbol, "Close")
        trade_cost = order.quantity * price
        cash = portfolio.holdings.current_holdings.get("cash", 0.0)
        return cash >= trade_cost


class DailyLossLimit(BaseRiskValidator):
    """rejects new trades if the daily loss exceeds a fixed threshold."""

    def __init__(self, max_daily_loss: float = 5000.0) -> None:
        self.max_daily_loss = max_daily_loss
        self.current_date: datetime.date | None = None
        self.start_of_day_equity: float = 0.0

    def validate_order(self, order: OrderEvent, portfolio: Any) -> bool:
        # if no holdings history let it pass.
        if len(portfolio.holdings.all_holdings) == 0:
            return True

        latest_record = portfolio.holdings.all_holdings[-1]
        dt: datetime.datetime = latest_record["datetime"]
        date_only = dt.date()

        current_equity = portfolio.holdings.current_holdings["total"]

        if self.current_date != date_only:
            self.current_date = date_only
            self.start_of_day_equity = current_equity

        daily_pnl = current_equity - self.start_of_day_equity

        # if we re down more than the limit block the trade.
        if daily_pnl < -self.max_daily_loss:
            return False

        return True


class MaxDrawdownStop(BaseRiskValidator):
    """halts trading if the portfolio experiences a peak to trough drawdown.
    greater than the specified percentage."""

    def __init__(self, max_dd: float = 0.20) -> None:
        self.max_dd = max_dd
        self.peak_equity = 0.0

    def validate_order(self, order: OrderEvent, portfolio: Any) -> bool:
        current_equity = portfolio.holdings.current_holdings["total"]

        if current_equity > self.peak_equity:
            self.peak_equity = current_equity

        if self.peak_equity == 0:
            return True

        current_dd = (self.peak_equity - current_equity) / self.peak_equity
        return current_dd <= self.max_dd


class MaxOpenPositions(BaseRiskValidator):
    """limits the total number of distinct symbols the portfolio can hold at once."""

    def __init__(self, max_positions: int = 5) -> None:
        self.max_positions = max_positions

    def validate_order(self, order: OrderEvent, portfolio: Any) -> bool:
        current_positions = portfolio.positions.current_positions
        active_symbols = sum(1 for sym, qty in current_positions.items() if qty != 0)

        # if we already have the position or we are closing a position it s fine.
        if current_positions.get(order.symbol, 0) != 0:
            return True

        return active_symbols < self.max_positions


class SectorExposureLimit(BaseRiskValidator):
    """limits exposure to a specific sector.
    requires a mapping of symbols to sectors."""

    def __init__(
        self, sector: str, max_sector_exposure_pct: float, symbol_to_sector: dict[str, str]
    ) -> None:
        self.sector = sector
        self.max_sector_exposure_pct = max_sector_exposure_pct
        self.symbol_to_sector = symbol_to_sector

    def validate_order(self, order: OrderEvent, portfolio: Any) -> bool:
        # check if the ordered symbol is in the targeted sector.
        if self.symbol_to_sector.get(order.symbol, "Unknown") != self.sector:
            return True  # not restricted by this validator.

        holdings = portfolio.holdings.current_holdings
        total_equity = holdings["total"]

        # calculate current sector exposure.
        sector_exposure = 0.0
        for sym, amount in holdings.items():
            if sym in ["cash", "commission", "total"]:
                continue
            if self.symbol_to_sector.get(sym, "Unknown") == self.sector:
                sector_exposure += abs(amount)

        price = portfolio.data_handler.get_latest_bar_value(order.symbol, "Close")
        trade_value = order.quantity * price

        current_pos = portfolio.positions.current_positions.get(order.symbol, 0)
        is_closing = (current_pos > 0 and order.direction == "SELL") or (
            current_pos < 0 and order.direction == "BUY"
        )

        if is_closing:
            return True

        projected_sector_exposure = sector_exposure + trade_value
        return (projected_sector_exposure / total_equity) <= self.max_sector_exposure_pct
