"""main cli entrypoint for nse quant research engine."""

import datetime
import os
import shutil
from pathlib import Path
from typing import Any, Optional

import numpy as np
import typer
import yaml
from rich import box
from rich.console import Console
from rich.prompt import Confirm
from rich.table import Table

from config.loader import load_config
from config.models import Config
from core.runner import run_backtest_with_config
from nse_quant_engine.prompts import interactive_config_builder
from strategy.registry import get_strategy, list_registered_strategies, load_strategies
from utils.indian_format import format_indian_currency

app = typer.Typer(
    name="nse-quant",
    help="NSE Quant Research Engine - Event-driven backtesting CLI for Indian equities",
    add_completion=False,
)

console = Console()


def save_config_to_yaml(config: Config, filepath: str) -> None:
    """helper to dump a config dataclass to yaml."""
    raw_dict = {
        "initial_capital": config.initial_capital,
        "data": {
            "source": config.data.source,
            "symbols": config.data.symbol_list,
            "start_date": config.data.start_date,
            "end_date": config.data.end_date,
            "warmup_days": config.data.warmup_days,
        },
        "strategy": {
            "name": config.strategy.name,
            "parameters": config.strategy.parameters,
        },
        "broker": {
            "name": config.broker.name,
            "product": config.broker.product,
            "charges": config.broker.charges,
        },
        "risk": {
            "position_sizer": {
                "name": config.risk.position_sizer.name,
                "parameters": config.risk.position_sizer.parameters,
            },
            "validators": [
                {"name": v.name, "parameters": v.parameters} for v in config.risk.validators
            ],
        },
        "reports": {
            "html": config.reports.html,
            "charts": config.reports.charts,
            "benchmark": config.reports.benchmark,
        },
    }
    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
    with open(filepath, "w") as f:
        yaml.safe_dump(raw_dict, f, sort_keys=False)


@app.command("run")
def run_command(
    config_path: Optional[str] = typer.Option(
        None, "--config", "-c", help="Path to YAML configuration file for non-interactive execution"
    ),
    preset: Optional[str] = typer.Option(
        None, "--preset", "-p", help="Named preset configuration (e.g. conservative-sma)"
    ),
    non_interactive: bool = typer.Option(
        False, "--non-interactive", "-n", help="Run without interactive prompts"
    ),
    output_dir: Optional[str] = typer.Option(
        None, "--output-dir", "-o", help="Custom output directory for run artifacts"
    ),
    no_charts: bool = typer.Option(
        False, "--no-charts", help="Disable chart generation for faster runs"
    ),
):
    """run strategy backtest."""
    console.print("\nNSE Quant Research Engine")
    console.print("Event-driven backtesting for NSE equities\n")

    # load configuration.
    if preset:
        preset_file = Path("config/presets") / f"{preset}.yaml"
        if not preset_file.exists():
            console.print(f"Preset '{preset}' not found at {preset_file}")
            raise typer.Exit(code=1)
        config = load_config(str(preset_file))
    elif config_path:
        config = load_config(config_path)
    elif non_interactive:
        config = load_config("config/settings.yaml")
    else:
        config = interactive_config_builder()

    if no_charts:
        config = Config(
            initial_capital=config.initial_capital,
            data=config.data,
            strategy=config.strategy,
            broker=config.broker,
            logging=config.logging,
            risk=config.risk,
            optimization=config.optimization,
            reports=config.reports.__class__(
                html=config.reports.html,
                pdf=config.reports.pdf,
                benchmark=config.reports.benchmark,
                charts=False,
            ),
            market=config.market,
        )

    # . confirm details cleanly without heavy boxes.
    table = Table(title="Backtest Summary Configuration", box=box.SIMPLE, show_header=True)
    table.add_column("Setting", style="bold cyan")
    table.add_column("Value")

    table.add_row("Symbols", ", ".join(config.data.symbol_list))
    table.add_row("Date Range", f"{config.data.start_date} -> {config.data.end_date}")
    table.add_row("Capital", format_indian_currency(config.initial_capital))
    table.add_row("Strategy", f"{config.strategy.name} {config.strategy.parameters}")
    table.add_row("Position Sizer", config.risk.position_sizer.name)
    broker_charges_str = (
        "None (Zero Charges)"
        if config.broker.name == "none"
        or not getattr(config.broker, "charges", {}).get("enabled", True)
        else f"{config.broker.name.title()} ({config.broker.product.upper()})"
    )
    table.add_row("Broker Charges", broker_charges_str)
    table.add_row("Benchmark", config.reports.benchmark or "None")

    console.print(table)

    if not non_interactive and not Confirm.ask(
        "\nConfiguration valid. Run backtest?", default=True
    ):
        console.print("Backtest cancelled by user.")
        raise typer.Exit(code=0)

    # . create simple logical run directory.
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir_name = f"run_{config.strategy.name}_{timestamp}"
    run_dir = Path(output_dir) if output_dir else Path("runs") / run_dir_name
    run_dir.mkdir(parents=True, exist_ok=True)

    save_config_to_yaml(config, str(run_dir / "config.yaml"))

    console.print(f"\nRunning backtest... Saving artifacts to {run_dir}")

    try:
        stats = run_backtest_with_config(config)
    except Exception as e:
        console.print(f"Backtest execution failed: {e}")
        raise typer.Exit(code=1)

    # copy output artifacts to run directory.
    if "Output_Dir" in stats and os.path.exists(stats["Output_Dir"]):
        audit_dir = stats["Output_Dir"]
        for item in os.listdir(audit_dir):
            s = os.path.join(audit_dir, item)
            d = os.path.join(run_dir, item)
            if os.path.isfile(s):
                shutil.copy2(s, d)
            elif os.path.isdir(s):
                shutil.copytree(s, d, dirs_exist_ok=True)

    # output summary metrics cleanly with indian formatting.
    res_table = Table(title="Backtest Performance Metrics", box=box.SIMPLE, show_header=True)
    res_table.add_column("Metric", style="bold yellow")
    res_table.add_column("Value")

    for key, val in stats.items():
        if key in [
            "Return",
            "Sharpe",
            "Max Drawdown",
            "Final Equity",
            "CAGR",
            "Sortino",
            "Win Rate",
        ]:
            if isinstance(val, (float, int)) and (np.isnan(val) or np.isinf(val)):
                val = 0.0
            if key == "Final Equity":
                val_str = format_indian_currency(val)
            elif "%" in key or key in ["Return", "Max Drawdown", "Win Rate", "CAGR"]:
                val_str = f"{val:.2f}%"
            else:
                val_str = f"{val:.2f}"
            res_table.add_row(key, val_str)

    console.print(res_table)
    console.print(f"Backtest completed successfully! Run artifacts saved in {run_dir}\n")


