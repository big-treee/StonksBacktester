import dataclasses
import json
import os
import sys
import time

import pandas as pd
import yfinance as yf

from config.loader import load_config
from core.runner import run_backtest_with_config
from research.analyzer import ResearchAnalyzer
from research.notebook import ResearchNotebook
from research.reporter import HTMLReportBuilder
from strategy.registry import load_strategies
from utils.logger import LogManager


def _resample_monthly_last(series: pd.Series) -> pd.Series:
    try:
        return series.resample("ME").last()
    except ValueError:
        return series.resample("M").last()


def run_comparison():
    strategies_to_test = []
    try:
        config = load_config()
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)

    log_manager = LogManager(log_level=config.logging.level, log_dir=config.logging.directory)
    logger = log_manager.engine

    load_strategies()

    output_dir = f"research/comparisons/comp_{time.strftime('%Y-%m-%d_%H-%M-%S')}"
    os.makedirs(output_dir, exist_ok=True)

    HTMLReportBuilder(output_dir)
    notebook = ResearchNotebook()

    stats_list = []
    equity_series_list = []
    drawdown_series_list = []
    monthly_returns_list = []

    all_trades = []
    all_decisions = []
    parameters_dict = {}

    stock_metadata = {}

    # outer loop run for every symbol independently.
    for symbol in config.data.symbol_list:
        logger.info(f"========== PROCESSING STOCK: {symbol} ==========")

        # fetch metadata.
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            stock_metadata[symbol] = {
                "sector": info.get("sector", "Unknown"),
                "marketCap": info.get("marketCap", None),
            }
        except Exception as e:
            logger.warning(f"Failed to fetch metadata for {symbol}: {e}")
            stock_metadata[symbol] = {"sector": "Unknown", "marketCap": None}

        # create config for single symbol.
        single_data_config = dataclasses.replace(config.data, symbol_list=[symbol])

        symbol_equity_series = []

        for strat_config in strategies_to_test:
            strat_name = strat_config["name"]
            parameters_dict[strat_name] = strat_config["parameters"]
            logger.info(f"--- Strategy: {strat_name.upper()} ---")

            new_reports_config = dataclasses.replace(config.reports, charts=False)
            new_strategy_config = dataclasses.replace(
                config.strategy, name=strat_name, parameters=strat_config["parameters"]
            )
            new_config = dataclasses.replace(
                config,
                strategy=new_strategy_config,
                data=single_data_config,
                reports=new_reports_config,
            )

            try:
                stats = run_backtest_with_config(new_config, log_manager=log_manager)
                stats["Strategy"] = strat_name
                stats["Stock"] = symbol
                stats_list.append(stats)

                out_dir = stats.get("Output_Dir")
                if out_dir:
                    # . load equity compute drawdowns.
                    equity_csv = os.path.join(out_dir, "portfolio.csv")
                    if os.path.exists(equity_csv):
                        df_eq = pd.read_csv(equity_csv)
                        df_eq["Date"] = pd.to_datetime(df_eq["Date"])
                        df_eq.set_index("Date", inplace=True)

                        if "Portfolio Value" in df_eq.columns:
                            col_name = f"{strat_name}_{symbol}"
                            s_eq = df_eq["Portfolio Value"].rename(col_name)
                            equity_series_list.append(s_eq)
                            symbol_equity_series.append(s_eq)

                            hwm = s_eq.cummax()
                            dd = (s_eq - hwm) / hwm
                            drawdown_series_list.append(dd.rename(col_name))

                            monthend_eq = _resample_monthly_last(s_eq)
                            mo_ret = monthend_eq.pct_change().dropna()
                            for dt, ret in mo_ret.items():
                                monthly_returns_list.append(
                                    {
                                        "Date": dt.strftime("%Y-%m"),
                                        "Stock": symbol,
                                        "Strategy": strat_name,
                                        "Return": ret,
                                    }
                                )

                    # . load trades.
                    trades_csv = os.path.join(out_dir, "trades.csv")
                    if os.path.exists(trades_csv):
                        df_tr = pd.read_csv(trades_csv)
                        if "Strategy" not in df_tr.columns:
                            df_tr["Strategy"] = strat_name
                        if "Stock" not in df_tr.columns:
                            df_tr["Stock"] = symbol
                        all_trades.append(df_tr)

                    # . load decisions trade replay.
                    decisions_csv = os.path.join(out_dir, "decision_log.csv")
                    if os.path.exists(decisions_csv):
                        df_dec = pd.read_csv(decisions_csv)
                        if "Strategy" not in df_dec.columns:
                            df_dec.insert(0, "Strategy", strat_name)
                        if "Stock" not in df_dec.columns:
                            df_dec.insert(1, "Stock", symbol)
                        all_decisions.append(df_dec)

            except Exception as e:
                logger.error(f"Failed to run {strat_name} on {symbol}: {e}")

        # compute buy hold for this symbol.
        logger.info(f"Computing Benchmark for {symbol}...")
        try:
            from analytics.benchmark import BenchmarkAnalyzer

            first_curve = symbol_equity_series[0] if symbol_equity_series else None
            if first_curve is not None:
                dummy_returns = pd.Series(0.0, index=first_curve.index)
                bench_analyzer = BenchmarkAnalyzer(
                    portfolio_returns=dummy_returns,
                    benchmark_ticker=symbol,  # use the symbol itself as its own benchmark.
                    start_date=config.data.start_date,
                    end_date=config.data.end_date,
                )
                b_returns = bench_analyzer.aligned_benchmark
                b_equity = (1.0 + b_returns).cumprod() * config.initial_capital

                col_name = f"Buy & Hold_{symbol}"
                b_eq_series = b_equity.rename(col_name)
                equity_series_list.append(b_eq_series)

                b_dd = (b_eq_series - b_eq_series.cummax()) / b_eq_series.cummax()
                drawdown_series_list.append(b_dd.rename(col_name))

                monthend_eq = _resample_monthly_last(b_eq_series)
                mo_ret = monthend_eq.pct_change().dropna()
                for dt, ret in mo_ret.items():
                    monthly_returns_list.append(
                        {
                            "Date": dt.strftime("%Y-%m"),
                            "Stock": symbol,
                            "Strategy": "Buy & Hold",
                            "Return": ret,
                        }
                    )

                bh_total_return = (
                    (b_equity.iloc[-1] / config.initial_capital - 1) * 100
                    if len(b_equity) > 0
                    else 0
                )
                bh_max_dd = b_dd.min() * -100
                stats_list.append(
                    {
                        "Strategy": "Buy & Hold",
                        "Stock": symbol,
                        "Return": bh_total_return,
                        "Max Drawdown": bh_max_dd,
                        "Sharpe": 0.0,
                        "Sortino": 0.0,
                        "Win Rate (%)": 0.0,
                        "Total Trades": 1,
                        "Net Profit (INR)": (
                            b_equity.iloc[-1] - config.initial_capital if len(b_equity) > 0 else 0
                        ),
                    }
                )
        except Exception as e:
            logger.error(f"Failed to compute Benchmark for {symbol}: {e}")

    # generate structured datasets.
    logger.info("Generating Structured Output Datasets...")

    # . strategy metrics.csv.
    df_stats = pd.DataFrame(stats_list)
    df_stats.to_csv(os.path.join(output_dir, "strategy_metrics.csv"), index=False)

    # . equity curves.csv.
    if equity_series_list:
        df_equity = pd.concat(equity_series_list, axis=1).ffill()
        df_equity.index.name = "Date"
        df_equity.to_csv(os.path.join(output_dir, "equity_curves.csv"))

    # . drawdowns.csv.
    if drawdown_series_list:
        df_dd = pd.concat(drawdown_series_list, axis=1).ffill()
        df_dd.index.name = "Date"
        df_dd.to_csv(os.path.join(output_dir, "drawdowns.csv"))

    # . monthly returns.csv.
    if monthly_returns_list:
        df_mo = pd.DataFrame(monthly_returns_list)
        df_mo["ColName"] = df_mo["Strategy"] + "_" + df_mo["Stock"]
        df_mo_piv = df_mo.pivot(index="Date", columns="ColName", values="Return")
        df_mo_piv.to_csv(os.path.join(output_dir, "monthly_returns.csv"))

    df_all_trades = pd.DataFrame()
    # . trade log.csv.
    if all_trades:
        df_all_trades = pd.concat(all_trades, ignore_index=True)
        df_all_trades.to_csv(os.path.join(output_dir, "trade_log.csv"), index=False)

    # . trade replay.csv decisions.
    if all_decisions:
        df_all_decisions = pd.concat(all_decisions, ignore_index=True)
        df_all_decisions.to_csv(os.path.join(output_dir, "trade_replay.csv"), index=False)

    # . parameters.json.
    with open(os.path.join(output_dir, "parameters.json"), "w") as f:
        json.dump(parameters_dict, f, indent=4)

    # . metadata.json.
    metadata = {
        "start_date": config.data.start_date,
        "end_date": config.data.end_date,
        "universe": config.data.symbol_list,
        "initial_capital": config.initial_capital,
        "commissions": config.broker.commission_model,
        "slippage": config.broker.slippage_model,
        "run_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    with open(os.path.join(output_dir, "metadata.json"), "w") as f:
        json.dump(metadata, f, indent=4)

    # invoke researchanalyzer for phase x reports.
    logger.info("Generating Phase X+1 Research Analysis Reports...")
    analyzer = ResearchAnalyzer(
        output_dir=output_dir,
        metadata=metadata,
        stats_list=stats_list,
        trades_df=df_all_trades,
        stock_metadata=stock_metadata,
    )
    analyzer.generate_all_reports()

    # log to research notebook.
    notebook.log_experiment(
        {
            "dataset": config.data.symbol_list,
            "start_date": config.data.start_date,
            "end_date": config.data.end_date,
            "strategies_tested": [s["name"] for s in strategies_to_test],
            "results_dir": output_dir,
            "best_return_strategy": (
                df_stats.loc[df_stats["Return"].idxmax(), "Strategy"]
                if not df_stats.empty and "Return" in df_stats.columns
                else None
            ),
        }
    )

    logger.info(f"Research datasets and Phase X+1 analysis successfully created in {output_dir}")


if __name__ == "__main__":
    run_comparison()
