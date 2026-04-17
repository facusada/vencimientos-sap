from app.services.document_intelligence import DocumentIntelligenceProvider
from app.services.ewa_analysis_service import build_expiration_records


class StubProvider(DocumentIntelligenceProvider):
    def extract_expirations(self, text: str) -> list[dict[str, str]]:
        assert "supported until 02.2027" in text
        return [
            {"nombre": "SAP Product Version", "fecha": "02.2027"},
            {"nombre": "SAP Product Version", "fecha": "02.2027"},
            {"nombre": "Kernel", "fecha": "2026-12-31"},
            {"nombre": "Broken", "fecha": "2026-99-99"},
        ]


def test_build_expiration_records_normalizes_and_deduplicates():
    provider = StubProvider()

    result = build_expiration_records(
        "SAP Product Version is supported until 02.2027. Kernel expires on 2026-12-31.",
        provider,
    )

    assert [(item.name, item.expiration_date) for item in result] == [
        ("SAP Product Version", "2027-02-28"),
        ("Kernel", "2026-12-31"),
    ]
