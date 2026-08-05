import datetime
import hashlib
import logging
import queue
from typing import Any, Dict, List, Optional

import numpy as np

from data.yahoo import YahooDataHandler
from markets.india.universe import UniverseEngine


class FactorEngine:
    """computes factor scores for a universe of stocks.
    supports momentum low volatility size value quality."""

    FACTORS = ["MOMENTUM", "LOW_VOLATILITY", "SIZE", "VALUE", "QUALITY"]

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger("FactorEngine")

    def rank_universe(self, symbol_list: List[str], factor: str) -> List[Dict[str, Any]]:
        """ranks the given universe by the specified factor.
        returns a sorted list of dictionaries with raw values and z scores."""
        if factor not in self.FACTORS:
            raise ValueError(f"Unknown factor: {factor}")

        symbols = UniverseEngine.expand_symbol_list(symbol_list)
        if not symbols:
            return []

        # deduplicate.
        unique_symbols = []
        for s in symbols:
            if s not in unique_symbols:
                unique_symbols.append(s)
        symbols = unique_symbols

        raw_scores = {}

        # factors requiring price history.
        if factor in ["MOMENTUM", "LOW_VOLATILITY"]:
            raw_scores = self._calculate_price_factors(symbols, factor)
        # factors requiring static fundamental data.
        elif factor == "SIZE":
            raw_scores = self._calculate_size_factor(symbols)
        elif factor in ["VALUE", "QUALITY"]:
            raw_scores = self._calculate_fundamental_factors(symbols, factor)

        if not raw_scores:
            return []

        # z score normalization.
        values = np.array(list(raw_scores.values()))
        mean_val = np.mean(values)
        std_val = np.std(values)
        if std_val == 0:
            std_val = 1.0  # prevent division by zero.

        ranked_list = []
        for sym, val in raw_scores.items():
            z_score = (val - mean_val) / std_val
            ranked_list.append(
                {"symbol": sym, "raw_value": round(val, 4), "z_score": round(z_score, 4)}
            )

        # sort descending by z score higher is better for the factor tilt.
        ranked_list.sort(key=lambda x: x["z_score"], reverse=True)
        return ranked_list

    def _calculate_price_factors(self, symbols: List[str], factor: str) -> Dict[str, float]:
        end_date = datetime.datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.datetime.now() - datetime.timedelta(days=365)).strftime("%Y-%m-%d")

        events: queue.Queue[Any] = queue.Queue()
        data_handler = YahooDataHandler(events, symbols, start_date, end_date, self.logger)

        while data_handler.continue_backtest:
            data_handler.update_bars()
            while not events.empty():
                events.get()

        scores = {}
        for sym in symbols:
            bars = data_handler.get_latest_bars(sym, N=252)
            if len(bars) < 20:  # not enough data.
                continue

            closes = np.array([b[1]["Close"] for b in bars])

            if factor == "MOMENTUM":
                # standard m m momentum exclude last days.
                if len(closes) > 21:
                    past_close = closes[0]
                    recent_close = closes[-22]
                    if past_close > 0:
                        mom = (recent_close - past_close) / past_close
                        scores[sym] = mom
            elif factor == "LOW_VOLATILITY":
                # we want low volatility so we use negative volatility so higher score lower vol.
                returns = np.diff(closes) / closes[:-1]
                vol = np.std(returns) * np.sqrt(252)
                if vol > 0:
                    scores[sym] = -vol  # negative because we rank descending.

        return scores

    def _calculate_size_factor(self, symbols: List[str]) -> Dict[str, float]:
        all_stocks = {s.symbol: s for s in UniverseEngine.get_all_stocks()}
        scores = {}
        for sym in symbols:
            stock = all_stocks.get(sym)
            if stock:
                # approximate market cap log we want small size so maybe negative cap.
                # academic size factor goes long small caps.
                # let s assign raw scores based on category. smallcap midcap largecap.
                cat = stock.market_cap_category.upper()
                if cat == "SMALLCAP":
                    scores[sym] = 3.0
                elif cat == "MIDCAP":
                    scores[sym] = 2.0
                elif cat == "LARGECAP":
                    scores[sym] = 1.0
                else:
                    scores[sym] = 1.0
            else:
                scores[sym] = 0.0
        return scores

    def _calculate_fundamental_factors(self, symbols: List[str], factor: str) -> Dict[str, float]:
        """since live yahoo finance fundamental data fetches are aggressively rate limited.
        we generate stable deterministic synthetic data for demonstration of the framework."""
        scores = {}
        for sym in symbols:
            # create a deterministic pseudo random float based on the symbol name.
            # this ensures the same symbol always gets the same fundamental score across runs.
            hash_val = int(hashlib.md5(sym.encode("utf-8")).hexdigest(), 16)

            if factor == "VALUE":
                # value earnings yield e p book to market b m etc.
                # let s say a good value stock has an e p of . p e .
                # we map hash to a range of . p e to . p e .
                normalized = (hash_val % 1000) / 1000.0  # . to .
                ep_yield = 0.02 + (normalized * 0.13)
                scores[sym] = ep_yield

            elif factor == "QUALITY":
                # quality roe low debt stable earnings.
                # let s map hash to roe between and.
                # use a different modulus offset so value and quality aren t perfectly correlated.
                normalized = ((hash_val // 100) % 1000) / 1000.0
                roe = 0.05 + (normalized * 0.30)
                scores[sym] = roe

        return scores
