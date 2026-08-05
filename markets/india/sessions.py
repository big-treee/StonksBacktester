import datetime
from enum import Enum

from markets.india.calendar import MUHURAT_DATES, TradingCalendar


class SessionType(Enum):
    CLOSED = "CLOSED"
    PRE_OPEN = "PRE_OPEN"
    NORMAL = "NORMAL"
    CLOSING = "CLOSING"
    MUHURAT = "MUHURAT"


class SessionEngine:
    """determines the intraday session state for the nse market."""

    @classmethod
    def get_session_for_time(cls, dt: datetime.datetime) -> SessionType:
        """given a datetime assumed to be in ist if tz naive or properly localized.
        returns the active trading session."""
        # convert to local time components.
        date_obj = dt.date()
        time_obj = dt.time()

        if not TradingCalendar.is_market_open(date_obj):
            return SessionType.CLOSED

        # check for muhurat trading.
        if date_obj in MUHURAT_DATES:
            # typically to.
            if datetime.time(18, 0) <= time_obj <= datetime.time(18, 14):
                return SessionType.PRE_OPEN
            elif datetime.time(18, 15) <= time_obj <= datetime.time(19, 15):
                return SessionType.MUHURAT
            elif datetime.time(19, 20) <= time_obj <= datetime.time(19, 30):
                return SessionType.CLOSING
            else:
                return SessionType.CLOSED

        # regular trading day.
        if datetime.time(9, 0) <= time_obj < datetime.time(9, 15):
            return SessionType.PRE_OPEN
        elif datetime.time(9, 15) <= time_obj <= datetime.time(15, 30):
            return SessionType.NORMAL
        elif datetime.time(15, 40) <= time_obj <= datetime.time(16, 0):
            return SessionType.CLOSING

        return SessionType.CLOSED
