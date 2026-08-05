import datetime
from typing import Any

from core.events import FillEvent


class HoldingsTracker:
    """tracks the current and historical equity and cash holdings of the portfolio."""

    def __init__(self, symbol_list: list[str], start_date: str, initial_capital: float) -> None:
        self.symbol_list = symbol_list
        self.start_date = start_date
        self.initial_capital = initial_capital

        self.all_holdings: list[dict[str, Any]] = self._construct_all_holdings()
        self.current_holdings: dict[str, float] = self._construct_current_holdings()

    def _construct_all_holdings(self) -> list[dict[str, Any]]:
        d: dict[str, Any] = {symbol: 0.0 for symbol in self.symbol_list}
        d["datetime"] = self.start_date
        d["cash"] = self.initial_capital
        d["commission"] = 0.0
        d["total"] = self.initial_capital
        return [d]

    def _construct_current_holdings(self) -> dict[str, float]:
        d: dict[str, float] = {symbol: 0.0 for symbol in self.symbol_list}
        d["cash"] = self.initial_capital
        d["commission"] = 0.0
        d["total"] = self.initial_capital
        return d

    def update_timeindex(
        self,
        latest_datetime: datetime.datetime | None,
        current_positions: dict[str, int],
        data_handler: Any,
    ) -> None:
        """snapshot current holdings at the new time index calculating market values."""
        dh: dict[str, Any] = {symbol: 0.0 for symbol in self.symbol_list}
        dh["datetime"] = latest_datetime
        dh["cash"] = self.current_holdings["cash"]
        dh["commission"] = self.current_holdings["commission"]
        dh["total"] = self.current_holdings["cash"]

        for symbol in self.symbol_list:
            market_value = current_positions[symbol] * data_handler.get_latest_bar_value(
                symbol, "Close"
            )
            dh[symbol] = market_value
            dh["total"] += market_value

        self.all_holdings.append(dh)

    def update_from_fill(self, fill: FillEvent) -> None:
        """updates the current holdings and cash based on a fill event."""
        fill_dir = 0
        if fill.direction == "BUY":
            fill_dir = 1
        elif fill.direction == "SELL":
            fill_dir = -1

        cost = fill_dir * fill.fill_cost * fill.quantity
        commission = fill.commission if fill.commission else 0.0

        self.current_holdings[fill.symbol] += cost
        self.current_holdings["commission"] += commission
        self.current_holdings["cash"] -= cost + commission
        self.current_holdings["total"] -= commission
