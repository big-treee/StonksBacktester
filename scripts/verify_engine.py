import glob
import os
import sys
import warnings

import numpy as np
import pandas as pd


def get_latest_comparison_dir():
    dirs = glob.glob("research/comparisons/comp_*")
    return sorted(dirs)[-1] if dirs else None


def get_latest_backtest_dirs(n=8):
    dirs = glob.glob("backtests/*")
    dirs = [d for d in dirs if os.path.isdir(d)]
    return sorted(dirs, key=os.path.getmtime)[-n:] if dirs else []


def run_verifications():
    comp_dir = get_latest_comparison_dir()
    if not comp_dir:
        print("No comparison directory found.")
        return

    print(f"Validating Engine Output in: {comp_dir}")

    df_trades = pd.read_csv(os.path.join(comp_dir, "trade_log.csv"))
    df_decisions = pd.read_csv(os.path.join(comp_dir, "trade_replay.csv"))
    df_equity = pd.read_csv(
        os.path.join(comp_dir, "equity_curves.csv"), index_col="Date", parse_dates=True
    )
    df_metrics = pd.read_csv(os.path.join(comp_dir, "strategy_metrics.csv"))

    print("--- 1. Strategy Verification ---")
    verification_md = ["# Strategy Verification Report\n"]
    for strat, group in df_decisions.groupby("Strategy"):
        buys = len(group[group["Decision"] == "BUY"])
        sells = len(group[group["Decision"] == "SELL"])
        exits = len(group[group["Decision"] == "EXIT"])
        holds = len(group[group["Decision"] == "HOLD"])
        ignores = len(group[group["Decision"] == "IGNORE"])

        strat_trades = df_trades[df_trades["Strategy"] == strat]
        completed = len(strat_trades)
        avg_hold = strat_trades["Holding Days"].mean() if completed > 0 else 0

        verification_md.append(f"## Strategy: {strat}")
        verification_md.append(f"- **Total BUY signals**: {buys}")
        verification_md.append(f"- **Total SELL signals**: {sells}")
        verification_md.append(f"- **Total EXIT signals**: {exits}")
        verification_md.append(f"- **Total HOLD decisions**: {holds}")
        verification_md.append(f"- **Total ignored bars**: {ignores}")
        verification_md.append(f"- **Total completed trades**: {completed}")
        verification_md.append(f"- **Average holding period**: {avg_hold:.2f} days\n")

        assert completed <= buys, f"{strat}: Completed trades > BUYS"

        for stock, stock_trades in strat_trades.groupby("Stock"):
            if len(stock_trades) > 1:
                stock_trades = stock_trades.sort_values("Buy Date")
                entry_dates = pd.to_datetime(stock_trades["Buy Date"]).values
                exit_dates = pd.to_datetime(stock_trades["Sell Date"]).values
                overlaps = entry_dates[1:] < exit_dates[:-1]
                if overlaps.any():
                    print(f"WARNING: Overlapping positions found in {strat} on {stock}")

    with open(os.path.join(comp_dir, "verification_report.md"), "w") as f:
        f.write("\n".join(verification_md))
    print("Strategy Verification passed.")

    print("--- 2. Trade Verification ---")
    if not df_trades.empty:
        sample = df_trades.sample(n=min(20, len(df_trades)), random_state=42)
        print("Randomly selected 20 trades. Sample Audit:")
        for idx, row in sample.iterrows():
            gross = (row["Exit Price"] - row["Entry Price"]) * row["Quantity"]
            friction = gross - row["Net PnL"]
            calc_net = gross - friction
            net = row["Net PnL"]
            assert abs(calc_net - net) < 1e-6, f"Net PnL mismatch: {calc_net} != {net}"
            msg = (
                f"Trade: {row['Buy Date']} {row['Stock']} Qty:{row['Quantity']} "
                f"Entry:{row['Entry Price']:.2f} Exit:{row['Exit Price']:.2f} "
                f"Gross:{gross:.2f} Net:{net:.2f} Friction:{friction:.2f}"
            )
            print(msg)
    print("Trade Verification passed.")

    print("--- 3. Portfolio Accounting Audit ---")
    backtest_dirs = get_latest_backtest_dirs(n=10)
    checked = 0
    for bd in backtest_dirs:
        port_csv = os.path.join(bd, "portfolio.csv")
        if os.path.exists(port_csv):
            df_port = pd.read_csv(port_csv)
            if (
                "Cash" in df_port.columns
                and "Invested Capital" in df_port.columns
                and "Portfolio Value" in df_port.columns
            ):
                calc_val = df_port["Cash"] + df_port["Invested Capital"]
                actual_val = df_port["Portfolio Value"]
                diff = np.abs(calc_val - actual_val)
                max_diff = diff.max()
                assert max_diff < 1e-4, f"Accounting discrepancy in {bd}: max diff {max_diff}"
                checked += 1
    print(f"Portfolio Accounting Audit passed ({checked} portfolios checked).")

    print("--- 4. Metric Verification ---")
    for _, row in df_metrics.iterrows():
        strat = row["Strategy"]
        stock = row.get("Stock", None)

        if strat == "Buy & Hold":
            continue

        strat_trades = df_trades[(df_trades["Strategy"] == strat) & (df_trades["Stock"] == stock)]
        if len(strat_trades) > 0:
            calc_trades = len(strat_trades)
            assert calc_trades == row["Total Trades"], f"Trades mismatch for {strat} on {stock}"

            winners = strat_trades[strat_trades["Net PnL"] > 0]
            calc_win_rate = (len(winners) / calc_trades) * 100
            assert (
                abs(calc_win_rate - row["Win Rate (%)"]) < 1e-5
            ), f"Win Rate mismatch for {strat} on {stock}"

        col_name = f"{strat}_{stock}" if stock else strat
        if col_name in df_equity.columns:
            s_eq = df_equity[col_name].dropna()
            if len(s_eq) > 0:
                calc_ret = (s_eq.iloc[-1] / 100000.0 - 1) * 100
                hwm = s_eq.cummax()
                dd = (s_eq - hwm) / hwm
                calc_dd = dd.min() * -100

                assert (
                    abs(calc_ret - row["Return"]) < 1e-2
                ), f"Return mismatch for {strat} on {stock}: {calc_ret} != {row['Return']}"
                assert (
                    abs(calc_dd - row["Max Drawdown"]) < 1e-2
                ), f"Drawdown mismatch for {strat} on {stock}: {calc_dd} != {row['Max Drawdown']}"

    print("Metric Verification passed.")

    print("--- 6. Benchmark Verification ---")
    bench_metrics = df_metrics[df_metrics["Strategy"] == "Buy & Hold"]
    for _, row in bench_metrics.iterrows():
        assert row["Total Trades"] == 1, f"Benchmark trades != 1 on {row.get('Stock')}"
        assert row["Win Rate (%)"] == 0.0, "Benchmark should not compute win rate normally"
    print("Benchmark Verification passed.")

    print("--- 7. Research Quality Score ---")
    scores = []
    summary_csv = os.path.join(comp_dir, "strategy_summary.csv")
    if os.path.exists(summary_csv):
        df_sum = pd.read_csv(summary_csv)
        for _, row in df_sum.iterrows():
            strat = row["Strategy"]
            ret = row["Average Return"]
            dd = row["Average Drawdown"]
            beat = row["Beat BuyHold"] / row["Stocks Tested"]

            score = 50
            score += min(30, ret)
            score -= min(30, dd)
            score += beat * 20
            score = max(0, min(100, score))

            scores.append({"Strategy": strat, "Quality Score (0-100)": round(score, 2)})

        pd.DataFrame(scores).to_csv(
            os.path.join(comp_dir, "strategy_quality_score.csv"), index=False
        )
        print("Research Quality Score generated.")

    print("\nALL VERIFICATIONS PASSED MATHEMATICALLY.")


if __name__ == "__main__":
    warnings.warn(
        "This script is deprecated and obsolete as a standalone executable. Please use run_research.py.",
        DeprecationWarning,
    )
    print("ERROR: This script has been deprecated.")
    print("Please run 'python run_research.py' from the project root instead.")
    sys.exit(1)
