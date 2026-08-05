from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class BrokerConfig:
    name: str = "zerodha"
    product: str = "cnc"
    charges: dict[str, Any] = field(default_factory=lambda: {"enabled": True})
    commission_model: str = "Zerodha"
    slippage_model: str = "ZeroSlippage"


@dataclass(frozen=True)
class StrategyConfig:
    name: str
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DataConfig:
    source: str
    symbol_list: list[str]
    start_date: str
    end_date: str
    warmup_days: int = 0


@dataclass(frozen=True)
class LoggingConfig:
    level: str
    directory: str
    save_backtest: bool = True
    output_folder: str = "backtests/"


@dataclass(frozen=True)
class RiskModelConfig:
    name: str
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RiskConfig:
    position_sizer: RiskModelConfig
    validators: list[RiskModelConfig] = field(default_factory=list)


@dataclass(frozen=True)
class OptimizationConfig:
    enabled: bool = False
    method: str = "grid"  # grid random walkforward montecarlo.
    workers: int = 1
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ReportsConfig:
    html: bool = True
    pdf: bool = False
    benchmark: str | None = None
    charts: bool = True


@dataclass(frozen=True)
class MarketConfig:
    country: str = "india"
    exchange: str = "NSE"
    currency: str = "INR"
    timezone: str = "Asia/Kolkata"


@dataclass(frozen=True)
class Config:
    initial_capital: float
    data: DataConfig
    strategy: StrategyConfig
    broker: BrokerConfig
    logging: LoggingConfig
    risk: RiskConfig
    optimization: OptimizationConfig = field(default_factory=OptimizationConfig)
    reports: ReportsConfig = field(default_factory=ReportsConfig)
    market: MarketConfig = field(default_factory=MarketConfig)
