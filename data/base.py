import datetime
from abc import ABC, abstractmethod

import pandas as pd


class BaseDataHandler(ABC):
    """datahandler is an abstract base class providing an interface for.
    all subsequent inherited data handlers both live and historic .
    the goal of a derived datahandler object is to output a generated.
    set of bars ohlcvi for each symbol requested."""

    @property
    @abstractmethod
    def symbol_list(self) -> list[str]:
        pass

    @property
    @abstractmethod
    def continue_backtest(self) -> bool:
        pass

    @abstractmethod
    def get_latest_bars(self, symbol: str, N: int = 1) -> list[tuple[datetime.datetime, pd.Series]]:
        pass

    @abstractmethod
    def update_bars(self) -> None:
        pass

    @abstractmethod
    def get_latest_bar_value(self, symbol: str, val_type: str) -> float:
        pass

    @abstractmethod
    def get_latest_bar_datetime(self, symbol: str) -> datetime.datetime | None:
        pass
