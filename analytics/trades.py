from typing import Any, Dict, List

from core.events import FillEvent


class TradeTracker:
    """passively listens to fillevents to reconstruct round trip trades using fifo matching."""

    def __init__(self):
        self.open_positions: Dict[str, List[Dict[str, Any]]] = {}
        self.closed_trades: List[Dict[str, Any]] = []

    def process_fill(self, fill: FillEvent):
        symbol = fill.symbol
        if symbol not in self.open_positions:
            self.open_positions[symbol] = []

        fill_qty = fill.quantity
        fill_dir = 1 if fill.direction == "BUY" else -1
        fill_price = fill.fill_cost
        fill_time = fill.timeindex
        fill_comm = fill.commission or 0.0
        fill_charges = {
            "brokerage": getattr(fill, "brokerage", 0.0),
            "stt": getattr(fill, "stt", 0.0),
            "gst": getattr(fill, "gst", 0.0),
            "exchange_charges": getattr(fill, "exchange_charges", 0.0),
            "stamp_duty": getattr(fill, "stamp_duty", 0.0),
            "sebi_fees": getattr(fill, "sebi_fees", 0.0),
        }

        open_list = self.open_positions[symbol]

        # if no open positions or adding to same direction.
        if not open_list or open_list[0]["direction"] == fill_dir:
            open_list.append(
                {
                    "datetime": fill_time,
                    "price": fill_price,
                    "quantity": fill_qty,
                    "direction": fill_dir,
                    "commission": fill_comm,
                    "charges": fill_charges,
                }
            )
            return

        # closing an existing position fifo matching.
        remaining_qty = fill_qty
        commission_pool = fill_comm
        charges_pool = dict(fill_charges)

        while remaining_qty > 0 and open_list:
            open_leg = open_list[0]
            close_qty = min(open_leg["quantity"], remaining_qty)

            # apportion proportional to size.
            ratio = close_qty / remaining_qty
            leg_comm = commission_pool * ratio
            commission_pool -= leg_comm

            leg_charges = {k: v * ratio for k, v in charges_pool.items()}
            for k in charges_pool:
                charges_pool[k] -= leg_charges[k]

            open_ratio = close_qty / open_leg["quantity"]
            open_leg_comm = open_leg["commission"] * open_ratio
            open_leg["commission"] -= open_leg_comm

            open_leg_charges = {k: v * open_ratio for k, v in open_leg["charges"].items()}
            for k in open_leg["charges"]:
                open_leg["charges"][k] -= open_leg_charges[k]

            total_comm = leg_comm + open_leg_comm
            total_charges = {k: leg_charges[k] + open_leg_charges[k] for k in leg_charges}

            # pnl calculation.
            if open_leg["direction"] == 1:  # long.
                gross_pnl = (fill_price - open_leg["price"]) * close_qty
                ret = (fill_price - open_leg["price"]) / open_leg["price"]
            else:  # short.
                gross_pnl = (open_leg["price"] - fill_price) * close_qty
                ret = (open_leg["price"] - fill_price) / open_leg["price"]

            pnl = gross_pnl - total_comm

            from markets.india.calendar import TradingCalendar

            trade = {
                "symbol": symbol,
                "entry_date": open_leg["datetime"],
                "exit_date": fill_time,
                "direction": "LONG" if open_leg["direction"] == 1 else "SHORT",
                "quantity": close_qty,
                "entry_price": open_leg["price"],
                "exit_price": fill_price,
                "gross_pnl": gross_pnl,
                "pnl": pnl,
                "return": ret,
                "commission": total_comm,
                "holding_period": TradingCalendar.trading_days_between(
                    open_leg["datetime"].date(), fill_time.date()
                ),
            }
            trade.update(total_charges)  # flattens brokerage stt etc. into the trade dict.

            self.closed_trades.append(trade)

            remaining_qty -= close_qty
            open_leg["quantity"] -= close_qty

            if open_leg["quantity"] == 0:
                open_list.pop(0)

        # if there s remaining quantity it s a new position in the opposite direction.
        if remaining_qty > 0:
            open_list.append(
                {
                    "datetime": fill_time,
                    "price": fill_price,
                    "quantity": remaining_qty,
                    "direction": fill_dir,
                    "commission": commission_pool,
                    "charges": charges_pool,
                }
            )
