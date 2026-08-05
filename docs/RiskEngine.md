# Risk Engine

The Risk Engine serves as the ultimate gatekeeper for the Portfolio. No signal can become an order without being sized and validated by the Risk Engine.

## Purpose
StonksBacktester requires rigorous capital allocation and drawdown limits. The Risk Engine protects the portfolio from strategy bugs overexposure and catastrophic losses.

## Position Sizers
* Fixed Fractional
* Fixed Shares
* Volatility Target
* Risk Percentage
* Kelly Criterion

## Risk Validators
* Max Drawdown Stop
* Max Open Positions
* Max Portfolio Exposure
* Sufficient Cash Validator
