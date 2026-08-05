import datetime

from markets.india.calendar import TradingCalendar
from markets.india.sessions import SessionEngine, SessionType


def test_is_weekend():
    # is a saturday.
    assert TradingCalendar.is_weekend(datetime.date(2024, 1, 6))
    # is a sunday.
    assert TradingCalendar.is_weekend(datetime.date(2024, 1, 7))
    # is a monday.
    assert not TradingCalendar.is_weekend(datetime.date(2024, 1, 8))


def test_is_holiday():
    # republic day.
    assert TradingCalendar.is_holiday(datetime.date(2024, 1, 26))
    # random normal day.
    assert not TradingCalendar.is_holiday(datetime.date(2024, 1, 10))


def test_is_market_open():
    # normal monday.
    assert TradingCalendar.is_market_open(datetime.date(2024, 1, 8))
    # republic day friday.
    assert not TradingCalendar.is_market_open(datetime.date(2024, 1, 26))
    # saturday.
    assert not TradingCalendar.is_market_open(datetime.date(2024, 1, 6))


def test_muhurat_trading_weekend():
    # diwali was on nov sunday.
    diwali_2023 = datetime.date(2023, 11, 12)
    assert TradingCalendar.is_weekend(diwali_2023)
    # but it is a muhurat date so market should be open.
    assert TradingCalendar.is_market_open(diwali_2023)


def test_next_previous_trading_day():
    # friday.
    friday = datetime.date(2024, 1, 5)
    monday = TradingCalendar.next_trading_day(friday)
    assert monday == datetime.date(2024, 1, 8)
    assert TradingCalendar.previous_trading_day(monday) == friday

    # across a holiday republic day is friday.
    thursday = datetime.date(2024, 1, 25)
    monday_after = TradingCalendar.next_trading_day(thursday)
    assert monday_after == datetime.date(2024, 1, 29)


def test_trading_days_between():
    # start mon jan end mon jan inclusive end exclusive start.
    # days weekend days.
    start = datetime.date(2024, 1, 8)
    end = datetime.date(2024, 1, 15)
    assert TradingCalendar.trading_days_between(start, end) == 5


def test_session_engine():
    # normal day.
    normal_day = datetime.date(2024, 1, 8)

    # closed.
    assert (
        SessionEngine.get_session_for_time(
            datetime.datetime.combine(normal_day, datetime.time(8, 30))
        )
        == SessionType.CLOSED
    )

    # pre open.
    assert (
        SessionEngine.get_session_for_time(
            datetime.datetime.combine(normal_day, datetime.time(9, 10))
        )
        == SessionType.PRE_OPEN
    )

    # normal.
    assert (
        SessionEngine.get_session_for_time(
            datetime.datetime.combine(normal_day, datetime.time(10, 30))
        )
        == SessionType.NORMAL
    )

    # closing.
    assert (
        SessionEngine.get_session_for_time(
            datetime.datetime.combine(normal_day, datetime.time(15, 50))
        )
        == SessionType.CLOSING
    )

    # closed.
    assert (
        SessionEngine.get_session_for_time(
            datetime.datetime.combine(normal_day, datetime.time(16, 15))
        )
        == SessionType.CLOSED
    )


def test_session_engine_muhurat():
    # diwali sunday.
    diwali = datetime.date(2023, 11, 12)

    # closed morning is closed.
    assert (
        SessionEngine.get_session_for_time(datetime.datetime.combine(diwali, datetime.time(10, 30)))
        == SessionType.CLOSED
    )

    # pre open.
    assert (
        SessionEngine.get_session_for_time(datetime.datetime.combine(diwali, datetime.time(18, 10)))
        == SessionType.PRE_OPEN
    )

    # muhurat.
    assert (
        SessionEngine.get_session_for_time(datetime.datetime.combine(diwali, datetime.time(18, 30)))
        == SessionType.MUHURAT
    )

    # closing.
    assert (
        SessionEngine.get_session_for_time(datetime.datetime.combine(diwali, datetime.time(19, 25)))
        == SessionType.CLOSING
    )
