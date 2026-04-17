from datetime import date

import pytest

from app.utils.dates import normalize_date


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        ("2026-12-31", date(2026, 12, 31)),
        ("2026/12/31", date(2026, 12, 31)),
        ("31.12.2026", date(2026, 12, 31)),
        ("02.2027", date(2027, 2, 28)),
    ],
)
def test_normalize_date_accepts_supported_formats(raw_value, expected):
    assert normalize_date(raw_value) == expected


@pytest.mark.parametrize("raw_value", ["2026-13-40", "31.02.2026", "not-a-date", ""])
def test_normalize_date_rejects_invalid_dates(raw_value):
    assert normalize_date(raw_value) is None
