from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd


def _safe_float(val: Any) -> float:
    """converts value to float safely defaulting to . if none or non numeric."""
    if val is None:
        return 0.0
    try:
        f = float(val)
        return 0.0 if np.isnan(f) or np.isinf(f) else f
    except (ValueError, TypeError):
        return 0.0


class MetricsEngine:
    def __init__(
        self,
        equity_curve: pd.DataFrame,
        trades: List[Dict[str, Any]],
        risk_free_rate: float = 0.0,
    ) -> None:
        self.equity_curve = equity_curve.copy()
        if not self.equity_curve.empty and not isinstance(
            self.equity_curve.index, pd.DatetimeIndex
        ):
            self.equity_curve.index = pd.DatetimeIndex(pd.to_datetime(self.equity_curve.index))

        self.trades = trades or []
        self.risk_free_rate = risk_free_rate

        # derived data.
        if "returns" in self.equity_curve.columns:
            self.returns: pd.Series = self.equity_curve["returns"].fillna(0.0)
        else:
            self.returns = pd.Series(dtype=float)

        if "total" in self.equity_curve.columns:
            self.equity: pd.Series = self.equity_curve["total"]
        else:
            self.equity = pd.Series(dtype=float)

        self.periods_per_year = 252  # daily trading periods per year.

    def calculate_all(self) -> Dict[str, float]:
        metrics: Dict[str, float] = {}

        # equity metrics.
        metrics["CAGR (%)"] = self.cagr() * 100
        metrics["Annual Return (%)"] = self.annual_return() * 100
        metrics["Annual Volatility (%)"] = self.annual_volatility() * 100
        metrics["Sharpe Ratio"] = self.sharpe_ratio()
        metrics["Sortino Ratio"] = self.sortino_ratio()
        metrics["Calmar Ratio"] = self.calmar_ratio()
        metrics["Omega Ratio"] = self.omega_ratio()

        dd, max_dd, avg_dd = self.drawdowns()
        metrics["Max Drawdown (%)"] = max_dd * 100
        metrics["Average Drawdown (%)"] = avg_dd * 100
        metrics["Recovery Factor"] = self.recovery_factor()

        # trade metrics.
        metrics["Total Trades"] = float(len(self.trades))
        metrics["Win Rate (%)"] = self.win_rate() * 100
        metrics["Profit Factor"] = self.profit_factor()
        metrics["Expectancy (INR)"] = self.expectancy()

        avg_win, avg_loss = self.average_win_loss()
        metrics["Average Win (INR)"] = avg_win
        metrics["Average Loss (INR)"] = avg_loss

        max_win, max_loss = self.largest_win_loss()
        metrics["Largest Win (INR)"] = max_win
        metrics["Largest Loss (INR)"] = max_loss

        metrics["Average Holding Period (Days)"] = self.average_holding_period()

        # add plain key aliases for backwards compatibility and logger lookups.
        metrics["CAGR"] = metrics["CAGR (%)"]
        metrics["Win Rate"] = metrics["Win Rate (%)"]
        metrics["Max Drawdown"] = metrics["Max Drawdown (%)"]
        metrics["Average Win"] = metrics["Average Win (INR)"]
        metrics["Average Loss"] = metrics["Average Loss (INR)"]

        (
            gross,
            net,
            charges,
            avg_cost,
            pct_lost,
            bkg,
            stt,
            gst,
            exc,
            stamp,
            sebi,
        ) = self.charge_metrics()

        metrics["Gross Profit (INR)"] = gross
        metrics["Net Profit (INR)"] = net
        metrics["Total Charges Paid (INR)"] = charges
        metrics["Average Cost Per Trade (INR)"] = avg_cost
        metrics["Percentage of Profit Lost to Charges (%)"] = pct_lost

        metrics["Brokerage (INR)"] = bkg
        metrics["STT (INR)"] = stt
        metrics["GST (INR)"] = gst
        metrics["Exchange Charges (INR)"] = exc
        metrics["Stamp Duty (INR)"] = stamp
        metrics["SEBI Fees (INR)"] = sebi

        # sanitize all metric dictionary values against nan inf.
        clean_metrics: Dict[str, float] = {}
        for k, v in metrics.items():
            clean_metrics[k] = _safe_float(v)

        return clean_metrics

    # equity metrics.

    def cagr(self) -> float:
        if len(self.equity) == 0:
            return 0.0
        start_val = _safe_float(self.equity.iloc[0])
        end_val = _safe_float(self.equity.iloc[-1])
        years = len(self.equity) / self.periods_per_year
        if years <= 0 or start_val <= 0:
            return 0.0
        if end_val <= 0:
            return -1.0
        try:
            res = (end_val / start_val) ** (1.0 / years) - 1.0
            return _safe_float(res)
        except Exception:
            return 0.0

    def annual_return(self) -> float:
        if len(self.equity) == 0 or self.returns.empty:
            return 0.0
        return _safe_float(self.returns.mean() * self.periods_per_year)

    def annual_volatility(self) -> float:
        if len(self.equity) <= 1 or self.returns.empty:
            return 0.0
        return _safe_float(self.returns.std() * float(np.sqrt(self.periods_per_year)))

    def sharpe_ratio(self) -> float:
        vol = self.annual_volatility()
        if vol == 0:
            return 0.0
        return _safe_float((self.annual_return() - self.risk_free_rate) / vol)

    def sortino_ratio(self) -> float:
        if self.returns.empty:
            return 0.0
        downside_returns = self.returns[self.returns < 0]
        if len(downside_returns) <= 1:
            return 0.0
        downside_vol = _safe_float(downside_returns.std() * float(np.sqrt(self.periods_per_year)))
        if downside_vol == 0:
            return 0.0
        return _safe_float((self.annual_return() - self.risk_free_rate) / downside_vol)

    def drawdowns(self) -> Tuple[pd.Series, float, float]:
        if len(self.equity) == 0:
            return pd.Series(dtype=float), 0.0, 0.0
        hwm = self.equity.cummax()
        drawdown = (hwm - self.equity) / hwm
        drawdown = drawdown.fillna(0.0)
        max_dd = _safe_float(drawdown.max()) if not drawdown.empty else 0.0
        pos_dd = drawdown[drawdown > 0]
        avg_dd = _safe_float(pos_dd.mean()) if not pos_dd.empty else 0.0
        return drawdown, max_dd, avg_dd

    def calmar_ratio(self) -> float:
        _, max_dd, _ = self.drawdowns()
        if max_dd == 0:
            return 0.0
        return _safe_float(self.annual_return() / max_dd)

    def omega_ratio(self) -> float:
        if self.returns.empty:
            return 0.0
        threshold = self.risk_free_rate / self.periods_per_year
        wins = self.returns[self.returns > threshold] - threshold
        losses = threshold - self.returns[self.returns < threshold]

        sum_wins = _safe_float(wins.sum())
        sum_losses = _safe_float(losses.sum())
        if sum_losses == 0:
            return 0.0
        return _safe_float(sum_wins / sum_losses)

    def recovery_factor(self) -> float:
        _, max_dd, _ = self.drawdowns()
        if max_dd == 0 or len(self.equity) == 0:
            return 0.0
        start_val = _safe_float(self.equity.iloc[0])
        if start_val == 0:
            return 0.0
        total_return = (_safe_float(self.equity.iloc[-1]) / start_val) - 1.0
        return _safe_float(total_return / max_dd)

    # trade metrics.

    def win_rate(self) -> float:
        if not self.trades:
            return 0.0
        wins = sum(1 for t in self.trades if _safe_float(t.get("pnl")) > 0)
        return wins / len(self.trades)

    def profit_factor(self) -> float:
        if not self.trades:
            return 0.0
        gross_profit = sum(
            _safe_float(t.get("pnl")) for t in self.trades if _safe_float(t.get("pnl")) > 0
        )
        gross_loss = sum(
            abs(_safe_float(t.get("pnl"))) for t in self.trades if _safe_float(t.get("pnl")) < 0
        )
        if gross_loss == 0:
            return 0.0
        return _safe_float(gross_profit / gross_loss)

    def expectancy(self) -> float:
        if not self.trades:
            return 0.0
        total_pnl = sum(_safe_float(t.get("pnl")) for t in self.trades)
        return total_pnl / len(self.trades)

    def average_win_loss(self) -> Tuple[float, float]:
        if not self.trades:
            return 0.0, 0.0
        wins = [_safe_float(t.get("pnl")) for t in self.trades if _safe_float(t.get("pnl")) > 0]
        losses = [_safe_float(t.get("pnl")) for t in self.trades if _safe_float(t.get("pnl")) < 0]
        avg_win = sum(wins) / len(wins) if wins else 0.0
        avg_loss = sum(losses) / len(losses) if losses else 0.0
        return avg_win, avg_loss

    def largest_win_loss(self) -> Tuple[float, float]:
        if not self.trades:
            return 0.0, 0.0
        pnls = [_safe_float(t.get("pnl")) for t in self.trades]
        max_win = max(pnls + [0.0])
        max_loss = min(pnls + [0.0])
        return max_win, max_loss

    def average_holding_period(self) -> float:
        if not self.trades:
            return 0.0
        total_days = sum(
            _safe_float(t.get("holding_period", t.get("holding_days"))) for t in self.trades
        )
        return total_days / len(self.trades)

    def charge_metrics(
        self,
    ) -> Tuple[
        float,
        float,
        float,
        float,
        float,
        float,
        float,
        float,
        float,
        float,
        float,
    ]:
        if not self.trades:
            return 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
        gross_profit = sum(_safe_float(t.get("gross_pnl", t.get("pnl"))) for t in self.trades)
        net_profit = sum(_safe_float(t.get("pnl")) for t in self.trades)
        total_charges = sum(_safe_float(t.get("commission")) for t in self.trades)
        avg_cost_per_trade = total_charges / len(self.trades)
        pct_lost = (total_charges / gross_profit * 100) if gross_profit > 0 else 0.0

        brokerage = sum(_safe_float(t.get("brokerage")) for t in self.trades)
        stt = sum(_safe_float(t.get("stt")) for t in self.trades)
        gst = sum(_safe_float(t.get("gst")) for t in self.trades)
        exchange = sum(_safe_float(t.get("exchange_charges")) for t in self.trades)
        stamp = sum(_safe_float(t.get("stamp_duty")) for t in self.trades)
        sebi = sum(_safe_float(t.get("sebi_fees")) for t in self.trades)

        return (
            gross_profit,
            net_profit,
            total_charges,
            avg_cost_per_trade,
            pct_lost,
            brokerage,
            stt,
            gst,
            exchange,
            stamp,
            sebi,
        )