@app.command("list-strategies")
def list_strategies():
    """list all available trading strategies and their parameters."""
    load_strategies()
    strategies = list_registered_strategies()

    table = Table(title="Registered Trading Strategies", box=box.SIMPLE, show_header=True)
    table.add_column("#", style="bold cyan")
    table.add_column("Strategy Identifier", style="bold yellow")
    table.add_column("Description")
    table.add_column("Required Parameters")

    for idx, name in enumerate(sorted(strategies), 1):
        strat_cls = get_strategy(name)
        desc = getattr(strat_cls, "description", "No description available")
        req_params = getattr(strat_cls, "required_parameters", {})
        param_str = (
            ", ".join(f"{k}: {v.__name__}" for k, v in req_params.items()) if req_params else "None"
        )
        table.add_row(str(idx), name, desc, param_str)

    console.print(table)


@app.command("history")
def history():
    """view previous backtest runs and performance summaries."""
    runs_dir = Path("runs")
    if not runs_dir.exists() or not any(runs_dir.iterdir()):
        console.print("No previous runs found in runs/")
        return

    table = Table(title="Historical Backtest Runs", box=box.SIMPLE, show_header=True)
    table.add_column("Run Directory", style="bold cyan")
    table.add_column("Strategy", style="yellow")
    table.add_column("Config File")

    for entry in sorted(runs_dir.iterdir(), reverse=True):
        if entry.is_dir():
            cfg_file = entry / "config.yaml"
            strat_name = (
                entry.name.split("_")[1]
                if "_" in entry.name and len(entry.name.split("_")) > 1
                else "Unknown"
            )
            table.add_row(entry.name, strat_name, str(cfg_file) if cfg_file.exists() else "Missing")

    console.print(table)


@app.command("optimize")
def optimize_command(
    config_path: str = typer.Option(
        "config/settings.yaml", "--config", "-c", help="Base config for optimization"
    ),
    method: str = typer.Option(
        "grid", "--method", "-m", help="Optimization method: grid or random"
    ),
):
    """run parameter optimization workflows."""
    console.print(f"Running parameter optimization using method: {method}")
    config = load_config(config_path)
    optimizer: Any
    if method == "random":
        from optimization.random_search import RandomSearchOptimizer

        optimizer = RandomSearchOptimizer(config)
    else:
        from optimization.grid_search import GridSearchOptimizer

        optimizer = GridSearchOptimizer(config)

    from optimization.runner import OptimizationRunner

    runner = OptimizationRunner(config, optimizer)
    results = runner.run() or []
    console.print(f"Optimization finished with {len(results)} parameter combinations tested.")


@app.command("walk-forward")
def walk_forward_command(
    config_path: str = typer.Option(
        "config/settings.yaml", "--config", "-c", help="Base config for walk-forward"
    ),
):
    """run walk forward optimization analysis."""
    console.print("Running Walk-Forward Optimization...")
    config = load_config(config_path)
    from optimization.walkforward import WalkForwardAnalyzer

    wf = WalkForwardAnalyzer(config)
    results = wf.run() or []
    console.print(f"Walk-Forward completed across {len(results)} folds.")


@app.command("monte-carlo")
def monte_carlo_command(
    config_path: str = typer.Option(
        "config/settings.yaml", "--config", "-c", help="Base config for Monte Carlo"
    ),
    simulations: int = typer.Option(
        100, "--simulations", "-s", help="Number of Monte Carlo simulations"
    ),
):
    """run monte carlo robustness simulations."""
    console.print(f"Running {simulations} Monte Carlo simulations...")
    config = load_config(config_path)
    from optimization.montecarlo import MonteCarloAnalyzer

    mc = MonteCarloAnalyzer(config)
    mc.iterations = simulations
    results = mc.run() or []
    returns = [r["stats"].get("Return", 0) for r in results if r.get("stats")]
    avg_return = sum(returns) / len(returns) if returns else 0.0
    console.print(
        f"Monte Carlo complete. Evaluated {len(results)} simulations (Mean Return: {avg_return:.2f}%)."
    )


def cli():
    """main cli entry point function."""
    app()


if __name__ == "__main__":
    cli()
