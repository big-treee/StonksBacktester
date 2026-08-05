"""symbol validation and formatting for the indian market."""


def format_yahoo_symbol(symbol: str, exchange: str = "NSE") -> str:
    """formats a base symbol into a yahoo finance compatible symbol.
    e.g. reliance reliance.ns for nse reliance.bo for bse."""
    if symbol.endswith(".NS") or symbol.endswith(".BO"):
        return symbol

    if exchange.upper() == "NSE":
        return f"{symbol}.NS"
    elif exchange.upper() == "BSE":
        return f"{symbol}.BO"

    return symbol
