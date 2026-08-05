import logging
import queue
from abc import ABC, abstractmethod
from typing import Any

from core.events import MarketEvent
from data.base import BaseDataHandler


class BaseStrategy(ABC):
    """abstract base class for all strategies in the plugin framework."""

    # metadata to be overridden by subclasses.
    strategy_name: str = "Base"
    description: str = "Base strategy"
    supported_assets: list[str] = ["EQUITY"]
    required_parameters: dict[str, type] = {}

    def __init__(
        self,
        data_handler: BaseDataHandler,
        events: queue.Queue,
        logger: logging.Logger | None = None,
        **kwargs: Any,
    ) -> None:
        self.data_handler = data_handler
        self.events = events
        self.logger = logger or logging.getLogger(self.__class__.__name__)

        # we will parse kwargs into self.parameters if needed but parameter validation.
        # is handled by the registry validation layer before instantiation.
        self.audit_logger = getattr(self, "audit_logger", kwargs.get("audit_logger", None))

        for k, v in kwargs.items():
            setattr(self, k, v)

        self.initialize()

    def log_decision(
        self,
        date,
        ticker,
        close_price,
        strategy_state,
        current_position,
        decision,
        reason,
        signal_strength=0.0,
    ):
        if self.audit_logger:
            self.audit_logger.log_decision(
                date,
                ticker,
                close_price,
                strategy_state,
                current_position,
                decision,
                reason,
                signal_strength=signal_strength,
            )

    def calculate_signals(self, event: MarketEvent) -> None:
        """the entrypoint from the engine. acts as a template method."""
        self.on_market_event(event)
        self.generate_signals(event)

    @abstractmethod
    def initialize(self) -> None:
        """called during initialization. setup internal state here."""
        pass

    @abstractmethod
    def on_market_event(self, event: MarketEvent) -> None:
        """called when new market data arrives. process data or indicators here."""
        pass

    @abstractmethod
    def generate_signals(self, event: MarketEvent) -> None:
        """called after on market event. emit signalevents based on the processed state."""
        pass

    @abstractmethod
    def reset(self) -> None:
        """reset strategy state e.g. between runs or environments ."""
        pass
