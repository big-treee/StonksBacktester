from abc import ABC, abstractmethod
from typing import Dict


class BaseBrokerCharges(ABC):
    """abstract base class for calculating broker specific and regulatory charges.
    returns a dictionary of detailed charges for a given transaction."""

    @abstractmethod
    def calculate_charges(
        self, product: str, price: float, qty: int, direction: str
    ) -> Dict[str, float]:
        """calculates all charges for a specific transaction.
        args.
        product str the product type cnc mis futures options.
        price float execution price.
        qty int quantity of shares contracts.
        direction str buy or sell.
        returns.
        dict str float detailed breakdown including brokerage stt.
        exchange txn sebi stamp duty gst total."""
        pass
