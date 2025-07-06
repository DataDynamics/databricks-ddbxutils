from datetime import datetime

from dateutil.relativedelta import relativedelta


def add_days(date_string: str, date_format: str, default_value: str, days: int = 0) -> str:
    return add_datetime(date_string, date_format, default_value, days=days)


def add_datetime(date_string: str, date_format: str, default_value: str,
                 years: int = 0, months: int = 0, days: int = 0, leapdays: int = 0, weeks: int = 0,
                 hours: int = 0, minutes: int = 0, seconds: int = 0, microseconds: int = 0) -> str:
    if (date_string is None or date_string.strip() == '' or
            date_format is None or date_format.strip() == ''):
        return default_value

    value = default_value
    try:
        # datetime.delta 는 months 가 불가능하여 dateutil.relativedelta 로 변경
        delta = _get_delta(years=years, months=months, days=days, leapdays=leapdays, weeks=weeks,
                           hours=hours, minutes=minutes, seconds=seconds, microseconds=microseconds)
        value = datetime.strftime(datetime.strptime(date_string, date_format) + delta, date_format)
    except ValueError as e:
        print(e)
    finally:
        return value


def _get_delta(years: int = 0, months: int = 0, days: int = 0, leapdays: int = 0, weeks: int = 0,
               hours: int = 0, minutes: int = 0, seconds: int = 0, microseconds: int = 0):
    return relativedelta(years=years, months=months, days=days, leapdays=leapdays, weeks=weeks,
                         hours=hours, minutes=minutes, seconds=seconds, microseconds=microseconds)
