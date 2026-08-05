from typing import Dict, Tuple

import numpy as np
import pandas as pd
import yfinance as yf


class BenchmarkAnalyzer:
    def __init__(
        self,
        portfolio_returns: pd.Series,
        benchmark_ticker: str,
        start_date: str,
        end_date: str,
        risk_free_rate: float = 0.0,
    ):
        self.portfolio_returns = portfolio_returns
        self.benchmark_ticker = benchmark_ticker
        self.start_date = start_date
        self.end_date = end_date
        self.risk_free_rate = risk_free_rate
        self.periods_per_year = 252

        self.benchmark_returns = self._fetch_benchmark()
        self._align_data()

    def _fetch_benchmark(self) -> pd.Series:
        if not self.benchmark_ticker:
            return pd.Series()

        try:
            data = yf.download(
                self.benchmark_ticker, start=self.start_date, end=self.end_date, progress=False
            )
            if data.empty:
                return pd.Series()
            returns = data["Close"].pct_change().fillna(0.0)
            if isinstance(returns, pd.DataFrame):
                returns = returns.iloc[:, 0]
            returns.index = pd.to_datetime(returns.index).tz_localize(None)
            returns = returns[~returns.index.duplicated(keep="last")].sort_index()
            return returns
        except Exception:
            return pd.Series()

    def _align_data(self):
        if self.benchmark_returns.empty:
            self.aligned_portfolio = pd.Series()
            self.aligned_benchmark = pd.Series()
            return

        # ensure portfolio index is tz naive for alignment.
        port_returns = self.portfolio_returns.copy()
        port_returns.index = pd.to_datetime(port_returns.index).tz_localize(None)
        port_returns = port_returns[~port_returns.index.duplicated(keep="last")].sort_index()
        benchmark_returns = self.benchmark_returns[
            ~self.benchmark_returns.index.duplicated(keep="last")
        ].sort_index()

        df = pd.DataFrame({"portfolio": port_returns, "benchmark": benchmark_returns}).dropna()
        self.aligned_portfolio = df["portfolio"]
        self.aligned_benchmark = df["benchmark"]

    def calculate_all(self) -> Dict[str, float]:
        if self.benchmark_returns.empty:
            return {}

        alpha, beta = self.alpha_beta()
        return {
            "Alpha (Annualized %)": alpha * 100,
            "Beta": beta,
            "Tracking Error (%)": self.tracking_error() * 100,
            "Information Ratio": self.information_ratio(),
        }

    def alpha_beta(self) -> Tuple[float, float]:
        if len(self.aligned_portfolio) < 2:
            return 0.0, 0.0

        cov = np.cov(self.aligned_portfolio, self.aligned_benchmark)
        beta = cov[0, 1] / cov[1, 1] if cov[1, 1] != 0 else 0.0

        port_ann_ret = self.aligned_portfolio.mean() * self.periods_per_year
        bench_ann_ret = self.aligned_benchmark.mean() * self.periods_per_year

        # jensen s alpha.
        alpha = port_ann_ret - (self.risk_free_rate + beta * (bench_ann_ret - self.risk_free_rate))
        return alpha, beta

    def tracking_error(self) -> float:
        if len(self.aligned_portfolio) < 2:
            return 0.0
        active_returns = self.aligned_portfolio - self.aligned_benchmark
        return active_returns.std() * np.sqrt(self.periods_per_year)

    def information_ratio(self) -> float:
        te = self.tracking_error()
        if te == 0:
            return 0.0

        port_ann_ret = self.aligned_portfolio.mean() * self.periods_per_year
        bench_ann_ret = self.aligned_benchmark.mean() * self.periods_per_year

        return (port_ann_ret - bench_ann_ret) / te
