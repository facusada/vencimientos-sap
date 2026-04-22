import calendar
from datetime import date, datetime


SUPPORTED_DATE_FORMATS = ("%Y-%m-%d", "%Y/%m/%d", "%d.%m.%Y")
MONTH_YEAR_FORMAT = "%m.%Y"


def normalize_date(raw_value: str) -> date | None:
    cleaned = raw_value.strip()
    if not cleaned:
        return None

    for date_format in SUPPORTED_DATE_FORMATS:
        try:
            return datetime.strptime(cleaned, date_format).date()
        except ValueError:
            continue

    try:
        parsed = datetime.strptime(cleaned, MONTH_YEAR_FORMAT)
    except ValueError:
        return None

    last_day = calendar.monthrange(parsed.year, parsed.month)[1]
    return date(parsed.year, parsed.month, last_day)
