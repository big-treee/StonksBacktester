import datetime

# hardcoded nse holidays for demonstration.
# in production this should ideally be driven by a database or api.
# but for now we provide a robust static list for a few years.
NSE_HOLIDAYS = {
    datetime.date(2023, 1, 26),  # republic day.
    datetime.date(2023, 3, 7),  # holi.
    datetime.date(2023, 3, 30),  # ram navami.
    datetime.date(2023, 4, 4),  # mahavir jayanti.
    datetime.date(2023, 4, 7),  # good friday.
    datetime.date(2023, 4, 14),  # dr. baba saheb ambedkar jayanti.
    datetime.date(2023, 5, 1),  # maharashtra day.
    datetime.date(2023, 6, 29),  # bakri id.
    datetime.date(2023, 8, 15),  # independence day.
    datetime.date(2023, 9, 19),  # ganesh chaturthi.
    datetime.date(2023, 10, 2),  # mahatma gandhi jayanti.
    datetime.date(2023, 10, 24),  # dussehra.
    datetime.date(2023, 11, 14),  # diwali balipratipada.
    datetime.date(2023, 11, 27),  # gurunanak jayanti.
    datetime.date(2023, 12, 25),  # christmas.
    datetime.date(2024, 1, 22),  # ayodhya ram mandir inauguration special holiday.
    datetime.date(2024, 1, 26),  # republic day.
    datetime.date(2024, 3, 8),  # mahashivratri.
    datetime.date(2024, 3, 25),  # holi.
    datetime.date(2024, 3, 29),  # good friday.
    datetime.date(2024, 4, 11),  # id ul fitr.
    datetime.date(2024, 4, 17),  # ram navami.
    datetime.date(2024, 5, 1),  # maharashtra day.
    datetime.date(2024, 6, 17),  # bakri id.
    datetime.date(2024, 7, 17),  # muharram.
    datetime.date(2024, 8, 15),  # independence day.
    datetime.date(2024, 10, 2),  # mahatma gandhi jayanti.
    datetime.date(2024, 11, 1),  # diwali.
    datetime.date(2024, 11, 15),  # gurunanak jayanti.
    datetime.date(2024, 12, 25),  # christmas.
}

# special muhurat trading dates usually evening session on diwali.
# these override weekends if they fall on one.
MUHURAT_DATES = {
    datetime.date(2023, 11, 12),
    datetime.date(2024, 11, 1),
}


class TradingCalendar:
    """provides trading calendar utilities for the indian market nse ."""

    @classmethod
    def is_weekend(cls, date_obj: datetime.date) -> bool:
        """returns true if the date is a saturday or sunday."""
        return date_obj.weekday() >= 5

    @classmethod
    def is_holiday(cls, date_obj: datetime.date) -> bool:
        """returns true if the date is an official nse holiday."""
        return date_obj in NSE_HOLIDAYS

    @classmethod
    def is_market_open(cls, date_obj: datetime.date) -> bool:
        """returns true if the market is open on the given date.
        takes into account weekends regular holidays and special muhurat trading dates."""
        if date_obj in MUHURAT_DATES:
            return True
        if cls.is_weekend(date_obj):
            return False
        if cls.is_holiday(date_obj):
            return False
        return True

    @classmethod
    def next_trading_day(cls, date_obj: datetime.date) -> datetime.date:
        """returns the next valid trading day."""
        next_day = date_obj + datetime.timedelta(days=1)
        while not cls.is_market_open(next_day):
            next_day += datetime.timedelta(days=1)
        return next_day

    @classmethod
    def previous_trading_day(cls, date_obj: datetime.date) -> datetime.date:
        """returns the previous valid trading day."""
        prev_day = date_obj - datetime.timedelta(days=1)
        while not cls.is_market_open(prev_day):
            prev_day -= datetime.timedelta(days=1)
        return prev_day

    @classmethod
    def trading_days_between(cls, start_date: datetime.date, end_date: datetime.date) -> int:
        """calculates the number of active trading days between start date and end date inclusive of end ."""
        if start_date > end_date:
            return 0

        days = 0
        current = start_date
        # exclusive of start inclusive of end to match holding period logic.
        # i.e. bought and sold on same day days. bought monday sold tuesday day.
        while current < end_date:
            current += datetime.timedelta(days=1)
            if cls.is_market_open(current):
                days += 1

        return days
