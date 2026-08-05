"""holiday definitions for the indian market nse bse ."""

import datetime


def get_nse_holidays(year: int) -> list[datetime.date]:
    """returns a list of nse trading holidays for a given year.
    stub implementation. in a production system this would load from a database or api."""
    # common holidays stubs.
    holidays = [
        datetime.date(year, 1, 26),  # republic day.
        datetime.date(year, 8, 15),  # independence day.
        datetime.date(year, 10, 2),  # mahatma gandhi jayanti.
        datetime.date(year, 12, 25),  # christmas.
    ]
    return holidays
