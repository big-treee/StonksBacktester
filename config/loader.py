import os

import yaml

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


def load_config(config_path: str = "config/settings.yaml") -> Config:
    """loads the yaml configuration file and returns a strongly typed config dataclass.
    args.
    config path str the path to the yaml configuration file.
    returns.
    config the complete application configuration.
    raises.
    filenotfounderror if the configuration file is not found."""
    if not os.path.isabs(config_path):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_path = os.path.join(base_dir, config_path)

    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found at {config_path}")

    with open(config_path, "r") as file:
        raw = yaml.safe_load(file)

    return Config(
        initial_capital=float(raw.get("initial_capital", 1000000.0)),
        data=DataConfig(
            source=raw["data"].get("source", "yahoo"),
            symbol_list=__import__(
                "markets.india.universe", fromlist=["UniverseEngine"]
            ).UniverseEngine.expand_symbol_list(raw["data"].get("symbols", [])),
            start_date=raw["data"].get("start_date", ""),
            end_date=raw["data"].get("end_date", ""),
        ),
        strategy=StrategyConfig(
            name=raw["strategy"].get("name", ""), parameters=raw["strategy"].get("parameters", {})
        ),
        broker=BrokerConfig(
            name=raw.get("broker", {}).get("name", "zerodha"),
            product=raw.get("broker", {}).get("product", "cnc"),
            charges=raw.get("broker", {}).get("charges", {"enabled": True}),
            commission_model=raw.get("broker", {}).get("commission_model", ""),
            slippage_model=raw.get("broker", {}).get("slippage_model", ""),
        ),
        logging=LoggingConfig(
            level=raw["logging"].get("level", "INFO"),
            directory=raw["logging"].get("directory", "logs"),
            save_backtest=raw["logging"].get("save_backtest", True),
            output_folder=raw["logging"].get("output_folder", "backtests/"),
        ),
        risk=RiskConfig(
            position_sizer=RiskModelConfig(
                name=raw.get("risk", {}).get("position_sizer", {}).get("name", "FixedShares"),
                parameters=raw.get("risk", {}).get("position_sizer", {}).get("parameters", {}),
            ),
            validators=[
                RiskModelConfig(name=v.get("name", ""), parameters=v.get("parameters", {}))
                for v in raw.get("risk", {}).get("validators", [])
            ],
        ),
        optimization=OptimizationConfig(
            enabled=raw.get("optimization", {}).get("enabled", False),
            method=raw.get("optimization", {}).get("method", "grid"),
            workers=raw.get("optimization", {}).get("workers", 1),
            parameters=raw.get("optimization", {}).get("parameters", {}),
        ),
        reports=ReportsConfig(
            html=raw.get("reports", {}).get("html", True),
            pdf=raw.get("reports", {}).get("pdf", False),
            benchmark=raw.get("reports", {}).get("benchmark", None),
            charts=raw.get("reports", {}).get("charts", True),
        ),
        market=MarketConfig(
            country=raw.get("market", {}).get("country", "india"),
            exchange=raw.get("market", {}).get("exchange", "NSE"),
            currency=raw.get("market", {}).get("currency", "INR"),
            timezone=raw.get("market", {}).get("timezone", "Asia/Kolkata"),
        ),
    )
