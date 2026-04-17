from collections.abc import Iterable

from app.models.expiration import ExpirationRecord
from app.models.expiration import RawExpirationFinding
from app.parsers.text_extractor import extract_text
from app.services.document_intelligence import (
    DocumentIntelligenceProvider,
    create_document_intelligence_provider,
)
from app.services.excel_service import build_expiration_workbook
from app.utils.dates import normalize_date
from app.utils.settings import get_settings


def get_document_intelligence_provider() -> DocumentIntelligenceProvider:
    return create_document_intelligence_provider(settings=get_settings())


def analyze_ewa_file(
    filename: str,
    payload: bytes,
    provider: DocumentIntelligenceProvider | None = None,
) -> bytes:
    content = extract_text(filename, payload)
    records = build_expiration_records(content, provider or get_document_intelligence_provider())
    return build_expiration_workbook(records)


def build_expiration_records(
    text: str,
    provider: DocumentIntelligenceProvider,
) -> list[ExpirationRecord]:
    raw_items = provider.extract_expirations(text)
    findings = _coerce_raw_findings(raw_items)
    deduplicated: list[ExpirationRecord] = []
    seen: set[tuple[str, str]] = set()

    for finding in findings:
        normalized = normalize_date(finding.raw_date)
        if normalized is None:
            continue

        key = (finding.name, normalized.isoformat())
        if key in seen:
            continue

        seen.add(key)
        deduplicated.append(
            ExpirationRecord(
                name=finding.name,
                expiration_date=normalized.isoformat(),
            )
        )

    return deduplicated


def _coerce_raw_findings(raw_items: Iterable[dict[str, str]]) -> list[RawExpirationFinding]:
    findings: list[RawExpirationFinding] = []

    for item in raw_items:
        name = item.get("nombre", "").strip()
        raw_date = item.get("fecha", "").strip()
        if not name or not raw_date:
            continue

        findings.append(RawExpirationFinding(name=name, raw_date=raw_date))

    return findings
