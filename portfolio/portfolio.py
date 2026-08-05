import logging
import queue
from typing import Any

import pandas as pd

from core.events import FillEvent, MarketEvent, OrderEvent, SignalEvent
from data.base import BaseDataHandler
from portfolio.holdings import HoldingsTracker
from portfolio.positions import PositionTracker
from utils.performance import create_drawdowns, create_sharpe_ratio


class Portfolio:
    """the portfolio class orchestrates position tracking and order generation.
    it acts as the central accounting system maintaining the history of cash.
    holdings and open positions. when signals are generated the portfolio.
    routes them through the riskmanager to size and validate orders before.
    emitting them to the executionengine.
    attributes.
    data handler basedatahandler the historical data provider.
    events queue.queue the central event queue.
    start date str the initial start date for tracking.
    initial capital float the starting cash balance.
    logger logging.logger handles runtime logging.
    risk manager any the riskmanager instance for sizing and validation.
    symbol list list the list of ticker symbols tracked.
    positions positiontracker tracks current open positions.
    holdings holdingstracker tracks historical holdings and cash over time.
    equity curve pd.dataframe none the computed equity curve dataframe."""

    def __init__(
        self,
        data_handler: BaseDataHandler,
        events: queue.Queue,
        start_date: str,
        initial_capital: float = 100000.0,
        logger: logging.Logger | None = None,
        risk_manager: Any = None,
        audit_logger: Any = None,
    ) -> None:
        """initializes the portfolio and internal trackers."""
        self.data_handler = data_handler
        self.events = events
        self.start_date = start_date
        self.initial_capital = initial_capital
        self.logger = logger or logging.getLogger("Portfolio")

        # we type hint risk manager as any to avoid circular dependency in portfolio.
        # but it expects a riskmanager instance.
        self.risk_manager = risk_manager
        self.audit_logger = audit_logger

        self.symbol_list = self.data_handler.symbol_list
        self.positions = PositionTracker(self.symbol_list, self.start_date)
        self.holdings = HoldingsTracker(self.symbol_list, self.start_date, self.initial_capital)
        self.equity_curve: pd.DataFrame | None = None

    def update_timeindex(self, event: MarketEvent) -> None:
        """updates the positions and holdings on a new market event.
        args.
        event marketevent the event indicating new market data has arrived."""
        latest_datetime = self.data_handler.get_latest_bar_datetime(self.symbol_list[0])
        self.positions.update_timeindex(latest_datetime)
        self.holdings.update_timeindex(
            latest_datetime, self.positions.current_positions, self.data_handler
        )

        if self.audit_logger:
            # current holdings mtm is in all holdings.
            ch = self.holdings.all_holdings[-1]
            open_pos_count = sum(
                1 for sym, qty in self.positions.current_positions.items() if qty != 0
            )

            # drawdown and returns can be approximated or we can just fetch from a fast running calc.
            # but we don t have cumulative daily running returns here easily. let s just log base stats.
            self.audit_logger.log_portfolio_snapshot(
                date=latest_datetime,
                cash=ch["cash"],
                invested=ch["total"] - ch["cash"],
                total=ch["total"],
                equity=ch["total"],
                returns=0.0,  # filled later in create equity curve dataframe or left.
                drawdown=0.0,  # filled later.
                open_pos_count=open_pos_count,
                exposure=(ch["total"] - ch["cash"]) / ch["total"] if ch["total"] > 0 else 0,
                leverage=1.0,  # default naive.
            )

            for sym, qty in self.positions.current_positions.items():
                if qty != 0:
                    current_price = self.data_handler.get_latest_bar_value(sym, "Close")
                    # naive position logging since entry price is complex without position objects.
                    self.audit_logger.log_position(
                        date=latest_datetime,
                        ticker=sym,
                        entry_price=0.0,
                        current_price=current_price,
                        quantity=qty,
                        value=qty * current_price,
                        pnl=0.0,
                        return_pct=0.0,
                        weight=(qty * current_price) / ch["total"] if ch["total"] > 0 else 0,
                        holding_days=0,
                    )

    def update_fill(self, event: FillEvent) -> None:
        """updates the portfolio trackers from a fillevent.
        args.
        event fillevent the event containing fill price and commission details."""
        if event.type == "FILL":
            prev_cash = self.holdings.current_holdings["cash"]
            self.positions.update_from_fill(event)
            self.holdings.update_from_fill(event)
            new_cash = self.holdings.current_holdings["cash"]

            if self.audit_logger:
                self.audit_logger.log_cashflow(
                    date=event.datetime if hasattr(event, "datetime") else "",
                    starting_cash=prev_cash,
                    cash_after=new_cash,
                    reserved=0.0,
                    available=new_cash,
                )

    def update_signal(self, event: SignalEvent) -> None:
        """processes a signalevent to generate and route new orders.
        queries the riskmanager to determine if the signal is valid and.
        calculates the appropriate position size. if approved emits an orderevent.
        args.
        event signalevent the trading signal generated by a strategy."""
        if event.type != "SIGNAL":
            return

        if self.risk_manager:
            order = self.risk_manager.size_and_validate(event, self)
        else:
            # fallback for old behavior if riskmanager isn t provided or for naive tests.
            order = self._generate_naive_order(event)

        if order is not None:
            self.events.put(order)

    def _generate_naive_order(self, signal: SignalEvent) -> OrderEvent | None:
        """generates a naive order of a fixed quantity for testing purposes."""
        symbol = signal.symbol
        direction = signal.signal_type

        mkt_quantity = 100
        cur_quantity = self.positions.current_positions[symbol]
        order_type = "MKT"

        if direction == "LONG" and cur_quantity == 0:
            return OrderEvent(symbol, order_type, mkt_quantity, "BUY")
        elif direction == "SHORT" and cur_quantity == 0:
            return OrderEvent(symbol, order_type, mkt_quantity, "SELL")
        elif direction == "EXIT" and cur_quantity > 0:
            return OrderEvent(symbol, order_type, abs(cur_quantity), "SELL")
        elif direction == "EXIT" and cur_quantity < 0:
            return OrderEvent(symbol, order_type, abs(cur_quantity), "BUY")

        return None

    def create_equity_curve_dataframe(self) -> None:
        """creates a pandas dataframe from the holdings history."""
        curve = pd.DataFrame(self.holdings.all_holdings)
        curve.set_index("datetime", inplace=True)
        curve.index = pd.to_datetime(curve.index).tz_localize(None)
        curve = curve[~curve.index.duplicated(keep="last")].sort_index()
        curve["returns"] = curve["total"].pct_change().fillna(0.0)
        curve["equity_curve"] = (1.0 + curve["returns"]).cumprod()
        self.equity_curve = curve

        # retroactively fill returns and drawdowns in portfolio snapshots if audit logger is present.
        if getattr(self, "audit_logger", None) and self.audit_logger.portfolio_snapshots:
            # we can zip and update since snapshots match the holding dates.
            drawdown, max_dd, dd_duration = create_drawdowns(self.equity_curve["total"])

            for i, snap in enumerate(self.audit_logger.portfolio_snapshots):
                if i < len(curve):
                    row = curve.iloc[i]
                    snap["Daily Return"] = row.get("returns", 0.0)
                    snap["Drawdown"] = drawdown.iloc[i] if len(drawdown) > i else 0.0

    def get_summary_stats(self) -> dict[str, float]:
        """returns a dictionary of summary statistics."""
        if self.equity_curve is None:
            return {}

        total_return = self.equity_curve["equity_curve"].iloc[-1]
        returns = self.equity_curve["returns"]
        pnl = self.equity_curve["total"].iloc[-1]

        sharpe = create_sharpe_ratio(returns)
        drawdown, max_dd, dd_duration = create_drawdowns(self.equity_curve["total"])

        # calculate win rate and trades if trades are recorded.
        # for now we will return base metrics.
        stats = {
            "Return": (total_return - 1.0) * 100.0,
            "Sharpe": sharpe,
            "Max Drawdown": max_dd * 100.0,
            "Final Equity": pnl,
        }
        return stats

    def output_summary_stats(self) -> None:
        """logs summary statistics of the portfolio performance."""
        stats = self.get_summary_stats()
        if not stats:
            self.logger.error("Equity curve is not generated yet.")
            return

        self.logger.info("--- Performance Stats ---")
        self.logger.info(f"Total Return: {stats['Return']:.2f}%")
        self.logger.info(f"Sharpe Ratio: {stats['Sharpe']:.2f}")
        self.logger.info(f"Max Drawdown: {stats['Max Drawdown']:.2f}%")
        # note dd duration is not in stats dict right now but we can just skip it here or re add it.
        self.logger.info(f"Final Equity: ₹{stats['Final Equity']:,.2f}")
