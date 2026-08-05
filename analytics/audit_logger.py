import csv
import dataclasses
import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import yaml


class AuditLogger:
    """records events signals orders and snapshots into structured audit files."""

    def __init__(self, config: Any, base_dir: str = "backtests") -> None:
        self.config = config
        self.enabled: bool = getattr(getattr(config, "logging", None), "save_backtest", False)
        self.base_dir: str = getattr(getattr(config, "logging", None), "output_folder", base_dir)

        strat_name = getattr(getattr(config, "strategy", None), "name", "unknown")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.run_id = f"run_{strat_name}_{timestamp}"

        # in memory storage.
        self.trades: List[Dict[str, Any]] = []
        self.signals: List[Dict[str, Any]] = []
        self.orders: List[Dict[str, Any]] = []
        self.portfolio_snapshots: List[Dict[str, Any]] = []
        self.positions: List[Dict[str, Any]] = []
        self.decisions: List[Dict[str, Any]] = []
        self.cashflow: List[Dict[str, Any]] = []
        self.rejections: List[Dict[str, Any]] = []
        self.market_snapshots: List[Dict[str, Any]] = []

        self.start_date_dt: pd.Timestamp = pd.Timestamp.min

        if self.enabled:
            if not os.path.isabs(self.base_dir):
                root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                self.base_dir = os.path.join(root_dir, self.base_dir)

            self.output_dir = os.path.join(self.base_dir, self.run_id)
            os.makedirs(self.output_dir, exist_ok=True)

            try:
                if hasattr(config.data, "start_date") and config.data.start_date:
                    self.start_date_dt = pd.to_datetime(config.data.start_date).tz_localize(None)
            except Exception:
                self.start_date_dt = pd.Timestamp.min

    def log_trade(self, trade_data: Dict[str, Any]) -> None:
        if self.enabled:
            self.trades.append(trade_data)

    def log_signal(
        self,
        event: Any,
        reason: str = "",
        confidence: float = 1.0,
        executed: bool = False,
    ) -> None:
        if self.enabled:
            self.signals.append(
                {
                    "Timestamp": getattr(event, "datetime", ""),
                    "Ticker": getattr(event, "symbol", ""),
                    "Strategy": getattr(getattr(self.config, "strategy", None), "name", ""),
                    "Signal": getattr(event, "signal_type", ""),
                    "Reason": reason,
                    "Confidence": confidence,
                    "Executed": executed,
                }
            )

    def log_order(
        self,
        order: Any,
        status: str = "PENDING",
        commission: float = 0.0,
        slippage: float = 0.0,
        fill_price: float = 0.0,
        executed_qty: int = 0,
        execution_delay: int = 0,
    ) -> None:
        if self.enabled:
            self.orders.append(
                {
                    "Timestamp": order.datetime if hasattr(order, "datetime") else "",
                    "Ticker": getattr(order, "symbol", ""),
                    "BUY/SELL": getattr(order, "direction", ""),
                    "Requested Quantity": getattr(order, "quantity", 0),
                    "Executed Quantity": executed_qty,
                    "Requested Price": getattr(order, "price", 0.0),
                    "Fill Price": fill_price,
                    "Commission": commission,
                    "Slippage": slippage,
                    "Execution Delay": execution_delay,
                    "Status": status,
                }
            )

    def log_portfolio_snapshot(
        self,
        date: Any,
        cash: float,
        invested: float,
        total: float,
        equity: float,
        returns: float,
        drawdown: float,
        open_pos_count: int,
        exposure: float,
        leverage: float,
    ) -> None:
        if self.enabled:
            self.portfolio_snapshots.append(
                {
                    "Date": date,
                    "Cash": cash,
                    "Invested Capital": invested,
                    "Portfolio Value": total,
                    "Equity": equity,
                    "Daily Return": returns,
                    "Drawdown": drawdown,
                    "Open Positions": open_pos_count,
                    "Exposure %": exposure,
                    "Leverage": leverage,
                }
            )

    def log_position(
        self,
        date: Any,
        ticker: str,
        entry_price: float,
        current_price: float,
        quantity: int,
        value: float,
        pnl: float,
        return_pct: float,
        weight: float,
        holding_days: int,
    ) -> None:
        if self.enabled:
            self.positions.append(
                {
                    "Date": date,
                    "Ticker": ticker,
                    "Entry Price": entry_price,
                    "Current Price": current_price,
                    "Quantity": quantity,
                    "Current Value": value,
                    "PnL": pnl,
                    "Return %": return_pct,
                    "Weight": weight,
                    "Holding Days": holding_days,
                }
            )

    def log_decision(
        self,
        date: Any,
        ticker: str,
        close_price: float,
        strategy_state: Any,
        current_position: Any,
        decision: str,
        reason: str,
        signal_strength: float = 0.0,
    ) -> None:
        if self.enabled:
            try:
                dt_obj = pd.to_datetime(date)
                dt_clean = (
                    dt_obj.tz_convert(None)
                    if getattr(dt_obj, "tzinfo", None) is not None
                    else (dt_obj.tz_localize(None) if hasattr(dt_obj, "tz_localize") else dt_obj)
                )
                if dt_clean < self.start_date_dt:
                    return
            except Exception:
                pass

            state_str = str(strategy_state) if strategy_state else ""
            portfolio_cash = 0.0
            exposure = 0.0
            if self.portfolio_snapshots:
                last_snap = self.portfolio_snapshots[-1]
                portfolio_cash = last_snap.get("Cash", 0.0)
                exposure = last_snap.get("Exposure %", 0.0)

            self.decisions.append(
                {
                    "Date": date,
                    "Ticker": ticker,
                    "Decision": decision,
                    "Reason": reason,
                    "Current Position": current_position,
                    "Indicator Values": state_str,
                    "Signal Strength": signal_strength,
                    "Portfolio Cash": portfolio_cash,
                    "Exposure": exposure,
                }
            )

    def log_cashflow(
        self,
        date: Any,
        starting_cash: float,
        cash_after: float,
        reserved: float,
        available: float,
    ) -> None:
        if self.enabled:
            self.cashflow.append(
                {
                    "Date": date,
                    "Starting Cash": starting_cash,
                    "Cash After Every Trade": cash_after,
                    "Cash Reserved": reserved,
                    "Cash Available": available,
                    "Daily Cash": available,
                }
            )

    def log_rejection(self, event: Any, reason: str) -> None:
        if self.enabled:
            self.rejections.append(
                {
                    "Timestamp": getattr(event, "datetime", ""),
                    "Ticker": getattr(event, "symbol", ""),
                    "Reason": reason,
                    "Signal": getattr(
                        event,
                        "signal_type",
                        getattr(event, "direction", "UNKNOWN"),
                    ),
                }
            )

    def log_market_snapshot(
        self,
        date: Any,
        nifty: float,
        banknifty: float,
        vix: float,
        breadth: float,
        universe_size: int,
    ) -> None:
        if self.enabled:
            self.market_snapshots.append(
                {
                    "Date": date,
                    "NIFTY": nifty,
                    "BANKNIFTY": banknifty,
                    "VIX": vix,
                    "Breadth": breadth,
                    "Universe Size": universe_size,
                }
            )

    def save_all(self, stats: Optional[Dict[str, Any]] = None) -> None:
        """dumps all recorded logs to their respective files."""
        if not self.enabled:
            return

        print(f"Saving audit logs to {self.output_dir}")

        trade_cols = [
            "Trade ID",
            "Ticker",
            "Buy Date",
            "Sell Date",
            "Entry Price",
            "Exit Price",
            "Quantity",
            "Gross PnL",
            "Net PnL",
            "Return %",
            "Holding Days",
            "Exit Reason",
            "Strategy",
        ]
        self._write_csv("trades.csv", self.trades, trade_cols)

        signal_cols = [
            "Timestamp",
            "Ticker",
            "Strategy",
            "Signal",
            "Reason",
            "Confidence",
            "Executed",
        ]
        self._write_csv("signals.csv", self.signals, signal_cols)

        order_cols = [
            "Timestamp",
            "Ticker",
            "BUY/SELL",
            "Requested Quantity",
            "Executed Quantity",
            "Requested Price",
            "Fill Price",
            "Commission",
            "Slippage",
            "Execution Delay",
            "Status",
        ]
        self._write_csv("orders.csv", self.orders, order_cols)

        port_cols = [
            "Date",
            "Cash",
            "Invested Capital",
            "Portfolio Value",
            "Equity",
            "Daily Return",
            "Drawdown",
            "Open Positions",
            "Exposure %",
            "Leverage",
        ]
        self._write_csv("portfolio.csv", self.portfolio_snapshots, port_cols)

        pos_cols = [
            "Date",
            "Ticker",
            "Entry Price",
            "Current Price",
            "Quantity",
            "Current Value",
            "PnL",
            "Return %",
            "Weight",
            "Holding Days",
        ]
        self._write_csv("positions.csv", self.positions, pos_cols)

        dec_cols = [
            "Date",
            "Ticker",
            "Decision",
            "Reason",
            "Current Position",
            "Indicator Values",
            "Signal Strength",
            "Portfolio Cash",
            "Exposure",
        ]
        self._write_csv("decision_log.csv", self.decisions, dec_cols)

        cf_cols = [
            "Date",
            "Starting Cash",
            "Cash After Every Trade",
            "Cash Reserved",
            "Cash Available",
            "Daily Cash",
        ]
        self._write_csv("cashflow.csv", self.cashflow, cf_cols)

        rej_cols = ["Timestamp", "Ticker", "Reason", "Signal"]
        self._write_csv("rejected_trades.csv", self.rejections, rej_cols)

        mkt_cols = ["Date", "NIFTY", "BANKNIFTY", "VIX", "Breadth", "Universe Size"]
        self._write_csv("market.csv", self.market_snapshots, mkt_cols)

        self._write_config("config_used.yaml")
        if stats:
            self._write_summary("summary.json", stats)

        self._generate_charts(stats)
        self._generate_report(stats)

    def _write_csv(
        self,
        filename: str,
        data: List[Dict[str, Any]],
        default_headers: Optional[List[str]] = None,
    ) -> None:
        filepath = os.path.join(self.output_dir, filename)
        if not data:
            with open(filepath, "w", newline="") as f:
                if default_headers:
                    writer = csv.writer(f)
                    writer.writerow(default_headers)
            return

        keys = list(data[0].keys())
        with open(filepath, "w", newline="") as f:
            dict_writer = csv.DictWriter(f, fieldnames=keys)
            dict_writer.writeheader()
            dict_writer.writerows(data)

    def _write_config(self, filename: str) -> None:
        filepath = os.path.join(self.output_dir, filename)
        if hasattr(self.config, "__dataclass_fields__"):
            config_dict = dataclasses.asdict(self.config)  # type: ignore[arg-type]
        else:
            config_dict = getattr(self.config, "__dict__", {})
        with open(filepath, "w") as f:
            yaml.dump(config_dict, f)

    def _write_summary(self, filename: str, stats: Dict[str, Any]) -> None:
        filepath = os.path.join(self.output_dir, filename)
        initial_cap = getattr(self.config, "initial_capital", 100000.0)
        final_equity = stats.get("Final Equity", initial_cap)

        strat = getattr(self.config, "strategy", None)
        data = getattr(self.config, "data", None)
        broker = getattr(self.config, "broker", None)
        risk = getattr(self.config, "risk", None)
        sizer = getattr(risk, "position_sizer", None) if risk else None

        summary = {
            "Strategy": getattr(strat, "name", "unknown"),
            "Parameters": getattr(strat, "parameters", {}),
            "Start Date": getattr(data, "start_date", ""),
            "End Date": getattr(data, "end_date", ""),
            "Universe": len(getattr(data, "symbol_list", [])),
            "Initial Capital": initial_cap,
            "Final Capital": final_equity,
            "Net Profit": final_equity - initial_cap,
            "CAGR": stats.get("CAGR", stats.get("CAGR (%)", 0.0)),
            "Sharpe": stats.get("Sharpe", stats.get("Sharpe Ratio", 0.0)),
            "Sortino": stats.get("Sortino Ratio", stats.get("Sortino", 0.0)),
            "Max Drawdown": stats.get("Max Drawdown", stats.get("Max Drawdown (%)", 0.0)),
            "Profit Factor": stats.get("Profit Factor", 0.0),
            "Win Rate": stats.get("Win Rate", stats.get("Win Rate (%)", 0.0)),
            "Average Win": stats.get("Average Win", stats.get("Average Win (INR)", 0.0)),
            "Average Loss": stats.get("Average Loss", stats.get("Average Loss (INR)", 0.0)),
            "Number of Trades": stats.get("Total Trades", stats.get("Trades", len(self.trades))),
            "Average Holding Days": stats.get(
                "Average Holding Period (Days)",
                stats.get("Avg Holding Days", 0.0),
            ),
            "Execution Model": getattr(broker, "name", "zerodha"),
            "Risk Model": getattr(sizer, "name", "FixedShares"),
            "Runtime": self.run_id,
        }
        with open(filepath, "w") as f:
            json.dump(summary, f, indent=4)

    def _generate_charts(self, stats: Optional[Dict[str, Any]]) -> None:
        if not self.portfolio_snapshots:
            return

        df = pd.DataFrame(self.portfolio_snapshots)
        if "Date" not in df.columns:
            return

        df["Date"] = pd.to_datetime(df["Date"])
        df.set_index("Date", inplace=True)

        sns.set_theme(style="darkgrid")

        # . equity curve.
        plt.figure(figsize=(10, 5))
        if "Portfolio Value" in df.columns:
            plt.plot(df.index, df["Portfolio Value"], label="Portfolio Value")
            plt.title("Equity Curve")
            plt.ylabel("Capital")
            plt.tight_layout()
            plt.savefig(os.path.join(self.output_dir, "equity_curve.png"))
        plt.close()

        # . drawdown.
        plt.figure(figsize=(10, 5))
        if "Drawdown" in df.columns:
            plt.fill_between(df.index, df["Drawdown"] * 100, 0, color="red", alpha=0.3)
            plt.title("Drawdown %")
            plt.ylabel("Drawdown (%)")
            plt.tight_layout()
            plt.savefig(os.path.join(self.output_dir, "drawdown.png"))
        plt.close()

        # . monthly returns.
        if "Daily Return" in df.columns:
            try:
                try:
                    monthly = df["Daily Return"].resample("ME").apply(lambda x: (1 + x).prod() - 1)
                except ValueError:
                    monthly = df["Daily Return"].resample("M").apply(lambda x: (1 + x).prod() - 1)
                vals = np.asarray(monthly, dtype=float)
                bar_labels = [pd.to_datetime(idx).strftime("%Y-%m") for idx in monthly.index]
                bar_colors = ["g" if float(v) > 0 else "r" for v in vals]
                bar_heights = [float(v) * 100.0 for v in vals]
                plt.figure(figsize=(10, 5))
                plt.bar(bar_labels, bar_heights, color=bar_colors)
                plt.title("Monthly Returns (%)")
                plt.ylabel("Return (%)")
                plt.xticks(rotation=45)
                plt.tight_layout()
                plt.savefig(os.path.join(self.output_dir, "monthly_returns.png"))
            except Exception:
                pass
            plt.close()

        # . trade distribution.
        if self.trades:
            tdf = pd.DataFrame(self.trades)
            if "Return %" in tdf.columns:
                plt.figure(figsize=(10, 5))
                sns.histplot(data=tdf, x="Return %", bins=20, kde=True)
                plt.title("Trade Return Distribution")
                plt.tight_layout()
                plt.savefig(os.path.join(self.output_dir, "trade_distribution.png"))
                plt.close()

        # . rolling sharpe.
        if "Daily Return" in df.columns:
            try:
                rolling_sharpe = (
                    df["Daily Return"].rolling(60).mean()
                    / df["Daily Return"].rolling(60).std()
                    * (252**0.5)
                )
                plt.figure(figsize=(10, 5))
                rolling_sharpe.plot()
                plt.title("60-Day Rolling Sharpe")
                plt.tight_layout()
                plt.savefig(os.path.join(self.output_dir, "rolling_sharpe.png"))
            except Exception:
                pass
            plt.close()

    def _generate_report(self, stats: Optional[Dict[str, Any]]) -> None:
        filepath = os.path.join(self.output_dir, "research_report.md")

        best_trade = "N/A"
        worst_trade = "N/A"
        if self.trades:
            tdf = pd.DataFrame(self.trades)
            if "Return %" in tdf.columns:
                try:
                    best_t = tdf.loc[tdf["Return %"].idxmax()]
                    best_trade = f"{best_t.get('Ticker', '')} ({best_t['Return %']:.2f}%)"
                    worst_t = tdf.loc[tdf["Return %"].idxmin()]
                    worst_trade = f"{worst_t.get('Ticker', '')} ({worst_t['Return %']:.2f}%)"
                except Exception:
                    pass

        strat_name = getattr(getattr(self.config, "strategy", None), "name", "unknown")
        with open(filepath, "w") as f:
            f.write("# Backtest Research Report\n\n")
            f.write("## Overview\n")
            f.write(f"- **Strategy:** {strat_name}\n")
            f.write(f"- **Best Trade:** {best_trade}\n")
            f.write(f"- **Worst Trade:** {worst_trade}\n")
            if stats:
                f.write(f"- **Total Return:** {stats.get('Return', 0):.2f}%\n")
                f.write(f"- **Max Drawdown:** {stats.get('Max Drawdown', 0):.2f}%\n")
                f.write(f"- **Win Rate:** {stats.get('Win Rate', 0):.2f}%\n")
            f.write("\n## Analytics Note\n")
            f.write(
                "This run was logged fully transparently. Check the CSV files in"
                " this directory for granular tick-level decisions.\n"
            )
