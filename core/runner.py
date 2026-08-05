import logging
import queue
from typing import Any, Dict

import pandas as pd

from analytics.audit_logger import AuditLogger
from config.models import Config
from core.engine import Engine
from data.yahoo import YahooDataHandler
from execution.simulated_broker import SimulatedBroker
from portfolio.portfolio import Portfolio
from risk import position_sizer as sizers
from risk import validators as vals
from risk.risk_manager import RiskManager
from strategy.registry import get_strategy, load_strategies
from strategy.validation import validate_strategy_parameters


def _resolve_sizer_class(name: str):
    if hasattr(sizers, name):
        return getattr(sizers, name)
    clean_name = name.lower().replace("_", "")
    for attr in dir(sizers):
        if attr.lower().replace("_", "") == clean_name:
            return getattr(sizers, attr)
    aliases = {
        "fixedfractional": "FixedFractional",
        "fixedshares": "FixedShares",
        "fixeddollar": "FixedDollar",
        "volatilitytarget": "VolatilityPositionSizer",
        "volatilitypositionsizer": "VolatilityPositionSizer",
        "riskparity": "FixedFractional",
        "kelly": "KellyCriterion",
        "kellycriterion": "KellyCriterion",
        "riskpercentage": "RiskPercentage",
    }
    target = aliases.get(clean_name)
    if target and hasattr(sizers, target):
        return getattr(sizers, target)
    raise AttributeError(f"Position sizer '{name}' not found in risk.position_sizer")


def _resolve_validator_class(name: str):
    if hasattr(vals, name):
        return getattr(vals, name)
    clean_name = name.lower().replace("_", "")
    for attr in dir(vals):
        if attr.lower().replace("_", "") == clean_name:
            return getattr(vals, attr)
    aliases = {
        "maxdrawdownvalidator": "MaxDrawdownStop",
        "maxdrawdownstop": "MaxDrawdownStop",
        "positioncountvalidator": "MaxOpenPositions",
        "maxopenpositions": "MaxOpenPositions",
    }
    target = aliases.get(clean_name)
    if target and hasattr(vals, target):
        return getattr(vals, target)
    raise AttributeError(f"Risk validator '{name}' not found in risk.validators")


def build_risk_manager(config: Config, logger: logging.Logger) -> RiskManager:
    sizer_cfg = config.risk.position_sizer
    sizer_cls = _resolve_sizer_class(sizer_cfg.name)
    sizer = sizer_cls(**sizer_cfg.parameters)

    active_validators = []
    for val_cfg in config.risk.validators:
        val_cls = _resolve_validator_class(val_cfg.name)
        active_validators.append(val_cls(**val_cfg.parameters))

    return RiskManager(position_sizer=sizer, validators=active_validators, logger=logger)


