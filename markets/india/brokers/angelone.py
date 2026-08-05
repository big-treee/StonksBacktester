from typing import Dict

from .base import BaseBrokerCharges


class AngelOneCharges(BaseBrokerCharges):
    def calculate_charges(
        self, product: str, price: float, qty: int, direction: str
    ) -> Dict[str, float]:
        trade_value = price * qty
        is_buy = direction.upper() == "BUY"
        product = product.lower()

        brokerage = 0.0
        stt = 0.0
        exc = 0.0000345 * trade_value
        sebi = 0.000001 * trade_value
        stamp = 0.0

        if product == "cnc":
            brokerage = 0.0
            stt = 0.001 * trade_value
            if is_buy:
                stamp = 0.00015 * trade_value
        elif product == "mis":
            brokerage = min(0.0003 * trade_value, 20.0)
            if not is_buy:
                stt = 0.00025 * trade_value
            if is_buy:
                stamp = 0.00003 * trade_value
        else:
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
