"""charge and taxation models for the indian market."""


def calculate_stt(trade_value: float, is_delivery: bool = True) -> float:
    """calculates securities transaction tax stt .
    equity delivery . on buy and sell.
    equity intraday . on sell side only."""
    if is_delivery:
        return trade_value * 0.001
    return trade_value * 0.00025


def calculate_exchange_tx_charge(trade_value: float) -> float:
    """calculates nse bse exchange transaction charges.
    approx . for nse."""
    return trade_value * 0.0000345


def calculate_stamp_duty(trade_value: float, is_buy: bool) -> float:
    """calculates stamp duty only on buy .
    equity delivery ."""
    if is_buy:
        return trade_value * 0.00015
    return 0.0
