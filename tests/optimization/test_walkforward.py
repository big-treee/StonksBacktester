from unittest.mock import MagicMock, patch

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
from optimization.walkforward import WalkForwardAnalyzer


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
            method="walkforward",
            parameters={"_train_months": 6, "_test_months": 3, "_step_months": 3},
        ),
    )


@patch("optimization.walkforward.OptimizationRunner")
@patch("optimization.walkforward.run_backtest_with_config")
def test_walkforward_run(mock_run_bt, MockRunner, base_config):
    # mock the optimizationrunner to return dummy results for training.
    mock_runner_instance = MagicMock()
    mock_runner_instance.run.return_value = [
        {"parameters": {"dummy": 1}, "stats": {"Return": 10.0}}
    ]
    MockRunner.return_value = mock_runner_instance

    # mock the oos backtest to return dummy stats.
    mock_run_bt.return_value = {"Return": 5.0}

    analyzer = WalkForwardAnalyzer(base_config)
    results = analyzer.run()

    # total months jan to jan.
    # train months test months. step months.
    # fold train jan jul. test jul oct.
    # fold train apr oct. test oct jan.
    assert len(results) == 2

    assert results[0]["train_start"] == "2020-01-01"
    assert results[0]["test_end"] == "2020-10-01"
    assert results[0]["oos_stats"]["Return"] == 5.0

    assert results[1]["train_start"] == "2020-04-01"
    assert results[1]["test_end"] == "2021-01-01"
    assert results[1]["oos_stats"]["Return"] == 5.0
