import os

import pytest

from analytics.tearsheet import ReportGenerator
from config.models import (
    BrokerConfig,
    Config,
    DataConfig,
    LoggingConfig,
    ReportsConfig,
    RiskConfig,
    StrategyConfig,
)


@pytest.fixture
def dummy_config():
    return Config(
        initial_capital=100000,
        data=DataConfig("yahoo", ["RELIANCE.NS"], "2020-01-01", "2020-12-31"),
        strategy=StrategyConfig("MovingAverageCross"),
        broker=BrokerConfig("zerodha", "cnc"),
        logging=LoggingConfig("INFO", "logs"),
        risk=RiskConfig(None),  # type ignore.
        reports=ReportsConfig(html=True, charts=False),
    )


def test_report_generator(dummy_config, tmpdir):
    # change working directory for report generation to tmpdir.
    original_cwd = os.getcwd()
    os.chdir(tmpdir)

    try:
        metrics = {"CAGR (%)": 15.0}
        bench = {"Alpha (Annualized %)": 5.0}
        trades = [{"symbol": "RELIANCE.NS", "pnl": 100}]
        charts = {}

        gen = ReportGenerator(metrics, bench, trades, charts, dummy_config)
        gen.export_all()

        assert os.path.exists("reports/tearsheet.html")
        assert os.path.exists("reports/trades.csv")
        assert os.path.exists("reports/metrics.json")
    finally:
        os.chdir(original_cwd)
