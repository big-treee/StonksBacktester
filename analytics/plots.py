import base64
import io
from typing import Any, Dict, List, Optional

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns


def _fig_to_base64(fig: plt.Figure) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=100)
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


class PlotGenerator:
    def __init__(
        self,
        equity_curve: pd.DataFrame,
        trades: List[Dict[str, Any]],
        benchmark_returns: Optional[pd.Series] = None,
    ) -> None:
        self.equity = equity_curve.copy()
        if not self.equity.empty and not isinstance(self.equity.index, pd.DatetimeIndex):
            self.equity.index = pd.DatetimeIndex(pd.to_datetime(self.equity.index))
        self.equity = self.equity[~self.equity.index.duplicated(keep="last")]

        self.trades = trades or []
        if benchmark_returns is not None:
            self.benchmark_returns: Optional[pd.Series] = benchmark_returns[
                ~benchmark_returns.index.duplicated(keep="last")
            ]
        else:
            self.benchmark_returns = None

        # set clean style.
        sns.set_theme(style="whitegrid")

    def plot_equity_curve(self) -> str:
        fig, ax = plt.subplots(figsize=(10, 5))

        # portfolio equity.
        ax.plot(
            self.equity.index,
            self.equity["total"],
            label="Strategy Equity",
            color="blue",
            linewidth=1.5,
        )

        # optional benchmark.
        if self.benchmark_returns is not None and not self.benchmark_returns.empty:
            bench_cum = (1.0 + self.benchmark_returns).cumprod() * float(
                self.equity["total"].iloc[0]
            )
            # align indices.
            bench_aligned = bench_cum.reindex(self.equity.index).ffill()
            ax.plot(
                bench_aligned.index,
                bench_aligned,
                label="Benchmark",
                color="gray",
                linestyle="--",
                linewidth=1.5,
            )

        ax.set_title("Equity Curve")
        ax.set_ylabel("Total Equity (INR)")
        ax.legend()
        return _fig_to_base64(fig)

    def plot_drawdowns(self) -> str:
        fig, ax = plt.subplots(figsize=(10, 3))
        hwm = self.equity["total"].cummax()
        drawdown = (hwm - self.equity["total"]) / hwm * 100

        ax.fill_between(self.equity.index, drawdown, 0, color="red", alpha=0.3)
        ax.plot(self.equity.index, drawdown, color="red", linewidth=1)
        ax.set_title("Drawdown (%)")
        ax.set_ylabel("Drawdown (%)")
        ax.invert_yaxis()
        return _fig_to_base64(fig)

    def plot_monthly_heatmap(self) -> str:
        fig, ax = plt.subplots(figsize=(8, 5))
        if self.equity.empty:
            return _fig_to_base64(fig)

        # resample to monthly returns.
        returns = self.equity["returns"].fillna(0)
        try:
            monthly = returns.resample("ME").apply(lambda x: (1 + x).prod() - 1)
        except ValueError:
            monthly = returns.resample("M").apply(lambda x: (1 + x).prod() - 1)

        df = pd.DataFrame({"return": monthly})
        dindex = pd.DatetimeIndex(df.index)
        df["year"] = dindex.year
        df["month"] = dindex.strftime("%b")

        pivot = df.pivot(index="year", columns="month", values="return")
        # reorder months.
        months = [
            "Jan",
            "Feb",
            "Mar",
            "Apr",
            "May",
            "Jun",
            "Jul",
            "Aug",
            "Sep",
            "Oct",
            "Nov",
            "Dec",
        ]
        pivot = pivot.reindex(columns=[m for m in months if m in pivot.columns])

        sns.heatmap(
            pivot * 100,
            annot=True,
            fmt=".1f",
            cmap="RdYlGn",
            center=0,
            ax=ax,
            cbar_kws={"label": "% Return"},
        )
        ax.set_title("Monthly Returns (%)")
        ax.set_ylabel("")
        ax.set_xlabel("")
        return _fig_to_base64(fig)

    def plot_trade_distribution(self) -> str:
        fig, ax = plt.subplots(figsize=(10, 4))
        if not self.trades:
            return _fig_to_base64(fig)

        pnls = [float(t.get("pnl", 0.0)) for t in self.trades]
        sns.histplot(x=pnls, bins=30, ax=ax, kde=True, color="purple")
        ax.axvline(0, color="black", linestyle="--")
        ax.set_title("Trade PnL Distribution")
        ax.set_xlabel("PnL (INR)")
        return _fig_to_base64(fig)

    def plot_rolling_sharpe(self, window: int = 126) -> str:
        fig, ax = plt.subplots(figsize=(10, 3))
        if len(self.equity) < window:
            return _fig_to_base64(fig)

        returns = self.equity["returns"].fillna(0)
        rolling_sharpe = (returns.rolling(window).mean() / returns.rolling(window).std()) * float(
            np.sqrt(252)
        )

        ax.plot(rolling_sharpe.index, rolling_sharpe, color="orange")
        ax.axhline(0, color="black", linestyle="--")
        ax.set_title(f"Rolling {window}-Day Sharpe Ratio")
        return _fig_to_base64(fig)