def run_backtest_with_config(
    config: Config,
    strategy_params_override: Dict[str, Any] | None = None,
    log_manager: Any = None,
    broker_override: Any = None,
) -> Dict[str, Any]:
    """executes a full backtest based on the given configuration.
    args.
    config config object containing all configuration settings.
    strategy params override optional dictionary of strategy parameters to override config.
    log manager optional logmanager instance.
    returns.
    dict dictionary containing performance metrics and output directory."""
    if log_manager is None:
        from utils.logger import LogManager

        log_manager = LogManager(log_level=config.logging.level, log_dir=config.logging.directory)

    class DummyLogger:
        def info(self, msg: str) -> None:
            pass

        def debug(self, msg: str) -> None:
            pass

        def warning(self, msg: str) -> None:
            pass

        def error(self, msg: str) -> None:
            pass

    class DummyLogManager:
        def __init__(self) -> None:
            self.engine = DummyLogger()
            self.strategy = DummyLogger()
            self.portfolio = DummyLogger()

    if log_manager is None:
        log_manager = DummyLogManager()

    engine_logger = log_manager.engine
    events: queue.Queue[Any] = queue.Queue()

    audit_logger = AuditLogger(config)

    if config.data.source == "yahoo":
        bars = YahooDataHandler(
            events=events,
            symbols=config.data.symbol_list,
            start_date=config.data.start_date,
            end_date=config.data.end_date,
            logger=engine_logger,
            warmup_days=getattr(config.data, "warmup_days", 0),
        )
    else:
        raise ValueError(f"Unsupported data source: {config.data.source}")

    if not bars.continue_backtest:
        raise RuntimeError("Failed to load data.")

    load_strategies()
    strategy_class = get_strategy(config.strategy.name)

    # merge override parameters.
    final_params = dict(config.strategy.parameters)
    if strategy_params_override:
        final_params.update(strategy_params_override)

    validate_strategy_parameters(strategy_class, final_params)

    strategy = strategy_class(
        data_handler=bars,
        events=events,
        logger=log_manager.strategy,
        audit_logger=audit_logger,
        **final_params,
    )

    risk_manager = build_risk_manager(config, log_manager.portfolio)
    risk_manager.audit_logger = audit_logger

    port = Portfolio(
        data_handler=bars,
        events=events,
        start_date=config.data.start_date,
        initial_capital=config.initial_capital,
        logger=log_manager.portfolio,
        risk_manager=risk_manager,
        audit_logger=audit_logger,
    )

    if broker_override:
        broker = broker_override(events=events, data_handler=bars)
    else:
        broker = SimulatedBroker(events=events, data_handler=bars, config=config)

    from analytics.trades import TradeTracker

    trade_tracker = TradeTracker()

    # wrap portfolio.update fill to intercept fills for tradetracker.
    original_update_fill = port.update_fill

    def wrapped_update_fill(event):
        if event.type == "FILL":
            trade_tracker.process_fill(event)
        original_update_fill(event)

    setattr(port, "update_fill", wrapped_update_fill)

    # let trade tracker log to audit logger when trades close.
    original_process_fill = trade_tracker.process_fill

    def wrapped_process_fill(event):
        original_process_fill(event)
        # we can just iterate closed trades later or let tradetracker log.
        # actually it s easier to just log all closed trades at the end.

    engine = Engine(
        events_queue=events,
        data_handler=bars,
        strategy=strategy,
        portfolio=port,
        execution_handler=broker,
        logger=engine_logger,
        audit_logger=audit_logger,
    )

    engine.run_backtest()

    # return basic stats for optimization backwards compatibility.
    stats = port.get_summary_stats()

    # if optimization is not enabled run the full analytics platform.
    # optimization runs thousands of backtests we don t want to generate tearsheets for each.
    if not config.optimization.enabled:
        from analytics.benchmark import BenchmarkAnalyzer
        from analytics.metrics import MetricsEngine
        from analytics.plots import PlotGenerator
        from analytics.tearsheet import ReportGenerator

        engine_logger.info("Generating Analytics Platform Reports...")

        metrics_engine = MetricsEngine(port.equity_curve, trade_tracker.closed_trades)
        adv_metrics = metrics_engine.calculate_all()

        bench_ticker = config.reports.benchmark or "^NSEI"
        eq_returns = (
            port.equity_curve["returns"].fillna(0.0)
            if port.equity_curve is not None
            else pd.Series(dtype=float)
        )

        bench_analyzer = BenchmarkAnalyzer(
            portfolio_returns=eq_returns,
            benchmark_ticker=bench_ticker,
            start_date=config.data.start_date,
            end_date=config.data.end_date,
        )
        bench_metrics = bench_analyzer.calculate_all()

        charts = {}
        if config.reports.charts:
            engine_logger.info("Generating Plots...")
            plotter = PlotGenerator(
                port.equity_curve, trade_tracker.closed_trades, bench_analyzer.benchmark_returns
            )
            charts = {
                "equity": plotter.plot_equity_curve(),
                "drawdown": plotter.plot_drawdowns(),
                "heatmap": plotter.plot_monthly_heatmap(),
                "rolling_sharpe": plotter.plot_rolling_sharpe(),
                "trade_dist": plotter.plot_trade_distribution(),
            }

        engine_logger.info("Exporting Tearsheet...")
        report_gen = ReportGenerator(
            metrics=adv_metrics,
            benchmark_metrics=bench_metrics,
            trades=trade_tracker.closed_trades,
            charts=charts,
            config=config,
        )
        report_gen.export_all()

        # merge advanced metrics into stats for output.
        stats.update(adv_metrics)
        stats.update(bench_metrics)

    # inject trades into audit logger at the end.
    for i, trade in enumerate(trade_tracker.closed_trades):
        audit_logger.log_trade(
            {
                "Trade ID": f"TRD-{i + 1}",
                "Ticker": trade.get("symbol", "Unknown"),
                "Buy Date": trade.get("entry_date"),
                "Sell Date": trade.get("exit_date"),
                "Entry Price": trade.get("entry_price", 0.0),
                "Exit Price": trade.get("exit_price", 0.0),
                "Quantity": trade.get("quantity", 0),
                "Gross PnL": trade.get("gross_pnl", trade.get("pnl", 0.0)),
                "Net PnL": trade.get("pnl", 0.0),
                "Return %": trade.get("return", 0.0) * 100,
                "Holding Days": trade.get("holding_period", 0),
                "Exit Reason": "Signal",
                "Strategy": config.strategy.name,
            }
        )

    out_stats: Dict[str, Any] = dict(stats)
    out_stats["Output_Dir"] = audit_logger.output_dir
    audit_logger.save_all(out_stats)

    # generate trade replay html.
    try:
        from research.trade_replay import generate_trade_replay

        generate_trade_replay(audit_logger.output_dir)
    except ImportError:
        engine_logger.warning("Trade replay generator not found.")

    return stats
