import re

from app.models.expiration import ParsedExpiration
from app.utils.dates import normalize_date


PATTERNS = (
    re.compile(
        r"(?P<name>.+?)\s+expiry:\s*(?P<date>\d{4}-\d{2}-\d{2})",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?P<name>.+?)\s+valid\s+until\s+(?P<date>\d{2}\.\d{2}\.\d{4})",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?P<name>.+?)\s+maintenance\s+ends\s+on\s+(?P<date>\d{4}/\d{2}/\d{2})",
        re.IGNORECASE,
    ),
)


def parse_expirations_from_text(content: str) -> list[ParsedExpiration]:
    parsed: list[ParsedExpiration] = []

    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        for pattern in PATTERNS:
            match = pattern.search(line)
            if not match:
                continue

            normalized = normalize_date(match.group("date"))
            if normalized is None:
                break

            parsed.append(
                ParsedExpiration(
                    name=match.group("name").strip(),
                    expiration_date=normalized,
                )
            )
            break

    return parsed
