"""interactive prompt and validation helpers for nse quant cli."""

import datetime
from typing import Any, Dict

from rich.console import Console
from rich.prompt import Confirm, Prompt

from config.models import (
    BrokerConfig,
    Config,
    DataConfig,
    LoggingConfig,
    MarketConfig,
    OptimizationConfig,
    ReportsConfig,
    RiskConfig,
    RiskModelConfig,
    StrategyConfig,
)
from markets.india.universe import get_universe_tickers
from strategy.registry import get_strategy, list_registered_strategies, load_strategies
from utils.indian_format import format_indian_currency

console = Console()


def prompt_universe() -> list[str]:
    """prompts the user for symbols or universe shortcuts."""
    default_input = "RELIANCE.NS, TCS.NS"
    raw = Prompt.ask(
        "\nStocks or universe (comma-separated or e.g. INDEX:NIFTY_50)",
        default=default_input,
    )
    raw = raw.strip()
    if raw.startswith("INDEX:") or raw.startswith("SECTOR:"):
        tickers = get_universe_tickers(raw)
        if tickers:
            console.print(f"Resolved {len(tickers)} symbols from {raw}")
            return tickers

    symbols = [s.strip().upper() for s in raw.split(",") if s.strip()]
    formatted = []
    for s in symbols:
        if not s.endswith(".NS") and not s.endswith(".BO") and not s.startswith("^"):
            s = f"{s}.NS"
        formatted.append(s)
    return formatted


def prompt_dates() -> tuple[str, str]:
    """prompts for start and end dates."""
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    start_date = Prompt.ask("Start date (YYYY-MM-DD)", default="2021-01-01")
    end_date = Prompt.ask("End date (YYYY-MM-DD)", default=today_str)
    return start_date, end_date


def prompt_capital() -> float:
    """prompts for initial capital."""
    val = Prompt.ask("Initial capital in INR", default="100000")
    try:
        cap = float(val.replace(",", "").replace("₹", ""))
        console.print(f"Capital set to: {format_indian_currency(cap)}")
        return cap
    except ValueError:
        return 100000.0


def prompt_strategy() -> tuple[str, Dict[str, Any]]:
    """prompts for strategy selection by number ... or name and sets strategy parameters."""
    load_strategies()
    strategies = list_registered_strategies()
    if not strategies:
        strategies = [
            "sma",
            "ema",
            "rsi",
            "macd",
            "bollinger",
            "mean_reversion",
            "breakout",
            "momentum",
        ]

    console.print("\nAvailable Strategies:")
    for idx, strat in enumerate(strategies, 1):
        strat_cls = get_strategy(strat)
        desc = getattr(strat_cls, "description", strat)
        console.print(f"  {idx}. {strat} ({desc})")

    ans = Prompt.ask(
        "\nChoose strategy (enter number 1-{} or name)".format(len(strategies)), default="1"
    ).strip()

    strat_name = strategies[0]
    if ans.isdigit():
        num = int(ans)
        if 1 <= num <= len(strategies):
            strat_name = strategies[num - 1]
    elif ans in strategies:
        strat_name = ans

    console.print(f"Selected strategy: {strat_name}")
    strat_cls = get_strategy(strat_name)

    params: Dict[str, Any] = {}
    req_params = getattr(strat_cls, "required_parameters", {})

    if req_params:
        console.print(f"\nStrategy parameters for {strat_name}:")
        defaults_map = {
            "short_window": 20,
            "long_window": 50,
            "rsi_period": 14,
            "oversold": 30,
            "overbought": 70,
            "slow_period": 26,
            "fast_period": 12,
            "signal_period": 9,
            "period": 20,
            "std_dev": 2,
            "lookback": 20,
            "window": 20,
            "entry_z": 2.0,
            "exit_z": 0.0,
            "fast": 12,
            "slow": 26,
            "signal": 9,
            "num_std": 2,
        }
        descriptions_map = {
            "short_window": "Short moving average period in days",
            "long_window": "Long moving average period in days",
            "rsi_period": "RSI momentum calculation lookback in days",
            "oversold": "RSI oversold buy threshold level (e.g. 30)",
            "overbought": "RSI overbought exit threshold level (e.g. 70)",
            "slow_period": "MACD slow EMA period in days",
            "fast_period": "MACD fast EMA period in days",
            "signal_period": "MACD signal line smoothing period in days",
            "period": "Indicator calculation lookback period in days",
            "std_dev": "Standard deviation multiplier for volatility bands",
            "lookback": "Historical price lookback window in days",
            "window": "Rolling mean lookback window in days",
            "entry_z": "Z-score oversold dip depth to buy (e.g. 2.0 = 2 std dev below mean)",
            "exit_z": "Z-score mean reversion target to exit (e.g. 0.0 = back to average)",
            "fast": "Fast moving average period in days",
            "slow": "Slow moving average period in days",
            "signal": "Signal smoothing period in days",
            "num_std": "Standard deviation multiplier for volatility bands",
            "threshold": "Minimum return percentage to trigger signal",
        }
        for param_name, param_type in req_params.items():
            default_val = defaults_map.get(param_name, 20)
            desc = descriptions_map.get(param_name, f"{param_name} value")
            user_val = Prompt.ask(
                f"  {param_name} ({param_type.__name__}) [{desc}]", default=str(default_val)
            )
            try:
                params[param_name] = param_type(user_val)
            except (ValueError, TypeError):
                params[param_name] = default_val

    return strat_name, params


