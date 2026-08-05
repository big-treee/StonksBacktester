import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


class ComparisonPlotter:
    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        plt.style.use("dark_background")

    def plot_equity_overlay(self, equity_curves: dict[str, pd.DataFrame]):
        """plotly matplotlib overlay of all strategy equities."""
        plt.figure(figsize=(12, 6))
        for name, df in equity_curves.items():
            if "equity_curve" in df.columns:
                plt.plot(df.index, df["equity_curve"], label=name, linewidth=1.5)
            elif "total" in df.columns:
                plt.plot(df.index, df["total"], label=name, linewidth=1.5)

        plt.title("Equity Curve Comparison")
        plt.xlabel("Date")
        plt.ylabel("Equity")
        plt.legend()
        plt.grid(True, alpha=0.3)
        out_path = os.path.join(self.output_dir, "equity_overlay.png")
        plt.tight_layout()
        plt.savefig(out_path)
        plt.close()
        return "equity_overlay.png"

    def plot_drawdown_overlay(self, equity_curves: dict[str, pd.DataFrame]):
        plt.figure(figsize=(12, 6))
        for name, df in equity_curves.items():
            if "total" in df.columns:
                hwm = df["total"].cummax()
                dd = (df["total"] - hwm) / hwm
                plt.plot(df.index, dd * 100, label=name, linewidth=1.0)

        plt.title("Drawdown Comparison (%)")
        plt.xlabel("Date")
        plt.ylabel("Drawdown (%)")
        plt.legend()
        plt.grid(True, alpha=0.3)
        out_path = os.path.join(self.output_dir, "drawdown_overlay.png")
        plt.tight_layout()
        plt.savefig(out_path)
        plt.close()
        return "drawdown_overlay.png"

    def plot_monthly_comparison(self, stats_list: list[dict]):
        # bar chart of annualized returns.
        names = [str(s.get("Strategy", "Unknown")) for s in stats_list]
        returns: list[float] = [float(s.get("Return") or 0.0) for s in stats_list]

        plt.figure(figsize=(10, 6))
        plt.bar(names, returns, color=["#0d6efd" if r > 0 else "#dc3545" for r in returns])
        plt.title("Total Return Comparison (%)")
        plt.ylabel("Return (%)")
        plt.xticks(rotation=45)
        plt.grid(axis="y", alpha=0.3)
        out_path = os.path.join(self.output_dir, "return_comparison.png")
        plt.tight_layout()
        plt.savefig(out_path)
        plt.close()
        return "return_comparison.png"

    def plot_trade_frequency(self, stats_list: list[dict]):
        names = [str(s.get("Strategy", "Unknown")) for s in stats_list]
        trades: list[int] = [
            int(s.get("Total Trades") or s.get("Number of Trades") or 0) for s in stats_list
        ]

        plt.figure(figsize=(10, 6))
        plt.bar(names, trades, color="#6c757d")
        plt.title("Trade Frequency")
        plt.ylabel("Number of Trades")
        plt.xticks(rotation=45)
        plt.grid(axis="y", alpha=0.3)
        out_path = os.path.join(self.output_dir, "trade_frequency.png")
        plt.tight_layout()
        plt.savefig(out_path)
        plt.close()
        return "trade_frequency.png"


class HTMLReportBuilder:
    def __init__(self, output_dir: str):
        self.output_dir = output_dir

    def generate_report(self, stats_list: list[dict], charts: dict[str, str]):
        df = pd.DataFrame(stats_list)
        if "Strategy" in df.columns:
            df.set_index("Strategy", inplace=True)

        # select and reorder key columns for leaderboard.
        cols_to_show = [
            "Return",
            "Sharpe",
            "Sortino",
            "Max Drawdown",
            "Win Rate (%)",
            "Total Trades",
            "Net Profit (INR)",
        ]
        existing_cols = [c for c in cols_to_show if c in df.columns]
        leaderboard_html = (
            df[existing_cols]
            .round(2)
            .to_html(classes="table table-dark table-striped table-hover", border=0)
        )

        best_return = df["Return"].idxmax() if not df.empty and "Return" in df.columns else "N/A"
        best_sharpe = df["Sharpe"].idxmax() if not df.empty and "Sharpe" in df.columns else "N/A"
        lowest_dd = (
            df["Max Drawdown"].idxmin() if not df.empty and "Max Drawdown" in df.columns else "N/A"
        )

        # build optional charts section if provided.
        charts_html = ""
        if charts:
            charts_html = f"""
                <div class="row">
                    <div class="col-md-6">
                        <div class="card">
                            <div class="card-header">Equity Overlay</div>
                            <div class="card-body text-center">
                                <img src="{charts.get("equity", "")}" class="img-fluid rounded" alt="Equity Overlay">
                            </div>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="card">
                            <div class="card-header">Drawdown Overlay</div>
                            <div class="card-body text-center">
                                <img src="{charts.get("drawdown", "")}" class="img-fluid rounded" alt="Drawdown Overlay">
                            </div>
                        </div>
                    </div>
                </div>

                <div class="row">
                    <div class="col-md-6">
                        <div class="card">
                            <div class="card-header">Total Return Comparison</div>
                            <div class="card-body text-center">
                                <img src="{charts.get("return", "")}" class="img-fluid rounded" alt="Return Comparison">
                            </div>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="card">
                            <div class="card-header">Trade Frequency</div>
                            <div class="card-body text-center">
                                <img src="{charts.get("trades", "")}" class="img-fluid rounded" alt="Trade Frequency">
                            </div>
                        </div>
                    </div>
                </div>
            """

        html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <title>Strategy Comparison Report</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
            <style>
                body {{ background-color: #121212; color: #f8f9fa; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; padding: 20px; }}
                .card {{ background-color: #1e1e1e; border: none; border-radius: 10px; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }}
                .card-header {{ background-color: #2b2b2b; border-bottom: 1px solid #444; font-weight: bold; border-radius: 10px 10px 0 0 !important; }}
                .metric-box {{ text-align: center; padding: 15px; background: #2b2b2b; border-radius: 8px; }}
                .metric-box h4 {{ margin: 0; color: #0d6efd; font-size: 1.2rem; }}
                .metric-box span {{ font-size: 1.5rem; font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="container-fluid">
                <h1 class="mb-4 text-center">Strategy Comparison & Research Framework</h1>
                
                <div class="row mb-4">
                    <div class="col-md-4">
                        <div class="metric-box">
                            <h4>Best Return</h4>
                            <span class="text-success">{best_return}</span>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="metric-box">
                            <h4>Best Sharpe</h4>
                            <span class="text-info">{best_sharpe}</span>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="metric-box">
                            <h4>Lowest Drawdown</h4>
                            <span class="text-warning">{lowest_dd}</span>
                        </div>
                    </div>
                </div>

                <div class="card">
                    <div class="card-header">Strategy Leaderboard</div>
                    <div class="card-body overflow-auto">
                        {leaderboard_html}
                    </div>
                </div>
                
                {charts_html}
            </div>
        </body>
        </html>
        """
        out_path = os.path.join(self.output_dir, "comparison_report.html")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html)
