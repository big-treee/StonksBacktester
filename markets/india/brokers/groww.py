from typing import Dict

from .base import BaseBrokerCharges


class GrowwCharges(BaseBrokerCharges):
    def calculate_charges(
        self, product: str, price: float, qty: int, direction: str
    ) -> Dict[str, float]:
        trade_value = price * qty
        is_buy = direction.upper() == "BUY"
        product = product.lower()

        brokerage = min(0.0005 * trade_value, 20.0)  # groww charges max for equity delivery too.
        stt = 0.0
        exc = 0.0000345 * trade_value
        sebi = 0.000001 * trade_value
        stamp = 0.0

        if product == "cnc":
            stt = 0.001 * trade_value
            if is_buy:
                stamp = 0.00015 * trade_value
        elif product == "mis":
            if not is_buy:
                stt = 0.00025 * trade_value
            if is_buy:
                stamp = 0.00003 * trade_value
        else:  # f o.
            brokerage = 20.0

        gst = 0.18 * (brokerage + exc + sebi)
        total = brokerage + stt + exc + sebi + stamp + gst

        return {
            "brokerage": float(brokerage),
            "stt": float(stt),
            "exchange_txn": float(exc),
            "sebi": float(sebi),
            "stamp_duty": float(stamp),
            "gst": float(gst),
            "total": float(total),
        }
