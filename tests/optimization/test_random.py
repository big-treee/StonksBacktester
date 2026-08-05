import pytest

from config.models import (
    BrokerConfig,
    Config,
    DataConfig,
    LoggingConfig,
    OptimizationConfig,
    RiskConfig,
    RiskModelConfig,
    StrategyConfig,
)
from optimization.random_search import RandomSearchOptimizer


@pytest.fixture
def base_config():
    return Config(
        initial_capital=100000.0,
        data=DataConfig(
            source="yahoo",
            symbol_list=["RELIANCE.NS"],
            start_date="2020-01-01",
            end_date="2021-01-01",
        ),
        strategy=StrategyConfig(name="sma"),
        broker=BrokerConfig(commission_model="Basic", slippage_model="Basic"),
        logging=LoggingConfig(level="INFO", directory="logs"),
        risk=RiskConfig(position_sizer=RiskModelConfig(name="FixedShares")),
        optimization=OptimizationConfig(
            enabled=True,
            method="random",
            parameters={"short": [10, 20], "long": [100, 200, 300], "_iterations": 5},
        ),
    )


def test_random_search_generation(base_config):
    optimizer = RandomSearchOptimizer(base_config)
    params = optimizer.generate_parameter_sets()

    assert len(params) == 5
    for p in params:
        assert p["short"] in [10, 20]
        assert p["long"] in [100, 200, 300]
        assert "_iterations" not in p


def test_random_search_empty(base_config):
    from dataclasses import replace

    empty_opt = replace(base_config.optimization, parameters={})
    cfg = replace(base_config, optimization=empty_opt)

    optimizer = RandomSearchOptimizer(cfg)
    params = optimizer.generate_parameter_sets()
    assert params == [{}]
