import datetime
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Event:
    """event is the base class providing an interface for all subsequent.
    inherited events that will trigger further events in the.
    trading infrastructure."""

    type: str = field(init=False, default="EVENT")


@dataclass(frozen=True)
class MarketEvent(Event):
    """handles the event of receiving a new market update with.
    corresponding bars."""

    type: str = field(init=False, default="MARKET")


@dataclass(frozen=True)
class SignalEvent(Event):
    """handles the event of sending a signal from a strategy object.
    this is received by a portfolio object and acted upon."""

    strategy_id: int
    symbol: str
    datetime: datetime.datetime
    signal_type: str
    strength: float
    type: str = field(init=False, default="SIGNAL")


@dataclass(frozen=True)
class OrderEvent(Event):
    """handles the event of sending an order to an execution system.
    the order contains a symbol e.g. reliance.ns a type market or limit.
    quantity and a direction."""

    symbol: str
    order_type: str
    quantity: int
    direction: str
    type: str = field(init=False, default="ORDER")


@dataclass(frozen=True)
class FillEvent(Event):
    """encapsulates the notion of a filled order as returned.
    from a brokerage. stores the quantity of an instrument.
    actually filled and at what price. in addition stores.
    the commission of the trade from the brokerage."""

    timeindex: datetime.datetime
    symbol: str
    exchange: str
    quantity: int
    direction: str
    fill_cost: float
    commission: float | None = None
    brokerage: float = 0.0
    stt: float = 0.0
    gst: float = 0.0
    exchange_charges: float = 0.0
    stamp_duty: float = 0.0
    sebi_fees: float = 0.0
    type: str = field(init=False, default="FILL")

    def __post_init__(self) -> None:
        if self.commission is None:
            # we use object. setattr to bypass frozen true constraint during init.
            object.__setattr__(self, "commission", self.calculate_ib_commission())

    def calculate_ib_commission(self) -> float:
        """calculates the fees of trading based on an interactive.
        brokers fee structure for api in usd.
        this does not include exchange or ecn fees."""
        full_cost = 1.3
        if self.quantity <= 500:
            full_cost = max(1.3, 0.013 * self.quantity)
        else:
            full_cost = max(1.3, 0.008 * self.quantity)
        return float(full_cost)
