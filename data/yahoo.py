import datetime
import logging
import queue
from typing import Any

import pandas as pd
import yfinance as yf

from core.events import MarketEvent
from data.base import BaseDataHandler


class YahooDataHandler(BaseDataHandler):
    """yahoodatahandler reads data directly from yfinance."""

    def __init__(
        self,
        events: queue.Queue,
        symbols: list[str],
        start_date: str,
        end_date: str,
        logger: logging.Logger,
        warmup_days: int = 0,
    ) -> None:
        self.events = events
        self._symbol_list = symbols
        self.start_date = start_date
        self.end_date = end_date
        self.logger = logger
        self.warmup_days = warmup_days

        self.symbol_data: dict[str, Any] = {}
        self.latest_symbol_data: dict[str, list[tuple[datetime.datetime, pd.Series]]] = {}
        self._continue_backtest: bool = True
        self.bar_index: int = 0

        self._load_data()

    @property
    def symbol_list(self) -> list[str]:
        return self._symbol_list

    @property
    def continue_backtest(self) -> bool:
        return self._continue_backtest

    def _load_data(self) -> None:
        self.logger.info(
            f"Loading data from yfinance for {self.symbol_list} "
            f"from {self.start_date} to {self.end_date}..."
        )

        if not self.symbol_list:
            self.logger.warning("No symbols provided.")
            self._continue_backtest = False
            return

        try:
            days_to_subtract = int(self.warmup_days * 1.5) + 30 if self.warmup_days > 0 else 365
            start_dt = pd.to_datetime(self.start_date) - pd.Timedelta(days=days_to_subtract)

            # print warmup report if applicable.
            if self.warmup_days > 0:
                print(f"Downloaded: {start_dt.strftime('%Y-%m-%d')}")
                print(f"Warm-up: {self.warmup_days} trading days")
                print(f"Trading starts: {self.start_date}")
                print("Warm-up complete.")
                print("Indicators initialized.\n")

            df = yf.download(
                self.symbol_list,
                start=start_dt.strftime("%Y-%m-%d"),
                end=self.end_date,
                progress=False,
            )

            if df.empty:
                self.logger.error("No historical data returned from yfinance.")
                self._continue_backtest = False
                return

            if isinstance(self.symbol_list, list) and len(self.symbol_list) > 1:
                for symbol in self.symbol_list:
                    symbol_df = self._prepare_symbol_frame(df.xs(symbol, level=1, axis=1))
                    self.symbol_data[symbol] = symbol_df.iterrows()
                    self.latest_symbol_data[symbol] = []
            else:
                symbol = self.symbol_list[0]
                self.symbol_data[symbol] = self._prepare_symbol_frame(df, symbol).iterrows()
                self.latest_symbol_data[symbol] = []
        except Exception as e:
            self.logger.error(f"Error loading data: {e}")
            self._continue_backtest = False

    def _prepare_symbol_frame(self, df: pd.DataFrame, symbol: str | None = None) -> pd.DataFrame:
        """normalizes yfinance output to one clean ohlcv frame per symbol.
        newer yfinance versions can return multiindex columns even for a.
        single ticker pandas analytics later require unique date labels."""
        frame = df.copy()

        if isinstance(frame.columns, pd.MultiIndex):
            if symbol is not None and symbol in frame.columns.get_level_values(-1):
                frame = frame.xs(symbol, level=-1, axis=1)
            else:
                frame.columns = frame.columns.get_level_values(0)

        frame.index = pd.to_datetime(frame.index).tz_localize(None)
        frame = frame[~frame.index.duplicated(keep="last")]
        frame = frame.loc[:, ~frame.columns.duplicated()]
        frame = frame.sort_index().dropna()

        if frame.empty:
            raise ValueError(f"No usable historical data for {symbol or 'symbol'}.")

        return frame

    def _get_new_bar(self, symbol: str) -> tuple[datetime.datetime, pd.Series] | None:
        from markets.india.calendar import TradingCalendar

        while True:
            try:
                bar = next(self.symbol_data[symbol])
                bar_date = bar[0].date()
                if TradingCalendar.is_market_open(bar_date):
                    return bar
                else:
                    self.logger.warning(f"Skipping non-trading day in historical data: {bar_date}")
            except StopIteration:
                return None

    def get_latest_bars(self, symbol: str, N: int = 1) -> list[tuple[datetime.datetime, pd.Series]]:
        try:
            bars_list = self.latest_symbol_data[symbol]
            return bars_list[-N:]
        except KeyError:
            self.logger.warning(
                f"That symbol is not available in the historical data set: {symbol}"
            )
            return []

    def get_latest_bar_value(self, symbol: str, val_type: str) -> float:
        try:
            bars_list = self.latest_symbol_data[symbol]
            if len(bars_list) > 0:
                return float(getattr(bars_list[-1][1], val_type))
            else:
                return 0.0
        except KeyError:
            return 0.0

    def get_latest_bar_datetime(self, symbol: str) -> datetime.datetime | None:
        try:
            bars_list = self.latest_symbol_data[symbol]
            if len(bars_list) > 0:
                return bars_list[-1][0]
            else:
                return None
        except KeyError:
            return None

    def update_bars(self) -> None:
        has_new_data = False
        for symbol in self.symbol_list:
            try:
                bar = self._get_new_bar(symbol)
            except StopIteration:
                self._continue_backtest = False
                continue

            if bar is not None:
                has_new_data = True
                self.latest_symbol_data[symbol].append(bar)

        if has_new_data:
            self.events.put(MarketEvent())
        else:
            self._continue_backtest = False
