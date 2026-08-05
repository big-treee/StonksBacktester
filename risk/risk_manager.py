import logging
from typing import Any

from core.events import OrderEvent, SignalEvent
from risk.base import BasePositionSizer, BaseRiskValidator


class RiskManager:
    """acts as the strict gatekeeper between strategy signals and order execution.
    it sizes the signal appropriately and validates the resulting order against all risk rules."""

    def __init__(
        self,
        position_sizer: BasePositionSizer,
        validators: list[BaseRiskValidator] | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.position_sizer = position_sizer
        self.validators = validators or []
        self.logger = logger or logging.getLogger("RiskManager")
        self.audit_logger: Any = None

    def size_and_validate(self, signal: SignalEvent, portfolio: Any) -> OrderEvent | None:
        """takes a signal determines the size and validates it.
        args.
        signal the signalevent from the strategy.
        portfolio the portfolio instance.
        returns.
        orderevent if successful and valid otherwise none."""
        # . size the order.
        order = self.position_sizer.size_order(signal, portfolio)

        if order is None:
            self.logger.debug(f"Position sizer rejected signal for {signal.symbol}")
            if getattr(self, "audit_logger", None):
                self.audit_logger.log_rejection(
                    signal, "Position Sizer Rejected (e.g. No Cash/Exposure Limit)"
                )
            return None

        # . validate the order.
        for validator in self.validators:
            if not validator.validate_order(order, portfolio):
                v_name = validator.__class__.__name__
                self.logger.warning(f"Order for {order.symbol} rejected by validator: {v_name}")
                if getattr(self, "audit_logger", None):
                    self.audit_logger.log_rejection(
                        signal, f"Validator Rejected: {validator.__class__.__name__}"
                    )
                return None

        self.logger.info(
            f"Order for {order.symbol} sized and validated: {order.direction} {order.quantity}"
        )
        return order