def prompt_risk() -> RiskConfig:
    """Prompts for position sizer and risk limits by number (1, 2, 3...)."""
    sizers_list = [
        ("1", "fixed_fractional", "Fixed Fractional (% of capital per trade)"),
        ("2", "fixed_shares", "Fixed Shares (Fixed number of shares)"),
        ("3", "volatility_target", "Volatility Target (Scaled by volatility)"),
        ("4", "risk_percentage", "Risk Percentage (Risk % with stop loss %)"),
        ("5", "kelly", "Kelly Criterion (Optimal fractional sizing)"),
    ]
    console.print("\nPosition Sizing Options:")
    for num, key, label in sizers_list:
        console.print(f"  {num}. {label}")

    ans = Prompt.ask("Choose position sizing (1-5)", default="1").strip()

    sizer_name = "fixed_fractional"
    for num, key, label in sizers_list:
        if ans == num or ans == key:
            sizer_name = key
            break

    sizer_params: Dict[str, Any] = {}
    resolved_sizer = "FixedFractional"

    if sizer_name == "fixed_shares":
        resolved_sizer = "FixedShares"
        console.print("  Info: Fixed Shares buys a constant number of shares per trade signal.")
        num_shares = Prompt.ask("  Shares per trade [Fixed number of shares]", default="100")
        sizer_params["shares"] = int(num_shares)
    elif sizer_name == "fixed_fractional":
        resolved_sizer = "FixedFractional"
        console.print(
            "  Info: Fixed Fractional allocates a fixed % of your portfolio capital per trade."
        )
        pct = Prompt.ask(
            "  Capital per trade (%) [% of total account capital per trade]", default="5.0"
        )
        sizer_params["fraction"] = float(pct) / 100.0
    elif sizer_name == "volatility_target":
        resolved_sizer = "VolatilityPositionSizer"
        console.print(
            "  Info: Volatility Target scales position sizes inversely based on asset volatility."
        )
        target = Prompt.ask(
            "  Target volatility (%) [Target annualized portfolio volatility %]", default="15.0"
        )
        sizer_params["target_volatility"] = float(target) / 100.0
    elif sizer_name == "risk_percentage":
        resolved_sizer = "RiskPercentage"
        console.print(
            "  Info: Risk Percentage calculates position size based on Risk % and Stop Loss % distance."
        )
        risk_pct = Prompt.ask(
            "  Risk per trade (%) [Max % of account lost if stop loss is hit]", default="1.0"
        )
        stop_loss_pct = Prompt.ask(
            "  Stop loss (%) [Price drop % distance from entry price to stop loss]", default="5.0"
        )
        sizer_params["risk_pct"] = float(risk_pct) / 100.0
        sizer_params["stop_loss_pct"] = float(stop_loss_pct) / 100.0
    elif sizer_name == "kelly":
        resolved_sizer = "KellyCriterion"
        console.print(
            "  Info: Kelly Criterion calculates optimal fraction using win rate and payoff ratio."
        )
        win_rate = Prompt.ask("  Win rate (%) [Historical strategy win percentage]", default="55.0")
        payoff = Prompt.ask(
            "  Payoff ratio [Ratio of average win size to average loss size]", default="1.5"
        )
        sizer_params["win_rate"] = float(win_rate) / 100.0
        sizer_params["payoff_ratio"] = float(payoff)
        sizer_params["kelly_fraction"] = 0.5

    validator_configs = [
        RiskModelConfig(name="MaxDrawdownStop", parameters={"max_dd": 0.20}),
        RiskModelConfig(name="MaxOpenPositions", parameters={"max_positions": 10}),
        RiskModelConfig(name="MaxPortfolioExposure", parameters={"max_exposure_pct": 1.0}),
        RiskModelConfig(name="SufficientCashValidator", parameters={}),
    ]

    return RiskConfig(
        position_sizer=RiskModelConfig(name=resolved_sizer, parameters=sizer_params),
        validators=validator_configs,
    )


