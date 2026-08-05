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
from optimization.montecarlo import MCBrokerFactory, MonteCarloAnalyzer


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
            method="montecarlo",
            workers=1,
            parameters={"_mc_iterations": 2, "_slippage_std": 0.002},
        ),
    )


@patch("optimization.montecarlo.run_backtest_with_config")
def test_montecarlo_run(mock_run_bt, base_config):
    # mock run backtest with config to return varying stats.
    def side_effect(config, broker_override):
        assert isinstance(broker_override, MCBrokerFactory)
        assert broker_override.slippage_std == 0.002
        return {"Return": 5.0, "Sharpe": 1.2}

    mock_run_bt.side_effect = side_effect

    analyzer = MonteCarloAnalyzer(base_config)
    results = analyzer.run()

    assert len(results) == 2
    for r in results:
        assert r["error"] is None
        assert r["stats"]["Return"] == 5.0


@patch("optimization.montecarlo.concurrent.futures.ProcessPoolExecutor")
@patch("optimization.montecarlo.run_backtest_with_config")
def test_montecarlo_run_parallel(mock_run_bt, mock_executor, base_config):
    from dataclasses import replace

    base_config = replace(base_config, optimization=replace(base_config.optimization, workers=2))
    mock_run_bt.return_value = {"Return": 10.0, "Sharpe": 2.0}

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

    with patch("optimization.montecarlo.concurrent.futures.as_completed", lambda fs: fs):
        analyzer = MonteCarloAnalyzer(base_config)
        results = analyzer.run()

    assert len(results) == 2
    assert results[0]["stats"]["Return"] == 10.0


def test_montecarlo_broker():
    import queue

    from core.events import OrderEvent
    from optimization.montecarlo import MonteCarloBroker

    events = queue.Queue()
    data_handler = MagicMock()
    data_handler.get_latest_bar_value.return_value = 100.0

    broker = MonteCarloBroker(
        events, data_handler, slippage_std=0.01, commission_base=1.0, latency_prob=0.0
    )

    # buy order.
    order = OrderEvent("RELIANCE.NS", "MKT", 100, "BUY")
    broker.execute_order(order)
    assert not events.empty()
    fill = events.get()
    assert fill.fill_cost >= 0  # slippage applied.
    assert fill.commission > 0

    # sell order.
    order = OrderEvent("RELIANCE.NS", "MKT", 100, "SELL")
    broker.execute_order(order)
    assert not events.empty()
    fill = events.get()

    # latency test.
    broker.latency_prob = 1.0
    broker.execute_order(order)
    assert events.empty()  # order dropped due to latency probability.


def test_montecarlo_error(base_config):
    from optimization.montecarlo import _run_mc_job_safe

    with patch(
        "optimization.montecarlo.run_backtest_with_config", side_effect=Exception("Test Error")
    ):
        res = _run_mc_job_safe(base_config, 0)
        assert res["error"] == "Test Error"
