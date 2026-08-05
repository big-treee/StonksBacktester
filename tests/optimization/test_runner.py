from unittest.mock import patch

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
from optimization.base import BaseOptimizer
from optimization.runner import OptimizationRunner


class DummyOptimizer(BaseOptimizer):
    def generate_parameter_sets(self):
        return [{"param1": 1}, {"param1": 2}]


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
        optimization=OptimizationConfig(enabled=True, method="grid", workers=1, parameters={}),
    )


@patch("optimization.runner.run_backtest_with_config")
def test_optimization_runner(mock_run_bt, base_config):
    mock_run_bt.return_value = {"Return": 10.0, "Sharpe": 1.5}

    optimizer = DummyOptimizer(base_config)
    runner = OptimizationRunner(base_config, optimizer)

    results = runner.run()

    assert len(results) == 2
    assert results[0]["stats"]["Return"] == 10.0
    # ensure sorted by sharpe reverse.
    assert results[0]["stats"]["Sharpe"] == 1.5


@patch("optimization.runner.concurrent.futures.ProcessPoolExecutor")
@patch("optimization.runner.run_backtest_with_config")
def test_optimization_runner_parallel(mock_run_bt, mock_executor, base_config):
    from dataclasses import replace

    base_config = replace(base_config, optimization=replace(base_config.optimization, workers=2))
    mock_run_bt.return_value = {"Return": 15.0, "Sharpe": 2.0}

    # mock processpoolexecutor to run synchronously.
    class MockExecutor:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def submit(self, fn, *args, **kwargs):
            class MockFuture:
                def result(self):
                    return fn(*args, **kwargs)

            return MockFuture()

    mock_executor.side_effect = MockExecutor

    # patch as completed.
    with patch("optimization.runner.concurrent.futures.as_completed", lambda fs: fs):
        optimizer = DummyOptimizer(base_config)
        runner = OptimizationRunner(base_config, optimizer)
        results = runner.run()

    assert len(results) == 2
    assert results[0]["stats"]["Return"] == 15.0


def test_runner_job_error(base_config):
    from optimization.runner import _run_single_job

    with patch(
        "optimization.runner.run_backtest_with_config", side_effect=Exception("Test Run Error")
    ):
        res = _run_single_job(base_config, {"param1": 1})
        assert res["error"] == "Test Run Error"
