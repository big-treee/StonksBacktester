# Strategy Framework

The Strategy Framework provides a strictly decoupled environment for quantitative researchers to implement test and register proprietary trading algorithms.

## Plugin Architecture

The Backtester leverages a Plugin Architecture through a global Strategy Registry. The core execution engine is entirely agnostic to the internal mechanics of individual strategies.

When a user defines a strategy name in their `Config` (or payload) the system queries the `STRATEGY_REGISTRY` and dynamically initializes the corresponding class injecting the required parameters.

## Building a Strategy

All user defined strategies must inherit from `BaseStrategy`.

### Abstract Methods
Every strategy must implement the following interfaces:

1. **`initialize(self)`**
   Called once before the simulation begins. Useful for warming up historical indicators allocating internal state or pre processing static data.

2. **`on_market_event(self, event)`**
   Triggered on every tick or bar. This acts as a notification that new market data is available in the `DataHandler`. It usually delegates to `generate_signals()`.

3. **`generate_signals(self)`**
   The core quantitative logic block. Reads current and historical data evaluates indicators and emits a `SignalEvent` (LONG or SHORT) if entry or exit thresholds are crossed.

4. **`reset(self)`**
   Called at the end of a backtest run. Essential for wiping internal state (such as indicator history) when running large scale parametric sweeps or Walk Forward analysis.
