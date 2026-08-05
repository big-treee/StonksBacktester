# Analytics Engine

The Analytics Engine transforms raw backtest data into professional StonksBacktester statistics and reports.

## Architecture

The Analytics Engine hooks into the core simulation post execution.

1. **Trade Tracker (`trades.py`)**: Intercepts every `FillEvent` via a wrapper function inside `core.runner`. Using a strict FIFO (First In First Out) queue mechanism it matches entry and exit orders to calculate true round trip transactions attributing accurate commissions to scaled positions.
2. **Metrics Engine (`metrics.py`)**: Consumes the raw Portfolio equity curve and the extracted round trip trades to compute exact statistics using `pandas` and `numpy`.
3. **Benchmark Analyzer (`benchmark.py`)**: Connects to `yfinance` to download a benchmark index (such as `^NSEI` for Nifty 50) aligning timestamps perfectly with the backtest to compute relative alpha and beta.
4. **Plot Generator (`plots.py`)**: Uses `matplotlib` and `seaborn` to render high quality visualizations. The charts are converted directly into Base64 strings eliminating the need for physical image files on the server.
5. **Tearsheet Generator (`tearsheet.py`)**: Injects the metrics and Base64 images into a Jinja2 template to create a standalone HTML report.

## Generated Metrics

* **Equity Profiling**: CAGR Annual Return Annual Volatility Sharpe Ratio Sortino Ratio Calmar Ratio Omega Ratio Max Drawdown Recovery Factor.
* **Trade Profiling**: Total Trades Win Rate Profit Factor Expectancy Average Win Loss Max Win Loss Average Holding Period.
* **Benchmark Comparisons**: Jensens Alpha Beta Tracking Error Information Ratio.

## Outputs
* **`reports/tearsheet.html`**: A fully portable HTML file containing all charts and tables.
* **`reports/metrics.json`**: A machine readable payload for external integration.
* **`reports/trades.csv`**: Raw export of every closed transaction.