def prompt_broker() -> BrokerConfig:
    """prompts for broker selection by number ... ."""
    brokers_list = [
        ("1", "zerodha", "Zerodha (CNC / Delivery)"),
        ("2", "upstox", "Upstox"),
        ("3", "groww", "Groww"),
        ("4", "angelone", "Angel One"),
        ("5", "none", "None / Zero Charges"),
    ]
    console.print("\nBroker Charges Options:")
    for num, key, label in brokers_list:
        console.print(f"  {num}. {label}")

    ans = Prompt.ask("Choose broker (1-5)", default="1").strip()

    broker_name = "zerodha"
    for num, key, label in brokers_list:
        if ans == num or ans == key:
            broker_name = key
            break

    enabled = broker_name != "none"
    return BrokerConfig(
        name=broker_name if enabled else "none",
        product="cnc" if enabled else "none",
        charges={"enabled": enabled},
    )


def prompt_reports() -> ReportsConfig:
    """prompts for report and chart options."""
    benchmark = Prompt.ask("\nBenchmark symbol", default="^NSEI")
    generate_charts = Confirm.ask("Generate charts and HTML tearsheet?", default=True)
    return ReportsConfig(html=generate_charts, charts=generate_charts, benchmark=benchmark)


def interactive_config_builder() -> Config:
    """builds a complete config object interactively from simple terminal inputs."""
    console.print("\nNSE Quant Research Engine Setup")

    symbols = prompt_universe()
    start_date, end_date = prompt_dates()
    capital = prompt_capital()
    strat_name, strat_params = prompt_strategy()
    risk_cfg = prompt_risk()
    broker_cfg = prompt_broker()
    reports_cfg = prompt_reports()

    config = Config(
        initial_capital=capital,
        data=DataConfig(
            source="yahoo",
            symbol_list=symbols,
            start_date=start_date,
            end_date=end_date,
            warmup_days=30,
        ),
        strategy=StrategyConfig(name=strat_name, parameters=strat_params),
        broker=broker_cfg,
        logging=LoggingConfig(level="INFO", directory="logs/", save_backtest=True),
        risk=risk_cfg,
        optimization=OptimizationConfig(enabled=False),
        reports=reports_cfg,
        market=MarketConfig(),
    )
    return config
