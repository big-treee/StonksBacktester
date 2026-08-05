# Architecture Overview

StonksBacktester is engineered with a strict **event driven architecture** (EDA) ensuring a production ready simulation environment that completely eradicates look ahead bias and tightly mirrors live trading mechanisms.

## Core Design Principles
1. **Decoupled Modules**: The Data Handler Strategy Portfolio and Execution Simulator communicate exclusively through an asynchronous Event Queue. 
2. **SOLID and Clean Architecture**: Dependencies point inwards. The core engine knows nothing about the GUI the API or the specific Analytics implementation.
3. **Plugin Based Extensibility**: Strategies and Risk models are dynamically registered plugins. The underlying engine requires zero modification to add new trading logic.

## System Components and Data Flow

```text
               +-------------------------------------------------+
               |                STONKSBACKTESTER                 |
               +-------------------------------------------------+

    [API / CLI / GUI] -> Dispatches BacktestConfig
            │
            ▼
    +------------------------------------------------------+
    |                    CORE RUNNER                       |
    |  Initializes Data, Portfolio, Risk, and Strategies.  |
    +------------------------------------------------------+
            │
            ▼
    +------------------------------------------------------+
    |                   EVENT ENGINE                       |
    |  Dispatches MarketEvent SignalEvent OrderEvent Fill. |
    +------------------------------------------------------+
            │
            ▼
    +------------------------------------------------------+
    |                RESEARCH ANALYTICS                    |
    |  Generates Metrics Plots Tearsheet and Audit Log.    |
    +------------------------------------------------------+
```
