import numpy as np
import pandas as pd


def create_sharpe_ratio(returns, periods=252):
    """annualized sharpe ratio assuming zero risk free rate."""
    if len(returns) == 0:
        return 0.0

    std_dev = float(np.std(returns))
    if std_dev == 0.0 or np.isnan(std_dev):
        return 0.0

    mean_ret = float(np.mean(returns))
    sharpe = np.sqrt(periods) * mean_ret / std_dev
    return 0.0 if np.isnan(sharpe) or np.isinf(sharpe) else float(sharpe)


def create_drawdowns(pnl):
    """peak to trough drawdown series and max drawdown duration."""
    if len(pnl) == 0:
        return pd.Series(dtype=float), 0.0, 0.0

    hwm = [0.0]
    eq_idx = pnl.index
    drawdown = pd.Series(index=eq_idx, dtype=float)
    duration = pd.Series(index=eq_idx, dtype=float)

    for t in range(1, len(eq_idx)):
        hwm.append(max(hwm[t - 1], float(pnl.iloc[t])))
        drawdown.iloc[t] = (hwm[t] - float(pnl.iloc[t])) / hwm[t] if hwm[t] > 0 else 0.0
        duration.iloc[t] = 0.0 if drawdown.iloc[t] == 0.0 else float(duration.iloc[t - 1]) + 1.0

    max_dd = float(drawdown.max()) if not drawdown.empty else 0.0
    max_dur = float(duration.max()) if not duration.empty else 0.0
    return drawdown, (0.0 if np.isnan(max_dd) else max_dd), (0.0 if np.isnan(max_dur) else max_dur)
