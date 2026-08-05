# Event Engine

The Event Engine is the beating heart of StonksBacktester. It manages the continuous simulation loop using a centralized `queue.Queue`. 

## Purpose
By relying on events rather than nested function calls the system exactly mirrors a live production trading system. This completely prevents look ahead bias as modules can only act upon data that has already been pushed to the event queue.

## Event Pipeline Flow

```text
DataHandler emits MarketEvent -> Strategy emits SignalEvent -> Portfolio emits OrderEvent -> ExecutionHandler fills OrderEvent -> Portfolio processes FillEvent
```
