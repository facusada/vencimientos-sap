from dataclasses import dataclass
from datetime import date


@dataclass(slots=True)
class RawExpirationFinding:
    name: str
    raw_date: str


@dataclass(slots=True)
class ExpirationRecord:
    name: str
    expiration_date: str


@dataclass(slots=True)
class ParsedExpiration:
    name: str
    expiration_date: date
