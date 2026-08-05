import logging
import queue

import pandas as pd

from core.events import Event, FillEvent, MarketEvent, OrderEvent, SignalEvent
from data.base import BaseDataHandler
from execution.simulated_broker import ExecutionHandler
from portfolio.portfolio import Portfolio
from strategy.base import BaseStrategy


class Engine:
    """encapsulates the settings and components for an event driven backtest.
    the engine manages the event queue and dispatches events sequentially to.
    the datahandler strategy portfolio and executionsimulator to simulate.
    a live trading environment without look ahead bias.
    attributes.
    events queue queue.queue shared queue holding all generated events.
    data handler basedatahandler ingests and provides market data.
    strategy basestrategy generates trading signals from market data.
    portfolio portfolio manages positions cash and risk evaluation.
    execution handler executionhandler simulates order fills.
    logger logging.logger handles runtime logging."""

    def __init__(
        self,
        events_queue: queue.Queue,
        data_handler: BaseDataHandler,
        strategy: BaseStrategy,
        portfolio: Portfolio,
        execution_handler: ExecutionHandler,
        logger: logging.Logger | None = None,
        **kwargs,
    ) -> None:
        """initializes the engine with its core components."""
        self.events_queue = events_queue
        self.data_handler = data_handler
        self.strategy = strategy
        self.portfolio = portfolio
        self.execution_handler = execution_handler
        self.logger = logger or logging.getLogger("Engine")
        self.audit_logger = getattr(self, "audit_logger", kwargs.get("audit_logger", None))

        # pull out audit logger explicitly if passed as kwarg for backwards compat.
        if "audit_logger" in kwargs:
            self.audit_logger = kwargs["audit_logger"]

        start_date = getattr(self.data_handler, "start_date", "2021-01-01")
        try:
            self.start_date_dt = pd.to_datetime(start_date).tz_localize(None)
        except Exception:
            self.start_date_dt = pd.Timestamp.min

    def handle_market_event(self, event: MarketEvent) -> None:
        """processes a marketevent by updating the strategy and portfolio time index."""
        self.strategy.calculate_signals(event)

        latest_dt = self.data_handler.get_latest_bar_datetime(self.data_handler.symbol_list[0])
        should_update = True
        if latest_dt is not None:
            try:
                dt_clean = (
                    latest_dt.tz_localize(None) if hasattr(latest_dt, "tz_localize") else latest_dt
                )
                if dt_clean < self.start_date_dt:
                    should_update = False
            except Exception:
                pass
        if should_update:
            self.portfolio.update_timeindex(event)

    def handle_signal_event(self, event: SignalEvent) -> None:
        """processes a signalevent by passing it to the portfolio for risk checks."""
        self.portfolio.update_signal(event)

    def handle_order_event(self, event: OrderEvent) -> None:
        """processes an orderevent by routing it to the execution simulator."""
        self.execution_handler.execute_order(event)

    def handle_fill_event(self, event: FillEvent) -> None:
        """processes a fillevent by updating portfolio holdings and cash."""
        self.portfolio.update_fill(event)

    def dispatch_event(self, event: Event) -> None:
        """routes an incoming event to the appropriate handler method."""
        if isinstance(event, MarketEvent):
            self.handle_market_event(event)
            # log market snapshot after market event processed.
            if self.audit_logger:
                try:
                    latest_dt = self.data_handler.get_latest_bar_datetime(
                        self.data_handler.symbol_list[0]
                    )
                    dt_clean = (
                        latest_dt.tz_localize(None)
                        if latest_dt is not None and hasattr(latest_dt, "tz_localize")
                        else latest_dt
                    )
                    if dt_clean is not None and dt_clean >= self.start_date_dt:
                        self.audit_logger.log_market_snapshot(
                            latest_dt, 0, 0, 0, 0, len(self.data_handler.symbol_list)
                        )
                except Exception:
                    pass
        elif isinstance(event, SignalEvent):
            sig_dt = getattr(event, "datetime", None)
            if sig_dt is not None:
                try:
                    dt_clean = (
                        sig_dt.tz_localize(None) if hasattr(sig_dt, "tz_localize") else sig_dt
                    )
                    if dt_clean < self.start_date_dt:
                        return  # skip signals during warm up.
                except Exception:
                    pass
            if self.audit_logger:
                self.audit_logger.log_signal(event)
            self.handle_signal_event(event)
        elif isinstance(event, OrderEvent):
            if self.audit_logger:
                self.audit_logger.log_order(event)
            self.handle_order_event(event)
        elif isinstance(event, FillEvent):
            if self.audit_logger:
                # assuming executionhandler already executed and this is fillevent.
                self.audit_logger.log_order(
                    order=event,  # dummy order for fill.
                    status="FILLED",
                    commission=event.commission,
                    fill_price=event.fill_cost,
                    executed_qty=event.quantity,
                )
            self.handle_fill_event(event)

    def run_backtest(self) -> None:
        """executes the main backtest simulation loop.
        continuously fetches new market data bars. while the event queue is not empty.
        dispatches events to their respective components. terminates when data is exhausted."""
        self.logger.info("Starting backtest...")

        while True:
            # update the market bars.
            if self.data_handler.continue_backtest:
                self.data_handler.update_bars()
            else:
                break

            # handle the events.
            while True:
                try:
                    event = self.events_queue.get(False)
                except queue.Empty:
                    break
                else:
                    if event is not None:
                        self.dispatch_event(event)

        self.logger.info("Backtest completed.")
        self.portfolio.create_equity_curve_dataframe()
        self.portfolio.output_summary_stats()
