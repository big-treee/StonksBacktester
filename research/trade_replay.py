import os

import pandas as pd


def generate_trade_replay(output_dir: str):
    """generates an interactive trade replay html view.
    reads decision log.csv and trades.csv from the output dir."""
    decision_log_path = os.path.join(output_dir, "decision_log.csv")
    trades_path = os.path.join(output_dir, "trades.csv")
    out_html = os.path.join(output_dir, "trade_replay.html")

    if not os.path.exists(decision_log_path):
        return

    decisions_df = pd.read_csv(decision_log_path)

    trades_df = pd.DataFrame()
    if os.path.exists(trades_path):
        trades_df = pd.read_csv(trades_path)

    # basic html skeleton using bootstrap.
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Trade Replay</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            body { background-color: #f8f9fa; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
            .replay-container { max-width: 1400px; margin: 2rem auto; background: white; padding: 2rem; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
            .decision-BUY { background-color: #d1e7dd; color: #0f5132; font-weight: bold; }
            .decision-SELL { background-color: #f8d7da; color: #842029; font-weight: bold; }
            .decision-EXIT { background-color: #f8d7da; color: #842029; font-weight: bold; }
            .decision-HOLD { background-color: #fff3cd; color: #664d03; }
            .decision-IGNORE { color: #6c757d; }
            .table-sm td, .table-sm th { padding: 0.5rem; font-size: 0.9rem; }
        </style>
    </head>
    <body>
        <div class="replay-container">
            <h2 class="mb-4">Trade Replay & Strategy Reasoning</h2>
            
            <ul class="nav nav-tabs mb-4" id="replayTabs" role="tablist">
                <li class="nav-item" role="presentation">
                    <button class="nav-link active" id="decisions-tab" data-bs-toggle="tab"
                        data-bs-target="#decisions" type="button" role="tab">Decision Log Timeline</button>
                </li>
                <li class="nav-item" role="presentation">
                    <button class="nav-link" id="trades-tab" data-bs-toggle="tab"
                        data-bs-target="#trades" type="button" role="tab">Executed Trades</button>
                </li>
            </ul>

            <div class="tab-content" id="replayTabsContent">
                <div class="tab-pane fade show active" id="decisions" role="tabpanel">
                    <table class="table table-hover table-sm border">
                        <thead class="table-dark">
                            <tr>
                                <th>Date</th>
                                <th>Ticker</th>
                                <th>Decision</th>
                                <th>Reasoning</th>
                                <th>Indicators</th>
                                <th>Position Before</th>
                            </tr>
                        </thead>
                        <tbody>
    """

    for _, row in decisions_df.iterrows():
        decision_class = f"decision-{str(row.get('Decision', '')).upper()}"
        ind_vals = row.get("Indicator Values", "")
        html += f"""
                            <tr>
                                <td>{row.get("Date", "")}</td>
                                <td>{row.get("Ticker", "")}</td>
                                <td class="{decision_class}">{row.get("Decision", "")}</td>
                                <td>{row.get("Reason", "")}</td>
                                <td><small class="text-muted">{ind_vals}</small></td>
                                <td>{row.get("Current Position", "")}</td>
                            </tr>
        """

    html += """
                        </tbody>
                    </table>
                </div>
                
                <div class="tab-pane fade" id="trades" role="tabpanel">
                    <table class="table table-hover table-sm border">
                        <thead class="table-dark">
                            <tr>
                                <th>Trade ID</th>
                                <th>Ticker</th>
                                <th>Buy Date</th>
                                <th>Sell Date</th>
                                <th>Entry Price</th>
                                <th>Exit Price</th>
                                <th>Return %</th>
                                <th>Net PnL</th>
                                <th>Strategy</th>
                            </tr>
                        </thead>
                        <tbody>
    """

    if not trades_df.empty:
        for _, row in trades_df.iterrows():
            ret = float(row.get("Return %", 0))
            ret_class = "text-success fw-bold" if ret > 0 else "text-danger fw-bold"
            pnl_val = float(row.get("Net PnL", 0))
            strat_val = row.get("Strategy", "")
            html += f"""
                                <tr>
                                    <td>{row.get("Trade ID", "")}</td>
                                    <td>{row.get("Ticker", "")}</td>
                                    <td>{row.get("Buy Date", "")}</td>
                                    <td>{row.get("Sell Date", "")}</td>
                                    <td>₹{float(row.get("Entry Price", 0)):,.2f}</td>
                                    <td>₹{float(row.get("Exit Price", 0)):,.2f}</td>
                                    <td class="{ret_class}">{ret:.2f}%</td>
                                    <td class="{ret_class}">₹{pnl_val:,.2f}</td>
                                    <td><span class="badge bg-secondary">{strat_val}</span></td>
                                </tr>
            """
    else:
        html += "<tr><td colspan='9' class='text-center'>No trades executed.</td></tr>"

    html += """
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    </body>
    </html>
    """

    with open(out_html, "w", encoding="utf-8") as f:
        f.write(html)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        generate_trade_replay(sys.argv[1])
