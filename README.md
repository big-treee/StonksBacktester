# StonksBacktester

> An event driven Python backtesting and research engine for NSE equities featuring pluggable strategies configurable risk controls Indian brokerage and taxation modeling parameter optimization and reproducible performance reports.

## Key Features

* Event Driven Backtest Core: Simulates realistic MarketEvent to SignalEvent to OrderEvent to FillEvent market flow with zero look ahead bias.
* Terminal First Experience: Interactive CLI (`nse-quant run`) with smart parameter prompts input validation and preset configurations.
* Pluggable Quantitative Strategies: Built in implementations for SMA Crossover EMA Crossover RSI MACD Bollinger Bands Donchian Channel Z Score Mean Reversion and Rate of Change Momentum.
* Indian Market Costs: Complete transaction cost simulation for Zerodha Upstox Groww and Angel One (Brokerage STT GST Exchange charges Stamp duty SEBI fees).
* Position Sizing and Risk Controls: Support for Fixed Fractional Fixed Shares Risk Parity and Volatility Target sizers paired with Max Drawdown and Position Count validators.
* Quantitative Research Workflows: Grid Search Random Search Walk Forward Validation and Monte Carlo robustness stress testing.
* Reproducible Artifacts: Every run automatically saves timestamped audit logs containing `config.yaml` `summary.json` `trades.csv` `metrics.json` and HTML tearsheets.

## Architecture Overview

```text
               +-------------------------------------------------+
               |             TERMINAL INTERACTIVE CLI            |
               |        [ nse-quant run | list-strategies ]       |
               +-------------------------------------------------+
                                       │ (Config Loader)
               +-------------------------------------------------+
               |               EVENT ENGINE CORE                 |
               |                                                 |
               |   +---------------+     MarketEvent      +----+ |
               |   | Data Handler  | -------------------> |Strt| |
               |   +---------------+                      +----+ |
               |          ^                                  │   |
               |          │ FillEvent                    Signal  |
               |          │                                  ▼   |
               |   +---------------+     OrderEvent       +----+ |
               |   |   Execution   | <------------------- |Port| |
               |   +---------------+                      +----+ |
               |                                             │   |
               |                                         (Risk)  |
               +-------------------------------------------------+
                                       │ (Closed Trades)
               +-------------------------------------------------+
               |                RESEARCH ANALYTICS               |
               |   [ Benchmark | Tearsheet | Plots | Audit Log ] |
               +-------------------------------------------------+
```

## Repository Structure

```text
nse_quant_engine/  CLI application and interactive setup wizard
core/              Event queue engine dispatcher and execution runner
data/              Yahoo Finance historical market data engine
strategy/          Plugin registry and base strategy interface
strategies/        8 built in technical and quant strategies
risk/              Modular position sizing and risk validation rules
portfolio/         Holdings positions and portfolio state tracking
execution/         Simulated broker execution with bar timestamp fills
markets/india/     Indian stock universe NSE calendar and broker charge calculators
analytics/         Trade matching risk metrics plotting and HTML tearsheets
optimization/      Parameter grid random search walk forward and Monte Carlo
config/            Configuration models YAML loaders and presets
tests/             Comprehensive pytest test suite
```

## Installation

Requires Python 3.10+

```bash
git clone https://github.com/your-username/stonks-backtester.git
cd stonks-backtester
pip install -e .
```

Verify installation:
```bash
nse-quant --help
```

## Quickstart

### 1. Interactive Terminal Backtest
Run the interactive wizard to pick stocks date ranges initial capital strategies broker charges and risk controls:

```bash
nse-quant run
```

### 2. Reproducible Run from Preset or Config
Run non interactively using a preset or configuration file:

```bash
nse-quant run --preset conservative-sma
nse-quant run --config config/settings.yaml --non-interactive
```

### 3. List Available Strategies
View all registered strategies descriptions and required parameters:

```bash
nse-quant list-strategies
```

### 4. Run Quantitative Research Workflows
```bash
nse-quant optimize --method grid
nse-quant walk-forward
nse-quant monte-carlo --simulations 100
```

### 5. View History
```bash
nse-quant history
```

## Testing

Run the automated test suite to verify correctness:

```bash
pytest
```

## Scope and Limitations

* Daily Bar Granularity: Designed for daily end of day equity data via Yahoo Finance.
* Research Simulation: Created for strategy research parameter sensitivity and performance attribution; not designed for direct automated live order placement.

## License

Distributed under the MIT License. See LICENSE for more information.
