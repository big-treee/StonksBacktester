from abc import ABC, abstractmethod
from typing import Any

from core.events import OrderEvent, SignalEvent


class BasePositionSizer(ABC):
    """abstract interface for determining the size quantity of an order.
    generated from a signalevent."""

    @abstractmethod
    def size_order(self, signal: SignalEvent, portfolio: Any) -> OrderEvent | None:
        """calculates the appropriate size for the signal and returns an orderevent.
        returns none if the order should not be placed.
        args.
        signal signalevent the signal to size.
        portfolio any a reference to the portfolio object to access.
        current holdings cash and positions.
        returns.
        orderevent none the sized order or none."""
        pass


class BaseRiskValidator(ABC):
    """abstract interface for validating an order against specific risk rules."""

    @abstractmethod
    def validate_order(self, order: OrderEvent, portfolio: Any) -> bool:
        """validates the order against risk rules.
        args.
        order orderevent the proposed order to validate.
        portfolio any a reference to the portfolio object.
        returns.
        bool true if the order passes validation false if it should be rejected."""
        pass
