"""indian numbering system formatting helpers lakhs and crores ."""


def format_indian_number(num: float | int, decimals: int = 2) -> str:
    """formats numbers according to the indian numbering system.
    examples.
    . ."""
    if num is None:
        return "0.00"
    try:
        val = float(num)
    except (ValueError, TypeError):
        return str(num)

    is_negative = val < 0
    val = abs(val)

    int_part = int(val)
    frac_part = round(val - int_part, decimals)

    # format fraction string.
    if decimals > 0:
        frac_str = f"{frac_part:.{decimals}f}"[1:]
    else:
        frac_str = ""

    s = str(int_part)
    if len(s) <= 3:
        formatted_int = s
    else:
        last3 = s[-3:]
        other = s[:-3]
        formatted_other = ""
        while len(other) > 2:
            formatted_other = "," + other[-2:] + formatted_other
            other = other[:-2]
        formatted_int = other + formatted_other + "," + last3

    res = formatted_int + frac_str
    return f"-{res}" if is_negative else res


def format_indian_currency(amount: float | int, decimals: int = 2) -> str:
    """formats an amount in inr with indian comma placement and symbol."""
    return f"₹{format_indian_number(amount, decimals)}"
