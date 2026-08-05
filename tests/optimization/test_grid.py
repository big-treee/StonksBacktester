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
from optimization.grid_search import GridSearchOptimizer


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
            enabled=True, method="grid", parameters={"short": [10, 20], "long": [100, 200, 300]}
        ),
    )


def test_grid_search_generation(base_config):
    optimizer = GridSearchOptimizer(base_config)
    params = optimizer.generate_parameter_sets()

    assert len(params) == 2 * 3
    # check if a specific combination exists.
    assert {"short": 10, "long": 200} in params
    assert {"short": 20, "long": 300} in params


def test_grid_search_empty(base_config):
    from dataclasses import replace

    empty_opt = replace(base_config.optimization, parameters={})
    cfg = replace(base_config, optimization=empty_opt)

    optimizer = GridSearchOptimizer(cfg)
    params = optimizer.generate_parameter_sets()
    assert params == [{}]


def test_grid_search_single_values(base_config):
    from dataclasses import replace

    opt = replace(base_config.optimization, parameters={"short": 10, "long": [100, 200]})
    cfg = replace(base_config, optimization=opt)

    optimizer = GridSearchOptimizer(cfg)
    params = optimizer.generate_parameter_sets()
    assert len(params) == 2
    assert {"short": 10, "long": 100} in params
