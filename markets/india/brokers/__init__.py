from .angelone import AngelOneCharges
from .base import BaseBrokerCharges
from .groww import GrowwCharges
from .upstox import UpstoxCharges
from .zerodha import ZerodhaCharges


def get_broker_charges(broker_name: str) -> BaseBrokerCharges:
    """factory method to retrieve the appropriate broker charges calculator."""
    broker_name = broker_name.lower().strip()
    if broker_name == "zerodha":
        return ZerodhaCharges()
    elif broker_name == "upstox":
        return UpstoxCharges()
    elif broker_name == "groww":
        return GrowwCharges()
    elif broker_name == "angelone":
        return AngelOneCharges()
    # provide default fallback.
    return ZerodhaCharges()
