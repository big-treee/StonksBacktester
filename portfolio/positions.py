import datetime
from typing import Any

from core.events import FillEvent


class PositionTracker:
    """tracks the current and historical positions of the portfolio."""

    def __init__(self, symbol_list: list[str], start_date: str) -> None:
        self.symbol_list = symbol_list
        self.start_date = start_date

        self.all_positions: list[dict[str, Any]] = self._construct_all_positions()
        self.current_positions: dict[str, int] = {symbol: 0 for symbol in self.symbol_list}

    def _construct_all_positions(self) -> list[dict[str, Any]]:
        d: dict[str, Any] = {symbol: 0 for symbol in self.symbol_list}
        d["datetime"] = self.start_date
        return [d]

    def update_timeindex(self, latest_datetime: datetime.datetime | None) -> None:
        """snapshot current positions at the new time index."""
        dp: dict[str, Any] = {symbol: self.current_positions[symbol] for symbol in self.symbol_list}
        dp["datetime"] = latest_datetime
        self.all_positions.append(dp)

    def update_from_fill(self, fill: FillEvent) -> None:
        """updates the current positions based on a fill event."""
        fill_dir = 0
        if fill.direction == "BUY":
            fill_dir = 1
        elif fill.direction == "SELL":
            fill_dir = -1

        self.current_positions[fill.symbol] += fill_dir * fill.quantity
