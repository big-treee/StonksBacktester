import json
import os
from typing import Any, Dict

import pandas as pd
from jinja2 import Template

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{{ title }}</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; margin: 20px; background-color: #f8f9fa; color: #333; }
        h1, h2, h3 { color: #1a1a1a; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 30px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); border-radius: 8px; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 30px; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background-color: #f1f3f5; font-weight: 600; }
        .chart { text-align: center; margin: 20px 0; }
        .chart img { max-width: 100%; border: 1px solid #eee; border-radius: 4px; }
        .full-width { grid-column: 1 / -1; }
    </style>
</head>
<body>
    <div class="container">
        <h1>StonksBacktester Tearsheet</h1>
        <p><strong>Strategy:</strong> {{ strategy_name }} | <strong>Period:</strong> {{ start_date }} to {{ end_date }}</p>
        
        <div class="grid">
            <div>
                <h2>Performance Statistics</h2>
                <table>
                    {% for key, value in performance_metrics.items() %}
                    <tr>
                        <td>{{ key }}</td>
                        <td>{{ "%.2f"|format(value) if value is number else value }}</td>
                    </tr>
                    {% endfor %}
                </table>
            </div>
            
            <div>
                <h2>Benchmark Comparison</h2>
                {% if benchmark_metrics %}
                <table>
                    {% for key, value in benchmark_metrics.items() %}
                    <tr>
                        <td>{{ key }}</td>
                        <td>{{ "%.2f"|format(value) if value is number else value }}</td>
                    </tr>
                    {% endfor %}
                </table>
                {% else %}
                <p>No benchmark configured or data unavailable.</p>
                {% endif %}
            </div>
        </div>

        {% if charts %}
        <div class="chart full-width">
            <h2>Equity Curve</h2>
            <img src="data:image/png;base64,{{ charts.equity }}" alt="Equity Curve">
        </div>
        
        <div class="chart full-width">
            <h2>Drawdown Profile</h2>
            <img src="data:image/png;base64,{{ charts.drawdown }}" alt="Drawdown">
        </div>
        
        <div class="grid">
            <div class="chart">
                <h2>Monthly Returns</h2>
                <img src="data:image/png;base64,{{ charts.heatmap }}" alt="Monthly Heatmap">
            </div>
            <div class="chart">
                <h2>Rolling 6-Month Sharpe</h2>
                <img src="data:image/png;base64,{{ charts.rolling_sharpe }}" alt="Rolling Sharpe">
            </div>
        </div>
        
        <div class="chart full-width">
            <h2>Trade PnL Distribution</h2>
            <img src="data:image/png;base64,{{ charts.trade_dist }}" alt="Trade Distribution">
        </div>
        {% endif %}
    </div>
</body>
</html>
"""


class ReportGenerator:
    def __init__(
        self,
        metrics: Dict[str, float],
        benchmark_metrics: Dict[str, float],
        trades: list,
        charts: Dict[str, str],
        config: Any,
    ):
        self.metrics = metrics
        self.benchmark_metrics = benchmark_metrics
        self.trades = trades
        self.charts = charts
        self.config = config

        self.reports_dir = "reports"
        if not os.path.exists(self.reports_dir):
            os.makedirs(self.reports_dir)

    def export_all(self):
        if self.config.reports.html:
            self._generate_html()

        # export trades to csv unconditionally as part of stonksbacktester reporting.
        self._export_trades_csv()
        self._export_metrics_json()

    def _generate_html(self):
        template = Template(HTML_TEMPLATE)
        html_content = template.render(
            title=f"Tearsheet - {self.config.strategy.name}",
            strategy_name=self.config.strategy.name,
            start_date=self.config.data.start_date,
            end_date=self.config.data.end_date,
            performance_metrics=self.metrics,
            benchmark_metrics=self.benchmark_metrics,
            charts=self.charts if self.config.reports.charts else None,
        )

        out_path = os.path.join(self.reports_dir, "tearsheet.html")
        with open(out_path, "w") as f:
            f.write(html_content)

    def _export_trades_csv(self):
        if not self.trades:
            return

        df = pd.DataFrame(self.trades)
        out_path = os.path.join(self.reports_dir, "trades.csv")
        df.to_csv(out_path, index=False)

    def _export_metrics_json(self):
        out_path = os.path.join(self.reports_dir, "metrics.json")
        combined = {"performance": self.metrics, "benchmark": self.benchmark_metrics}
        with open(out_path, "w") as f:
            json.dump(combined, f, indent=4)
