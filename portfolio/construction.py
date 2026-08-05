import datetime
import logging
import queue
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from data.yahoo import YahooDataHandler
from markets.india.universe import UniverseEngine


class PortfolioConstructor:
    """constructs optimized portfolios from a list of symbols using various weighting schemes."""

    METHODS = [
        "EQUAL_WEIGHT",
        "MARKET_CAP_WEIGHT",
        "VOLATILITY_WEIGHT",
        "RISK_PARITY",
        "MAX_DIVERSIFICATION",
    ]

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger("PortfolioConstructor")

    def construct(self, symbols: List[str], method: str = "EQUAL_WEIGHT") -> Dict[str, Any]:
        """calculates optimal weights and portfolio stats for the given symbols."""
        if not symbols:
            raise ValueError("No symbols provided for construction.")

        if method not in self.METHODS:
            raise ValueError(f"Unknown construction method: {method}")

        # remove duplicates keep order.
        unique_symbols = []
        for s in symbols:
            if s not in unique_symbols:
                unique_symbols.append(s)
        symbols = unique_symbols

        n_assets = len(symbols)

        # . fetch year of historical data for correlation and volatility.
        end_date = datetime.datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.datetime.now() - datetime.timedelta(days=365)).strftime("%Y-%m-%d")

        # we also need a benchmark for beta calculation.
        bench_symbol = "^NSEI"  # nifty.
        fetch_symbols = symbols + [bench_symbol]

        events: queue.Queue[Any] = queue.Queue()
        data_handler = YahooDataHandler(events, fetch_symbols, start_date, end_date, self.logger)

        # load all data into memory.
        while data_handler.continue_backtest:
            data_handler.update_bars()
            while not events.empty():
                events.get()  # drain queue.

        # build price dataframe.
        prices = {}
        for sym in fetch_symbols:
            bars = data_handler.get_latest_bars(sym, N=252)  # up to a year of trading days.
            if not bars:
                continue
            dates = [b[0] for b in bars]
            closes = [b[1]["Close"] for b in bars]
            prices[sym] = pd.Series(data=closes, index=dates)

        df = pd.DataFrame(prices).dropna()
        if df.empty or len(df) < 20:
            raise ValueError("Not enough historical data to construct portfolio.")

        returns = df.pct_change().dropna()
        asset_returns = returns[[s for s in symbols if s in returns.columns]]

        if asset_returns.empty:
            raise ValueError("No valid returns data for the requested assets.")

        symbols = list(asset_returns.columns)
        n_assets = len(symbols)

        # calculate stats.
        mean_returns = asset_returns.mean() * 252
        cov_matrix = asset_returns.cov() * 252
        vols = np.sqrt(np.diag(cov_matrix))

        # calculate weights.
        weights = self._calculate_weights(method, symbols, n_assets, cov_matrix, vols)

        # portfolio stats.
        port_return = np.sum(mean_returns * weights)
        port_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))

        # beta.
        beta = 1.0
        if bench_symbol in returns.columns:
            bench_returns = returns[bench_symbol]
            port_daily_returns = asset_returns.dot(weights)
            # covariance between portfolio and benchmark variance of benchmark.
            cov_pb = port_daily_returns.cov(bench_returns)
            var_b = bench_returns.var()
            if var_b > 0:
                beta = cov_pb / var_b

        # sector exposure.
        all_stocks = UniverseEngine.get_all_stocks()
        stock_map = {s.symbol: s for s in all_stocks}

        sector_exposure: dict[str, float] = {}
        for sym, w in zip(symbols, weights):
            stock = stock_map.get(sym)
            sector = stock.sector if stock else "Unknown"
            sector_exposure[sector] = sector_exposure.get(sector, 0.0) + w

        return {
            "method": method,
            "weights": {sym: round(w, 4) for sym, w in zip(symbols, weights)},
            "statistics": {
                "expected_return": round(port_return, 4),
                "volatility": round(port_vol, 4),
                "beta": round(beta, 4),
            },
            "sector_exposure": {s: round(w, 4) for s, w in sector_exposure.items()},
            "correlation_matrix": asset_returns.corr().round(4).to_dict(),
        }

    def _calculate_weights(
        self, method: str, symbols: List[str], n: int, cov_matrix: pd.DataFrame, vols: np.ndarray
    ) -> np.ndarray:
        if method == "EQUAL_WEIGHT":
            return np.ones(n) / n

        elif method == "MARKET_CAP_WEIGHT":
            all_stocks = UniverseEngine.get_all_stocks()
            stock_map = {s.symbol: s for s in all_stocks}
            caps = []
            for sym in symbols:
                stock = stock_map.get(sym)
                # assign arbitrary proxy weights for large mid small if we don t have real market cap.
                if stock and stock.market_cap_category.upper() == "LARGECAP":
                    caps.append(10.0)
                elif stock and stock.market_cap_category.upper() == "MIDCAP":
                    caps.append(3.0)
                elif stock and stock.market_cap_category.upper() == "SMALLCAP":
                    caps.append(1.0)
                else:
                    caps.append(1.0)  # default.
            caps_arr = np.array(caps)
            return caps_arr / np.sum(caps_arr)

        elif method == "VOLATILITY_WEIGHT":
            # inverse volatility.
            inv_vol = 1.0 / np.maximum(vols, 1e-6)
            return inv_vol / np.sum(inv_vol)

        elif method == "RISK_PARITY":
            # minimize sum i w i w cov w n cov w i.
            # alternative formulation sum i sum j rc i rc j where rc i w i cov w i.
            def risk_budget_objective(w, cov):
                port_var = w.T @ cov @ w
                marginal_contrib = cov @ w
                risk_contrib = w * marginal_contrib
                target_risk = port_var / n
                return np.sum((risk_contrib - target_risk) ** 2)

            init_guess = np.ones(n) / n
            bounds = tuple((0.0, 1.0) for _ in range(n))
            constraints = {"type": "eq", "fun": lambda w: np.sum(w) - 1.0}

            res = minimize(
                risk_budget_objective,
                init_guess,
                args=(cov_matrix.values,),
                method="SLSQP",
                bounds=bounds,
                constraints=constraints,
            )
            return res.x

        elif method == "MAX_DIVERSIFICATION":
            # maximize diversification ratio w.t vols sqrt w.t cov w.
            # minimize inverse.
            def max_div_objective(w, cov, v):
                port_vol = np.sqrt(w.T @ cov @ w)
                weighted_vol = w.T @ v
                return -(weighted_vol / port_vol)

            init_guess = np.ones(n) / n
            bounds = tuple((0.0, 1.0) for _ in range(n))
            constraints = {"type": "eq", "fun": lambda w: np.sum(w) - 1.0}

            res = minimize(
                max_div_objective,
                init_guess,
                args=(cov_matrix.values, vols),
                method="SLSQP",
                bounds=bounds,
                constraints=constraints,
            )
            return res.x

        return np.ones(n) / n
